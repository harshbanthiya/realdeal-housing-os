#!/usr/bin/env python3
"""Print safe count-only NocoDB review summary for one import batch."""

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

def summary_sql(batch_label: str) -> str:
    label = sql_literal(batch_label)
    return f"""
WITH target_batches AS (
  SELECT id FROM import_batches WHERE metadata->>'batch_label' = {label}
)
SELECT 'canonical_contacts_total' AS item, count(*) FROM contacts
UNION ALL SELECT 'dashboard_rows', count(*) FROM vw_review_dashboard_summary WHERE batch_label = {label}
UNION ALL SELECT 'batch_sources_rows', count(*) FROM vw_review_batch_sources WHERE batch_label = {label}
UNION ALL SELECT 'contact_methods_rows', count(*) FROM vw_review_contact_methods WHERE batch_label = {label}
UNION ALL SELECT 'business_leads_rows', count(*) FROM vw_review_business_leads WHERE batch_label = {label}
UNION ALL SELECT 'duplicate_candidate_rows', count(*) FROM vw_review_duplicate_candidates WHERE batch_label = {label}
UNION ALL SELECT 'review_queue_rows', count(*) FROM vw_review_queue WHERE batch_label = {label}
UNION ALL SELECT 'pending_review_items', count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM target_batches) AND status = 'pending'
UNION ALL SELECT 'approved_review_items', count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM target_batches) AND status = 'approved'
UNION ALL SELECT 'rejected_review_items', count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM target_batches) AND status = 'rejected'
ORDER BY item;

SELECT review_type, status, count(*) AS count
FROM import_review_items
WHERE import_batch_id IN (
  SELECT id FROM import_batches WHERE metadata->>'batch_label' = {label}
)
GROUP BY review_type, status
ORDER BY review_type, status;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Print safe count-only review summary for a batch.")
    parser.add_argument("--batch-label", required=True, help="Import batch label to summarize.")
    args = parser.parse_args()
    print("NocoDB review summary. Counts only; no raw contact values are printed.")
    print(f"Batch label: {args.batch_label}")
    result = run_psql(summary_sql(args.batch_label))
    if result != 0:
        return result
    print("Inspect in NocoDB: http://localhost:8080")
    print("Recommended views: vw_review_dashboard_summary, vw_review_batch_sources, vw_review_business_leads, vw_review_contact_methods, vw_review_duplicate_candidates, vw_review_queue")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
