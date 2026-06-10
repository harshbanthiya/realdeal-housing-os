#!/usr/bin/env python3
"""Phase 6.9 cleanup of MANUAL RERA verification rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.9', source='manual_rera_verification_entry'
(created by apply_manual_rera_verification.py), in FK-safe order. It NEVER touches
buildings, relationships, building_web_profiles, SEO/content rows, or earlier-phase data.

It refuses to delete if the verification has progressed: any tagged profile is 'verified',
any tagged match is 'accepted', any tagged area-mismatch is 'corrected', or any content
source gap has been resolved. Deleting requires --apply AND --real-ok. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.9"
SOURCE = "manual_rera_verification_entry"

# FK-safe order: children first; the project profile (referenced by all) goes last.
DELETE_ORDER = [
    "rera_verification_review_items",
    "rera_area_mismatch_candidates",
    "rera_carpet_area_records",
    "rera_project_status_checks",
    "rera_building_match_candidates",
    "rera_project_profiles",
]


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


def tag() -> str:
    return f"raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'"


def counts_sql() -> str:
    parts = [f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {tag()}" for t in DELETE_ORDER]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def guard_sql() -> str:
    return f"""
SELECT 'profiles_verified' k, count(*)::text v FROM rera_project_profiles WHERE {tag()} AND verification_status = 'verified'
UNION ALL SELECT 'matches_accepted', count(*)::text FROM rera_building_match_candidates WHERE {tag()} AND match_status = 'accepted'
UNION ALL SELECT 'mismatch_corrected', count(*)::text FROM rera_area_mismatch_candidates WHERE {tag()} AND mismatch_status = 'corrected'
UNION ALL SELECT 'content_gaps_resolved', count(*)::text FROM content_source_gap_items WHERE status <> 'open'
ORDER BY k;"""


def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag()};" for t in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.9 manual RERA verification rows. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Manual RERA verification cleanup. phase={PHASE}; source={SOURCE}. Counts only; only tagged 6.9 rows are "
          "deleted; buildings/relationships/SEO/content and earlier phases are never touched.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql())
    if code != 0:
        print(guard)
        return code
    g = dict(line.split("|", 1) for line in guard.splitlines() if "|" in line)
    blocked = (g.get("profiles_verified", "0") != "0" or g.get("matches_accepted", "0") != "0"
               or g.get("mismatch_corrected", "0") != "0" or g.get("content_gaps_resolved", "0") != "0")

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current phase-6.9 rows (would delete):")
        print(current)
        print(f"guard -> profiles_verified={g.get('profiles_verified','0')}, matches_accepted={g.get('matches_accepted','0')}, "
              f"mismatch_corrected={g.get('mismatch_corrected','0')}, content_gaps_resolved={g.get('content_gaps_resolved','0')}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if blocked:
        print("Refusing: verification progressed (verified/accepted/corrected) or content gaps resolved. Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.9 rows after cleanup (expect all 0):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
