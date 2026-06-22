#!/usr/bin/env python3
"""Dedup-aware BULK attach: link a building's merged canonical contacts to that
building (and its unit, where known) as owner/tenant/broker relationships.

The building is derived from the import batch (one file per building), since the
per-row hints carry unit numbers but rarely a building name. For each merged
canonical contact in a batch:
  - resolve/create the building (reuse existing by id/name; never duplicate),
  - find-or-create the building_unit from the row's wing/unit hint (if present),
  - create ONE active relationship (role from contact_type), skipping if it
    already exists.

Reversible: relationships are tagged with a rel_label in raw_context; rollback
deletes exactly those. Creates NO outreach.

  Dry run:   python3 scripts/bulk_attach_to_buildings.py --batch-label REAL_EKTA_TRIPOLIS_001 --building-name "Ekta Tripolis"
  Apply:     ... --apply --real-ok
  Rollback:  python3 scripts/bulk_attach_to_buildings.py --rollback --rel-label REAL_ATTACH_REAL_EKTA_TRIPOLIS_001 --apply --real-ok
"""
from __future__ import annotations
from _db import lit, read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# One file per building; explicit so resolution never guesses.
BATCH_BUILDING = {
    "REAL_EKTA_TRIPOLIS_001": "Ekta Tripolis",
    "REAL_IMPERIAL_HEIGHTS_UNIT_001": "Imperial Heights",
    "REAL_KALPATARU_RADIANCE_001": "Kalpataru Radiance",
    "REAL_OBEROI_ESQUIRE_001": "Oberoi Esquire",
    "REAL_WINDSOR_GRANDE_001": "Windsor Grande Residences",
}
# Reuse the canonical Imperial Heights (has the web profile) — never create a 3rd.
BUILDING_ID_OVERRIDE = {"Imperial Heights": "0e72db71-8b93-4ecd-879c-17d8d8f2b206"}
def resolve_building_id(name: str, merge_label: str) -> str | None:
    if name in BUILDING_ID_OVERRIDE:
        return BUILDING_ID_OVERRIDE[name]
    code, out = run_psql(f"SELECT id FROM buildings WHERE name = {lit(name)} ORDER BY created_at LIMIT 1;")
    if code == 0 and out.strip():
        return out.strip().split("\t")[0]
    # create it
    code, out = run_psql(
        f"INSERT INTO buildings (name, metadata) VALUES ({lit(name)}, "
        f"jsonb_build_object('created_by','bulk_attach','merge_label',{lit(merge_label)})) RETURNING id;")
    return out.strip().split("\t")[0] if code == 0 else None

ROLE_CASE = ("CASE c.contact_type WHEN 'owner' THEN 'owner' WHEN 'tenant' THEN 'tenant' "
             "WHEN 'agent' THEN 'broker' WHEN 'buyer' THEN 'buyer' WHEN 'seller' THEN 'seller' ELSE 'unknown' END")

def target_select_sql(batch_label: str, merge_label: str) -> str:
    # One row per merged canonical contact in this batch, with its best unit hint.
    return f"""
SELECT DISTINCT ON (c.id)
  c.id AS contact_id, c.contact_type, cml.contact_import_row_id,
  cph.id AS hint_id, NULLIF(TRIM(cph.wing), '') AS wing, NULLIF(TRIM(cph.unit_number), '') AS unit_number
FROM contacts c
JOIN canonical_merge_links cml ON cml.canonical_contact_id = c.id AND cml.merge_action = 'create_contact'
JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id AND cmb.merge_label = {lit(merge_label)}
JOIN import_batches ib ON ib.id = c.import_batch_id AND ib.metadata->>'batch_label' = {lit(batch_label)}
LEFT JOIN contact_property_hints cph ON cph.contact_import_row_id = cml.contact_import_row_id
ORDER BY c.id, (cph.unit_number IS NULL), cph.created_at"""

def dry_run(batch_label: str, building_name: str, merge_label: str) -> int:
    sql = f"WITH target AS ({target_select_sql(batch_label, merge_label)})\n" + """
SELECT count(*) AS contacts,
       count(*) FILTER (WHERE unit_number IS NOT NULL) AS with_unit,
       count(DISTINCT unit_number) AS distinct_units
FROM target;"""
    code, out = run_psql(sql)
    if code != 0:
        print(out)
        return code
    c, u, du = (out.strip().split("\t") + ["0", "0", "0"])[:3]
    print(f"Bulk attach DRY RUN — batch {batch_label} -> building '{building_name}'")
    print(f"  contacts to attach: {c}")
    print(f"  with a unit hint:   {u}  (distinct units: {du})")
    print("  Run with --apply --real-ok to create the building/units/relationships.")
    return 0

def apply(batch_label: str, building_name: str, merge_label: str, rel_label: str) -> int:
    bid = resolve_building_id(building_name, merge_label)
    if not bid:
        print("Could not resolve/create building.")
        return 1
    # Build the per-contact target as a TEMP TABLE so the unit inserts below are
    # visible to the relationship inserts (data-modifying CTEs would not be).
    sql = f"""
BEGIN;
CREATE TEMP TABLE tmp_target AS
{target_select_sql(batch_label, merge_label)};

-- 1) create any missing units for this building from the hints
INSERT INTO building_units (id, building_id, building_name, wing, unit_number, canonical_status, source_import_row_id, confidence)
SELECT gen_random_uuid(), {lit(bid)}, {lit(building_name)}, t.wing, t.unit_number, 'active', t.contact_import_row_id, 0.7
FROM (SELECT DISTINCT wing, unit_number, (min(contact_import_row_id::text))::uuid AS contact_import_row_id
      FROM tmp_target WHERE unit_number IS NOT NULL GROUP BY wing, unit_number) t
WHERE NOT EXISTS (SELECT 1 FROM building_units bu WHERE bu.building_id = {lit(bid)}
                    AND COALESCE(bu.unit_number,'') = COALESCE(t.unit_number,'')
                    AND COALESCE(bu.wing,'') = COALESCE(t.wing,''));

-- 2) create one relationship per contact (skip if already present)
INSERT INTO contact_property_relationships
  (id, contact_id, building_id, building_unit_id, source_contact_import_row_id, source_property_hint_id,
   relationship_type, relationship_status, confidence, notes, raw_context)
SELECT gen_random_uuid(), c.id, {lit(bid)}, bu.id, t.contact_import_row_id, t.hint_id,
       {ROLE_CASE}, 'active', 0.7, 'Bulk attach from import.',
       jsonb_build_object('rel_label', {lit(rel_label)}, 'bulk_attach', true)
FROM tmp_target t
JOIN contacts c ON c.id = t.contact_id
LEFT JOIN building_units bu ON bu.building_id = {lit(bid)}
   AND COALESCE(bu.unit_number,'') = COALESCE(t.unit_number,'')
   AND COALESCE(bu.wing,'') = COALESCE(t.wing,'')
WHERE NOT EXISTS (
  SELECT 1 FROM contact_property_relationships r
  WHERE r.contact_id = c.id AND r.building_id = {lit(bid)}
    AND COALESCE(r.building_unit_id::text,'') = COALESCE(bu.id::text,''));

DROP TABLE tmp_target;
COMMIT;
SELECT 'relationships_created', count(*) FROM contact_property_relationships
WHERE raw_context->>'rel_label' = {lit(rel_label)};
"""
    code, out = run_psql(sql)
    if code != 0:
        print(f"Attach failed: {out}")
        return code
    print(f"Bulk attach applied (rel_label {rel_label}, building {building_name}):")
    print(out)
    return 0

def rollback(rel_label: str) -> int:
    code, out = run_psql(
        f"DELETE FROM contact_property_relationships WHERE raw_context->>'rel_label' = {lit(rel_label)};")
    print(out if code == 0 else f"Rollback failed: {out}")
    return code

def main() -> int:
    p = argparse.ArgumentParser(description="Dedup-aware bulk attach to buildings. Dry-run by default.")
    p.add_argument("--batch-label")
    p.add_argument("--building-name")
    p.add_argument("--merge-label", default="REAL_BULK_MERGE_001")
    p.add_argument("--rel-label")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--real-ok", action="store_true")
    p.add_argument("--rollback", action="store_true")
    args = p.parse_args()

    if args.rollback:
        if not args.rel_label:
            print("--rollback needs --rel-label.")
            return 1
        if not (args.apply and args.real_ok):
            print(f"Rollback dry-run. Would delete relationships tagged '{args.rel_label}'. Add --apply --real-ok.")
            return 0
        return rollback(args.rel_label)

    if not args.batch_label:
        print("--batch-label is required.")
        return 1
    building = args.building_name or BATCH_BUILDING.get(args.batch_label)
    if not building:
        print(f"No building mapping for {args.batch_label}; pass --building-name.")
        return 1
    rel_label = args.rel_label or f"REAL_ATTACH_{args.batch_label}"

    if not args.apply:
        return dry_run(args.batch_label, building, args.merge_label)
    if not args.real_ok:
        print("Refusing real attach without --real-ok.")
        return 1
    return apply(args.batch_label, building, args.merge_label, rel_label)

if __name__ == "__main__":
    raise SystemExit(main())
