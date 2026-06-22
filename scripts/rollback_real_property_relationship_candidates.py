#!/usr/bin/env python3
"""Rollback Phase 5.8 real owner/unit relationship CANDIDATE rows. Dry-run by default.

Removes only rows tagged phase=5.8 AND the given rel-label (default
REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001): property_relationship_review_items,
contact_property_relationships, building_units, building_aliases, and the building
anchor created by the apply — in FK-safe order. REFUSES if any targeted
relationship has already been approved or activated. Never deletes the canonical
contact, contact_methods, source-aware audit rows (contact_import_rows,
contact_property_hints, inventory_import_rows, source_files), or import batches.
Writing requires --apply, --real-ok, and --confirm-real-rollback. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REL_LABEL = "REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001"
def counts_sql(rl: str) -> str:
    b = sql_literal(rl)
    return f"""
SELECT 'review_items' AS item, count(*)::text AS val FROM property_relationship_review_items
  WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b}
UNION ALL SELECT 'relationships', count(*)::text FROM contact_property_relationships
  WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b}
UNION ALL SELECT 'relationships_already_approved_or_active', count(*)::text FROM contact_property_relationships
  WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b}
    AND relationship_status IN ('approved', 'active')
UNION ALL SELECT 'building_units', count(*)::text FROM building_units
  WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b}
UNION ALL SELECT 'building_aliases', count(*)::text FROM building_aliases
  WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b}
UNION ALL SELECT 'buildings', count(*)::text FROM buildings
  WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b}
ORDER BY item;
"""

def delete_sql(rl: str) -> str:
    b = sql_literal(rl)
    return f"""
BEGIN;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM contact_property_relationships
    WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b}
      AND relationship_status IN ('approved', 'active')
  ) THEN
    RAISE EXCEPTION 'Refusing rollback: a Phase 5.8 relationship is already approved/active.';
  END IF;
END $$;
DELETE FROM property_relationship_review_items WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b};
DELETE FROM contact_property_relationships WHERE raw_context->>'phase' = '5.8' AND raw_context->>'rel_label' = {b};
DELETE FROM building_units WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b};
DELETE FROM building_aliases WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b};
DELETE FROM buildings WHERE metadata->>'phase' = '5.8' AND metadata->>'rel_label' = {b};
COMMIT;
{counts_sql(rl)}
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback Phase 5.8 real relationship candidates. Dry-run by default.")
    parser.add_argument("--rel-label", default=DEFAULT_REL_LABEL)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--confirm-real-rollback", action="store_true")
    args = parser.parse_args()

    print(f"Phase 5.8 relationship candidate rollback. rel_label={args.rel_label}. Counts only.")
    code, counts = run_psql(counts_sql(args.rel_label))
    if code != 0:
        print(counts)
        return code

    approved = 0
    for line in counts.splitlines():
        if line.startswith("relationships_already_approved_or_active|"):
            approved = int(line.split("|")[1] or 0)

    if not args.apply:
        print("Dry run only. No rows were deleted. Rows that WOULD be deleted:")
        print(counts)
        print("merge_status_change|candidate rows removed (would apply)")
        print("Deleting requires --apply, --real-ok, and --confirm-real-rollback.")
        return 0

    if not (args.real_ok and args.confirm_real_rollback):
        print("Refusing apply: real rollback needs --real-ok and --confirm-real-rollback.")
        return 1
    if approved > 0:
        print("Refusing: a Phase 5.8 relationship is already approved/active. Not rolling back.")
        print(counts)
        return 1

    code, output = run_psql(delete_sql(args.rel_label))
    print("Phase 5.8 candidate rows deleted. Remaining (should all be 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
