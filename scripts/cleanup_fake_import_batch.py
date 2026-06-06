#!/usr/bin/env python3
"""Clean up fake Phase 3.4 source-aware import rows."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
BATCH_LABEL = "FAKE_PHASE_3_4_TEST"
FAKE_SOURCE_MARKER = "FAKE_EXAMPLE_ONLY"


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
    return "'" + str(value).replace("'", "''") + "'"


def psql(sql: str) -> int:
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


def batch_filter(batch_id: str) -> str:
    if batch_id:
        return f"id = {sql_literal(batch_id)} AND metadata->>'batch_label' = {sql_literal(BATCH_LABEL)}"
    return f"metadata->>'batch_label' = {sql_literal(BATCH_LABEL)}"


def count_sql(batch_id: str) -> str:
    where = batch_filter(batch_id)
    marker = sql_literal(FAKE_SOURCE_MARKER)
    return f"""
WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
SELECT 'import_batches' AS table_name, count(*) FROM fake_batches
UNION ALL
SELECT 'source_files', count(*) FROM source_files WHERE import_batch_id IN (SELECT id FROM fake_batches)
UNION ALL
SELECT 'contact_import_rows', count(*) FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
UNION ALL
SELECT 'contact_methods', count(*) FROM contact_methods WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
)
UNION ALL
SELECT 'contact_aliases', count(*) FROM contact_aliases WHERE source_file = {marker}
UNION ALL
SELECT 'contact_property_hints', count(*) FROM contact_property_hints WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
)
UNION ALL
SELECT 'lead_requirements', count(*) FROM lead_requirements WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
)
UNION ALL
SELECT 'inventory_import_rows', count(*) FROM inventory_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
UNION ALL
SELECT 'contact_duplicate_candidates', count(*) FROM contact_duplicate_candidates WHERE import_batch_id IN (SELECT id FROM fake_batches)
UNION ALL
SELECT 'import_review_items', count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM fake_batches)
ORDER BY table_name;
"""


def delete_sql(batch_id: str) -> str:
    where = batch_filter(batch_id)
    marker = sql_literal(FAKE_SOURCE_MARKER)
    return f"""
BEGIN;
WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM import_review_items WHERE import_batch_id IN (SELECT id FROM fake_batches);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_duplicate_candidates WHERE import_batch_id IN (SELECT id FROM fake_batches);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM inventory_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM lead_requirements WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_methods WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
);

DELETE FROM contact_aliases WHERE source_file = {marker};

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_property_hints WHERE contact_import_row_id IN (
  SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches)
);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM fake_batches);

WITH fake_batches AS (
  SELECT id FROM import_batches WHERE {where}
)
DELETE FROM source_files WHERE import_batch_id IN (SELECT id FROM fake_batches);

DELETE FROM import_batches WHERE {where};
COMMIT;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or clean up fake Phase 3.4 import rows.")
    parser.add_argument("--import-batch-id", default="", help="Optional fake import_batch_id to target.")
    parser.add_argument("--apply", action="store_true", help="Delete fake rows. Dry-run by default.")
    args = parser.parse_args()

    if not read_env_value("POSTGRES_USER") or not read_env_value("POSTGRES_PASSWORD") or not read_env_value("POSTGRES_DB"):
        print("Refusing to run: docker/.env cannot be read safely.")
        return 1

    print("Fake cleanup target only.")
    print(f"Batch label: {BATCH_LABEL}")
    if args.import_batch_id:
        print("Targeting one explicit fake import_batch_id.")
    else:
        print("Targeting all fake Phase 3.4 batches.")
    print("Counts before cleanup:")
    result = psql(count_sql(args.import_batch_id))
    if result != 0:
        return result
    if not args.apply:
        print("Dry run only. Add --apply to delete fake rows.")
        return 0
    print("Applying fake cleanup.")
    result = psql(delete_sql(args.import_batch_id))
    if result != 0:
        return result
    print("Counts after cleanup:")
    return psql(count_sql(args.import_batch_id))


if __name__ == "__main__":
    raise SystemExit(main())
