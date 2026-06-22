#!/usr/bin/env python3
"""Print safe count-only summaries for review queues."""

from __future__ import annotations
from _db import read_env_value, sql_literal

import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def run_psql(sql: str) -> int:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        print("Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env.")
        return 1
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
        "-v",
        "ON_ERROR_STOP=1",
    ]
    return subprocess.run(command, input=sql, text=True, check=False).returncode

def where_clause(batch_label: str, status: str, review_type: str) -> str:
    filters = []
    if batch_label:
        filters.append(f"ib.metadata->>'batch_label' = {sql_literal(batch_label)}")
    if status:
        filters.append(f"iri.status = {sql_literal(status)}")
    if review_type:
        filters.append(f"iri.review_type = {sql_literal(review_type)}")
    return " AND ".join(filters) if filters else "true"

def summary_sql(batch_label: str, status: str, review_type: str) -> str:
    where = where_clause(batch_label, status, review_type)
    batch_filter = f"ib.metadata->>'batch_label' = {sql_literal(batch_label)}" if batch_label else "true"
    return f"""
SELECT iri.status, count(*) AS count
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id
WHERE {where}
GROUP BY iri.status
ORDER BY iri.status;

SELECT iri.review_type, count(*) AS count
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id
WHERE {where}
GROUP BY iri.review_type
ORDER BY iri.review_type;

SELECT iri.priority, count(*) AS count
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id
WHERE {where}
GROUP BY iri.priority
ORDER BY iri.priority;

SELECT cdc.status, cdc.duplicate_strength, count(*) AS count
FROM contact_duplicate_candidates cdc
JOIN import_batches ib ON ib.id = cdc.import_batch_id
WHERE {batch_filter}
GROUP BY cdc.status, cdc.duplicate_strength
ORDER BY cdc.status, cdc.duplicate_strength;

SELECT 'lead_requirements_needing_review' AS item, count(*)
FROM lead_requirements lr
JOIN contact_import_rows cir ON cir.id = lr.contact_import_row_id
JOIN import_batches ib ON ib.id = cir.import_batch_id
WHERE {batch_filter} AND lr.needs_review = true;

SELECT 'contact_import_rows_needing_review' AS item, count(*)
FROM contact_import_rows cir
JOIN import_batches ib ON ib.id = cir.import_batch_id
WHERE {batch_filter} AND cir.needs_review = true;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Print review queue counts only.")
    parser.add_argument("--batch-label", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--review-type", default="")
    args = parser.parse_args()

    print("Review queue summary. Counts only; no raw contact values are printed.")
    if args.batch_label:
        print(f"batch_label: {args.batch_label}")
    if args.status:
        print(f"status_filter: {args.status}")
    if args.review_type:
        print(f"review_type_filter: {args.review_type}")
    return run_psql(summary_sql(args.batch_label, args.status, args.review_type))

if __name__ == "__main__":
    raise SystemExit(main())
