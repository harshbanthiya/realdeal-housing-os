#!/usr/bin/env python3
"""Phase 6.2 cleanup of Wix content-review prep rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.2', source='wix_content_review_prep'
(created by prepare_wix_content_review.py) in FK-safe order. It NEVER deletes the
Phase 6.1 artifacts (building_web_profiles, seo_keywords, content_briefs,
content_publishing_queue, ai_agent_tasks), the building, contacts, or relationships.

It refuses to delete if anything has progressed past planning: any publishing-queue
row is 'published', or any tagged row recorded external_calls_made=true. Deleting
requires --apply AND --real-ok. Counts only; no raw personal values are printed.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.2"
SOURCE = "wix_content_review_prep"

# FK-safe delete order: children before parents. (table, jsonb tag column)
DELETE_ORDER = [
    ("publishing_readiness_checks", "raw_context"),
    ("content_review_items", "raw_context"),
    ("wix_cms_field_mappings", "raw_context"),
    ("wix_cms_collections", "raw_context"),
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


def tag(col: str) -> str:
    return f"{col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"


def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {tag(col)}"
        for t, col in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def guard_sql() -> str:
    """published publishing rows | tagged rows with external_calls_made=true."""
    ext_parts = " + ".join(
        f"(SELECT count(*) FROM {t} WHERE {tag(col)} AND {col}->>'external_calls_made' = 'true')"
        for t, col in DELETE_ORDER
    )
    return (
        "SELECT (SELECT count(*) FROM content_publishing_queue WHERE publish_status = 'published')::text, "
        f"({ext_parts})::text;"
    )


def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag(col)};" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.2 Wix content-review prep. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Wix content-review prep cleanup. phase={PHASE}; source={SOURCE}. Counts only; "
          "only tagged 6.2 rows are deleted; Phase 6.1 artifacts are never touched.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql())
    if code != 0:
        print(guard)
        return code
    published, ext = (guard.split("|") + ["0", "0"])[:2]

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current phase-6.2 rows (would delete):")
        print(current)
        print(f"guard checks -> published_rows={published}  external_calls_made={ext}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if published != "0" or ext != "0":
        print(f"Refusing: progressed past planning (published={published}, external_calls_made={ext}). Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.2 rows after cleanup (expect all 0):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
