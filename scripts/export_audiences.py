#!/usr/bin/env python3
"""Export attached canonical contacts to audience CSVs.

Two outputs (to the git-ignored exports/audiences/):
  - meta_custom_audience_<...>.csv  : SHA-256 hashed email + phone, Meta Custom/
                                       Lookalike Audience format. Safe if leaked.
  - whatsapp_recipients_<...>.csv   : name + E.164 phone + building + role +
                                       consent_status, for WhatsApp Business.
                                       Contains REAL phone numbers (PII).

Includes every contact attached to a building EXCEPT anyone on the active
outreach_suppression_list. Each row carries its consent_status so you send
responsibly. This script only writes FILES — it sends nothing.

  Dry run:  python3 scripts/export_audiences.py [--building NAME] [--role owner]
  Write:    python3 scripts/export_audiences.py --apply [--building NAME] [--role owner]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
OUT_DIR = PROJECT_ROOT / "exports" / "audiences"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user, pw, db = read_env_value("POSTGRES_USER"), read_env_value("POSTGRES_PASSWORD"), read_env_value("POSTGRES_DB")
    if not user or not pw or not db:
        return 1, "Missing POSTGRES_* in docker/.env."
    cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={pw}", "realdeal-postgres",
           "psql", "-U", user, "-d", db, "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1"]
    res = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return res.returncode, (res.stderr.strip() if res.returncode else res.stdout.rstrip("\n"))


def e164_in(phone: str) -> str:
    """Normalize an Indian-leaning phone to E.164 (+91XXXXXXXXXX). '' if unusable."""
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("00"):
        d = d[2:]
    if len(d) == 10:
        d = "91" + d
    elif len(d) == 11 and d.startswith("0"):
        d = "91" + d[1:]
    if len(d) != 12 or not d.startswith("91"):
        return ""  # leave malformed numbers out rather than guess
    return "+" + d


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else ""


def fetch_rows(building: str | None, role: str | None, limit: int | None) -> list[dict]:
    where = ["r.raw_context->>'bulk_attach' = 'true'", "r.relationship_status = 'active'"]
    if building:
        where.append(f"b.name = '{building.replace(chr(39), chr(39) * 2)}'")
    if role:
        where.append(f"r.relationship_type = '{role.replace(chr(39), chr(39) * 2)}'")
    where.append(
        "NOT EXISTS (SELECT 1 FROM outreach_suppression_list s "
        "WHERE s.contact_id = c.id AND s.status = 'active')")
    limit_sql = f"LIMIT {limit}" if limit else ""
    sql = f"""
SELECT DISTINCT ON (c.id)
  c.id::text,
  c.full_name,
  COALESCE((SELECT coalesce(nullif(m.normalized_value,''), m.raw_value) FROM contact_methods m
            WHERE m.contact_id = c.id AND m.method_type IN ('mobile','phone')
            ORDER BY m.is_primary DESC, (m.method_type='mobile') DESC LIMIT 1), ''),
  COALESCE((SELECT coalesce(nullif(m.normalized_value,''), m.raw_value) FROM contact_methods m
            WHERE m.contact_id = c.id AND m.method_type = 'email'
            ORDER BY m.is_primary DESC LIMIT 1), ''),
  COALESCE(b.name, ''),
  r.relationship_type,
  COALESCE((SELECT cp.permission_status FROM channel_permissions cp
            WHERE cp.contact_id = c.id AND cp.channel = 'whatsapp' LIMIT 1), 'not_set')
FROM contacts c
JOIN contact_property_relationships r ON r.contact_id = c.id
LEFT JOIN buildings b ON b.id = r.building_id
WHERE {' AND '.join(where)} AND coalesce(c.is_test,false) = false
ORDER BY c.id
{limit_sql};
"""
    code, out = run_psql(sql)
    if code != 0:
        raise RuntimeError(out)
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = (line.split("\t") + [""] * 7)[:7]
        rows.append({"id": parts[0], "name": parts[1], "phone": parts[2],
                     "email": parts[3], "building": parts[4], "role": parts[5], "consent": parts[6]})
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Export attached contacts to Meta + WhatsApp audience CSVs.")
    p.add_argument("--building")
    p.add_argument("--role")
    p.add_argument("--limit", type=int)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    rows = fetch_rows(args.building, args.role, args.limit)
    with_phone = [r for r in rows if e164_in(r["phone"])]
    with_email = [r for r in rows if r["email"]]
    scope = (args.building or "all-buildings").lower().replace(" ", "-")
    if args.role:
        scope += f"-{args.role}"

    print(f"Audience export — scope: {scope}")
    print(f"  contacts (attached, not suppressed): {len(rows)}")
    print(f"  with usable E.164 phone:  {len(with_phone)}  -> WhatsApp CSV")
    print(f"  with email:               {len(with_email)}")
    print(f"  Meta hashed rows (phone OR email): {len({r['id'] for r in rows if e164_in(r['phone']) or r['email']})}")

    if not args.apply:
        print("  Dry run — no files written. Add --apply to write CSVs to exports/audiences/.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = OUT_DIR / f"meta_custom_audience_{scope}.csv"
    wa_path = OUT_DIR / f"whatsapp_recipients_{scope}.csv"

    # Meta: pre-hashed (SHA-256) email + phone. Meta hashes raw on upload anyway.
    with meta_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email", "phone"])
        for r in rows:
            ph = e164_in(r["phone"])
            email_norm = r["email"].strip().lower()
            phone_norm = ph.lstrip("+") if ph else ""  # E.164 digits, no '+'
            if email_norm or phone_norm:
                w.writerow([sha256(email_norm), sha256(phone_norm)])

    # WhatsApp: real E.164 numbers for sending — PII, stays in git-ignored exports/.
    with wa_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "phone_e164", "building", "role", "consent_status"])
        for r in with_phone:
            w.writerow([r["name"], e164_in(r["phone"]), r["building"], r["role"], r["consent"]])

    print(f"  wrote {meta_path.relative_to(PROJECT_ROOT)}")
    print(f"  wrote {wa_path.relative_to(PROJECT_ROOT)} ({len(with_phone)} real numbers)")
    print("  NOTE: WhatsApp messaging requires recipient opt-in; consent_status flags who is cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
