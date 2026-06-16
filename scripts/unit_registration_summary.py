#!/usr/bin/env python3
"""Phase 6.15 unit-registration summary. Counts only; no DB writes; no personal names.

Prints row counts for the building-structure + IGR unit-registration tables and the Imperial
Heights registration readiness rollup. Read-only: never writes, never calls IGR/MahaRERA or
any external API, never browses the web, and never prints party/contact names.
"""

from __future__ import annotations

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


SUMMARY_SQL = """
SELECT 'building_tower_structure' AS item, count(*)::text AS val FROM building_tower_structure
UNION ALL SELECT 'building_property_identifiers', count(*)::text FROM building_property_identifiers
UNION ALL SELECT 'igr_registration_search_jobs', count(*)::text FROM igr_registration_search_jobs
UNION ALL SELECT 'igr_search_jobs_with_external_call', count(*)::text FROM igr_registration_search_jobs WHERE external_call_made
UNION ALL SELECT 'unit_registration_records', count(*)::text FROM unit_registration_records
UNION ALL SELECT 'unit_registration_parties', count(*)::text FROM unit_registration_parties
UNION ALL SELECT 'registration_party_contact_matches', count(*)::text FROM registration_party_contact_matches
UNION ALL SELECT 'party_contact_matches_accepted', count(*)::text FROM registration_party_contact_matches WHERE match_status = 'accepted'
UNION ALL SELECT 'unit_registration_review_items', count(*)::text FROM unit_registration_review_items
UNION ALL SELECT 'review_items_pending', count(*)::text FROM unit_registration_review_items WHERE status = 'pending'
ORDER BY item;"""

READINESS_SQL = """
SELECT 'imperial_heights:' || building_name
       || ' towers=' || tower_structure_count
       || ' identifiers=' || identifier_count
       || ' verified_search_keys=' || verified_search_key_count
       || ' search_jobs=' || search_job_count
       || ' external_calls=' || external_call_count
       || ' records=' || registration_record_count
       || ' verified_records=' || verified_record_count
       || ' accepted_matches=' || accepted_match_count
       || ' ready_for_igr_search=' || ready_for_igr_search
       || ' ready_for_party_matching=' || ready_for_party_matching
       || ' ready_for_relationship_creation=' || ready_for_relationship_creation
       || ' blocked_reason=' || blocked_reason
FROM vw_imperial_heights_registration_readiness;"""


def main() -> int:
    print("Unit-registration summary (counts only; read-only; no IGR/MahaRERA/external calls; no names).")
    code, table_counts = run_psql(SUMMARY_SQL)
    if code != 0:
        print(table_counts)
        return code
    print("Unit-registration table row counts:")
    print(table_counts)

    code, readiness = run_psql(READINESS_SQL)
    if code != 0:
        print(readiness)
        return code
    print("Imperial Heights registration readiness:")
    print(readiness or "(no Imperial Heights building found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
