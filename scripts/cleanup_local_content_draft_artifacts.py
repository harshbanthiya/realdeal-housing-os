#!/usr/bin/env python3
"""Phase 6.4 cleanup of local content draft workspace rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.4', source='local_content_draft_workspace'
(created by create_local_content_draft_artifacts.py) in FK-safe order. It NEVER
deletes Phase 6.1 (SEO plan), Phase 6.2 (Wix mapping/review), or Phase 6.3
(quality/source/AI planning) rows.

It refuses to delete if any tagged draft artifact has progressed past internal draft:
public_ready=true, published=true, external_calls_made=true, or communication_sent=true.
Deleting requires --apply AND --real-ok. Exported files under exports/content/ are
git-ignored and are left untouched. Counts only; no raw personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.4"
SOURCE = "local_content_draft_workspace"

# FK-safe order: gap items + reviews reference artifacts, so artifacts go last.
DELETE_ORDER = [
    ("content_source_gap_items", "raw_context"),
    ("content_draft_reviews", "raw_context"),
    ("content_draft_artifacts", "raw_context"),
]
def tag(col: str) -> str:
    return f"{col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {tag(col)}"
        for t, col in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def guard_sql() -> str:
    """count of tagged draft artifacts that progressed past internal draft."""
    return (
        "SELECT count(*)::text FROM content_draft_artifacts "
        f"WHERE {tag('raw_context')} AND (public_ready = true OR published = true "
        "OR external_calls_made = true OR communication_sent = true);"
    )

def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag(col)};" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.4 local content draft workspace. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Local content draft workspace cleanup. phase={PHASE}; source={SOURCE}. Counts only; "
          "only tagged 6.4 rows are deleted; Phase 6.1/6.2/6.3 rows are never touched.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql())
    if code != 0:
        print(guard)
        return code
    progressed = guard.strip() or "0"

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current phase-6.4 rows (would delete):")
        print(current)
        print(f"guard check -> artifacts past internal draft (public_ready/published/external/comm): {progressed}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if progressed != "0":
        print(f"Refusing: {progressed} artifact(s) progressed past internal draft. Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.4 rows after cleanup (expect all 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
