"""Consolidate 3 Kalpataru building rows → 1 canonical (f63d75ab).

Steps (all wrapped in one transaction, rolled back in dry-run):
  1. Re-point bb53ca24's reg record → canonical (f63d75ab)
  2. NULL building_unit_id on any reg records linked to the 11 short-label units
     (those units have no long-label counterpart — they become unlinked candidates)
  3. DELETE 11 short-label building_units (wing IN A/B/C/D, canonical building)
  4. DELETE bb53ca24's 702 building_units
  5. DELETE 8272dc3e's 1 building_unit
  6. DELETE buildings bb53ca24 + 8272dc3e

Usage:
  python scripts/consolidate_kalpataru_buildings.py          # dry run
  python scripts/consolidate_kalpataru_buildings.py --apply  # write
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql  # noqa: E402

CANONICAL   = 'f63d75ab-2ef9-48a9-afe2-cab3c4283283'
STUB_NEW    = 'bb53ca24-7954-417a-8943-e21c3f8f0fa2'  # New Parser
STUB_A      = '8272dc3e-6f05-45c3-a40e-c14b41dd7f05'  # Kalpataru Radiance A

# ponytail: single transaction SQL; rollback = dry-run; one round-trip
_CONSOLIDATE_SQL = f"""
BEGIN;

-- 1. Re-point bb53ca24 reg records → canonical
UPDATE unit_registration_records
  SET building_id = '{CANONICAL}', updated_at = now()
  WHERE building_id = '{STUB_NEW}';

-- 2. Unlink reg records tied to short-label units (C/86 is the only linked one)
UPDATE unit_registration_records
  SET building_unit_id = NULL, updated_at = now()
  WHERE building_unit_id IN (
    SELECT id FROM building_units
    WHERE building_id = '{CANONICAL}' AND wing IN ('A','B','C','D')
  );

-- 3. Delete 11 short-label units from canonical
DELETE FROM building_units
  WHERE building_id = '{CANONICAL}' AND wing IN ('A','B','C','D');

-- 4. Re-point unit_registration_review_items (107 rows on bb53ca24)
UPDATE unit_registration_review_items
  SET building_id = '{CANONICAL}', updated_at = now()
  WHERE building_id = '{STUB_NEW}';

-- 5. Re-point igr_registration_search_jobs (2 rows)
UPDATE igr_registration_search_jobs
  SET building_id = '{CANONICAL}', updated_at = now()
  WHERE building_id IN ('{STUB_NEW}', '{STUB_A}');

-- 6. Migrate village/pincode property identifiers from STUB_A to canonical (cts_number already exists)
UPDATE building_property_identifiers
  SET building_id = '{CANONICAL}', updated_at = now()
  WHERE building_id = '{STUB_A}'
    AND identifier_type IN ('village', 'pincode');
-- Re-point FK references from stub cts_number → canonical cts_number
UPDATE igr_registration_search_jobs
  SET building_property_identifier_id = (
    SELECT id FROM building_property_identifiers
    WHERE building_id='{CANONICAL}' AND identifier_type='cts_number' LIMIT 1
  )
  WHERE building_property_identifier_id IN (
    SELECT id FROM building_property_identifiers WHERE building_id='{STUB_A}'
  );
UPDATE unit_registration_review_items
  SET building_property_identifier_id = (
    SELECT id FROM building_property_identifiers
    WHERE building_id='{CANONICAL}' AND identifier_type='cts_number' LIMIT 1
  )
  WHERE building_property_identifier_id IN (
    SELECT id FROM building_property_identifiers WHERE building_id='{STUB_A}'
  );
DELETE FROM building_property_identifiers
  WHERE building_id = '{STUB_A}';  -- removes cts_number duplicate

-- 7. Delete stub tower structure, aliases (canonical already has real data)
UPDATE unit_registration_review_items
  SET building_tower_structure_id = NULL, updated_at = now()
  WHERE building_tower_structure_id IN (
    SELECT id FROM building_tower_structure WHERE building_id IN ('{STUB_NEW}', '{STUB_A}')
  );
DELETE FROM building_tower_structure WHERE building_id IN ('{STUB_NEW}', '{STUB_A}');
DELETE FROM building_aliases WHERE building_id IN ('{STUB_NEW}', '{STUB_A}');

-- 8. Delete stub building_units
DELETE FROM building_units WHERE building_id IN ('{STUB_NEW}', '{STUB_A}');

-- 9. Delete stub buildings
DELETE FROM buildings WHERE id IN ('{STUB_NEW}', '{STUB_A}');

ROLLBACK;
"""

_APPLY_SQL = _CONSOLIDATE_SQL.replace("\nROLLBACK;", "\nCOMMIT;")

_AUDIT_SQL = """
SELECT b.name,
  (SELECT COUNT(*) FROM building_units bu WHERE bu.building_id=b.id) AS units,
  (SELECT COUNT(*) FROM unit_registration_records urr WHERE urr.building_id=b.id) AS reg_records
FROM buildings b WHERE b.name ILIKE '%kalpataru%'
ORDER BY b.name;
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Commit changes (default: dry run)")
    args = ap.parse_args()

    sql = _APPLY_SQL if args.apply else _CONSOLIDATE_SQL
    code, out = run_psql(sql)
    if code != 0:
        print(f"Error:\n{out}")
        return 1

    print("dry run — transaction rolled back" if not args.apply else "applied — committed")
    print()

    code2, audit = run_psql(_AUDIT_SQL)
    if code2 == 0:
        print("Kalpataru buildings after:")
        for line in audit.splitlines():
            print(" ", line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
