#!/usr/bin/env python3
"""Phase 6.8 FAKE MahaRERA verification workflow seeder. Dry-run by default.

Creates CLEARLY-FAKE, self-contained test rows that exercise the Phase 6.8 RERA tables
end to end: one fake building (named so it never matches the real "Imperial Heights"
anchors), a fake rera_project_profile, a fake building-match candidate, fake carpet-area
records, fake status/risk checks, a fake area-mismatch candidate, and fake review items.

It NEVER touches the real Imperial Heights buildings or any real SEO/content rows, NEVER
calls MahaRERA or any external API, and NEVER browses the web. Every row is tagged in
raw_context/metadata with fake_batch='FAKE_PHASE_6_8_RERA_VERIFICATION' so cleanup is
exact. Writing requires --apply AND --fake-ok. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.8"
SOURCE = "fake_rera_verification"
FAKE_BATCH = "FAKE_PHASE_6_8_RERA_VERIFICATION"
# Name deliberately does NOT contain "imperial heights" so the real readiness view stays clean.
FAKE_BUILDING_NAME = "ZZ_FAKE RERA Test Tower (Phase 6.8) — DO NOT USE"

# (table, tag_column) — buildings is tagged via metadata, RERA tables via raw_context.
FAKE_TABLES = [
    ("buildings", "metadata"),
    ("rera_project_profiles", "raw_context"),
    ("rera_building_match_candidates", "raw_context"),
    ("rera_carpet_area_records", "raw_context"),
    ("rera_project_status_checks", "raw_context"),
    ("rera_area_mismatch_candidates", "raw_context"),
    ("rera_verification_review_items", "raw_context"),
]
TAG = (
    "jsonb_build_object("
    f"'fake_batch', '{FAKE_BATCH}', 'phase', '{PHASE}', 'source', '{SOURCE}', "
    "'external_calls_made', false, 'is_fake', true)"
)
# Tag for the buildings.metadata column (same keys; standalone so it reads naturally).
META_TAG = TAG

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {col}->>'fake_batch' = '{FAKE_BATCH}'"
        for t, col in FAKE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

# Subqueries that resolve the fake rows by tag (no hardcoded UUIDs).
FAKE_BUILDING = f"(SELECT id FROM buildings WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_PROFILE = f"(SELECT id FROM rera_project_profiles WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_MATCH = f"(SELECT id FROM rera_building_match_candidates WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_CARPET = f"(SELECT id FROM rera_carpet_area_records WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_MISMATCH = f"(SELECT id FROM rera_area_mismatch_candidates WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"

def insert_sql() -> str:
    stmts = []
    # 1. Fake building (clearly fake; tagged in metadata).
    stmts.append(f"""
INSERT INTO buildings (name, developer, project_name, area, locality, city, state, postal_code, notes, metadata)
VALUES ('{FAKE_BUILDING_NAME}', 'FAKE Test Developers LLP', 'ZZ_FAKE RERA Test Project',
        'Test Area', 'Test Locality', 'Mumbai', 'Maharashtra', '400000',
        'Phase 6.8 fake RERA verification test building. Not a real project.', {META_TAG});""")

    # 2. Fake RERA project profile (candidate_found; not verified).
    stmts.append(f"""
INSERT INTO rera_project_profiles
  (building_id, rera_authority, rera_registration_number, official_project_name, promoter_name,
   project_type, project_status, registration_status, district, taluka, locality, pincode,
   official_project_url, verification_status, confidence_score, raw_context)
VALUES ({FAKE_BUILDING}, 'MahaRERA', 'P5XXXX0000FAKE', 'ZZ_FAKE RERA Test Project',
   'FAKE Test Developers LLP', 'Residential', 'New Project', 'Registered',
   'Mumbai Suburban', 'Andheri', 'Test Locality', '400000',
   'https://maharera.maharashtra.gov.in/', 'candidate_found', 0.50, {TAG});""")

    # 3. Fake building-match candidate (fake building <-> fake profile).
    stmts.append(f"""
INSERT INTO rera_building_match_candidates
  (building_id, rera_project_profile_id, match_status, match_strength, match_reason,
   name_similarity_score, location_similarity_score, pincode_match, developer_match, raw_context)
VALUES ({FAKE_BUILDING}, {FAKE_PROFILE}, 'candidate', 'medium',
   'Fake name+locality overlap for workflow test only.', 0.82, 0.70, true, false, {TAG});""")

    # 4. Fake carpet-area records (two apartment types).
    stmts.append(f"""
INSERT INTO rera_carpet_area_records
  (rera_project_profile_id, building_name, wing, apartment_type, carpet_area_sqm, carpet_area_sqft,
   apartment_count, booked_count, source_label, verification_status, raw_context)
VALUES
  ({FAKE_PROFILE}, '{FAKE_BUILDING_NAME}', 'A', '1BHK', 41.80, 450.0, 40, 10, 'FAKE RERA test extract', 'unverified', {TAG}),
  ({FAKE_PROFILE}, '{FAKE_BUILDING_NAME}', 'A', '2BHK', 65.00, 699.7, 30, 8, 'FAKE RERA test extract', 'unverified', {TAG});""")

    # 5. Fake status/risk checks (registered=clear/info; complaint=not_found/info; extension=present/warning).
    stmts.append(f"""
INSERT INTO rera_project_status_checks
  (rera_project_profile_id, check_type, check_status, severity, safe_summary, checked_at, raw_context)
VALUES
  ({FAKE_PROFILE}, 'registered_project', 'clear', 'info', 'FAKE: project shows as registered.', now(), {TAG}),
  ({FAKE_PROFILE}, 'complaint_present', 'not_found', 'info', 'FAKE: no complaints found.', now(), {TAG}),
  ({FAKE_PROFILE}, 'extension_present', 'present', 'warning', 'FAKE: one extension on record.', now(), {TAG});""")

    # 6. Fake area-mismatch candidate (internal 2BHK sqft vs RERA carpet sqft).
    stmts.append(f"""
INSERT INTO rera_area_mismatch_candidates
  (building_id, rera_carpet_area_record_id, internal_source_table, internal_source_id,
   internal_area_value, internal_area_unit, rera_area_sqft, mismatch_percent, mismatch_status,
   suspected_reason, raw_context)
VALUES ({FAKE_BUILDING},
   (SELECT id FROM rera_carpet_area_records WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' AND apartment_type = '2BHK' ORDER BY created_at LIMIT 1),
   'building_units', NULL, 825.0, 'sqft', 699.7, 17.91, 'candidate', 'carpet_vs_builtup', {TAG});""")

    # 7. Fake review items (one per review_type).
    stmts.append(f"""
INSERT INTO rera_verification_review_items
  (rera_project_profile_id, rera_building_match_candidate_id, rera_area_mismatch_candidate_id,
   review_type, status, priority, raw_context)
VALUES
  ({FAKE_PROFILE}, {FAKE_MATCH}, NULL, 'rera_project_match_review', 'pending', 'normal', {TAG}),
  ({FAKE_PROFILE}, NULL, NULL, 'rera_fact_review', 'pending', 'normal', {TAG}),
  ({FAKE_PROFILE}, NULL, {FAKE_MISMATCH}, 'rera_area_mismatch_review', 'pending', 'normal', {TAG}),
  ({FAKE_PROFILE}, NULL, NULL, 'rera_status_risk_review', 'pending', 'normal', {TAG});""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed FAKE RERA verification rows. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    args = parser.parse_args()

    print(f"Fake RERA verification seed. phase={PHASE}; source={SOURCE}; fake_batch={FAKE_BATCH}. "
          "Counts only; clearly-fake rows only; no MahaRERA/external calls; no real building/SEO/content change.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply or not args.fake_ok:
        print("Dry run only. No database writes were made.")
        print("planned fake rows: 1 building, 1 rera_project_profile, 1 match candidate, 2 carpet-area records, "
              "3 status checks, 1 area-mismatch candidate, 4 review items.")
        print("current fake-batch rows:")
        print(current)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if already:
        print("Refusing: fake-batch rows already exist. Run cleanup_fake_rera_verification.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql())
    print("Fake RERA verification rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
