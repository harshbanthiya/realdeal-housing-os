#!/usr/bin/env python3
"""Safely update one duplicate candidate status without merging contacts."""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"pending_review", "not_duplicate", "duplicate_confirmed", "needs_more_info", "skipped"}
def candidate_query(candidate_id: str) -> str:
    return f"""
SELECT
  cdc.id,
  cdc.status,
  COALESCE(cdc.duplicate_strength, ''),
  COALESCE(cdc.candidate_type, ''),
  COALESCE(ib.metadata->>'batch_label', ''),
  COALESCE(cdc.created_at::text, '')
FROM contact_duplicate_candidates cdc
JOIN import_batches ib ON ib.id = cdc.import_batch_id
WHERE cdc.id = {sql_literal(candidate_id)};
"""

def update_sql(candidate_id: str, status: str, reviewed_by: str, decision_notes: str) -> str:
    return f"""
WITH old_row AS (
  SELECT id, status AS old_status
  FROM contact_duplicate_candidates
  WHERE id = {sql_literal(candidate_id)}
),
updated AS (
  UPDATE contact_duplicate_candidates cdc
  SET status = {sql_literal(status)}
  FROM old_row
  WHERE cdc.id = old_row.id
  RETURNING cdc.id, old_row.old_status, cdc.status AS new_status
)
INSERT INTO review_action_log (
  duplicate_candidate_id, old_status, new_status, action_type, reviewed_by, decision_notes, raw_context
)
SELECT
  id, old_status, new_status, 'update_duplicate_candidate', {sql_literal(reviewed_by)}, {sql_literal(decision_notes)},
  jsonb_build_object('script', 'update_duplicate_candidate.py')
FROM updated;
"""

def print_candidate(prefix: str, row_text: str, new_status: str | None = None) -> None:
    fields = row_text.split("\t")
    if len(fields) < 6:
        print("Duplicate candidate not found.")
        return
    print(prefix)
    print(f"candidate_id: {fields[0]}")
    print(f"old_status: {fields[1]}")
    if new_status:
        print(f"new_status: {new_status}")
    print(f"duplicate_strength: {fields[2]}")
    print(f"candidate_type: {fields[3]}")
    print(f"batch_label: {fields[4]}")
    print(f"created_at: {fields[5]}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Update one duplicate candidate status. Dry-run by default.")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.status not in ALLOWED_STATUSES:
        print("Invalid status.")
        print("Allowed statuses: " + ", ".join(sorted(ALLOWED_STATUSES)))
        return 1

    code, row_text = run_psql(candidate_query(args.candidate_id))
    if code != 0:
        print(row_text)
        return code
    if not row_text:
        print("Duplicate candidate not found.")
        return 1

    if not args.apply:
        print_candidate("Dry run only. No database rows were updated.", row_text, args.status)
        return 0

    code, output = run_psql(update_sql(args.candidate_id, args.status, args.reviewed_by, args.decision_notes))
    if code != 0:
        print(output)
        return code
    code, updated_row = run_psql(candidate_query(args.candidate_id))
    if code != 0:
        print(updated_row)
        return code
    print_candidate("Duplicate candidate updated. No contacts were merged.", updated_row, args.status)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
