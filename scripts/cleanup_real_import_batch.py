#!/usr/bin/env python3
"""Dry-run or clean up a real source-aware import batch."""

from __future__ import annotations

import argparse

from apply_fake_source_aware_import import psql, read_env_value, sql_literal


def batch_filter(batch_id: str, batch_label: str) -> str:
    base = "metadata->>'source_aware_only' = 'true' AND metadata->>'canonical_merge_done' = 'false'"
    if batch_id:
        return f"{base} AND id = {sql_literal(batch_id)}"
    return f"{base} AND metadata->>'batch_label' = {sql_literal(batch_label)}"


def label_filter(batch_id: str, batch_label: str) -> str:
    if batch_id:
        return f"source_file IN (SELECT metadata->>'batch_label' FROM import_batches WHERE {batch_filter(batch_id, '')})"
    return f"source_file = {sql_literal(batch_label)}"


def count_sql(batch_id: str, batch_label: str) -> str:
    where = batch_filter(batch_id, batch_label)
    alias_where = label_filter(batch_id, batch_label)
    return f"""
WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
SELECT 'import_batches' AS table_name, count(*) FROM target_batches
UNION ALL
SELECT 'source_files', count(*) FROM source_files WHERE import_batch_id IN (SELECT id FROM target_batches)
UNION ALL
SELECT 'contact_import_rows', count(*) FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
UNION ALL
SELECT 'contact_methods', count(*) FROM contact_methods WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
)
UNION ALL
SELECT 'contact_aliases', count(*) FROM contact_aliases WHERE {alias_where}
UNION ALL
SELECT 'contact_property_hints', count(*) FROM contact_property_hints WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
)
UNION ALL
SELECT 'lead_requirements', count(*) FROM lead_requirements WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
)
UNION ALL
SELECT 'inventory_import_rows', count(*) FROM inventory_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
UNION ALL
SELECT 'contact_duplicate_candidates', count(*) FROM contact_duplicate_candidates WHERE import_batch_id IN (SELECT id FROM target_batches)
UNION ALL
SELECT 'import_review_items', count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM target_batches)
UNION ALL
SELECT 'canonical_contacts', count(*) FROM contacts WHERE import_batch_id IN (SELECT id FROM target_batches)
ORDER BY table_name;
"""


def delete_sql(batch_id: str, batch_label: str) -> str:
    where = batch_filter(batch_id, batch_label)
    alias_where = label_filter(batch_id, batch_label)
    return f"""
BEGIN;
WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM import_review_items WHERE import_batch_id IN (SELECT id FROM target_batches);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_duplicate_candidates WHERE import_batch_id IN (SELECT id FROM target_batches);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM inventory_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM lead_requirements WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_methods WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
);

DELETE FROM contact_aliases WHERE {alias_where};

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_property_hints WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches)
);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM target_batches);

WITH target_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM source_files WHERE import_batch_id IN (SELECT id FROM target_batches);

DELETE FROM import_batches WHERE {where};
COMMIT;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or clean up a real source-aware import batch.")
    parser.add_argument("--import-batch-id", default="", help="Target one import batch id.")
    parser.add_argument("--batch-label", default="", help="Target batches by metadata batch_label.")
    parser.add_argument("--apply", action="store_true", help="Delete rows. Dry-run by default.")
    args = parser.parse_args()

    if not args.import_batch_id and not args.batch_label:
        print("Refusing to run: provide --import-batch-id or --batch-label.")
        return 1
    if args.batch_label.upper().startswith("FAKE"):
        print("Refusing to run: this script does not clean fake batches.")
        return 1
    if not read_env_value("POSTGRES_USER") or not read_env_value("POSTGRES_PASSWORD") or not read_env_value("POSTGRES_DB"):
        print("Refusing to run: docker/.env cannot be read safely.")
        return 1

    print("Real source-aware cleanup target only.")
    if args.import_batch_id:
        print("Targeting one explicit import_batch_id.")
    else:
        print(f"Batch label: {args.batch_label}")
    print("Counts before cleanup:")
    result = psql(count_sql(args.import_batch_id, args.batch_label))
    if result != 0:
        return result
    if not args.apply:
        print("Dry run only. Add --apply to delete this source-aware import batch.")
        return 0
    print("Applying real source-aware cleanup.")
    result = psql(delete_sql(args.import_batch_id, args.batch_label))
    if result != 0:
        return result
    print("Counts after cleanup:")
    return psql(count_sql(args.import_batch_id, args.batch_label))


if __name__ == "__main__":
    raise SystemExit(main())
