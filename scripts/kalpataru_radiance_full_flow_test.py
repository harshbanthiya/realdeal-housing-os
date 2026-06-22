#!/usr/bin/env python3
"""Phase 6.18 — ONE full per-unit flow, end to end, on Kalpataru Radiance A (RERA P51800000591).

Purpose: prove the whole pipeline produces a usable per-unit ownership/tenancy timeline. Dry-run
by default. Writing requires --apply AND --real-ok. Fully reversible via --revert.

REAL (from the operator-supplied MahaRERA PDF view/3924, kept as the genuine milestone):
  - building 'Kalpataru Radiance A'
  - RERA profile P51800000591 + 5 carpet-area records (151 apartments)
  - tower structure: Wing A-Ora, 38 sanctioned floors, 151 units
  - property identifiers incl. CTS 260/5A, village Pahadi (Goregaon West), Mumbai Suburban, 400104
    -> the CTS is a VERIFIED IGR search key, so vw_..._registration_readiness flips
       ready_for_igr_search = TRUE for this building (Imperial Heights cannot — no CTS).
  - 1 building_unit (Flat 1203, a 3BHK) + 1 IGR search job (planned) for CTS 260/5A / village Pahadi.

ILLUSTRATIVE (clearly flagged is_sample=true, verification_status='parsed_candidate',
source='illustrative_pending_igr') — present ONLY to exercise the downstream timeline until the
real operator-assisted IGR Index II capture replaces them:
  - ownership chain on Flat 1203 (2019 builder->buyer, 2023 resale) -> current owner
  - one ACTIVE leave-and-license (ends 2027) -> active tenant
  - parties for each + 1 sample contact + 1 party->contact match candidate + review items

This script does NOT scrape MahaRERA/IGR, call any external API, browse the web, or solve a CAPTCHA.
Every row is tagged source='kalpataru_radiance_test_6_18' for clean revert.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.18"
SOURCE = "kalpataru_radiance_test_6_18"
RERA_REG = "P51800000591"
BUILDING_NAME = "Kalpataru Radiance A"
CONTACT_NAME = "SAMPLE Owner Two (Kalpataru test)"

# (table, tag_column). buildings/contacts/building_units via metadata; rest via raw_context.
TAGGED_TABLES = [
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
REAL_TAG = (
    "jsonb_build_object('source', '" + SOURCE + "', 'phase', '" + PHASE + "', "
    "'rera_reg', '" + RERA_REG + "', 'external_calls_made', false, 'is_fake', false, 'is_sample', false)"
)
# Illustrative transaction rows: clearly flagged, pending real IGR capture.
SAMPLE_TAG = (
    "jsonb_build_object('source', '" + SOURCE + "', 'phase', '" + PHASE + "', "
    "'rera_reg', '" + RERA_REG + "', 'external_calls_made', false, 'is_fake', false, 'is_sample', true, "
    "'sample_source', 'illustrative_pending_igr', "
    "'note', 'Illustrative registration to exercise the timeline; replace with real IGR Index II after operator-assisted capture.')"
)
META_REAL = REAL_TAG

BUILDING = f"(SELECT id FROM buildings WHERE metadata->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
CONTACT = f"(SELECT id FROM contacts WHERE metadata->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
UNIT = f"(SELECT id FROM building_units WHERE metadata->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
PROFILE = f"(SELECT id FROM rera_project_profiles WHERE raw_context->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
CTS_ID = (
    f"(SELECT id FROM building_property_identifiers WHERE raw_context->>'source' = '{SOURCE}' "
    "AND identifier_type = 'cts_number' ORDER BY created_at LIMIT 1)"
)
JOB = f"(SELECT id FROM igr_registration_search_jobs WHERE raw_context->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
STRUCT = f"(SELECT id FROM building_tower_structure WHERE raw_context->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"
SALE_2023 = (
    f"(SELECT id FROM unit_registration_records WHERE raw_context->>'source' = '{SOURCE}' "
    "AND doc_number = 'SAMPLE-GGN-2-2023' ORDER BY created_at LIMIT 1)"
)
LL_2024 = (
    f"(SELECT id FROM unit_registration_records WHERE raw_context->>'source' = '{SOURCE}' "
    "AND doc_number = 'SAMPLE-GGN-3-2024' ORDER BY created_at LIMIT 1)"
)
PARTY_OWNER = (
    "(SELECT id FROM unit_registration_parties WHERE raw_context->>'source' = "
    f"'{SOURCE}' AND party_role = 'purchaser' AND party_name_raw = '{CONTACT_NAME}' ORDER BY created_at LIMIT 1)"
)
MATCH = f"(SELECT id FROM registration_party_contact_matches WHERE raw_context->>'source' = '{SOURCE}' ORDER BY created_at LIMIT 1)"

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {col}->>'source' = '{SOURCE}'"
        for t, col in TAGGED_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def insert_sql() -> str:
    s = []
    s.append(f"""
INSERT INTO buildings (name, developer, project_name, area, locality, city, state, postal_code, notes, metadata)
VALUES ('{BUILDING_NAME}', 'Keyana Estate LLP', 'Kalpataru Radiance A', 'Goregaon West', 'Goregaon West',
        'Mumbai', 'Maharashtra', '400104',
        'Phase 6.18 full-flow test building from MahaRERA P51800000591. Structure/CTS real; transactions illustrative pending IGR.',
        {META_REAL});""")

    s.append(f"""
INSERT INTO contacts (full_name, contact_type, status, notes, metadata)
VALUES ('{CONTACT_NAME}', 'owner', 'active',
        'Phase 6.18 sample contact for party->contact match test. Not a real person.', {META_REAL});""")

    s.append(f"""
INSERT INTO rera_project_profiles
  (building_id, rera_authority, rera_registration_number, official_project_name, promoter_name,
   project_type, project_status, registration_status, registration_date, district, taluka, locality,
   pincode, official_project_url, verification_status, confidence_score, raw_context)
VALUES ({BUILDING}, 'MahaRERA', '{RERA_REG}', 'Kalpataru Radiance A', 'Keyana Estate LLP',
   'Residential / Group Housing', 'Completed', 'Registered', '2017-07-18', 'Mumbai Suburban', 'Borivali',
   'Goregaon West', '400104', 'https://maharerait.maharashtra.gov.in/public/project/view/3924',
   'verified', 0.90, {REAL_TAG});""")

    # 5 carpet-area records (151 apartments).
    s.append(f"""
INSERT INTO rera_carpet_area_records
  (rera_project_profile_id, building_name, wing, apartment_type, carpet_area_sqm, apartment_count,
   source_label, verification_status, raw_context)
VALUES
  ({PROFILE}, 'Wing A-Ora', 'A', '3BHK', 126.35, 31, 'MahaRERA P51800000591 apartment summary', 'verified', {REAL_TAG}),
  ({PROFILE}, 'Wing A-Ora', 'A', '2BHK', 78.90, 31, 'MahaRERA P51800000591 apartment summary', 'verified', {REAL_TAG}),
  ({PROFILE}, 'Wing A-Ora', 'A', '3BHK', 127.39, 31, 'MahaRERA P51800000591 apartment summary', 'verified', {REAL_TAG}),
  ({PROFILE}, 'Wing A-Ora', 'A', '4BHK', 182.93, 31, 'MahaRERA P51800000591 apartment summary', 'verified', {REAL_TAG}),
  ({PROFILE}, 'Wing A-Ora', 'A', '3BHK', 126.71, 27, 'MahaRERA P51800000591 apartment summary', 'verified', {REAL_TAG});""")

    s.append(f"""
INSERT INTO building_tower_structure
  (building_id, rera_project_profile_id, tower_label, tower_type, sanctioned_floors, total_units,
   source_label, source_type, confidence_score, verification_status, raw_context)
VALUES ({BUILDING}, {PROFILE}, 'Wing A-Ora', 'residential', 38, 151,
   'MahaRERA P51800000591 Building Details + Apartment Summary', 'rera_filing', 0.90, 'verified',
   {REAL_TAG} || jsonb_build_object('sanctioned_floors_definition', 'Including Basement+Stilt+Podium+Service+Habitable excluding terrace', 'apartment_type_row_count', 5));""")

    # Identifiers: CTS is a VERIFIED search key -> ready_for_igr_search becomes true.
    s.append(f"""
INSERT INTO building_property_identifiers
  (building_id, rera_project_profile_id, identifier_type, identifier_value, district, village,
   is_igr_search_key, source_label, source_type, source_url, confidence_score, verification_status, raw_context)
VALUES
  ({BUILDING}, {PROFILE}, 'cts_number', '260/5A', 'Mumbai Suburban', 'Pahadi',
   true, 'MahaRERA P51800000591 Land Area / Address (CTS no.260/5A part of village Pahadi Goregaon west)',
   'rera_filing', 'https://maharerait.maharashtra.gov.in/public/project/view/3924', 0.90, 'verified',
   {REAL_TAG} || jsonb_build_object('note', 'Revenue village Pahadi; locality Goregaon West; taluka Borivali. Use village=Pahadi for IGR eSearch.')),
  ({BUILDING}, {PROFILE}, 'village', 'Pahadi', 'Mumbai Suburban', 'Pahadi',
   false, 'MahaRERA P51800000591', 'rera_filing', 'https://maharerait.maharashtra.gov.in/public/project/view/3924', 0.90, 'verified', {REAL_TAG}),
  ({BUILDING}, {PROFILE}, 'pincode', '400104', 'Mumbai Suburban', 'Pahadi',
   false, 'MahaRERA P51800000591', 'rera_filing', 'https://maharerait.maharashtra.gov.in/public/project/view/3924', 0.90, 'verified', {REAL_TAG});""")

    # 1 IGR search job (planned) for the verified CTS / village.
    s.append(f"""
INSERT INTO igr_registration_search_jobs
  (building_id, building_property_identifier_id, search_year, district, village, property_number,
   job_status, captcha_required, external_call_made, raw_context)
VALUES ({BUILDING}, {CTS_ID}, 2023, 'Mumbai Suburban', 'Pahadi', '260/5A',
   'planned', true, false, {REAL_TAG} || jsonb_build_object('note', 'Operator runs this via headed IGR eSearch with human CAPTCHA; one year per job.'));""")

    # 1 building_unit (Flat 1203, 3BHK) — real unit slot for the test.
    s.append(f"""
INSERT INTO building_units
  (building_id, building_name, wing, unit_number, floor, typology, bhk, area_carpet, area_unit, canonical_status, metadata)
VALUES ({BUILDING}, '{BUILDING_NAME}', 'A', '1203', '12', '3BHK', '3', 126.35, 'sqm', 'active', {META_REAL});""")

    # Illustrative registration records on Flat 1203: ownership chain + active tenancy.
    s.append(f"""
INSERT INTO unit_registration_records
  (building_id, building_unit_id, igr_registration_search_job_id, doc_number, registration_year,
   registration_date, sro_office, document_type, property_description_raw, wing_text, unit_text,
   floor_text, area_text, consideration_amount, market_value, parse_confidence, verification_status,
   source_label, raw_context)
VALUES
  ({BUILDING}, {UNIT}, {JOB}, 'SAMPLE-GGN-1-2019', 2019, '2019-02-12', 'Borivali-5', 'sale_deed',
   'SAMPLE Flat 1203, Wing A-Ora, Kalpataru Radiance, CTS 260/5A', 'A', '1203', '12', '126.35 sqm',
   28000000, 29000000, NULL, 'parsed_candidate', 'ILLUSTRATIVE pending IGR', {SAMPLE_TAG}),
  ({BUILDING}, {UNIT}, {JOB}, 'SAMPLE-GGN-2-2023', 2023, '2023-08-20', 'Borivali-5', 'sale_deed',
   'SAMPLE Flat 1203, Wing A-Ora, Kalpataru Radiance, CTS 260/5A', 'A', '1203', '12', '126.35 sqm',
   35000000, 36000000, NULL, 'parsed_candidate', 'ILLUSTRATIVE pending IGR', {SAMPLE_TAG}),
  ({BUILDING}, {UNIT}, {JOB}, 'SAMPLE-GGN-3-2024', 2024, '2024-06-01', 'Borivali-5', 'leave_and_license',
   'SAMPLE Flat 1203, Wing A-Ora, Kalpataru Radiance, CTS 260/5A', 'A', '1203', '12', '126.35 sqm',
   NULL, NULL, NULL, 'parsed_candidate', 'ILLUSTRATIVE pending IGR', {SAMPLE_TAG});""")

    s.append(f"""
UPDATE unit_registration_records
   SET transaction_category = 'tenancy', tenancy_start_date = '2024-06-01',
       tenancy_end_date = '2027-05-31', tenancy_monthly_rent = 90000, tenancy_deposit = 540000
 WHERE id = {LL_2024};""")

    # Parties: 2019 builder->buyer1; 2023 buyer1->Owner Two (current); 2024 Owner Two->Tenant Three.
    s.append(f"""
INSERT INTO unit_registration_parties
  (unit_registration_record_id, party_role, party_name_raw, party_name_normalized, party_type, display_order, raw_context)
VALUES
  ((SELECT id FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND doc_number='SAMPLE-GGN-1-2019'),
     'seller', 'Keyana Estate LLP', 'keyana estate llp', 'company', 0, {SAMPLE_TAG}),
  ((SELECT id FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND doc_number='SAMPLE-GGN-1-2019'),
     'purchaser', 'SAMPLE Buyer One', 'sample buyer one', 'individual', 1, {SAMPLE_TAG}),
  ({SALE_2023}, 'seller', 'SAMPLE Buyer One', 'sample buyer one', 'individual', 0, {SAMPLE_TAG}),
  ({SALE_2023}, 'purchaser', '{CONTACT_NAME}', 'sample owner two kalpataru test', 'individual', 1, {SAMPLE_TAG}),
  ({LL_2024}, 'lessor', '{CONTACT_NAME}', 'sample owner two kalpataru test', 'individual', 0, {SAMPLE_TAG}),
  ({LL_2024}, 'lessee', 'SAMPLE Tenant Three', 'sample tenant three', 'individual', 1, {SAMPLE_TAG});""")

    s.append(f"""
INSERT INTO registration_party_contact_matches
  (unit_registration_party_id, contact_id, building_id, building_unit_id, match_status, match_strength,
   name_similarity_score, match_reason, creates_relationship, raw_context)
VALUES ({PARTY_OWNER}, {CONTACT}, {BUILDING}, {UNIT}, 'candidate', 'strong',
   0.95, 'ILLUSTRATIVE exact-name overlap (current owner party vs contact).', true, {SAMPLE_TAG});""")

    s.append(f"""
INSERT INTO unit_registration_review_items
  (building_id, building_tower_structure_id, building_property_identifier_id,
   igr_registration_search_job_id, unit_registration_record_id, registration_party_contact_match_id,
   review_type, status, priority, decision_notes, raw_context)
VALUES
  ({BUILDING}, {STRUCT}, NULL, NULL, NULL, NULL, 'structure_review', 'pending', 'normal',
   'Confirm Wing A-Ora 38 floors / 151 units from RERA.', {REAL_TAG}),
  ({BUILDING}, NULL, {CTS_ID}, NULL, NULL, NULL, 'identifier_review', 'pending', 'high',
   'Confirm CTS 260/5A village Pahadi -> ready to run IGR eSearch.', {REAL_TAG}),
  ({BUILDING}, NULL, NULL, {JOB}, NULL, NULL, 'search_job_review', 'pending', 'high',
   'IGR eSearch job for CTS 260/5A / village Pahadi / 2023 — operator-assisted (human CAPTCHA).', {REAL_TAG}),
  ({BUILDING}, NULL, NULL, NULL, {SALE_2023}, NULL, 'registration_record_review', 'pending', 'normal',
   'ILLUSTRATIVE record — replace with real IGR Index II.', {SAMPLE_TAG}),
  ({BUILDING}, NULL, NULL, NULL, NULL, {MATCH}, 'party_contact_match_review', 'pending', 'normal',
   'ILLUSTRATIVE party->contact match.', {SAMPLE_TAG});""")

    body = "\n".join(s)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def delete_sql() -> str:
    order = [t for t, _ in reversed(TAGGED_TABLES)]
    cols = {t: c for t, c in TAGGED_TABLES}
    stmts = "\n".join(f"DELETE FROM {t} WHERE {cols[t]}->>'source' = '{SOURCE}';" for t in order)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Kalpataru Radiance A full-flow test. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()

    print(f"Kalpataru Radiance A full-flow test. phase={PHASE}; source={SOURCE}; rera_reg={RERA_REG}. "
          "Structure/CTS REAL (from PDF); transactions ILLUSTRATIVE (is_sample=true); reversible; "
          "no MahaRERA/IGR/external call.")

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    existing = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if args.revert:
        if not args.apply or not args.real_ok:
            print("Revert dry-run. current tagged rows (would delete):")
            print(current)
            print("Reverting requires --revert --apply --real-ok.")
            return 0
        code, output = run_psql(delete_sql())
        print("Remaining tagged rows after revert (expect all 0):")
        print(output)
        return code

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("planned: 1 building, 1 contact, 1 RERA profile, 5 carpet records, 1 tower structure, "
              "3 identifiers (CTS verified), 1 search job, 1 unit, 3 illustrative records "
              "(2 sales + 1 active L&L), 6 parties, 1 match, 5 review items.")
        print("current tagged rows:")
        print(current)
        print("Writing requires --apply and --real-ok.")
        return 0

    if existing:
        print("Refusing: tagged rows already exist. Run with --revert --apply --real-ok first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql())
    print("Recorded rows (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
