#!/usr/bin/env python3
"""Rollback fake canonical merge test rows. Real rollback is disabled."""

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


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_psql(sql: str, tuples_only: bool = False) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={password}",
        "realdeal-postgres",
        "psql",
        "-U",
        user,
        "-d",
        db_name,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        command.extend(["-At"])
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def status_sql(merge_label: str) -> str:
    return f"""
SELECT
  count(*) AS merge_batch_count,
  count(*) FILTER (WHERE is_test = true OR merge_label LIKE 'FAKE_%') AS fake_merge_count,
  count(*) FILTER (WHERE is_test = false AND merge_label NOT LIKE 'FAKE_%') AS real_merge_count
FROM canonical_merge_batches
WHERE merge_label = {sql_literal(merge_label)};
"""


def dry_run_sql(merge_label: str) -> str:
    return f"""
WITH target AS (
  SELECT id
  FROM canonical_merge_batches
  WHERE merge_label = {sql_literal(merge_label)}
    AND (is_test = true OR merge_label LIKE 'FAKE_%')
),
target_contacts AS (
  SELECT c.id
  FROM contacts c
  JOIN target t ON t.id = c.source_merge_batch_id
  WHERE c.is_test = true
)
SELECT 'merge_batches' AS item, count(*) FROM target
UNION ALL
SELECT 'contacts_to_delete', count(*) FROM target_contacts
UNION ALL
SELECT 'contact_methods_to_unlink', count(*)
FROM contact_methods cm
WHERE cm.contact_id IN (SELECT id FROM target_contacts)
UNION ALL
SELECT 'lead_requirements_to_unlink', count(*)
FROM lead_requirements lr
WHERE lr.contact_id IN (SELECT id FROM target_contacts)
UNION ALL
SELECT 'merge_links_to_mark', count(*)
FROM canonical_merge_links cml
WHERE cml.merge_batch_id IN (SELECT id FROM target)
ORDER BY item;
"""


def rollback_sql(merge_label: str) -> str:
    return f"""
BEGIN;

CREATE TEMP TABLE tmp_target_merge AS
SELECT id
FROM canonical_merge_batches
WHERE merge_label = {sql_literal(merge_label)}
  AND (is_test = true OR merge_label LIKE 'FAKE_%');

CREATE TEMP TABLE tmp_target_contacts AS
SELECT c.id
FROM contacts c
JOIN tmp_target_merge t ON t.id = c.source_merge_batch_id
WHERE c.is_test = true;

UPDATE contact_methods
SET contact_id = NULL
WHERE contact_id IN (SELECT id FROM tmp_target_contacts);

UPDATE lead_requirements
SET contact_id = NULL
WHERE contact_id IN (SELECT id FROM tmp_target_contacts);

UPDATE canonical_merge_links cml
SET metadata = cml.metadata || jsonb_build_object('rolled_back', true, 'rolled_back_at', now())
WHERE cml.merge_batch_id IN (SELECT id FROM tmp_target_merge);

DELETE FROM contacts
WHERE id IN (SELECT id FROM tmp_target_contacts);

UPDATE canonical_merge_batches cmb
SET
  status = 'rolled_back',
  rolled_back_at = now(),
  metadata = cmb.metadata || jsonb_build_object('rolled_back', true, 'rolled_back_at', now())
WHERE cmb.id IN (SELECT id FROM tmp_target_merge);

COMMIT;

SELECT 'merge_batches_rolled_back' AS item, count(*) FROM canonical_merge_batches
WHERE merge_label = {sql_literal(merge_label)} AND status = 'rolled_back'
UNION ALL
SELECT 'remaining_test_contacts_for_merge', count(*) FROM contacts c
JOIN canonical_merge_batches cmb ON cmb.id = c.source_merge_batch_id
WHERE cmb.merge_label = {sql_literal(merge_label)} AND c.is_test = true
UNION ALL
SELECT 'remaining_linked_contact_methods', count(*) FROM contact_methods cm
JOIN canonical_merge_links cml ON cml.canonical_contact_id = cm.contact_id
JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
WHERE cmb.merge_label = {sql_literal(merge_label)}
UNION ALL
SELECT 'remaining_linked_lead_requirements', count(*) FROM lead_requirements lr
JOIN canonical_merge_links cml ON cml.canonical_contact_id = lr.contact_id
JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
WHERE cmb.merge_label = {sql_literal(merge_label)}
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback fake canonical merge rows. Dry-run by default.")
    parser.add_argument("--merge-label", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    code, status = run_psql(status_sql(args.merge_label), tuples_only=True)
    if code != 0:
        print(status)
        return code
    fields = status.split("|") if status else ["0", "0", "0"]
    merge_batch_count = int(fields[0] or 0)
    fake_merge_count = int(fields[1] or 0)
    real_merge_count = int(fields[2] or 0)
    if merge_batch_count != 1:
        print("Refusing rollback: expected exactly one canonical merge batch for label.")
        return 1
    if real_merge_count > 0 or fake_merge_count != 1 or not args.merge_label.startswith("FAKE_"):
        print("Real canonical merge rollback is not enabled yet.")
        return 1

    if not args.apply:
        print("Dry run only. No canonical rows were changed.")
        code, output = run_psql(dry_run_sql(args.merge_label))
        print(output)
        return code

    code, output = run_psql(rollback_sql(args.merge_label))
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
