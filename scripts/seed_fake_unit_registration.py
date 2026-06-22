#!/usr/bin/env python3
"""Phase 6.15/6.16 FAKE unit-registration workflow seeder. Dry-run by default.

Creates a CLEARLY-FAKE, self-contained test set that exercises the building-structure + IGR
unit-registration tables AND the Phase 6.16 per-unit ownership/tenancy timeline end to end:

  - 1 fake building (named so it never matches the real "Imperial Heights" anchors)
  - 1 fake RERA project profile (linked to the fake building) + 2 carpet-area records
    (so the unit-accounting view shows RERA-expected units)
  - 1 fake tower structure, 2 property identifiers (one CTS search key), 1 IGR search job
  - 1 fake building_unit (Flat 1201) that registrations link to
  - an OWNERSHIP CHAIN on that unit: 2 sale deeds (2018 -> 2022) so current owner = latest buyer
  - an ACTIVE TENANCY on that unit: 1 leave-and-license (ends in the future)
  - parties for every record, 1 fake contact, 1 party->contact match candidate, review items

It NEVER touches the real Imperial Heights buildings or any real contact/SEO/content rows,
NEVER calls IGR/MahaRERA or any external API, NEVER browses the web, NEVER solves a CAPTCHA,
and NEVER auto-creates a contact relationship. Every row is tagged in raw_context/metadata
with fake_batch='FAKE_PHASE_6_15_UNIT_REGISTRATION' so cleanup is exact. Writing requires
--apply AND --fake-ok. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.16"
SOURCE = "fake_unit_registration"
FAKE_BATCH = "FAKE_PHASE_6_15_UNIT_REGISTRATION"
# Name deliberately does NOT contain "imperial heights" so the real readiness view stays clean.
FAKE_BUILDING_NAME = "ZZ_FAKE IGR Registration Tower (Phase 6.15) — DO NOT USE"
FAKE_CONTACT_NAME = "ZZ_FAKE Owner C (Phase 6.15)"

# (table, tag_column) — buildings/contacts/building_units tagged via metadata; rest via raw_context.
FAKE_TABLES = [
    ("buildings", "metadata"),
    ("contacts", "metadata"),
    ("building_units", "metadata"),
    ("rera_project_profiles", "raw_context"),
    ("rera_carpet_area_records", "raw_context"),
    ("building_tower_structure", "raw_context"),
    ("building_property_identifiers", "raw_context"),
    ("igr_registration_search_jobs", "raw_context"),
    ("unit_registration_records", "raw_context"),
    ("unit_registration_parties", "raw_context"),
    ("registration_party_contact_matches", "raw_context"),
    ("unit_registration_review_items", "raw_context"),
]
TAG = (
    "jsonb_build_object("
    f"'fake_batch', '{FAKE_BATCH}', 'phase', '{PHASE}', 'source', '{SOURCE}', "
    "'external_calls_made', false, 'is_fake', true)"
)
META_TAG = TAG

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {col}->>'fake_batch' = '{FAKE_BATCH}'"
        for t, col in FAKE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

# Subqueries that resolve the fake rows by tag (no hardcoded UUIDs).
FAKE_BUILDING = f"(SELECT id FROM buildings WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_CONTACT = f"(SELECT id FROM contacts WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_UNIT = f"(SELECT id FROM building_units WHERE metadata->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_PROFILE = f"(SELECT id FROM rera_project_profiles WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_IDENTIFIER = (
    f"(SELECT id FROM building_property_identifiers WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' "
    "AND is_igr_search_key ORDER BY created_at LIMIT 1)"
)
FAKE_JOB = f"(SELECT id FROM igr_registration_search_jobs WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_STRUCTURE = f"(SELECT id FROM building_tower_structure WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"
FAKE_SALE_2018 = (
    f"(SELECT id FROM unit_registration_records WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' "
    "AND doc_number = 'FAKE-AND-1-2018' ORDER BY created_at LIMIT 1)"
)
FAKE_SALE_2022 = (
    f"(SELECT id FROM unit_registration_records WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' "
    "AND doc_number = 'FAKE-AND-2-2022' ORDER BY created_at LIMIT 1)"
)
FAKE_LL_2023 = (
    f"(SELECT id FROM unit_registration_records WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' "
    "AND doc_number = 'FAKE-AND-3-2023' ORDER BY created_at LIMIT 1)"
)
# Purchaser party of the LATEST sale (2022) -> the current owner -> matched to the fake contact.
FAKE_PARTY_OWNER_C = (
    "(SELECT id FROM unit_registration_parties WHERE raw_context->>'fake_batch' = "
    f"'{FAKE_BATCH}' AND party_role = 'purchaser' AND party_name_raw = '{FAKE_CONTACT_NAME}' "
    "ORDER BY created_at LIMIT 1)"
)
FAKE_MATCH = f"(SELECT id FROM registration_party_contact_matches WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}' ORDER BY created_at LIMIT 1)"

def insert_sql() -> str:
    stmts = []
    # 1. Fake building.
    stmts.append(f"""
INSERT INTO buildings (name, developer, project_name, area, locality, city, state, postal_code, notes, metadata)
VALUES ('{FAKE_BUILDING_NAME}', 'FAKE Test Developers LLP', 'ZZ_FAKE IGR Test Project',
        'Test Area', 'Test Locality', 'Mumbai', 'Maharashtra', '400000',
        'Phase 6.15/6.16 fake unit-registration test building. Not a real project.', {META_TAG});""")

    # 2. Fake contact (the current owner, for the party->contact match test).
    stmts.append(f"""
INSERT INTO contacts (full_name, contact_type, status, notes, metadata)
VALUES ('{FAKE_CONTACT_NAME}', 'owner', 'active',
        'Phase 6.15/6.16 fake contact for party->contact match test. Not a real person.', {META_TAG});""")

    # 3. Fake RERA project profile (linked to the fake building) so accounting shows expected units.
    stmts.append(f"""
INSERT INTO rera_project_profiles
  (building_id, rera_authority, rera_registration_number, official_project_name, promoter_name,
   project_type, project_status, registration_status, district, locality, pincode,
   verification_status, confidence_score, raw_context)
VALUES ({FAKE_BUILDING}, 'MahaRERA', 'PFAKE000000615', 'ZZ_FAKE IGR Test Project',
   'FAKE Test Developers LLP', 'Residential', 'New Project', 'Registered',
   'Mumbai Suburban', 'Test Locality', '400000', 'verified', 0.50, {TAG});""")

    # 4. Fake carpet-area records (expected 80 apartments to match the tower total_units).
    stmts.append(f"""
INSERT INTO rera_carpet_area_records
  (rera_project_profile_id, building_name, wing, apartment_type, carpet_area_sqm, carpet_area_sqft,
   apartment_count, source_label, verification_status, raw_context)
VALUES
  ({FAKE_PROFILE}, '{FAKE_BUILDING_NAME}', 'Z', '1BHK', 41.80, 450.0, 40, 'FAKE RERA extract', 'unverified', {TAG}),
  ({FAKE_PROFILE}, '{FAKE_BUILDING_NAME}', 'Z', '2BHK', 60.40, 650.0, 40, 'FAKE RERA extract', 'unverified', {TAG});""")

    # 5. Fake tower structure (one wing, 20 floors, 4 units/floor, 80 units).
    stmts.append(f"""
INSERT INTO building_tower_structure
  (building_id, rera_project_profile_id, tower_label, tower_type, floors_above_ground, floors_below_ground,
   units_per_typical_floor, total_units, sanctioned_floors, source_label, source_type,
   confidence_score, verification_status, raw_context)
VALUES ({FAKE_BUILDING}, {FAKE_PROFILE}, 'Wing Z', 'residential', 20, 2, 4, 80, 20,
   'FAKE structure extract', 'rera_filing', 0.50, 'unverified', {TAG});""")

    # 6. Fake property identifiers (a CTS search key + a village; both unverified).
    stmts.append(f"""
INSERT INTO building_property_identifiers
  (building_id, identifier_type, identifier_value, district, village, sro_office,
   is_igr_search_key, source_label, source_type, confidence_score, verification_status, raw_context)
VALUES
  ({FAKE_BUILDING}, 'cts_number', 'CTS-FAKE-1234', 'Mumbai Suburban', 'Andheri', 'Andheri-3',
   true, 'FAKE property card', 'property_card', 0.50, 'unverified', {TAG}),
  ({FAKE_BUILDING}, 'village', 'Andheri', 'Mumbai Suburban', 'Andheri', NULL,
   false, 'FAKE property card', 'property_card', 0.50, 'unverified', {TAG});""")

    # 7. Fake IGR search job (planned; CAPTCHA assumed; NO external call).
    stmts.append(f"""
INSERT INTO igr_registration_search_jobs
  (building_id, building_property_identifier_id, search_year, district, village, property_number,
   job_status, captcha_required, external_call_made, raw_context)
VALUES ({FAKE_BUILDING}, {FAKE_IDENTIFIER}, 2022, 'Mumbai Suburban', 'Andheri', 'CTS-FAKE-1234',
   'planned', true, false, {TAG});""")

    # 8. Fake building_unit (Flat 1201, Wing Z) that registrations link to.
    stmts.append(f"""
INSERT INTO building_units
  (building_id, building_name, wing, unit_number, floor, typology, bhk, area_carpet, area_unit,
   canonical_status, metadata)
VALUES ({FAKE_BUILDING}, '{FAKE_BUILDING_NAME}', 'Z', '1201', '12', '2BHK', '2', 650.0, 'sqft',
   'active', {META_TAG});""")

    # 9. Registration records on Flat 1201: ownership chain (2018 -> 2022) + active tenancy (2023).
    stmts.append(f"""
INSERT INTO unit_registration_records
  (building_id, building_unit_id, igr_registration_search_job_id, doc_number, registration_year,
   registration_date, sro_office, document_type, property_description_raw, wing_text, unit_text,
   floor_text, area_text, consideration_amount, market_value, parse_confidence, verification_status,
   source_label, raw_context)
VALUES
  ({FAKE_BUILDING}, {FAKE_UNIT}, {FAKE_JOB}, 'FAKE-AND-1-2018', 2018, '2018-03-10', 'Andheri-3',
   'sale_deed', 'FAKE Flat 1201, Wing Z, CTS-FAKE-1234', 'Z', '1201', '12', '650 sqft',
   9000000, 9500000, 0.50, 'parsed_candidate', 'FAKE Index II extract', {TAG}),
  ({FAKE_BUILDING}, {FAKE_UNIT}, {FAKE_JOB}, 'FAKE-AND-2-2022', 2022, '2022-04-15', 'Andheri-3',
   'sale_deed', 'FAKE Flat 1201, Wing Z, CTS-FAKE-1234', 'Z', '1201', '12', '650 sqft',
   12500000, 13000000, 0.50, 'parsed_candidate', 'FAKE Index II extract', {TAG}),
  ({FAKE_BUILDING}, {FAKE_UNIT}, {FAKE_JOB}, 'FAKE-AND-3-2023', 2023, '2023-06-01', 'Andheri-3',
   'leave_and_license', 'FAKE Flat 1201, Wing Z, CTS-FAKE-1234', 'Z', '1201', '12', '650 sqft',
   NULL, NULL, 0.50, 'parsed_candidate', 'FAKE Index II extract', {TAG});""")

    # 9b. Tenancy details on the leave-and-license (ACTIVE: ends in the future).
    stmts.append(f"""
UPDATE unit_registration_records
   SET transaction_category = 'tenancy', tenancy_start_date = '2023-06-01',
       tenancy_end_date = '2099-05-31', tenancy_monthly_rent = 55000, tenancy_deposit = 200000
 WHERE id = {FAKE_LL_2023};""")

    # 10. Parties. Sale 2018: A -> B. Sale 2022: B -> C (current owner). L&L 2023: C -> D (tenant).
    stmts.append(f"""
INSERT INTO unit_registration_parties
  (unit_registration_record_id, party_role, party_name_raw, party_name_normalized, party_type, display_order, raw_context)
VALUES
  ({FAKE_SALE_2018}, 'seller', 'ZZ_FAKE Owner A', 'zz fake owner a', 'individual', 0, {TAG}),
  ({FAKE_SALE_2018}, 'purchaser', 'ZZ_FAKE Owner B', 'zz fake owner b', 'individual', 1, {TAG}),
  ({FAKE_SALE_2022}, 'seller', 'ZZ_FAKE Owner B', 'zz fake owner b', 'individual', 0, {TAG}),
  ({FAKE_SALE_2022}, 'purchaser', '{FAKE_CONTACT_NAME}', 'zz fake owner c phase 6 15', 'individual', 1, {TAG}),
  ({FAKE_LL_2023}, 'lessor', '{FAKE_CONTACT_NAME}', 'zz fake owner c phase 6 15', 'individual', 0, {TAG}),
  ({FAKE_LL_2023}, 'lessee', 'ZZ_FAKE Tenant D', 'zz fake tenant d', 'individual', 1, {TAG});""")

    # 11. Party->contact match candidate (current owner party -> fake contact; NOT accepted).
    stmts.append(f"""
INSERT INTO registration_party_contact_matches
  (unit_registration_party_id, contact_id, building_id, building_unit_id, match_status, match_strength,
   name_similarity_score, match_reason, creates_relationship, raw_context)
VALUES ({FAKE_PARTY_OWNER_C}, {FAKE_CONTACT}, {FAKE_BUILDING}, {FAKE_UNIT}, 'candidate', 'strong',
   0.95, 'FAKE exact-name overlap for workflow test only.', true, {TAG});""")

    # 12. Review items (one per review_type).
    stmts.append(f"""
INSERT INTO unit_registration_review_items
  (building_id, building_tower_structure_id, building_property_identifier_id,
   igr_registration_search_job_id, unit_registration_record_id, registration_party_contact_match_id,
   review_type, status, priority, raw_context)
VALUES
  ({FAKE_BUILDING}, {FAKE_STRUCTURE}, NULL, NULL, NULL, NULL, 'structure_review', 'pending', 'normal', {TAG}),
  ({FAKE_BUILDING}, NULL, {FAKE_IDENTIFIER}, NULL, NULL, NULL, 'identifier_review', 'pending', 'normal', {TAG}),
  ({FAKE_BUILDING}, NULL, NULL, {FAKE_JOB}, NULL, NULL, 'search_job_review', 'pending', 'normal', {TAG}),
  ({FAKE_BUILDING}, NULL, NULL, NULL, {FAKE_SALE_2022}, NULL, 'registration_record_review', 'pending', 'normal', {TAG}),
  ({FAKE_BUILDING}, NULL, NULL, NULL, NULL, {FAKE_MATCH}, 'party_contact_match_review', 'pending', 'normal', {TAG}),
  ({FAKE_BUILDING}, NULL, NULL, NULL, {FAKE_SALE_2022}, NULL, 'unit_link_review', 'pending', 'normal', {TAG});""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed FAKE unit-registration rows. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    args = parser.parse_args()

    print(f"Fake unit-registration seed. phase={PHASE}; source={SOURCE}; fake_batch={FAKE_BATCH}. "
          "Counts only; clearly-fake rows only; no IGR/MahaRERA/external calls; "
          "no real building/contact/SEO/content change.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply or not args.fake_ok:
        print("Dry run only. No database writes were made.")
        print("planned fake rows: 1 building, 1 contact, 1 RERA profile, 2 carpet records, 1 unit, "
              "1 tower structure, 2 identifiers, 1 search job, 3 registration records "
              "(2 sales + 1 active L&L), 6 parties, 1 party->contact match, 6 review items.")
        print("current fake-batch rows:")
        print(current)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if already:
        print("Refusing: fake-batch rows already exist. Run cleanup_fake_unit_registration.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql())
    print("Fake unit-registration rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
