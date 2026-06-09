#!/usr/bin/env python3
"""Phase 6.0 cleanup of FAKE growth-pipeline rows. Dry-run by default.

Deletes ONLY rows tagged fake_batch='FAKE_PHASE_6_0_GROWTH_PIPELINE' (the marker
written by seed_fake_growth_pipeline.py), in FK-safe order. It never touches real
contacts, real buildings, real leads, or real source rows: every DELETE is filtered
on the fake_batch tag in the row's own metadata/raw_context/raw_payload/raw_input
column. Writing requires --apply. Counts only; no raw personal values are printed.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
FAKE_BATCH = "FAKE_PHASE_6_0_GROWTH_PIPELINE"

# Delete order respects foreign keys: children before parents. Each tuple is
# (table, jsonb column holding the fake_batch tag).
DELETE_ORDER = [
    ("lead_attribution_events", "raw_context"),
    ("channel_permissions", "raw_context"),
    ("outreach_suppression_list", "raw_context"),
    ("content_publishing_queue", "raw_context"),
    ("campaign_drafts", "raw_context"),
    ("inbound_leads", "raw_payload"),
    ("inbound_lead_sources", "raw_context"),
    ("ai_agent_tasks", "raw_input"),
    ("content_briefs", "raw_context"),
    ("seo_keywords", "raw_context"),
    ("building_web_profiles", "raw_context"),
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
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'fake_batch' = '{FAKE_BATCH}'"
        for t, col in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def delete_sql() -> str:
    stmts = "\n".join(
        f"DELETE FROM {t} WHERE {col}->>'fake_batch' = '{FAKE_BATCH}';"
        for t, col in DELETE_ORDER
    )
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup FAKE Phase 6.0 growth pipeline. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Fake growth-pipeline cleanup. fake_batch={FAKE_BATCH}. Counts only; only tagged fake rows are deleted.")

    code, existing = run_psql(counts_sql())
    if code != 0:
        print(existing)
        return code

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("current fake rows (would delete):")
        print(existing)
        print("Deleting requires --apply.")
        return 0

    code, output = run_psql(delete_sql())
    print("Remaining fake rows after cleanup (expect all 0):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
