#!/usr/bin/env python3
"""Phase 8.1 — Seed the outreach 'Test group' + 3 test contacts. Dry-run by default.

Creates a non-building 'test-group' and three REAL test contacts the operator owns,
so the full assisted-outreach pipeline + activity dashboard can be exercised safely:

  * Harsh (test)              +1 581 398 8848   (your own number)
  * Padmini Jain (test)       +91 829 129 3889  (director's personal)
  * Company business (test)   +91 740 010 6562  (company WhatsApp Business)

It also sets director_display_name = 'Padmini Jain' (UPSERT — overwrites the
placeholder). Contacts are tagged ['test','outreach_test'], NOT attached to any
building, identified idempotently by metadata->>'outreach_test_id'. They are left
visible (is_test not set) so they show in the contact view for testing.

Writing requires BOTH --real-ok and --apply. Idempotent; re-running is a no-op.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


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
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


APPLY_SQL = """
BEGIN;
INSERT INTO contact_groups (name, slug, group_type, description, created_by)
VALUES ('Test group','test-group','test','End-to-end outreach testing — not building-attached','cockpit')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO outreach_settings (setting_key, setting_value, notes)
VALUES ('director_display_name','Padmini Jain','Director name resolved in {{director}} templates.')
ON CONFLICT (setting_key) DO UPDATE SET setting_value=excluded.setting_value, updated_at=now();

WITH v(test_id, name, phone) AS (VALUES
  ('self','Harsh (test)','15813988848'),
  ('director','Padmini Jain (test)','918291293889'),
  ('company','Company business (test)','917400106562')
),
ins_contacts AS (
  INSERT INTO contacts (full_name, contact_type, status, tags, metadata)
  SELECT v.name, 'other', 'active', ARRAY['test','outreach_test'],
         jsonb_build_object('outreach_test_id', v.test_id)
  FROM v
  WHERE NOT EXISTS (SELECT 1 FROM contacts c WHERE c.metadata->>'outreach_test_id' = v.test_id)
  RETURNING id, metadata->>'outreach_test_id' AS test_id
),
all_contacts AS (
  SELECT id, test_id FROM ins_contacts
  UNION ALL
  SELECT c.id, c.metadata->>'outreach_test_id' AS test_id FROM contacts c
  WHERE c.metadata->>'outreach_test_id' IN ('self','director','company')
    AND NOT EXISTS (SELECT 1 FROM ins_contacts i WHERE i.test_id = c.metadata->>'outreach_test_id')
),
ins_methods AS (
  INSERT INTO contact_methods (contact_id, method_type, raw_value, normalized_value, is_primary, validation_status)
  SELECT ac.id, 'mobile', '+'||v.phone, v.phone, true, 'valid'
  FROM all_contacts ac JOIN v ON v.test_id = ac.test_id
  WHERE NOT EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_id=ac.id AND cm.method_type IN ('mobile','phone','whatsapp'))
  RETURNING contact_id
)
INSERT INTO contact_group_members (group_id, contact_id, added_by)
SELECT (SELECT id FROM contact_groups WHERE slug='test-group'), ac.id, 'cockpit'
FROM all_contacts ac
ON CONFLICT (group_id, contact_id) DO NOTHING;

DO $$ DECLARE se text; BEGIN
  SELECT setting_value INTO se FROM outreach_settings WHERE setting_key='send_enabled';
  IF se='true' THEN RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF;
END $$;
COMMIT;

SELECT 'test_contacts='||(SELECT count(*) FROM contacts WHERE metadata->>'outreach_test_id' IN ('self','director','company'))
     ||'  group_members='||(SELECT count(*) FROM contact_group_members m JOIN contact_groups g ON g.id=m.group_id WHERE g.slug='test-group')
     ||'  director='||(SELECT setting_value FROM outreach_settings WHERE setting_key='director_display_name');
"""

PROBE_SQL = """
SELECT 'existing_test_contacts='||(SELECT count(*) FROM contacts WHERE metadata->>'outreach_test_id' IN ('self','director','company'))
     ||'  test_group_exists='||(SELECT count(*) FROM contact_groups WHERE slug='test-group')
     ||'  director_now='||coalesce((SELECT setting_value FROM outreach_settings WHERE setting_key='director_display_name'),'(unset)');
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the outreach Test group + 3 test contacts. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print("Seed Test group (Harsh / Padmini Jain / Company business) + set director = Padmini Jain.")
    code, out = run_psql(PROBE_SQL)
    print(f"  {out}" if code == 0 else f"  probe failed: {out}")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(APPLY_SQL)
    print("\nTest group seeded:" if code == 0 else "Seed FAILED (rolled back):")
    print(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
