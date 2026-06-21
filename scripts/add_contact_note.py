"""Add a manual note to a contact's activity timeline.

Writes one row to contact_activity_events with event_type='note', direction='internal',
channel='cockpit', source='manual_mark'. Dry-run by default; use --apply to write.

  python3 scripts/add_contact_note.py \\
      --contact-id <uuid> \\
      --note "Spoke on phone — interested in 3BHK" \\
      --by operator \\
      [--apply]

Safety rules:
- contact_id validated as UUID before any SQL.
- note stripped to 500 chars, NUL bytes removed.
- by stripped to 100 chars, NUL bytes removed.
- SQL values escaped via lit() — never f-string interpolated raw.
- Dry-run by default; --apply required to write.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def lit(value: str) -> str:
    """Return a safely-quoted SQL string literal (no NUL, single-quotes escaped)."""
    return "'" + value.replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB in docker/.env."
    cmd = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def sanitise(text: str, max_len: int) -> str:
    return text.replace("\0", "").strip()[:max_len]


def probe_sql(contact_id: str) -> str:
    return (
        f"SELECT (c.id IS NOT NULL), mask_name(c.full_name) "
        f"FROM contacts c WHERE c.id = {lit(contact_id)};"
    )


def insert_sql(contact_id: str, note: str, by: str) -> str:
    return f"""
BEGIN;
INSERT INTO contact_activity_events
  (contact_id, channel, event_type, direction, source, safe_summary, created_by)
VALUES
  ({lit(contact_id)}, 'cockpit', 'note', 'internal', 'manual_mark', {lit(note)}, {lit(by)});
COMMIT;
SELECT 'note_added=true  contact_id={contact_id}';
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a manual note to a contact. Dry-run by default.")
    parser.add_argument("--contact-id", required=True, help="UUID of the contact")
    parser.add_argument("--note", required=True, help="Note text (max 500 chars)")
    parser.add_argument("--by", default="operator", help="Operator name (max 100 chars)")
    parser.add_argument("--apply", action="store_true", help="Write to database (default: dry-run)")
    args = parser.parse_args()

    # Validate contact-id format
    if not UUID_RE.match(args.contact_id):
        print("Refusing: --contact-id must be a valid UUID.")
        return 2

    # Sanitise inputs
    note = sanitise(args.note, 500)
    by = sanitise(args.by, 100) or "operator"
    if not note:
        print("Refusing: --note cannot be empty after sanitisation.")
        return 2

    # Probe: verify contact exists
    code, out = run_psql(probe_sql(args.contact_id))
    if code != 0:
        print(f"DB probe failed: {out}")
        return code
    parts = out.split("|")
    if not out or parts[0] not in ("t", "true"):
        print(f"Refusing: contact {args.contact_id} not found.")
        return 1
    masked_name = parts[1] if len(parts) > 1 else "?"
    print(f"contact={masked_name}  note_length={len(note)}  by={by}")

    if not args.apply:
        print("\nDry run only. No database writes were made.")
        print("Pass --apply to write the note.")
        return 0

    code, out = run_psql(insert_sql(args.contact_id, note, by))
    if code == 0:
        print("\nNote recorded:")
        print(f"note_added=true")
        print(f"contact_id={args.contact_id}")
    else:
        print("\nNote FAILED (rolled back):")
        print(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
