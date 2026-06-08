#!/usr/bin/env python3
"""Remove ONLY Phase 5.2 fake relationship-candidate rows. Dry-run by default.

Targets rows tagged fake_batch (default FAKE_PHASE_5_2_REL_CANDIDATES) AND
phase '5.2', deleting in FK-safe order. Never deletes real canonical contacts
(is_test=false), real buildings, or anything in REAL_PHASE_3_5_TEST_001. Writing
requires --apply. Counts only; no raw personal values.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
DEFAULT_FAKE_BATCH = "FAKE_PHASE_5_2_REL_CANDIDATES"


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


def counts_sql(fb: str) -> str:
    b = sql_literal(fb)
    return f"""
SELECT 'action_log' AS item, count(*)::text AS val FROM property_relationship_action_log
  WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2'
UNION ALL SELECT 'review_items', count(*)::text FROM property_relationship_review_items
  WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2'
UNION ALL SELECT 'relationships', count(*)::text FROM contact_property_relationships
  WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2'
UNION ALL SELECT 'building_units', count(*)::text FROM building_units
  WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2'
UNION ALL SELECT 'building_aliases', count(*)::text FROM building_aliases
  WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2'
UNION ALL SELECT 'fake_buildings', count(*)::text FROM buildings
  WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2' AND metadata->>'is_test' = 'true'
ORDER BY item;
"""


def delete_sql(fb: str) -> str:
    b = sql_literal(fb)
    return f"""
BEGIN;
DELETE FROM property_relationship_action_log WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2';
DELETE FROM property_relationship_review_items WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2';
DELETE FROM contact_property_relationships WHERE raw_context->>'fake_batch' = {b} AND raw_context->>'phase' = '5.2';
DELETE FROM building_units WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2';
DELETE FROM building_aliases WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2';
DELETE FROM buildings WHERE metadata->>'fake_batch' = {b} AND metadata->>'phase' = '5.2' AND metadata->>'is_test' = 'true';
COMMIT;
{counts_sql(fb)}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove FAKE Phase 5.2 relationship candidates. Dry-run by default.")
    parser.add_argument("--fake-batch", default=DEFAULT_FAKE_BATCH)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.fake_batch.startswith("FAKE_"):
        print("Refusing: --fake-batch must start with FAKE_.")
        return 1

    print(f"Cleanup of fake relationship candidates. fake_batch={args.fake_batch}; phase=5.2. Counts only.")
    code, counts = run_psql(counts_sql(args.fake_batch))
    if code != 0:
        print(counts)
        return code

    if not args.apply:
        print("Dry run only. No rows were deleted. Rows that WOULD be deleted:")
        print(counts)
        print("Deleting requires --apply.")
        return 0

    code, output = run_psql(delete_sql(args.fake_batch))
    print("Fake candidate rows deleted. Remaining (should all be 0):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
