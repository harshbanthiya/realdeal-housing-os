#!/usr/bin/env python3
"""Apply review-to-canonical merge.

Two modes:
  * Fake/test mode (FAKE_ labels, --test-ok): unchanged Phase 3.8 behaviour.
  * Real mode (Phase 4, --real-ok): creates AT MOST ONE canonical contact from a
    single approved 'merge_candidate' review item, behind strict guards. Counts
    only are printed; no raw contact values are ever emitted. No communications
    are sent by this script under any flag.

Real mode requires ALL of: --apply --real-ok --batch-label --merge-label
--review-item-id. See main() for the full refusal matrix.
"""

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


# --- Phase 4 real-mode: single approved review item, maximum guardrails --------

# The one real batch real canonical merge is currently allowed for. Any other
# batch requires the explicit --allow-other-batch escape hatch.
ALLOWED_REAL_BATCH = "REAL_PHASE_3_5_TEST_001"


def real_guard_sql(batch_label: str, merge_label: str, review_item_id: str) -> str:
    """One row of booleans/counts used to gate a real merge. Read-only."""
    label = sql_literal(batch_label)
    rid = sql_literal(review_item_id)
    mlabel = sql_literal(merge_label)
    return f"""
WITH ri AS (
  SELECT id, review_type, status, contact_import_row_id AS row_id, import_batch_id
  FROM import_review_items WHERE id = {rid}
),
b AS (
  SELECT id, source_name, metadata->>'batch_label' AS batch_label
  FROM import_batches
  WHERE source_name = {label} OR metadata->>'batch_label' = {label}
)
SELECT
  (SELECT count(*) FROM ri),
  (SELECT count(*) FROM b),
  COALESCE((SELECT review_type = 'merge_candidate' FROM ri), false),
  COALESCE((SELECT status = 'approved' FROM ri), false),
  COALESCE((SELECT ri.import_batch_id = b.id FROM ri, b), false),
  COALESCE((SELECT source_name = '{ALLOWED_REAL_BATCH}' FROM b), false),
  EXISTS (
    SELECT 1 FROM canonical_merge_links cml
    JOIN contacts c ON c.id = cml.canonical_contact_id
    WHERE cml.contact_import_row_id = (SELECT row_id FROM ri)
      AND cml.merge_action = 'create_contact'
  ),
  EXISTS (
    SELECT 1 FROM contacts c
    WHERE c.metadata->>'source_import_row_id' = (SELECT row_id::text FROM ri)
  ),
  EXISTS (
    SELECT 1 FROM contact_duplicate_candidates dc
    WHERE dc.status = 'pending_review'
      AND (dc.contact_import_row_id_1 = (SELECT row_id FROM ri)
        OR dc.contact_import_row_id_2 = (SELECT row_id FROM ri))
  ),
  EXISTS (SELECT 1 FROM canonical_merge_batches WHERE merge_label = {mlabel}),
  COALESCE((SELECT count(*) FROM contact_methods WHERE contact_import_row_id = (SELECT row_id FROM ri)), 0),
  COALESCE((SELECT count(*) FROM lead_requirements WHERE contact_import_row_id = (SELECT row_id FROM ri)), 0);
"""


def real_merge_sql(batch_label: str, merge_label: str, review_item_id: str) -> str:
    """Transactional real merge for exactly one approved review item."""
    label = sql_literal(batch_label)
    rid = sql_literal(review_item_id)
    mlabel = sql_literal(merge_label)
    return f"""
BEGIN;

CREATE TEMP TABLE tmp_merge_batch AS SELECT gen_random_uuid() AS id;

INSERT INTO canonical_merge_batches (
  id, merge_label, import_batch_id, is_test, source_description, status, metadata
)
SELECT
  t.id,
  {mlabel},
  ib.id,
  false,
  'Phase 4 first real canonical merge (single approved review item).',
  'applied',
  jsonb_build_object(
    'batch_label', {label},
    'phase', '4',
    'first_real_canonical_merge', true,
    'source_aware_only', false,
    'communication_sent', false,
    'review_item_id', {rid}
  )
FROM tmp_merge_batch t
CROSS JOIN import_batches ib
WHERE ib.source_name = {label} OR ib.metadata->>'batch_label' = {label};

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
  (SELECT sf.id FROM source_files sf
     WHERE sf.import_batch_id = cir.import_batch_id
       AND (sf.stored_relative_path = cir.source_file OR sf.original_file_name = cir.source_file)
     ORDER BY sf.created_at LIMIT 1) AS source_file_id
FROM import_review_items iri
JOIN contact_import_rows cir ON cir.id = iri.contact_import_row_id
JOIN import_batches ib ON ib.id = cir.import_batch_id
WHERE iri.id = {rid}
  AND iri.review_type = 'merge_candidate'
  AND iri.status = 'approved'
  AND (ib.source_name = {label} OR ib.metadata->>'batch_label' = {label})
  AND (NULLIF(cir.cleaned_display_name, '') IS NOT NULL OR NULLIF(cir.raw_name, '') IS NOT NULL);

-- Hard guarantee: at most one canonical contact per real merge.
DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_merge_eligible) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 eligible row, got %.', (SELECT count(*) FROM tmp_merge_eligible);
  END IF;
END $$;

INSERT INTO contacts (
  id, full_name, contact_type, company_name, source, status, tags, notes,
  import_batch_id, metadata, is_test, source_import_batch_id, source_merge_batch_id, canonical_status
)
SELECT
  canonical_contact_id,
  COALESCE(NULLIF(cleaned_display_name, ''), NULLIF(raw_name, '')),
  'lead',
  NULL,
  {label},
  'active',
  ARRAY['real', 'phase_4', 'canonical_merge']::text[],
  'Real canonical contact created by Phase 4 first real canonical merge.',
  import_batch_id,
  jsonb_build_object(
    'phase', '4',
    'first_real_canonical_merge', true,
    'source_import_row_id', contact_import_row_id,
    'review_item_id', review_item_id
  ),
  false,
  import_batch_id,
  (SELECT id FROM tmp_merge_batch),
  'active'
FROM tmp_merge_eligible;

INSERT INTO canonical_merge_links (
  merge_batch_id, import_batch_id, contact_import_row_id, canonical_contact_id,
  source_file_id, merge_action, review_item_id, confidence, notes, metadata
)
SELECT
  (SELECT id FROM tmp_merge_batch),
  import_batch_id, contact_import_row_id, canonical_contact_id, source_file_id,
  'create_contact', review_item_id, 1.0,
  'Created real canonical contact from approved real review item.',
  jsonb_build_object('phase', '4')
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
  t.import_batch_id, t.contact_import_row_id, t.canonical_contact_id, t.source_file_id,
  'link_method', t.review_item_id, 1.0,
  'Linked real contact method to real canonical contact.',
  jsonb_build_object('phase', '4', 'contact_method_id', cm.id)
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
  t.import_batch_id, t.contact_import_row_id, t.canonical_contact_id, t.source_file_id,
  'link_lead_requirement', t.review_item_id, 1.0,
  'Linked real lead requirement to real canonical contact.',
  jsonb_build_object('phase', '4', 'lead_requirement_id', lr.id)
FROM tmp_merge_eligible t
JOIN lead_requirements lr ON lr.contact_import_row_id = t.contact_import_row_id;

UPDATE canonical_merge_batches cmb
SET
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
  metadata = cmb.metadata || jsonb_build_object('canonical_merge_real_enabled', true)
WHERE cmb.id = (SELECT id FROM tmp_merge_batch);

COMMIT;

SELECT 'canonical_contacts_created' AS item, canonical_contacts_created FROM canonical_merge_batches WHERE merge_label = {mlabel}
UNION ALL SELECT 'contact_methods_linked', contact_methods_linked FROM canonical_merge_batches WHERE merge_label = {mlabel}
UNION ALL SELECT 'lead_requirements_linked', lead_requirements_linked FROM canonical_merge_batches WHERE merge_label = {mlabel}
UNION ALL SELECT 'canonical_merge_links', count(*)::integer FROM canonical_merge_links cml JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id WHERE cmb.merge_label = {mlabel}
ORDER BY item;
"""


def run_real_merge(args) -> int:
    if not args.review_item_id:
        print("Refusing real merge: --review-item-id is required.")
        return 1
    if not args.batch_label:
        print("Refusing real merge: --batch-label is required.")
        return 1
    if not args.merge_label:
        print("Refusing real merge: --merge-label is required.")
        return 1
    if args.limit is not None and args.limit != 1:
        print("Refusing real merge: only one review item at a time (--limit must be 1 if set).")
        return 1
    if args.merge_label.startswith("FAKE_") or args.batch_label.startswith("FAKE_"):
        print("Refusing real merge: real labels must not start with FAKE_.")
        return 1

    code, status = run_psql(real_guard_sql(args.batch_label, args.merge_label, args.review_item_id), tuples_only=True)
    if code != 0:
        print(status)
        return code
    f = status.split("|") if status else []
    if len(f) < 12:
        print("Refusing real merge: guard query returned no usable result.")
        return 1

    def b(i: int) -> bool:
        return f[i].strip() == "t"

    ri_exists = int(f[0] or 0)
    batch_exists = int(f[1] or 0)
    is_merge_candidate = b(2)
    is_approved = b(3)
    row_in_batch = b(4)
    is_allowed_batch = b(5)
    canonical_already_linked = b(6)
    contact_already_for_row = b(7)
    unresolved_dup_for_row = b(8)
    merge_label_used = b(9)
    methods_for_row = int(f[10] or 0)
    leads_for_row = int(f[11] or 0)

    if ri_exists != 1:
        print("Refusing real merge: review item id not found (expected exactly 1).")
        return 1
    if batch_exists != 1:
        print("Refusing real merge: expected exactly one import batch for label.")
        return 1
    if not is_merge_candidate:
        print("Refusing real merge: review item is not type 'merge_candidate'.")
        return 1
    if not is_approved:
        print("Refusing real merge: review item is not 'approved'.")
        return 1
    if not row_in_batch:
        print("Refusing real merge: review item does not belong to the named batch.")
        return 1
    if not is_allowed_batch and not args.allow_other_batch:
        print(f"Refusing real merge: batch is not {ALLOWED_REAL_BATCH}. Pass --allow-other-batch to override.")
        return 1
    if canonical_already_linked or contact_already_for_row:
        print("Refusing real merge: a canonical contact is already linked for that import row.")
        return 1
    if unresolved_dup_for_row:
        print("Refusing real merge: an unresolved duplicate candidate exists for that import row.")
        return 1
    if merge_label_used:
        print("Refusing real merge: merge label already exists. Choose a new --merge-label.")
        return 1

    planned_links = 1 + methods_for_row + leads_for_row
    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("item|count")
        print("planned_canonical_contacts|1")
        print(f"planned_contact_methods_to_link|{methods_for_row}")
        print(f"planned_lead_requirements_to_link|{leads_for_row}")
        print(f"planned_canonical_merge_links|{planned_links}")
        print("communication_sent|false")
        print("Applying requires --apply.")
        return 0

    code, output = run_psql(real_merge_sql(args.batch_label, args.merge_label, args.review_item_id))
    print(output)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply canonical merge (fake/test or guarded real mode).")
    parser.add_argument("--batch-label", required=True)
    parser.add_argument("--merge-label", required=True)
    parser.add_argument("--review-item-id", help="Required for real mode: the single approved merge_candidate review item.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--test-ok", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--allow-other-batch", action="store_true", help="Permit a real merge on a batch other than the allowed one.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("--limit must be positive.")
        return 1

    # Phase 4 real mode is gated entirely behind --real-ok.
    if args.real_ok:
        return run_real_merge(args)

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
        print("This is a real batch. Real canonical merge requires --real-ok.")
        return 1
    if fake_count != 1 or not args.batch_label.startswith("FAKE_"):
        print("Refusing merge: fake mode only allows fake/test batches.")
        return 1
    if not args.merge_label.startswith("FAKE_"):
        print("Refusing merge: fake canonical merge label must start with FAKE_.")
        return 1
    if not args.apply or not args.test_ok:
        print("Dry run only. No canonical contacts were created.")
        print("Writing fake canonical contacts requires --apply and --test-ok.")
        return 0

    code, output = run_psql(merge_sql(args.batch_label, args.merge_label, args.limit))
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
