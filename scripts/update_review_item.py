#!/usr/bin/env python3
"""Safely update one import review item status."""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"pending", "approved", "rejected", "skipped", "needs_more_info", "merged_later"}
def item_query(review_item_id: str) -> str:
    return f"""
SELECT
  iri.id,
  iri.status,
  iri.review_type,
  COALESCE(ib.metadata->>'batch_label', ''),
  COALESCE(iri.created_at::text, ''),
  COALESCE(iri.reviewed_at::text, '')
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id
WHERE iri.id = {sql_literal(review_item_id)};
"""

def update_sql(review_item_id: str, status: str, reviewed_by: str, decision_notes: str) -> str:
    return f"""
WITH old_row AS (
  SELECT iri.id, iri.status AS old_status
  FROM import_review_items iri
  WHERE iri.id = {sql_literal(review_item_id)}
),
updated AS (
  UPDATE import_review_items iri
  SET
    status = {sql_literal(status)},
    reviewed_by = {sql_literal(reviewed_by)},
    reviewed_at = now(),
    decision_notes = {sql_literal(decision_notes)}
  FROM old_row
  WHERE iri.id = old_row.id
  RETURNING iri.id, old_row.old_status, iri.status AS new_status
)
INSERT INTO review_action_log (
  import_review_item_id, old_status, new_status, action_type, reviewed_by, decision_notes, raw_context
)
SELECT
  id, old_status, new_status, 'update_review_item', {sql_literal(reviewed_by)}, {sql_literal(decision_notes)},
  jsonb_build_object('script', 'update_review_item.py')
FROM updated;
"""

def print_item(prefix: str, row_text: str, new_status: str | None = None, reviewed_at_override: str | None = None) -> None:
    fields = row_text.split("\t")
    while len(fields) < 6:
        fields.append("")
    if len(fields) < 5:
        print("Review item not found.")
        return
    print(prefix)
    print(f"review_item_id: {fields[0]}")
    print(f"old_status: {fields[1]}")
    if new_status:
        print(f"new_status: {new_status}")
    print(f"review_type: {fields[2]}")
    print(f"batch_label: {fields[3]}")
    print(f"created_at: {fields[4]}")
    print(f"reviewed_at: {reviewed_at_override if reviewed_at_override is not None else fields[5]}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Update one import_review_items status. Dry-run by default.")
    parser.add_argument("--review-item-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.status not in ALLOWED_STATUSES:
        print("Invalid status.")
        print("Allowed statuses: " + ", ".join(sorted(ALLOWED_STATUSES)))
        return 1

    code, row_text = run_psql(item_query(args.review_item_id))
    if code != 0:
        print(row_text)
        return code
    if not row_text:
        print("Review item not found.")
        return 1

    if not args.apply:
        print_item("Dry run only. No database rows were updated.", row_text, args.status)
        return 0

    code, output = run_psql(update_sql(args.review_item_id, args.status, args.reviewed_by, args.decision_notes))
    if code != 0:
        print(output)
        return code

    old_row = row_text
    code, updated_row = run_psql(item_query(args.review_item_id))
    if code != 0:
        print(updated_row)
        return code
    updated_fields = updated_row.split("\t")
    reviewed_at = updated_fields[5] if len(updated_fields) > 5 else ""
    print_item("Review item updated.", old_row, args.status, reviewed_at)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
