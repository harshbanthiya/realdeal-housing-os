#!/usr/bin/env python3
"""Phase 5.2 FAKE source-aware property-hint seed. Dry-run by default.

Creates a tiny fake source-aware batch (import_batch -> source_file ->
contact_import_row with parsed building/wing/unit -> contact_property_hint), plus a
fake/test canonical contact, so the candidate planner has fake data to work on.
Everything is tagged batch FAKE_PHASE_5_2_PROPERTY_HINTS / phase 5.2 and is fully
cleanup-able (--cleanup). Writing needs --apply and --fake-ok. Counts only; no raw
personal values.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
SEED_BATCH = "FAKE_PHASE_5_2_PROPERTY_HINTS"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


COUNTS_SQL = f"""
WITH b AS (SELECT id FROM import_batches WHERE source_name = '{SEED_BATCH}')
SELECT 'seed_batches' AS item, count(*)::text AS val FROM b
UNION ALL SELECT 'seed_source_files', count(*)::text FROM source_files WHERE import_batch_id IN (SELECT id FROM b)
UNION ALL SELECT 'seed_import_rows', count(*)::text FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM b)
UNION ALL SELECT 'seed_property_hints', count(*)::text FROM contact_property_hints
  WHERE contact_import_row_id IN (SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM b))
UNION ALL SELECT 'seed_fake_contacts', count(*)::text FROM contacts
  WHERE metadata->>'fake_batch' = '{SEED_BATCH}' AND is_test = true
ORDER BY item;
"""

TAG = "jsonb_build_object('is_test', true, 'phase', '5.2', 'fake_batch', '" + SEED_BATCH + "')"

INSERT_SQL = f"""
BEGIN;
WITH nbatch AS (
  INSERT INTO import_batches (source_name, source_type, status, notes, metadata)
  VALUES ('{SEED_BATCH}', 'contacts', 'completed',
          'Fake Phase 5.2 property-hint seed batch.', {TAG})
  RETURNING id
),
ncontact AS (
  INSERT INTO contacts (full_name, contact_type, source, status, tags, notes, metadata, is_test, canonical_status)
  VALUES ('FAKE Owner 5.2', 'lead', '{SEED_BATCH}', 'active',
          ARRAY['fake', 'phase_5_2', 'property_hint']::text[],
          'Fake/test contact for Phase 5.2 property-hint seed.', {TAG}, true, 'test')
  RETURNING id
),
nsf AS (
  INSERT INTO source_files (import_batch_id, original_file_name, stored_relative_path, file_ext,
                            detected_source_format, processing_status, processing_notes, profile_summary)
  SELECT nbatch.id, 'FAKE_PHASE_5_2_hints.csv', 'fake/phase_5_2/hints.csv', 'csv',
         'fake_property_sheet', 'profiled', 'Fake Phase 5.2 seed source file.', {TAG}
  FROM nbatch
  RETURNING id
),
nrow AS (
  INSERT INTO contact_import_rows (import_batch_id, matched_contact_id,
                                   cleaned_display_name, raw_name,
                                   parsed_building_code, parsed_building_name, parsed_wing, parsed_unit_number,
                                   source_file, source_format, source_row_number)
  SELECT nbatch.id, ncontact.id, 'FAKE Owner 5.2', 'FAKE Owner 5.2',
         'IMPH', 'FAKE Imperial Heights (5.2)', 'A', '1203',
         'FAKE_PHASE_5_2_hints.csv', 'fake_property_sheet', 1
  FROM nbatch, ncontact
  RETURNING id
)
INSERT INTO contact_property_hints (contact_id, contact_import_row_id, building_code, building_name,
                                    wing, unit_number, relationship_type, confidence, raw_hint, needs_review)
SELECT ncontact.id, nrow.id, 'IMPH', 'FAKE Imperial Heights (5.2)', 'A', '1203',
       'owner', 0.800, 'FAKE owner hint (Phase 5.2)', true
FROM ncontact, nrow;
COMMIT;
{COUNTS_SQL}
"""

CLEANUP_SQL = f"""
BEGIN;
DELETE FROM contact_property_hints
  WHERE contact_import_row_id IN (
    SELECT id FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM import_batches WHERE source_name = '{SEED_BATCH}'))
  OR contact_id IN (SELECT id FROM contacts WHERE metadata->>'fake_batch' = '{SEED_BATCH}' AND is_test = true);
DELETE FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM import_batches WHERE source_name = '{SEED_BATCH}');
DELETE FROM source_files WHERE import_batch_id IN (SELECT id FROM import_batches WHERE source_name = '{SEED_BATCH}');
DELETE FROM contacts WHERE metadata->>'fake_batch' = '{SEED_BATCH}' AND is_test = true;
DELETE FROM import_batches WHERE source_name = '{SEED_BATCH}' AND metadata->>'is_test' = 'true';
COMMIT;
{COUNTS_SQL}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed FAKE Phase 5.2 property hints. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    parser.add_argument("--cleanup", action="store_true", help="Remove the fake seed batch instead of creating it.")
    args = parser.parse_args()

    print(f"Fake property-hint seed. batch={SEED_BATCH}. Counts only.")
    code, counts = run_psql(COUNTS_SQL)
    if code != 0:
        print(counts)
        return code

    if args.cleanup:
        if not args.apply:
            print("Dry run only. No rows deleted. Current seed rows:")
            print(counts)
            print("Deleting requires --apply.")
            return 0
        code, output = run_psql(CLEANUP_SQL)
        print("Seed rows removed. Remaining (should be 0):")
        print(output)
        return code

    if not (args.apply and args.fake_ok):
        print("Dry run only. No database writes were made.")
        print("planned (would create): import_batch|1 source_file|1 import_row|1 property_hint|1 fake_contact|1")
        print("current seed rows:")
        print(counts)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if any(int(line.split("|")[1]) > 0 for line in counts.splitlines() if "|" in line):
        print("Refusing: seed rows already exist. Run with --cleanup --apply first.")
        print(counts)
        return 1

    code, output = run_psql(INSERT_SQL)
    print("Seed rows created:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
