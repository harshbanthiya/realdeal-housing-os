#!/usr/bin/env python3
"""Phase 6.8 RERA verification summary. Counts only; no DB writes; no personal values.

Prints row counts for the RERA verification tables and the Imperial Heights RERA
readiness rollup. Read-only: this script never writes, never calls MahaRERA or any
external API, and never browses the web.
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
SELECT 'rera_project_profiles' AS item, count(*)::text AS val FROM rera_project_profiles
UNION ALL SELECT 'rera_building_match_candidates', count(*)::text FROM rera_building_match_candidates
UNION ALL SELECT 'rera_carpet_area_records', count(*)::text FROM rera_carpet_area_records
UNION ALL SELECT 'rera_project_status_checks', count(*)::text FROM rera_project_status_checks
UNION ALL SELECT 'rera_area_mismatch_candidates', count(*)::text FROM rera_area_mismatch_candidates
UNION ALL SELECT 'rera_verification_review_items', count(*)::text FROM rera_verification_review_items
ORDER BY item;"""

READINESS_SQL = """
SELECT 'imperial_heights:' || profile_slug
       || ' rera_profiles=' || rera_project_profile_count
       || ' verified=' || verified_profile_count
       || ' accepted_match=' || accepted_match_count
       || ' blocker_risk=' || blocker_risk_count
       || ' ready_for_building_dedupe=' || ready_for_building_dedupe
       || ' ready_for_content_fact_use=' || ready_for_content_fact_use
       || ' blocked_reason=' || blocked_reason
FROM vw_imperial_heights_rera_readiness;"""


def main() -> int:
    print("RERA verification summary (counts only; read-only; no MahaRERA/external calls).")
    code, table_counts = run_psql(SUMMARY_SQL)
    if code != 0:
        print(table_counts)
        return code
    print("RERA table row counts:")
    print(table_counts)

    code, readiness = run_psql(READINESS_SQL)
    if code != 0:
        print(readiness)
        return code
    print("Imperial Heights RERA readiness:")
    print(readiness or "(no Imperial Heights web profile found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
