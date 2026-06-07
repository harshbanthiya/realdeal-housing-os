#!/usr/bin/env python3
"""Plan review-to-canonical merge without writing to the database."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


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


def plan_sql(batch_label: str, approved_only: bool, limit: int | None) -> str:
    label = sql_literal(batch_label)
    review_filter = "iri.status = 'approved'" if approved_only else "iri.status IN ('approved', 'pending')"
    limit_sql = f"LIMIT {limit}" if limit else ""
    return f"""
WITH batch AS (
  SELECT id, metadata
  FROM import_batches
  WHERE metadata->>'batch_label' = {label}
),
eligible AS (
  SELECT cir.id
  FROM contact_import_rows cir
  JOIN batch b ON b.id = cir.import_batch_id
  JOIN import_review_items iri ON iri.contact_import_row_id = cir.id
  WHERE iri.review_type = 'merge_candidate'
    AND {review_filter}
    AND (NULLIF(cir.cleaned_display_name, '') IS NOT NULL OR NULLIF(cir.raw_name, '') IS NOT NULL)
    AND (
      EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id)
      OR EXISTS (SELECT 1 FROM lead_requirements lr WHERE lr.contact_import_row_id = cir.id)
    )
  ORDER BY cir.created_at, cir.id
  {limit_sql}
),
skips AS (
  SELECT cir.id,
    CASE
      WHEN iri.id IS NULL THEN 'missing_merge_candidate_review'
      WHEN iri.status <> 'approved' THEN 'not_approved'
      WHEN NULLIF(cir.cleaned_display_name, '') IS NULL AND NULLIF(cir.raw_name, '') IS NULL THEN 'missing_display_name'
      WHEN NOT EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id)
        AND NOT EXISTS (SELECT 1 FROM lead_requirements lr WHERE lr.contact_import_row_id = cir.id) THEN 'missing_method_or_lead'
      ELSE 'other'
    END AS reason
  FROM contact_import_rows cir
  JOIN batch b ON b.id = cir.import_batch_id
  LEFT JOIN import_review_items iri
    ON iri.contact_import_row_id = cir.id
   AND iri.review_type = 'merge_candidate'
  WHERE cir.id NOT IN (SELECT id FROM eligible)
)
SELECT 'batch_count' AS item, count(*) FROM batch
UNION ALL SELECT 'is_real_import', count(*) FILTER (WHERE metadata->>'is_real_import' = 'true') FROM batch
UNION ALL SELECT 'planned_contacts_to_create', count(*) FROM eligible
UNION ALL SELECT 'planned_contact_methods_to_link', count(*) FROM contact_methods WHERE contact_import_row_id IN (SELECT id FROM eligible)
UNION ALL SELECT 'planned_aliases_to_link', 0
UNION ALL SELECT 'planned_lead_requirements_to_link', count(*) FROM lead_requirements WHERE contact_import_row_id IN (SELECT id FROM eligible)
UNION ALL SELECT 'planned_skips', count(*) FROM skips
UNION ALL SELECT 'skip_reason_' || reason, count(*) FROM skips GROUP BY reason
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan canonical merge. No database writes.")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--approved-only", default="true", choices=["true", "false"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    approved_only = args.approved_only == "true"
    if not approved_only:
        print("Refusing non-approved planning for real batches. Use approved-only review flow.")
        return 1
    if args.limit is not None and args.limit < 1:
        print("--limit must be positive.")
        return 1
    print("Canonical merge plan. Counts only; no raw contact values are printed.")
    print(f"batch_label: {args.batch_label}")
    return run_psql(plan_sql(args.batch_label, approved_only, args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
