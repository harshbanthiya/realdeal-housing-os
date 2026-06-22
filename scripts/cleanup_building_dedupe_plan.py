#!/usr/bin/env python3
"""Phase 6.7 cleanup of building-dedupe planning rows. Dry-run by default.

Deletes ONLY rows tagged raw_context phase='6.7', source='building_dedupe_planning'
(created by plan_building_dedupe.py) in FK-safe order. It NEVER touches buildings,
building_aliases, building_units, contact_property_relationships, building_web_profiles,
SEO/content rows, or any earlier-phase data.

It refuses to delete if any tagged duplicate candidate has progressed to
status 'merged' or 'approved_for_merge'. Deleting requires --apply AND --real-ok.
Counts only; no personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.7"
SOURCE = "building_dedupe_planning"

# FK-safe order: review items + action log reference candidates, so candidates go last.
DELETE_ORDER = [
    ("building_dedupe_review_items", "raw_context"),
    ("building_dedupe_action_log", "raw_context"),
    ("building_duplicate_candidates", "raw_context"),
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
    return (
        "SELECT count(*)::text FROM building_duplicate_candidates "
        f"WHERE {tag('raw_context')} AND status IN ('merged', 'approved_for_merge');"
    )

def delete_sql() -> str:
    stmts = "\n".join(f"DELETE FROM {t} WHERE {tag(col)};" for t, col in DELETE_ORDER)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Phase 6.7 building-dedupe planning rows. Dry-run by default.")
    parser.add_argument("--building-name", default="Imperial Heights")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Building dedupe planning cleanup. phase={PHASE}; source={SOURCE}. Counts only; only tagged 6.7 rows "
          "are deleted; buildings/relationships/SEO/content and earlier phases are never touched.")

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
        print("current phase-6.7 rows (would delete):")
        print(current)
        print(f"guard check -> candidates merged/approved_for_merge: {progressed}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if progressed != "0":
        print(f"Refusing: {progressed} candidate(s) are merged/approved_for_merge. Not deleting.")
        return 1

    code, output = run_psql(delete_sql())
    print("Remaining phase-6.7 rows after cleanup (expect all 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
