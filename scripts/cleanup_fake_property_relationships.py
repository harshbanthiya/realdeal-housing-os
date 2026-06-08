#!/usr/bin/env python3
"""Remove ONLY the Phase 5.1 fake property-relationship rows. Dry-run by default.

Targets rows tagged with fake_batch 'FAKE_PHASE_5_1_REL_001' (and is_test markers),
deleting in FK-safe order. Never touches real canonical contacts (is_test=false) or
real buildings. Writing requires --apply. Counts only; no raw personal values.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
FAKE_BATCH = "FAKE_PHASE_5_1_REL_001"


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


COUNTS_SQL = f"""
SELECT 'action_log' AS item, count(*)::text AS val FROM property_relationship_action_log WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'review_items', count(*)::text FROM property_relationship_review_items WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'relationships', count(*)::text FROM contact_property_relationships WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'building_units', count(*)::text FROM building_units WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'building_aliases', count(*)::text FROM building_aliases WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_contacts', count(*)::text FROM contacts WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' AND is_test = true
UNION ALL SELECT 'fake_buildings', count(*)::text FROM buildings WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' AND metadata->>'is_test' = 'true'
ORDER BY item;
"""

# FK-safe deletion order; every clause is scoped to the fake batch tag, and the
# contacts/buildings deletes additionally require the is_test marker.
DELETE_SQL = f"""
BEGIN;
DELETE FROM property_relationship_action_log WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}';
DELETE FROM property_relationship_review_items WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}';
DELETE FROM contact_property_relationships WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}';
DELETE FROM building_units WHERE metadata->>'fake_batch' = '{FAKE_BATCH}';
DELETE FROM building_aliases WHERE metadata->>'fake_batch' = '{FAKE_BATCH}';
DELETE FROM contacts WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' AND is_test = true;
DELETE FROM buildings WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' AND metadata->>'is_test' = 'true';
COMMIT;
{COUNTS_SQL}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove FAKE Phase 5.1 property relationships. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Cleanup of fake property relationships. fake_batch={FAKE_BATCH}. Counts only.")

    code, counts = run_psql(COUNTS_SQL)
    if code != 0:
        print(counts)
        return code

    if not args.apply:
        print("Dry run only. No rows were deleted. Rows that WOULD be deleted:")
        print(counts)
        print("Deleting requires --apply.")
        return 0

    code, output = run_psql(DELETE_SQL)
    if code != 0:
        print(output)
        return code
    print("Fake rows deleted. Remaining fake rows (should all be 0):")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
