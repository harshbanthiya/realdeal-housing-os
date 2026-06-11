#!/usr/bin/env python3
"""Phase 7.10 — clean up the DLF fake lead-intake test rows. Dry-run by default.

Deletes ONLY the Phase 7.10 harness rows (raw_context.phase='7.10' AND source='dlf_test_lead_intake')
from launch_test_lead_review_items / launch_test_lead_validation_results / launch_test_lead_payloads.
It REFUSES if any matching payload is flagged uses_fake_data=false / creates_real_contact=true /
creates_real_lead=true / external_call_made=true. It never deletes real inbound_leads or contacts.

Writing requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.10"
SOURCE = "dlf_test_lead_intake"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


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


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT
  (SELECT count(*) FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id
     WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}' AND t.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM launch_test_lead_validation_results v JOIN launch_projects p ON p.id = v.launch_project_id
     WHERE p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}' AND v.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM launch_test_lead_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id
     WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id
     WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}'
       AND (t.uses_fake_data = false OR t.creates_real_contact OR t.creates_real_lead OR t.external_call_made));
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE bad int;
BEGIN
  SELECT count(*) FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id
    WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}'
      AND (t.uses_fake_data = false OR t.creates_real_contact OR t.creates_real_lead OR t.external_call_made) INTO bad;
  IF bad > 0 THEN RAISE EXCEPTION 'Refusing cleanup: % test row(s) flagged real/external — investigate, do not auto-delete.', bad; END IF;
END $GUARD$;

DELETE FROM launch_test_lead_review_items ri USING launch_projects p
  WHERE p.id = ri.launch_project_id AND p.launch_key = {lk}
    AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}';
DELETE FROM launch_test_lead_validation_results v USING launch_projects p
  WHERE p.id = v.launch_project_id AND p.launch_key = {lk}
    AND v.raw_context->>'phase' = '{PHASE}' AND v.raw_context->>'source' = '{SOURCE}';
DELETE FROM launch_test_lead_payloads t USING launch_projects p
  WHERE p.id = t.launch_project_id AND p.launch_key = {lk}
    AND t.raw_context->>'phase' = '{PHASE}' AND t.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'payloads_remaining', count(*)::text FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'validations_remaining', count(*)::text FROM launch_test_lead_validation_results v JOIN launch_projects p ON p.id = v.launch_project_id WHERE p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items_remaining', count(*)::text FROM launch_test_lead_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'real_inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.10 fake lead-intake test rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF test lead intake cleanup. launch_key={args.launch_key}. Counts only.")

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 4:
        print("Refusing: probe returned no usable result.")
        return 1
    payloads, validations, reviews, bad = (int(x or 0) for x in f[:4])

    if bad > 0:
        print(f"Refusing: {bad} test payload(s) flagged real/external — investigate, not deleting.")
        return 1
    if payloads == 0 and validations == 0 and reviews == 0:
        print("Nothing to clean: no Phase 7.10 fake test rows found for this launch_key.")
        return 0

    print("intended deletions (fake test rows only):")
    print(f"  payloads: {payloads}   validation results: {validations}   review items: {reviews}")
    print("  real inbound_leads / contacts: UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Cleanup applied:" if code == 0 else "Cleanup FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
