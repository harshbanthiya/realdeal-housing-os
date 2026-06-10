#!/usr/bin/env python3
"""Phase 6.8 cleanup of FAKE RERA verification rows. Dry-run by default.

Deletes ONLY rows tagged fake_batch='FAKE_PHASE_6_8_RERA_VERIFICATION' (created by
seed_fake_rera_verification.py), in FK-safe order, including the one clearly-fake test
building. It NEVER touches the real Imperial Heights buildings, any real SEO/content
rows, or any earlier-phase data. Deleting requires --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
FAKE_BATCH = "FAKE_PHASE_6_8_RERA_VERIFICATION"

# FK-safe order: children first; the fake building (referenced by several) goes last.
DELETE_ORDER = [
    ("rera_verification_review_items", "raw_context"),
    ("rera_area_mismatch_candidates", "raw_context"),
    ("rera_project_status_checks", "raw_context"),
    ("rera_carpet_area_records", "raw_context"),
    ("rera_building_match_candidates", "raw_context"),
    ("rera_project_profiles", "raw_context"),
    ("buildings", "metadata"),
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


def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {col}->>'fake_batch' = '{FAKE_BATCH}'"
        for t, col in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {col}->>'fake_batch' = '{FAKE_BATCH}';" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup FAKE RERA verification rows. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Fake RERA verification cleanup. fake_batch={FAKE_BATCH}. Counts only; only fake-batch rows are deleted; "
          "real buildings/SEO/content and earlier phases are never touched.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("current fake-batch rows (would delete):")
        print(current)
        print("Deleting requires --apply.")
        return 0

    code, output = run_psql(delete_sql())
    print("Remaining fake-batch rows after cleanup (expect all 0):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
