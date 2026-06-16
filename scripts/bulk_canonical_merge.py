#!/usr/bin/env python3
"""Dedup-aware BULK canonical merge for real import batches.

Promotes safe `merge_candidate` review items (across all real import batches) to
canonical contacts in ONE transaction. "Safe" means the source import row:
  - has a name and at least one contact method or lead requirement,
  - is NOT involved in any unresolved (pending_review) duplicate candidate,
  - is NOT already merged.
Duplicate-involved rows are DEFERRED (left for review) so we never create two
canonical contacts for the same person.

Writes to the same audit tables as the single-item merge (canonical_merge_batches,
canonical_merge_links, contacts.source_merge_batch_id), so it is fully reversible.
Creates NO outreach and sends nothing.

  Dry run (default):   python3 scripts/bulk_canonical_merge.py
  Apply:               python3 scripts/bulk_canonical_merge.py --apply --real-ok [--limit N] [--merge-label L]
  Rollback:            python3 scripts/bulk_canonical_merge.py --rollback --merge-label L --real-ok --apply
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


def lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user, pw, db = read_env_value("POSTGRES_USER"), read_env_value("POSTGRES_PASSWORD"), read_env_value("POSTGRES_DB")
    if not user or not pw or not db:
        return 1, "Missing POSTGRES_* in docker/.env."
    cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={pw}", "realdeal-postgres",
           "psql", "-U", user, "-d", db, "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1"]
    res = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return res.returncode, (res.stdout.rstrip("\n") or res.stderr.strip())


# Eligibility: safe, non-duplicate, not-yet-merged merge candidates in REAL batches.
ELIGIBLE_FROM = """
FROM contact_import_rows cir
JOIN import_batches ib ON ib.id = cir.import_batch_id
 AND COALESCE((ib.metadata->>'is_real_import')::boolean, false)
JOIN import_review_items iri ON iri.contact_import_row_id = cir.id
 AND iri.review_type = 'merge_candidate' AND iri.status IN ('pending', 'approved')
WHERE (NULLIF(cir.cleaned_display_name, '') IS NOT NULL OR NULLIF(cir.raw_name, '') IS NOT NULL)
  AND (EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id)
    OR EXISTS (SELECT 1 FROM lead_requirements lr WHERE lr.contact_import_row_id = cir.id))
  AND NOT EXISTS (SELECT 1 FROM canonical_merge_links cml WHERE cml.contact_import_row_id = cir.id)
  AND NOT EXISTS (SELECT 1 FROM contact_duplicate_candidates dc
                  WHERE dc.status = 'pending_review'
                    AND (dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id))
"""

DEFERRED_DUP_SQL = """
SELECT count(DISTINCT cir.id)
FROM contact_import_rows cir
JOIN import_batches ib ON ib.id = cir.import_batch_id AND COALESCE((ib.metadata->>'is_real_import')::boolean, false)
JOIN import_review_items iri ON iri.contact_import_row_id = cir.id
 AND iri.review_type = 'merge_candidate' AND iri.status IN ('pending', 'approved')
WHERE EXISTS (SELECT 1 FROM contact_duplicate_candidates dc
              WHERE dc.status = 'pending_review'
                AND (dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id))
"""


def dry_run() -> int:
    code, out = run_psql(
        f"SELECT count(DISTINCT cir.id) {ELIGIBLE_FROM};\n")
    if code != 0:
        print(out)
        return code
    safe = out.strip()
    code2, deferred = run_psql(DEFERRED_DUP_SQL + ";")
    print("Dedup-aware bulk canonical merge — DRY RUN (no writes).")
    print(f"  safe to merge (non-duplicate, not yet merged): {safe}")
    print(f"  deferred (duplicate-involved, left for review): {deferred.strip() if code2 == 0 else '?'}")
    print("  Run with --apply --real-ok to create canonical contacts.")
    return 0


def apply_sql(merge_label: str, limit: int | None) -> str:
    limit_sql = f"LIMIT {limit}" if limit else ""
    role_case = (
        "CASE lower(coalesce(e.parsed_role,'')) "
        "WHEN 'owner' THEN 'owner' WHEN 'landlord' THEN 'owner' "
        "WHEN 'tenant' THEN 'tenant' WHEN 'broker' THEN 'agent' WHEN 'agent' THEN 'agent' "
        "WHEN 'buyer' THEN 'buyer' WHEN 'seller' THEN 'seller' ELSE 'lead' END")
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_mb AS SELECT gen_random_uuid() AS id;
INSERT INTO canonical_merge_batches (id, merge_label, import_batch_id, is_test, source_description, status, metadata)
SELECT t.id, {lit(merge_label)}, NULL, false, 'Dedup-aware bulk canonical merge', 'created',
       jsonb_build_object('bulk_merge', true, 'dedup_aware', true)
FROM tmp_mb t;

CREATE TEMP TABLE tmp_eligible AS
SELECT DISTINCT ON (cir.id)
  gen_random_uuid() AS canonical_contact_id,
  cir.id AS contact_import_row_id, cir.import_batch_id,
  cir.cleaned_display_name, cir.raw_name, cir.parsed_role, cir.source_file,
  iri.id AS review_item_id,
  (SELECT sf.id FROM source_files sf WHERE sf.import_batch_id = cir.import_batch_id LIMIT 1) AS source_file_id
{ELIGIBLE_FROM}
ORDER BY cir.id, iri.created_at
{limit_sql};

INSERT INTO contacts (
  id, full_name, contact_type, source, status, tags, notes,
  import_batch_id, metadata, is_test, source_import_batch_id, source_merge_batch_id, canonical_status
)
SELECT
  e.canonical_contact_id,
  COALESCE(NULLIF(e.cleaned_display_name, ''), NULLIF(e.raw_name, ''), 'Imported Contact'),
  {role_case},
  'bulk_merge', 'active',
  ARRAY['real', 'bulk_merge']::text[],
  'Canonical contact from dedup-aware bulk merge.',
  e.import_batch_id,
  jsonb_build_object('source_import_row_id', e.contact_import_row_id, 'bulk_merge', true),
  false, e.import_batch_id, (SELECT id FROM tmp_mb), 'active'
FROM tmp_eligible e;

INSERT INTO canonical_merge_links (merge_batch_id, import_batch_id, contact_import_row_id, canonical_contact_id, source_file_id, merge_action, review_item_id, confidence, notes, metadata)
SELECT (SELECT id FROM tmp_mb), e.import_batch_id, e.contact_import_row_id, e.canonical_contact_id, e.source_file_id, 'create_contact', e.review_item_id, 1.0, 'Bulk merge: created canonical contact.', '{{}}'::jsonb
FROM tmp_eligible e;

UPDATE contact_methods cm SET contact_id = e.canonical_contact_id
FROM tmp_eligible e WHERE cm.contact_import_row_id = e.contact_import_row_id;

UPDATE lead_requirements lr SET contact_id = e.canonical_contact_id
FROM tmp_eligible e WHERE lr.contact_import_row_id = e.contact_import_row_id;

UPDATE import_review_items iri SET status = 'merged', reviewed_at = now(), reviewed_by = 'bulk_merge'
FROM tmp_eligible e WHERE iri.id = e.review_item_id;

UPDATE canonical_merge_batches cmb SET status = 'applied', applied_at = now(),
  canonical_contacts_created = (SELECT count(*) FROM tmp_eligible)
WHERE cmb.id = (SELECT id FROM tmp_mb);
COMMIT;

SELECT 'canonical_contacts_created', canonical_contacts_created FROM canonical_merge_batches WHERE merge_label = {lit(merge_label)};
"""


def rollback_sql(merge_label: str) -> str:
    sel = f"(SELECT id FROM canonical_merge_batches WHERE merge_label = {lit(merge_label)})"
    return f"""
BEGIN;
UPDATE import_review_items SET status = 'pending', reviewed_by = NULL, reviewed_at = NULL
WHERE id IN (SELECT review_item_id FROM canonical_merge_links WHERE merge_batch_id IN {sel} AND merge_action = 'create_contact');
UPDATE contact_methods SET contact_id = NULL WHERE contact_id IN (SELECT canonical_contact_id FROM canonical_merge_links WHERE merge_batch_id IN {sel});
UPDATE lead_requirements SET contact_id = NULL WHERE contact_id IN (SELECT canonical_contact_id FROM canonical_merge_links WHERE merge_batch_id IN {sel});
DELETE FROM canonical_merge_links WHERE merge_batch_id IN {sel};
DELETE FROM contacts WHERE source_merge_batch_id IN {sel};
UPDATE canonical_merge_batches SET status = 'rolled_back' WHERE merge_label = {lit(merge_label)};
COMMIT;
SELECT 'rolled_back', {lit(merge_label)};
"""


def main() -> int:
    p = argparse.ArgumentParser(description="Dedup-aware bulk canonical merge. Dry-run by default.")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--real-ok", action="store_true")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--merge-label", default="REAL_BULK_MERGE_001")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    if args.rollback:
        if not (args.apply and args.real_ok):
            print(f"Rollback dry-run. Would delete canonical contacts from merge '{args.merge_label}'. Add --apply --real-ok to execute.")
            return 0
        code, out = run_psql(rollback_sql(args.merge_label))
        print(out if code == 0 else f"Rollback failed: {out}")
        return code

    if not args.apply:
        return dry_run()
    if not args.real_ok:
        print("Refusing real bulk merge without --real-ok.")
        return 1

    code, out = run_psql(apply_sql(args.merge_label, args.limit))
    if code != 0:
        print(f"Bulk merge failed: {out}")
        return code
    print(f"Bulk merge applied under '{args.merge_label}':")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
