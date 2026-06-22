#!/usr/bin/env python3
"""Phase 5.2 guarded FAKE apply of relationship candidates. Dry-run by default.

Reads property hints from a FAKE_ source batch and materialises the candidate chain
building -> alias -> unit -> relationship -> review item, all tagged fake_batch
FAKE_PHASE_5_2_REL_CANDIDATES / phase 5.2 / source fake_property_relationship_candidates.
Writing needs --apply and --fake-ok. Refuses non-FAKE_ batch labels and refuses to
act on a non-test (real) contact. Counts only; no raw personal values; no outreach.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAND_BATCH = "FAKE_PHASE_5_2_REL_CANDIDATES"
CAND_TAG = ("jsonb_build_object('is_test', true, 'phase', '5.2', 'fake_batch', '"
            + CAND_BATCH + "', 'source', 'fake_property_relationship_candidates')")

def counts_sql() -> str:
    return f"""
SELECT 'cand_buildings' AS item, count(*)::text AS val FROM buildings WHERE metadata->>'fake_batch' = '{CAND_BATCH}'
UNION ALL SELECT 'cand_building_aliases', count(*)::text FROM building_aliases WHERE metadata->>'fake_batch' = '{CAND_BATCH}'
UNION ALL SELECT 'cand_building_units', count(*)::text FROM building_units WHERE metadata->>'fake_batch' = '{CAND_BATCH}'
UNION ALL SELECT 'cand_relationships', count(*)::text FROM contact_property_relationships WHERE raw_context->>'fake_batch' = '{CAND_BATCH}'
UNION ALL SELECT 'cand_review_items', count(*)::text FROM property_relationship_review_items WHERE raw_context->>'fake_batch' = '{CAND_BATCH}'
ORDER BY item;
"""

def hint_probe_sql(batch_label: str) -> str:
    """Return: number of usable hints | number resolving to a real (non-test) contact."""
    return f"""
WITH h AS (
  SELECT cph.id, COALESCE(cph.contact_id, cir.matched_contact_id) AS contact_id
  FROM contact_property_hints cph
  JOIN contact_import_rows cir ON cir.id = cph.contact_import_row_id
  JOIN import_batches ib ON ib.id = cir.import_batch_id
  WHERE ib.source_name = {sql_literal(batch_label)}
)
SELECT
  (SELECT count(*) FROM h)::text,
  (SELECT count(*) FROM h JOIN contacts c ON c.id = h.contact_id WHERE c.is_test = false)::text,
  (SELECT count(*) FROM h WHERE contact_id IS NULL)::text;
"""

def insert_sql(batch_label: str) -> str:
    label = sql_literal(batch_label)
    bld_tag = ("jsonb_build_object('is_test', true, 'phase', '5.2', 'fake_batch', '"
               + CAND_BATCH + "', 'source', 'fake_property_relationship_candidates')")
    return f"""
BEGIN;
WITH h AS (
  SELECT cph.id AS hint_id,
         COALESCE(cph.contact_id, cir.matched_contact_id) AS contact_id,
         NULLIF(btrim(cph.building_name), '') AS building_name,
         NULLIF(btrim(cph.building_code), '') AS building_code,
         NULLIF(btrim(cph.wing), '') AS wing,
         NULLIF(btrim(cph.unit_number), '') AS unit_number,
         COALESCE(NULLIF(btrim(cph.relationship_type), ''), 'owner') AS rel_type,
         cir.id AS cir_id,
         (SELECT sf.id FROM source_files sf WHERE sf.import_batch_id = cir.import_batch_id ORDER BY sf.created_at LIMIT 1) AS source_file_id,
         cir.source_format AS source_format
  FROM contact_property_hints cph
  JOIN contact_import_rows cir ON cir.id = cph.contact_import_row_id
  JOIN import_batches ib ON ib.id = cir.import_batch_id
  JOIN contacts c ON c.id = COALESCE(cph.contact_id, cir.matched_contact_id) AND c.is_test = true
  WHERE ib.source_name = {label}
  ORDER BY cph.created_at, cph.id
  LIMIT 1
),
nb AS (
  INSERT INTO buildings (name, city, notes, metadata)
  SELECT COALESCE(h.building_name, 'FAKE Building (Phase 5.2)'), 'Mumbai',
         'Fake building from Phase 5.2 relationship candidate.', {bld_tag}
  FROM h
  RETURNING id
),
na AS (
  INSERT INTO building_aliases (building_id, alias_text, alias_type, normalized_alias, source_file_id, source_format, status, notes, metadata)
  SELECT nb.id, COALESCE(h.building_code, h.building_name, 'FAKE-ALIAS'), 'import_alias',
         lower(COALESCE(h.building_code, h.building_name, 'fake-alias')), h.source_file_id, h.source_format,
         'pending_review', 'Fake building alias candidate (Phase 5.2).', {CAND_TAG}
  FROM nb, h
  RETURNING id
),
nu AS (
  INSERT INTO building_units (building_id, building_name, building_code, wing, unit_number, canonical_status, source_file_id, source_import_row_id, confidence, metadata)
  SELECT nb.id, h.building_name, h.building_code, h.wing, h.unit_number, 'needs_review',
         h.source_file_id, h.cir_id, 0.700, {CAND_TAG}
  FROM nb, h
  RETURNING id
),
nr AS (
  INSERT INTO contact_property_relationships (contact_id, building_id, building_unit_id, source_contact_import_row_id, source_property_hint_id, source_file_id, relationship_type, relationship_status, confidence, notes, raw_context)
  SELECT h.contact_id, nb.id, nu.id, h.cir_id, h.hint_id, h.source_file_id, h.rel_type, 'pending_review', 0.700,
         'Fake relationship candidate from Phase 5.2 property hint.', {CAND_TAG}
  FROM h, nb, nu
  RETURNING id
)
INSERT INTO property_relationship_review_items (
  contact_property_relationship_id, contact_id, building_id, building_unit_id,
  review_type, status, priority, title, summary, recommended_action, raw_context
)
SELECT nr.id, h.contact_id, nb.id, nu.id, 'owner_tenant_review', 'pending', 'normal',
       'Fake 5.2 relationship candidate',
       'Fake owner_tenant_review created from a Phase 5.2 property hint candidate.',
       'review_relationship', {CAND_TAG}
FROM nr, h, nb, nu;
COMMIT;
{counts_sql()}
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Apply FAKE Phase 5.2 relationship candidates. Dry-run by default.")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    args = parser.parse_args()

    if not args.batch_label.startswith("FAKE_"):
        print("Refusing: --batch-label must start with FAKE_ (this script only applies fake/test candidates).")
        return 1

    print(f"Fake relationship candidate apply. source batch={args.batch_label}; candidate batch={CAND_BATCH}. Counts only.")

    code, probe = run_psql(hint_probe_sql(args.batch_label))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    usable = int(fields[0] or 0)
    real_contact = int(fields[1] or 0)
    missing_contact = int(fields[2] or 0)
    if real_contact > 0:
        print("Refusing: source batch hints resolve to a real (non-test) contact. This script is fake-only.")
        return 1

    code, existing = run_psql(counts_sql())
    if code != 0:
        print(existing)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in existing.splitlines() if "|" in line)

    if not (args.apply and args.fake_ok):
        print("Dry run only. No database writes were made.")
        print(f"usable fake hints in batch: {usable} (missing canonical contact: {missing_contact})")
        print("planned (would create): buildings|1 building_aliases|1 building_units|1 relationships|1 review_items|1")
        print("current candidate rows:")
        print(existing)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if already:
        print("Refusing: candidate rows already exist. Run cleanup_fake_property_relationship_candidates.py first.")
        print(existing)
        return 1
    if usable < 1:
        print("Refusing: no usable fake hint (with a fake/test contact) found in that batch.")
        return 1

    code, output = run_psql(insert_sql(args.batch_label))
    print("Fake candidate rows created:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
