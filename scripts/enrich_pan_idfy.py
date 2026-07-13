#!/usr/bin/env python3
"""
IDfy PAN enrichment + name comparison.

Usage:
  # Dry run — shows what would be sent (no API calls, no DB writes)
  python3 scripts/enrich_pan_idfy.py --limit 20

  # Dry run — expiring leases only for priority buildings
  python3 scripts/enrich_pan_idfy.py --expiring-leases \
    --building-name "Kalpataru Radiance" --building-name "Imperial Heights"

  # Real test run (hits IDfy, writes to idfy_pan_results)
  python3 scripts/enrich_pan_idfy.py --limit 20 --apply

  # Real priority run: expiring leases in the next 183 days
  python3 scripts/enrich_pan_idfy.py --apply --expiring-leases \
    --building-name "Kalpataru Radiance" --building-name "Imperial Heights"

  # Full production run
  python3 scripts/enrich_pan_idfy.py --apply

Credentials: set IDFY_ACCOUNT_ID and IDFY_API_KEY in docker/.env
"""

import argparse, os, sys, uuid, time, re
import urllib.request, urllib.error, json
from pathlib import Path

# ── config ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web" / "src"))

IDFY_BASE   = "https://eve.idfy.com/v3"
IDFY_ENDPOINT = "tasks/sync/verify_with_source/ind_pan_plus"  # ind_pan returns 400; ind_pan_plus works
PHASE       = "6.26"
DRY_LIMIT   = 20       # default limit for dry runs
SLEEP_MS    = 500      # ms between calls to avoid rate-limit

# name match verdict thresholds
MATCH_THRESH = 0.80
CLOSE_THRESH = 0.50

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONEISH_KEYS = {
    "mobile", "mobile_number", "mobile_no", "phone", "phone_number", "phone_no",
    "contact", "contact_number", "registered_mobile", "registered_mobile_number",
}
EMAIL_KEYS = {"email", "email_id", "email_address", "registered_email", "registered_email_id"}

# ── db connection ─────────────────────────────────────────────────────────────
def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (list, tuple)):
        return "ARRAY[" + ",".join(sql_literal(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"

def render_sql(sql: str, params: list | tuple | None) -> str:
    if not params:
        return sql
    parts = sql.split("%s")
    if len(parts) - 1 != len(params):
        raise ValueError(f"SQL placeholder count mismatch: {len(parts) - 1} placeholders, {len(params)} params")
    out = [parts[0]]
    for value, part in zip(params, parts[1:]):
        out.append(sql_literal(value))
        out.append(part)
    return "".join(out)

class PsqlCursor:
    def __init__(self):
        self._rows = []
        self.description = None

    def execute(self, sql: str, params: list | tuple | None = None):
        from _db import run_psql
        rendered = render_sql(sql.strip().rstrip(";"), params)
        first = rendered.lstrip().split(None, 1)[0].upper() if rendered.strip() else ""
        if first in {"SELECT", "WITH"}:
            wrapped = f"SELECT COALESCE(json_agg(row_to_json(q))::text, '[]') FROM ({rendered}) q;"
            code, out = run_psql(wrapped)
            if code != 0:
                raise RuntimeError(out)
            rows = json.loads(out or "[]")
            if rows:
                keys = list(rows[0].keys())
                self.description = [(k,) for k in keys]
                self._rows = [tuple(row.get(k) for k in keys) for row in rows]
            else:
                self.description = []
                self._rows = []
        else:
            code, out = run_psql(rendered + ";")
            if code != 0:
                raise RuntimeError(out)
            self.description = None
            self._rows = []

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows

class PsqlConn:
    def cursor(self):
        return PsqlCursor()

    def commit(self):
        return None

    def close(self):
        return None

def get_conn():
    try:
        import psycopg2
    except ModuleNotFoundError:
        return PsqlConn()
    env_file = ROOT / "docker" / ".env"
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    cfg = {
        "host": env.get("POSTGRES_HOST", "localhost"),
        "port": int(env.get("POSTGRES_PORT", 5432)),
        "dbname": env.get("POSTGRES_DB", "realdeal_os"),
        "user":   env.get("POSTGRES_USER", "realdeal_admin"),
        "password": env.get("POSTGRES_PASSWORD", ""),
    }
    return psycopg2.connect(**cfg)

def get_idfy_creds():
    env_file = ROOT / "docker" / ".env"
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    account_id = env.get("IDFY_ACCOUNT_ID") or os.environ.get("IDFY_ACCOUNT_ID", "")
    api_key    = env.get("IDFY_API_KEY")    or os.environ.get("IDFY_API_KEY", "")
    return account_id, api_key

# ── output / data extraction helpers ─────────────────────────────────────────
def mask_pan(pan: str) -> str:
    if pan and re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
        return f"{pan[:5]}****{pan[-1]}"
    return "[PAN_MASKED]"

def norm_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 and digits[0] in "6789" else None

def norm_email(raw: str | None) -> str | None:
    if not raw:
        return None
    m = EMAIL_RE.search(str(raw))
    return m.group(0).lower() if m else None

def walk_json(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            child_path = f"{path}.{k}" if path else str(k)
            yield from walk_json(v, child_path)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk_json(v, f"{path}[{i}]")
    else:
        yield path, value

def extract_contact_details(resp: dict) -> tuple[str | None, str | None, dict]:
    email = None
    phone = None
    found = {"email_fields": [], "phone_fields": [], "masked_or_invalid_phone_fields": []}
    for path, value in walk_json(resp):
        if value is None:
            continue
        key = path.split(".")[-1].split("[")[0].lower()
        text = str(value).strip()
        if not text:
            continue
        maybe_email = norm_email(text) if key in EMAIL_KEYS or "email" in key else None
        if maybe_email:
            email = email or maybe_email
            found["email_fields"].append(path)
        maybe_phone = norm_phone(text) if key in PHONEISH_KEYS or "mobile" in key or "phone" in key else None
        if maybe_phone:
            phone = phone or maybe_phone
            found["phone_fields"].append(path)
        elif key in PHONEISH_KEYS or "mobile" in key or "phone" in key:
            found["masked_or_invalid_phone_fields"].append(path)
    return phone, email, found

# ── IDfy API calls ────────────────────────────────────────────────────────────
def idfy_post(endpoint: str, payload: dict, account_id: str, api_key: str) -> dict:
    url  = f"{IDFY_BASE}/{endpoint}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("account-id",   account_id)
    req.add_header("api-key",      api_key)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"error": str(e), "body": body}
    except Exception as e:
        return {"error": str(e)}

def verify_pan(pan: str, account_id: str, api_key: str) -> dict:
    payload = {
        "task_id":  str(uuid.uuid4()),
        "group_id": str(uuid.uuid4()),
        "data":     {"id_number": pan},
    }
    return idfy_post(IDFY_ENDPOINT, payload, account_id, api_key)

def local_name_score(a: str, b: str) -> float:
    """difflib ratio — no API credits needed for name comparison."""
    import difflib
    return round(difflib.SequenceMatcher(None, a.upper(), b.upper()).ratio(), 4)

# ── helpers ───────────────────────────────────────────────────────────────────
def verdict(score) -> str:
    if score is None: return "unknown"
    if float(score) >= MATCH_THRESH: return "match"
    if float(score) >= CLOSE_THRESH: return "close"
    return "mismatch"

def source_status(resp: dict) -> str:
    source = resp.get("result", {}).get("source_output", resp.get("result", {}))
    api_stat = resp.get("status", "error")
    return source.get("status") or ("id_found" if api_stat == "completed" else "error")

def preflight_should_abort(resp: dict, status: str) -> bool:
    body = json.dumps(resp).lower()
    return bool(resp.get("error") or status in {"source_down", "source_unavailable", "error"} or "source_down" in body)

def ensure_schema(cur, conn):
    schema_sql = (ROOT / "schemas" / "054_idfy_pan_enrichment.sql").read_text()
    cur.execute(schema_sql)
    conn.commit()

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",  type=int, default=None, help="Max PANs to process")
    ap.add_argument("--apply",  action="store_true",    help="Actually call IDfy + write DB")
    ap.add_argument("--skip-name-match", action="store_true", help="Skip name comparison step")
    ap.add_argument("--expiring-leases", action="store_true",
                    help="Queue only parties from expiring tenancy records.")
    ap.add_argument("--building-name", action="append", default=[],
                    help="Exact building name filter for --expiring-leases; repeatable.")
    ap.add_argument("--lease-expiry-days", type=int, default=183,
                    help="Expiring lease window in days from current_date.")
    ap.add_argument("--preflight-only", action="store_true",
                    help="Run only the first API probe; stores the result when --apply is used.")
    args = ap.parse_args()

    is_dry = not args.apply
    limit  = args.limit if args.limit else (DRY_LIMIT if is_dry else None)

    account_id, api_key = get_idfy_creds()
    if not is_dry and (account_id in ("", "change_me") or api_key in ("", "change_me")):
        print("ERROR: Set IDFY_ACCOUNT_ID and IDFY_API_KEY in docker/.env first.")
        sys.exit(1)

    conn = get_conn()
    cur  = conn.cursor()

    ensure_schema(cur, conn)

    if args.expiring_leases:
        building_names = args.building_name or ["Kalpataru Radiance", "Imperial Heights"]
        cur.execute(f"""
            WITH picked AS (
              SELECT DISTINCT ON (p.party_pan)
                  p.party_pan,
                  COALESCE(
                    NULLIF(p.party_name_english, p.party_pan),
                    NULLIF(p.party_name_normalized, p.party_pan),
                    NULLIF(p.party_name_raw, p.party_pan)
                  ) AS igr_name,
                  p.party_type,
                  r.building_name,
                  r.tenancy_end_date
              FROM vw_unit_registration_full_operator r
              JOIN unit_registration_parties p ON p.unit_registration_record_id = r.record_id
              LEFT JOIN idfy_pan_results res ON res.party_pan = p.party_pan
              WHERE r.category = 'tenancy'
                AND r.tenancy_end_date IS NOT NULL
                AND r.tenancy_end_date >= current_date
                AND r.tenancy_end_date <= current_date + (%s::text || ' days')::interval
                AND r.building_name = ANY(%s)
                AND p.party_pan IS NOT NULL
                AND p.party_pan ~ '^[A-Z]{{5}}[0-9]{{4}}[A-Z]{{1}}$'
                AND (res.id IS NULL OR res.idfy_status IN ('source_down', 'error'))
              ORDER BY p.party_pan, r.tenancy_end_date NULLS LAST, p.created_at
            )
            SELECT party_pan, igr_name, party_type
            FROM picked
            ORDER BY (substring(party_pan, 4, 1) != 'P'), tenancy_end_date NULLS LAST, party_pan
            {'LIMIT %s' if limit else ''}
        """, [args.lease_expiry_days, building_names] + ([limit] if limit else []))
    else:
        # fetch queue — individuals first (4th char = P), companies sorted after
        cur.execute(f"""
            SELECT party_pan, igr_name, party_type
            FROM vw_idfy_pan_queue
            ORDER BY (substring(party_pan, 4, 1) != 'P'), party_pan
            {'LIMIT %s' if limit else ''}
        """, [limit] if limit else [])
    queue = cur.fetchall()

    scope = "expiring leases" if args.expiring_leases else "global"
    print(f"{'[DRY RUN] ' if is_dry else ''}Queue ({scope}): {len(queue)} PANs to verify")
    if not queue:
        print("Nothing to do."); conn.close(); return

    pan_results = []   # (pan, idfy_name, status) for name match phase

    def store_response(pan: str, igr_name: str | None, resp: dict) -> tuple[str, str | None]:
        source = resp.get("result", {}).get("source_output", resp.get("result", {}))
        api_stat = resp.get("status", "error")
        status = source.get("status") or ("id_found" if api_stat == "completed" else "error")
        idfy_name = source.get("full_name") or source.get("name_on_card")
        name_on_card = source.get("name_on_card")
        pan_type = source.get("category")
        pan_status = source.get("pan_status")
        phone, email, contact_details = extract_contact_details(resp)
        error_msg = resp.get("error") or (None if api_stat == "completed" else str(resp))

        cur.execute("""
            INSERT INTO idfy_pan_results
                (party_pan, idfy_status, idfy_name, idfy_name_on_card, idfy_pan_type, idfy_pan_status,
                 idfy_phone, idfy_email, idfy_contact_details, idfy_raw_response, error_message, phase)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (party_pan) DO UPDATE SET
                idfy_status          = EXCLUDED.idfy_status,
                idfy_name            = EXCLUDED.idfy_name,
                idfy_name_on_card    = EXCLUDED.idfy_name_on_card,
                idfy_pan_type        = EXCLUDED.idfy_pan_type,
                idfy_pan_status      = EXCLUDED.idfy_pan_status,
                idfy_phone           = EXCLUDED.idfy_phone,
                idfy_email           = EXCLUDED.idfy_email,
                idfy_contact_details = EXCLUDED.idfy_contact_details,
                idfy_raw_response    = EXCLUDED.idfy_raw_response,
                error_message        = EXCLUDED.error_message,
                fetched_at           = now()
        """, [pan, status, idfy_name, name_on_card, pan_type, pan_status,
              phone, email, json.dumps(contact_details), json.dumps(resp), error_msg, PHASE])
        conn.commit()
        return status, idfy_name

    # preflight: probe first PAN before burning the full queue
    completed_pans = set()
    if not is_dry:
        probe_pan, probe_igr_name, _probe_party_type = queue[0]
        print(f"Preflight check on {mask_pan(probe_pan)} …", end=" ", flush=True)
        probe = verify_pan(probe_pan, account_id, api_key)
        probe_status = source_status(probe)
        print(probe_status)
        time.sleep(SLEEP_MS / 1000)
        if preflight_should_abort(probe, probe_status):
            print("IDfy/govt source preflight failed — aborting to save credits. Try again later.")
            conn.close(); return
        stored_status, stored_name = store_response(probe_pan, probe_igr_name, probe)
        completed_pans.add(probe_pan)
        if stored_status == "id_found" and stored_name and probe_igr_name:
            pan_results.append((probe_pan, probe_igr_name, stored_name))
        if args.preflight_only:
            print("\nPreflight-only run complete.")
            conn.close(); return

    credits_total = 3 if completed_pans else 0

    for i, (pan, igr_name, party_type) in enumerate(queue, 1):
        if pan in completed_pans:
            continue
        print(f"  [{i}/{len(queue)}] {mask_pan(pan)}  igr_name={igr_name!r}", end="")

        if is_dry:
            credits_total += 3
            print("  → [dry, no call]")
            continue

        resp = verify_pan(pan, account_id, api_key)
        time.sleep(SLEEP_MS / 1000)
        credits_total += 3

        status, idfy_name = store_response(pan, igr_name, resp)

        print(f"  → {status}  name={idfy_name!r}")
        if preflight_should_abort(resp, status):
            print("  Source/API became unavailable — aborting remaining queue.")
            break

        if status == "id_found" and idfy_name and igr_name:
            pan_results.append((pan, igr_name, idfy_name))

    # ── name match phase (local difflib, 0 credits) ───────────────────────────
    if not args.skip_name_match and not is_dry and pan_results:
        print(f"\nName match phase: {len(pan_results)} pairs (local, 0 credits)")
        for pan, igr_name, idfy_name in pan_results:
            cur.execute("""
                SELECT p.id FROM unit_registration_parties p
                WHERE p.party_pan = %s AND p.party_name_english IS NOT NULL
                LIMIT 1
            """, [pan])
            row = cur.fetchone()
            party_id = row[0] if row else None

            score = local_name_score(igr_name, idfy_name)
            v     = verdict(score)
            print(f"  {mask_pan(pan)}  {igr_name!r} vs {idfy_name!r}  → {score} ({v})")

            cur.execute("""
                INSERT INTO idfy_name_match_results
                    (unit_registration_party_id, party_pan, igr_name, idfy_name,
                     match_score, match_verdict, idfy_raw_response, phase)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, [party_id, pan, igr_name, idfy_name,
                  score, v, json.dumps({"method": "local_difflib"}), PHASE])
            conn.commit()

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\n{'[DRY RUN] ' if is_dry else ''}Done.")
    print(f"  Credits {'would use' if is_dry else 'used'}: ~{credits_total}")

    if not is_dry:
        cur.execute("SELECT * FROM vw_idfy_pan_enrichment_summary")
        row = cur.fetchone()
        if row:
            cols = [d[0] for d in cur.description]
            print("\n  IDfy PAN enrichment summary:")
            for c, v in zip(cols, row): print(f"    {c}: {v}")

    conn.close()

if __name__ == "__main__":
    main()
