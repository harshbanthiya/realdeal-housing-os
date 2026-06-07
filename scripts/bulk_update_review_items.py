#!/usr/bin/env python3
"""Carefully scoped bulk updates for import review item statuses."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
ALLOWED_STATUSES = {"pending", "approved", "rejected", "skipped", "needs_more_info", "merged_later"}


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={password}",
        "realdeal-postgres",
        "psql",
        "-U",
        user,
        "-d",
        db_name,
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def target_sql(batch_label: str, review_type: str, from_status: str, limit: int | None) -> str:
    limit_sql = f"LIMIT {limit}" if limit is not None else ""
    return f"""
SELECT count(*)
FROM (
  SELECT iri.id
  FROM import_review_items iri
  JOIN import_batches ib ON ib.id = iri.import_batch_id
  WHERE ib.metadata->>'batch_label' = {sql_literal(batch_label)}
    AND iri.review_type = {sql_literal(review_type)}
    AND iri.status = {sql_literal(from_status)}
  ORDER BY iri.created_at, iri.id
  {limit_sql}
) target;
"""


def update_sql(batch_label: str, review_type: str, from_status: str, to_status: str, reviewed_by: str, decision_notes: str, limit: int | None) -> str:
    limit_sql = f"LIMIT {limit}" if limit is not None else ""
    return f"""
WITH target AS (
  SELECT iri.id, iri.status AS old_status
  FROM import_review_items iri
  JOIN import_batches ib ON ib.id = iri.import_batch_id
  WHERE ib.metadata->>'batch_label' = {sql_literal(batch_label)}
    AND iri.review_type = {sql_literal(review_type)}
    AND iri.status = {sql_literal(from_status)}
  ORDER BY iri.created_at, iri.id
  {limit_sql}
),
updated AS (
  UPDATE import_review_items iri
  SET
    status = {sql_literal(to_status)},
    reviewed_by = {sql_literal(reviewed_by)},
    reviewed_at = now(),
    decision_notes = {sql_literal(decision_notes)}
  FROM target
  WHERE iri.id = target.id
  RETURNING iri.id, target.old_status, iri.status AS new_status
),
logged AS (
  INSERT INTO review_action_log (
    import_review_item_id, old_status, new_status, action_type, reviewed_by, decision_notes, raw_context
  )
  SELECT
    id, old_status, new_status, 'bulk_update_review_items', {sql_literal(reviewed_by)}, {sql_literal(decision_notes)},
    jsonb_build_object('script', 'bulk_update_review_items.py', 'batch_label', {sql_literal(batch_label)}, 'review_type', {sql_literal(review_type)})
  FROM updated
  RETURNING id
)
SELECT count(*) FROM updated;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk update review item statuses. Dry-run by default.")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--review-type", required=True)
    parser.add_argument("--from-status", required=True)
    parser.add_argument("--to-status", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", default="")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.to_status not in ALLOWED_STATUSES or args.from_status not in ALLOWED_STATUSES:
        print("Invalid status.")
        print("Allowed statuses: " + ", ".join(sorted(ALLOWED_STATUSES)))
        return 1
    if args.limit is not None and args.limit < 1:
        print("--limit must be positive.")
        return 1

    code, count_text = run_psql(target_sql(args.batch_label, args.review_type, args.from_status, args.limit))
    if code != 0:
        print(count_text)
        return code

    print("Bulk review update summary. Counts only; no raw contact values are printed.")
    print(f"batch_label: {args.batch_label}")
    print(f"review_type: {args.review_type}")
    print(f"from_status: {args.from_status}")
    print(f"to_status: {args.to_status}")
    print(f"matched_rows: {count_text or '0'}")
    if not args.apply:
        print("Dry run only. No database rows were updated.")
        return 0

    code, updated_count = run_psql(update_sql(args.batch_label, args.review_type, args.from_status, args.to_status, args.reviewed_by, args.decision_notes, args.limit))
    if code != 0:
        print(updated_count)
        return code
    print(f"updated_rows: {updated_count or '0'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
