#!/usr/bin/env python3
"""Apply fake review-to-canonical merge. Real canonical merge is disabled."""

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


def run_psql(sql: str, tuples_only: bool = False) -> tuple[int, str]:
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
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        command.extend(["-At"])
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def batch_status_sql(batch_label: str) -> str:
    return f"""
SELECT
  count(*) AS batch_count,
  count(*) FILTER (WHERE metadata->>'is_real_import' = 'true') AS real_count,
  count(*) FILTER (WHERE metadata->>'is_test' = 'true' OR metadata->>'batch_label' LIKE 'FAKE_%') AS fake_count
FROM import_batches
WHERE metadata->>'batch_label' = {sql_literal(batch_label)};
"""


def merge_sql(batch_label: str, merge_label: str, limit: int | None) -> str:
    limit_sql = f"LIMIT {limit}" if limit else ""
    return f"""
BEGIN;

CREATE TEMP TABLE tmp_merge_batch AS
SELECT gen_random_uuid() AS id;

INSERT INTO canonical_merge_batches (
  id, merge_label, import_batch_id, is_test, source_description, status, metadata
)
SELECT
  t.id,
  {sql_literal(merge_label)},
  ib.id,
  true,
  'Fake Phase 3.8 canonical merge test',
  'created',
  jsonb_build_object('batch_label', {sql_literal(batch_label)}, 'fake_phase', '3.8')
FROM tmp_merge_batch t
CROSS JOIN import_batches ib
WHERE ib.metadata->>'batch_label' = {sql_literal(batch_label)};

CREATE TEMP TABLE tmp_merge_eligible AS
SELECT
  gen_random_uuid() AS canonical_contact_id,
  cir.id AS contact_import_row_id,
  cir.import_batch_id,
  cir.cleaned_display_name,
  cir.raw_name,
  cir.parsed_role,
  cir.source_file,
  cir.source_format,
  iri.id AS review_item_id,
  sf.id AS source_file_id
FROM contact_import_rows cir
JOIN import_batches ib ON ib.id = cir.import_batch_id
JOIN import_review_items iri
  ON iri.contact_import_row_id = cir.id
 AND iri.review_type = 'merge_candidate'
 AND iri.status = 'approved'
LEFT JOIN source_files sf
  ON sf.import_batch_id = cir.import_batch_id
 AND (sf.stored_relative_path = cir.source_file OR sf.original_file_name = cir.source_file OR sf.original_file_name = 'FAKE_EXAMPLE_ONLY')
WHERE ib.metadata->>'batch_label' = {sql_literal(batch_label)}
  AND (NULLIF(cir.cleaned_display_name, '') IS NOT NULL OR NULLIF(cir.raw_name, '') IS NOT NULL)
  AND (
    EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id)
    OR EXISTS (SELECT 1 FROM lead_requirements lr WHERE lr.contact_import_row_id = cir.id)
  )
ORDER BY cir.created_at, cir.id
{limit_sql};

INSERT INTO contacts (
  id, full_name, contact_type, company_name, source, status, tags, notes,
  import_batch_id, metadata, is_test, source_import_batch_id, source_merge_batch_id, canonical_status
)
SELECT
  canonical_contact_id,
  COALESCE(NULLIF(cleaned_display_name, ''), NULLIF(raw_name, ''), 'Fake Imported Contact'),
  'lead',
  NULL,
  {sql_literal(batch_label)},
  'active',
  ARRAY['fake', 'phase_3_8', 'canonical_merge_test']::text[],
  'Fake canonical contact created by Phase 3.8 merge test.',
  import_batch_id,
  jsonb_build_object('fake_phase', '3.8', 'source_import_row_id', contact_import_row_id),
  true,
  import_batch_id,
  (SELECT id FROM tmp_merge_batch),
  'test'
FROM tmp_merge_eligible;

INSERT INTO canonical_merge_links (
  merge_batch_id, import_batch_id, contact_import_row_id, canonical_contact_id,
  source_file_id, merge_action, review_item_id, confidence, notes, metadata
)
SELECT
  (SELECT id FROM tmp_merge_batch),
  import_batch_id,
  contact_import_row_id,
  canonical_contact_id,
  source_file_id,
  'create_contact',
  review_item_id,
  1.0,
  'Created fake canonical contact from approved fake import row.',
  jsonb_build_object('fake_phase', '3.8')
FROM tmp_merge_eligible;

UPDATE contact_methods cm
SET contact_id = t.canonical_contact_id
FROM tmp_merge_eligible t
WHERE cm.contact_import_row_id = t.contact_import_row_id;

INSERT INTO canonical_merge_links (
  merge_batch_id, import_batch_id, contact_import_row_id, canonical_contact_id,
  source_file_id, merge_action, review_item_id, confidence, notes, metadata
)
SELECT
  (SELECT id FROM tmp_merge_batch),
  t.import_batch_id,
  t.contact_import_row_id,
  t.canonical_contact_id,
  t.source_file_id,
  'link_method',
  t.review_item_id,
  1.0,
  'Linked fake contact method to fake canonical contact.',
  jsonb_build_object('fake_phase', '3.8', 'contact_method_id', cm.id)
FROM tmp_merge_eligible t
JOIN contact_methods cm ON cm.contact_import_row_id = t.contact_import_row_id;

UPDATE lead_requirements lr
SET contact_id = t.canonical_contact_id
FROM tmp_merge_eligible t
WHERE lr.contact_import_row_id = t.contact_import_row_id;

INSERT INTO canonical_merge_links (
  merge_batch_id, import_batch_id, contact_import_row_id, canonical_contact_id,
  source_file_id, merge_action, review_item_id, confidence, notes, metadata
)
SELECT
  (SELECT id FROM tmp_merge_batch),
  t.import_batch_id,
  t.contact_import_row_id,
  t.canonical_contact_id,
  t.source_file_id,
  'link_lead_requirement',
  t.review_item_id,
  1.0,
  'Linked fake lead requirement to fake canonical contact.',
  jsonb_build_object('fake_phase', '3.8', 'lead_requirement_id', lr.id)
FROM tmp_merge_eligible t
JOIN lead_requirements lr ON lr.contact_import_row_id = t.contact_import_row_id;

UPDATE canonical_merge_batches cmb
SET
  status = 'applied',
  canonical_contacts_created = (SELECT count(*) FROM tmp_merge_eligible),
  contact_methods_linked = (
    SELECT count(*) FROM contact_methods cm
    WHERE cm.contact_import_row_id IN (SELECT contact_import_row_id FROM tmp_merge_eligible)
  ),
  aliases_linked = 0,
  lead_requirements_linked = (
    SELECT count(*) FROM lead_requirements lr
    WHERE lr.contact_import_row_id IN (SELECT contact_import_row_id FROM tmp_merge_eligible)
  ),
  inventory_hints_linked = 0,
  applied_at = now(),
  metadata = cmb.metadata || jsonb_build_object('canonical_merge_real_enabled', false)
WHERE cmb.id = (SELECT id FROM tmp_merge_batch);

COMMIT;

SELECT 'canonical_contacts_created' AS item, canonical_contacts_created FROM canonical_merge_batches WHERE merge_label = {sql_literal(merge_label)}
UNION ALL SELECT 'contact_methods_linked', contact_methods_linked FROM canonical_merge_batches WHERE merge_label = {sql_literal(merge_label)}
UNION ALL SELECT 'lead_requirements_linked', lead_requirements_linked FROM canonical_merge_batches WHERE merge_label = {sql_literal(merge_label)}
UNION ALL SELECT 'canonical_merge_links', count(*)::integer FROM canonical_merge_links cml JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id WHERE cmb.merge_label = {sql_literal(merge_label)}
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply fake canonical merge. Real canonical merge is disabled.")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--merge-label", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--test-ok", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("--limit must be positive.")
        return 1

    code, status = run_psql(batch_status_sql(args.batch_label), tuples_only=True)
    if code != 0:
        print(status)
        return code
    fields = status.split("|") if status else ["0", "0", "0"]
    batch_count = int(fields[0] or 0)
    real_count = int(fields[1] or 0)
    fake_count = int(fields[2] or 0)
    if batch_count != 1:
        print("Refusing merge: expected exactly one import batch for label.")
        return 1
    if real_count > 0:
        print("Real canonical merge is not enabled yet.")
        return 1
    if fake_count != 1 or not args.batch_label.startswith("FAKE_"):
        print("Refusing merge: Phase 3.8 only allows fake/test batches.")
        return 1
    if not args.merge_label.startswith("FAKE_"):
        print("Refusing merge: fake canonical merge label must start with FAKE_.")
        return 1
    if not args.apply or not args.test_ok:
        print("Dry run only. No canonical contacts were created.")
        print("Writing fake canonical contacts requires --apply and --test-ok.")
        return 0
    if args.real_ok:
        print("Real canonical merge is not enabled yet.")
        return 1

    code, output = run_psql(merge_sql(args.batch_label, args.merge_label, args.limit))
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
