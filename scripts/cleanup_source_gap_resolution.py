#!/usr/bin/env python3
"""Phase 6.5 cleanup of source-gap resolution workflow rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.5', source='source_gap_resolution_workflow'
(created by plan_source_gap_resolution.py) in FK-safe order. It NEVER deletes Phase
6.1 (SEO plan), 6.2 (Wix mapping/review), 6.3 (quality/source/AI planning), or 6.4
(local draft workspace) rows, and never touches the content_source_gap_items themselves.

It refuses to delete if any tagged resolution task has progressed past planning:
task_status='resolved', external_calls_allowed=true, or the row was ever marked
communication_sent / published in raw_context. Deleting requires --apply AND --real-ok.
Counts only; no raw personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.5"
SOURCE = "source_gap_resolution_workflow"

# FK-safe order: review items reference resolution tasks, so tasks are deleted last.
DELETE_ORDER = [
    ("source_gap_review_items", "raw_context"),
    ("internal_source_evidence", "raw_context"),
    ("source_gap_resolution_tasks", "raw_context"),
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
    """count of tagged resolution tasks that progressed past planning."""
    return (
        "SELECT count(*)::text FROM source_gap_resolution_tasks "
        f"WHERE {tag('raw_context')} AND (task_status = 'resolved' OR external_calls_allowed = true "
        "OR raw_context->>'communication_sent' = 'true' OR raw_context->>'published' = 'true');"
    )

def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag(col)};" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.5 source-gap resolution workflow. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Source-gap resolution cleanup. phase={PHASE}; source={SOURCE}. Counts only; "
          "only tagged 6.5 rows are deleted; Phase 6.1/6.2/6.3/6.4 rows and the gaps themselves are never touched.")

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
        print("current phase-6.5 rows (would delete):")
        print(current)
        print(f"guard check -> tasks past planning (resolved/external_calls_allowed/communication_sent/published): {progressed}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if progressed != "0":
        print(f"Refusing: {progressed} resolution task(s) progressed past planning. Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.5 rows after cleanup (expect all 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
