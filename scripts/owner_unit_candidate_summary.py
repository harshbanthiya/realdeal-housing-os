#!/usr/bin/env python3
"""Summarize owner/unit audit rows for future canonical-contact review.

Read-only. Prints counts and safe row/review IDs only; never prints names, phone
numbers, emails, websites, addresses, or raw row payloads.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def source_filter(source_format: str | None) -> str:
    if not source_format:
        return ""
    return f"AND cir.source_format = {sql_literal(source_format)}"

def status_filter(status: str | None) -> str:
    if not status:
        return ""
    return f"AND COALESCE(mri.status, '') = {sql_literal(status)}"

def summary_sql(batch_label: str, source_format: str | None, status: str | None, limit: int) -> str:
    label = sql_literal(batch_label)
    return f"""
WITH batch AS (
  SELECT id FROM import_batches
  WHERE source_name = {label} OR metadata->>'batch_label' = {label}
),
base AS (
  SELECT
    cir.id,
    cir.source_row_number,
    cir.source_format,
    cir.cleaned_display_name,
    cir.raw_name,
    EXISTS (
      SELECT 1 FROM contact_methods cm
      WHERE cm.contact_import_row_id = cir.id
    ) AS has_method,
    (SELECT count(*) FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) AS method_count,
    EXISTS (
      SELECT 1 FROM contact_property_hints cph
      WHERE cph.contact_import_row_id = cir.id
    ) AS has_property_hint,
    EXISTS (
      SELECT 1 FROM inventory_import_rows iir
      WHERE iir.owner_contact_import_row_id = cir.id
    ) AS has_inventory_hint,
    EXISTS (
      SELECT 1 FROM contact_property_hints cph
      WHERE cph.contact_import_row_id = cir.id
        AND (NULLIF(btrim(cph.unit_number), '') IS NOT NULL OR NULLIF(btrim(cph.wing), '') IS NOT NULL)
    ) OR EXISTS (
      SELECT 1 FROM inventory_import_rows iir
      WHERE iir.owner_contact_import_row_id = cir.id
        AND (NULLIF(btrim(iir.unit_number), '') IS NOT NULL OR NULLIF(btrim(iir.wing), '') IS NOT NULL)
    ) AS has_unit_hint,
    EXISTS (
      SELECT 1 FROM contact_property_hints cph
      WHERE cph.contact_import_row_id = cir.id
        AND (NULLIF(btrim(cph.building_name), '') IS NOT NULL OR NULLIF(btrim(cph.building_code), '') IS NOT NULL)
    ) OR EXISTS (
      SELECT 1 FROM inventory_import_rows iir
      WHERE iir.owner_contact_import_row_id = cir.id
        AND (NULLIF(btrim(iir.building_name), '') IS NOT NULL OR NULLIF(btrim(iir.building_code), '') IS NOT NULL)
    ) AS has_building_hint,
    EXISTS (
      SELECT 1 FROM contact_duplicate_candidates dc
      WHERE dc.import_batch_id = cir.import_batch_id
        AND (dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id)
    ) AS duplicate_involved,
    EXISTS (
      SELECT 1 FROM contact_methods cm
      WHERE cm.contact_import_row_id = cir.id AND cm.contact_id IS NOT NULL
    ) OR EXISTS (
      SELECT 1 FROM canonical_merge_links cml
      WHERE cml.contact_import_row_id = cir.id
        AND cml.merge_action = 'create_contact'
    ) AS linked_to_canonical,
    mri.id AS merge_review_item_id,
    mri.status AS merge_review_status,
    EXISTS (
      SELECT 1 FROM import_review_items iri
      WHERE iri.contact_import_row_id = cir.id AND iri.review_type = 'missing_name'
    ) AS has_missing_name_review,
    EXISTS (
      SELECT 1 FROM import_review_items iri
      WHERE iri.contact_import_row_id = cir.id AND iri.review_type IN ('invalid_phone', 'invalid_email')
    ) AS has_invalid_contact_review
  FROM contact_import_rows cir
  JOIN batch b ON b.id = cir.import_batch_id
  LEFT JOIN import_review_items mri
    ON mri.contact_import_row_id = cir.id
   AND mri.review_type = 'merge_candidate'
  WHERE true
  {source_filter(source_format)}
),
classified AS (
  SELECT *,
    CASE
      WHEN linked_to_canonical THEN 'needs_more_info'
      WHEN duplicate_involved THEN 'skip_duplicate_review_first'
      WHEN NOT has_method OR has_invalid_contact_review THEN 'reject_invalid'
      WHEN NULLIF(cleaned_display_name, '') IS NULL AND NULLIF(raw_name, '') IS NULL THEN 'reject_invalid'
      WHEN NOT (has_building_hint AND has_unit_hint AND has_inventory_hint AND has_property_hint) THEN 'needs_more_info'
      ELSE 'approve_for_canonical_contact'
    END AS recommended_action,
    CASE
      WHEN linked_to_canonical THEN 'already_linked_to_canonical'
      WHEN duplicate_involved THEN 'duplicate_review_first'
      WHEN NOT has_method THEN 'missing_valid_contact_method'
      WHEN has_invalid_contact_review THEN 'invalid_contact_method_review'
      WHEN NULLIF(cleaned_display_name, '') IS NULL AND NULLIF(raw_name, '') IS NULL THEN 'missing_name'
      WHEN NOT has_building_hint THEN 'missing_building_hint'
      WHEN NOT has_unit_hint THEN 'missing_unit_hint'
      WHEN NOT has_inventory_hint THEN 'missing_inventory_hint'
      WHEN NOT has_property_hint THEN 'missing_property_hint'
      ELSE 'complete_owner_unit_audit_row'
    END AS reason
  FROM base
),
filtered AS (
  SELECT * FROM classified WHERE true {status_filter(status)}
),
ranked_candidates AS (
  SELECT * FROM filtered
  WHERE recommended_action = 'approve_for_canonical_contact'
  ORDER BY source_row_number NULLS LAST, id
  LIMIT {int(limit)}
),
risky_reasons AS (
  SELECT reason, count(*) AS count
  FROM filtered
  WHERE recommended_action <> 'approve_for_canonical_contact'
  GROUP BY reason
)
SELECT 'total_import_rows' AS item, count(*)::text AS value FROM filtered
UNION ALL SELECT 'rows_with_valid_contact_method', count(*) FILTER (WHERE has_method)::text FROM filtered
UNION ALL SELECT 'rows_with_multiple_contact_methods', count(*) FILTER (WHERE method_count > 1)::text FROM filtered
UNION ALL SELECT 'rows_with_property_hint', count(*) FILTER (WHERE has_property_hint)::text FROM filtered
UNION ALL SELECT 'rows_with_inventory_hint', count(*) FILTER (WHERE has_inventory_hint)::text FROM filtered
UNION ALL SELECT 'rows_with_unit_hint', count(*) FILTER (WHERE has_unit_hint)::text FROM filtered
UNION ALL SELECT 'rows_with_building_hint', count(*) FILTER (WHERE has_building_hint)::text FROM filtered
UNION ALL SELECT 'rows_with_duplicate_candidate_involvement', count(*) FILTER (WHERE duplicate_involved)::text FROM filtered
UNION ALL SELECT 'rows_already_linked_to_canonical', count(*) FILTER (WHERE linked_to_canonical)::text FROM filtered
UNION ALL SELECT 'candidate_rows_safe_for_review', count(*) FILTER (WHERE recommended_action = 'approve_for_canonical_contact')::text FROM filtered
UNION ALL SELECT 'risky_rows', count(*) FILTER (WHERE recommended_action <> 'approve_for_canonical_contact')::text FROM filtered
UNION ALL SELECT 'review_item|' || review_type || '|' || status, count(*)::text
  FROM import_review_items
  WHERE import_batch_id IN (SELECT id FROM batch)
  GROUP BY review_type, status
UNION ALL SELECT 'duplicate_candidate_status|' || status, count(*)::text
  FROM contact_duplicate_candidates
  WHERE import_batch_id IN (SELECT id FROM batch)
  GROUP BY status
UNION ALL SELECT 'risky_reason|' || reason, count::text FROM risky_reasons
UNION ALL SELECT
  'candidate|' || id::text || '|' || COALESCE(merge_review_item_id::text, '') || '|' ||
  COALESCE(source_row_number::text, '') || '|' || COALESCE(source_format, '') || '|' ||
  has_method::text || '|' || method_count::text || '|' ||
  has_building_hint::text || '|' || has_unit_hint::text || '|' ||
  has_inventory_hint::text || '|' || duplicate_involved::text || '|' ||
  recommended_action || '|' || reason,
  '1'
FROM ranked_candidates
ORDER BY item;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize owner/unit canonical-contact candidates. Read-only.")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--status")
    parser.add_argument("--source-format")
    args = parser.parse_args()

    if args.limit < 1:
        print("--limit must be positive.")
        return 1

    print("Owner/unit candidate summary. Read-only; counts and safe IDs only.")
    print(f"batch_label: {args.batch_label}")
    if args.source_format:
        print(f"source_format: {args.source_format}")
    if args.status:
        print(f"status: {args.status}")
    print(f"candidate_limit: {args.limit}")
    code, output = run_psql(summary_sql(args.batch_label, args.source_format, args.status, args.limit))
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
