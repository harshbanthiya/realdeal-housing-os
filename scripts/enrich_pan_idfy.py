#!/usr/bin/env python3
"""
IDfy PAN enrichment + name comparison.

Usage:
  # Dry run — shows what would be sent (no API calls, no DB writes)
  python3 scripts/enrich_pan_idfy.py --limit 20

  # Real test run (hits IDfy, writes to idfy_pan_results)
  python3 scripts/enrich_pan_idfy.py --limit 20 --apply

  # Full production run
  python3 scripts/enrich_pan_idfy.py --apply

Credentials: set IDFY_ACCOUNT_ID and IDFY_API_KEY in docker/.env
"""

import argparse, os, sys, uuid, time
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

# ── db connection ─────────────────────────────────────────────────────────────
def get_conn():
    import psycopg2
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

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",  type=int, default=None, help="Max PANs to process")
    ap.add_argument("--apply",  action="store_true",    help="Actually call IDfy + write DB")
    ap.add_argument("--skip-name-match", action="store_true", help="Skip name comparison step")
    args = ap.parse_args()

    is_dry = not args.apply
    limit  = args.limit if args.limit else (DRY_LIMIT if is_dry else None)

    account_id, api_key = get_idfy_creds()
    if not is_dry and (account_id in ("", "change_me") or api_key in ("", "change_me")):
        print("ERROR: Set IDFY_ACCOUNT_ID and IDFY_API_KEY in docker/.env first.")
        sys.exit(1)

    conn = get_conn()
    cur  = conn.cursor()

    # apply schema if tables don't exist yet
    cur.execute("SELECT to_regclass('idfy_pan_results')")
    if cur.fetchone()[0] is None:
        schema_sql = (ROOT / "schemas" / "054_idfy_pan_enrichment.sql").read_text()
        cur.execute(schema_sql)
        conn.commit()
        print("✓ Schema 054 applied")

    # fetch queue — individuals first (4th char = P), companies sorted after
    cur.execute(f"""
        SELECT party_pan, igr_name, party_type
        FROM vw_idfy_pan_queue
        ORDER BY (substring(party_pan, 4, 1) != 'P'), party_pan
        {'LIMIT %s' if limit else ''}
    """, [limit] if limit else [])
    queue = cur.fetchall()

    print(f"{'[DRY RUN] ' if is_dry else ''}Queue: {len(queue)} PANs to verify")
    if not queue:
        print("Nothing to do."); conn.close(); return

    # preflight: probe first PAN before burning the full queue
    if not is_dry:
        probe_pan = queue[0][0]
        print(f"Preflight check on {probe_pan} …", end=" ", flush=True)
        probe = verify_pan(probe_pan, account_id, api_key)
        probe_status = probe.get("result", {}).get("source_output", {}).get("status") or probe.get("status", "error")
        print(probe_status)
        time.sleep(SLEEP_MS / 1000)
        if probe_status in ("source_down",):
            print("Govt source is down — aborting to save credits. Try again later.")
            conn.close(); return

    pan_results = []   # (pan, idfy_name, status) for name match phase
    credits_total = 0

    for i, (pan, igr_name, party_type) in enumerate(queue, 1):
        print(f"  [{i}/{len(queue)}] {pan}  igr_name={igr_name!r}", end="")
        credits_total += 3

        if is_dry:
            print("  → [dry, no call]")
            continue

        resp = verify_pan(pan, account_id, api_key)
        time.sleep(SLEEP_MS / 1000)

        source   = resp.get("result", {}).get("source_output", resp.get("result", {}))
        api_stat = resp.get("status", "error")          # 'completed' | 'failed'
        status   = source.get("status") or ("id_found" if api_stat == "completed" else "error")
        idfy_name = source.get("full_name") or source.get("name_on_card")
        pan_type  = source.get("category")
        pan_status = source.get("pan_status")
        error_msg = resp.get("error") or (None if api_stat == "completed" else str(resp))

        print(f"  → {status}  name={idfy_name!r}")

        cur.execute("""
            INSERT INTO idfy_pan_results
                (party_pan, idfy_status, idfy_name, idfy_pan_type, idfy_pan_status,
                 idfy_raw_response, error_message, phase)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (party_pan) DO UPDATE SET
                idfy_status        = EXCLUDED.idfy_status,
                idfy_name          = EXCLUDED.idfy_name,
                idfy_pan_type      = EXCLUDED.idfy_pan_type,
                idfy_pan_status    = EXCLUDED.idfy_pan_status,
                idfy_raw_response  = EXCLUDED.idfy_raw_response,
                error_message      = EXCLUDED.error_message,
                fetched_at         = now()
        """, [pan, status, idfy_name, pan_type, pan_status,
              json.dumps(resp), error_msg, PHASE])
        conn.commit()

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
            print(f"  {pan}  {igr_name!r} vs {idfy_name!r}  → {score} ({v})")

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
