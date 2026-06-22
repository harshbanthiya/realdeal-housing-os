#!/usr/bin/env python3
"""Phase 6.9 guarded MANUAL MahaRERA verification entry for Imperial Heights Wing C & D.

Inserts REAL but REVIEW-GATED RERA rows transcribed by a human from a manually-supplied
official MahaRERA PDF snapshot (no scraping, no API, no browsing). It creates a RERA
project profile (verification_status='needs_human_review'), two building-match candidates
(match_status='candidate', NOT accepted), 26 carpet-area records
(verification_status='needs_human_review'), 13 status/risk/document checks, and 6 pending
review items.

It NEVER scrapes MahaRERA, calls an external API, browses the web, updates buildings or
building addresses, merges buildings, touches building_web_profiles/SEO/content rows,
resolves source gaps, marks the profile verified, accepts a match, publishes, or sends
outreach. Per the operator note, RERA street/boundary/lat/long are deliberately NOT stored
as trusted building address data; address handling is left for operator review.

Personal names from director/complainant/allottee/respondent/grievance/appeal/complaint
sections are intentionally NOT stored. Writing requires --real-ok AND --apply. Counts only.
"""

from __future__ import annotations
from _db import jsonb_lit, read_env_value, run_psql, sql_literal

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.9"
SOURCE = "manual_rera_verification_entry"
SQM_TO_SQFT = 10.76391041671

# Base raw_context tag applied to every row created in this phase.
BASE_TAG = {
    "phase": PHASE,
    "source": SOURCE,
    "official_url_supplied_by_user": True,
    "source_pdf_snapshot": True,
    "address_requires_operator_review": True,
    "do_not_use_rera_address_for_public_listing": True,
    "external_calls_made": False,
    "scraped": False,
    "human_visual_verification_required": True,
    "published": False,
    "communication_sent": False,
}

# Project-level official facts stored in rera_project_profiles.raw_context (Task D/E).
# NOTE: RERA address/boundary/lat/long are intentionally absent (operator review).
PROFILE_FACTS = {
    "date_of_registration_display": "05/08/2017",
    "original_proposed_completion_date": "2019-06-30",
    "revised_proposed_completion_date": "2021-06-30",
    "project_location": "Maharashtra",
    "planning_authority": "Others",
    "final_plot_cts_survey_number": "1 part",
    "total_land_area_approved_layout_sqm": 10084.49,
    "land_area_for_registration_sqm": 10084.49,
    "permissible_built_up_area_sqm": 66750.15,
    "sanctioned_built_up_area_sqm": 64062.15,
    "recreational_open_space_sqm": 7081.93,
    "promoter_type": "Company",
    "investor_other_than_promoter": "No",
    "financial_encumbrance": "No",
    "source_pdf_name": "Maharashtra Real Estate Regulatory Authority.pdf",
    "source_pdf_generated_at": "2026-06-10 09:54",
    "source_label": "official_maharera_pdf_snapshot_user_supplied",
    "address_verification_status": "needs_operator_review",
    "do_not_use_rera_address_for_public_listing": True,
    "rera_address_fields_skipped": True,
    "rera_building_wing_records": [
        {"building_name": "Imperial Heights Wing C", "identification_of_wing_as_per_sanctioned_plan": "NA", "number_of_sanctioned_floors": 51},
        {"building_name": "Imperial Heights Wing D", "identification_of_wing_as_per_sanctioned_plan": "NA", "number_of_sanctioned_floors": 51},
    ],
}

# 26 carpet-area rows: (building_name, apartment_type, carpet_area_sqm, apartment_count). Task F.
CARPET_ROWS = [
    ("Imperial Heights Wing D", "DUP 8 \\ 2 BHK E", 63.87, 1),
    ("Imperial Heights Wing D", "2.5 BHK B", 93.38, 32),
    ("Imperial Heights Wing D", "3 BHK D", 118.67, 2),
    ("Imperial Heights Wing D", "DUP 1 \\ 1.5 BHK G", 63.01, 1),
    ("Imperial Heights Wing D", "DUP 3 \\ 3 BHK H", 103.25, 1),
    ("Imperial Heights Wing D", "DUP 13 \\ 1.5 BHK C", 63.62, 1),
    ("Imperial Heights Wing D", "DUP 14 \\ 1.5 BHK B", 63.28, 1),
    ("Imperial Heights Wing D", "DUP 9 \\ 3 BHK I", 99.18, 1),
    ("Imperial Heights Wing D", "3.5 BHK A", 126.81, 24),
    ("Imperial Heights Wing D", "4 BHK F", 139.89, 1),
    ("Imperial Heights Wing D", "3.5 BHK H", 129.09, 15),
    ("Imperial Heights Wing D", "2.5 BHK C", 77.91, 2),
    ("Imperial Heights Wing D", "4 BHK E", 172.53, 17),
    ("Imperial Heights Wing D", "DUP 5 \\ 1.5 BHK B", 63.28, 1),
    ("Imperial Heights Wing D", "2.5 BHK A", 82.51, 42),
    ("Imperial Heights Wing D", "DUP 12 \\ 1 BHK", 37.00, 1),
    ("Imperial Heights Wing D", "DUP 7 \\ 1.5 BHK F", 45.00, 1),
    ("Imperial Heights Wing D", "DUP 2 \\ 3.5 BHK J", 125.00, 1),
    ("Imperial Heights Wing D", "3.5 BHK G", 122.87, 24),
    ("Imperial Heights Wing D", "3.5 BHK F", 130.21, 17),
    ("Imperial Heights Wing D", "DUP 6 \\ 1.5 BHK C", 63.62, 1),
    ("Imperial Heights Wing D", "DUP 15 \\ 1.5 BHK E", 51.11, 1),
    ("Imperial Heights Wing D", "DUP 4 \\ 1.5 BHK D", 51.33, 1),
    ("Imperial Heights Wing D", "4 BHK D", 151.85, 22),
    ("Imperial Heights Wing D", "DUP 10 \\ 3 BHK I", 99.18, 1),
    ("Imperial Heights Wing D", "DUP 11 \\ 2 BHK D", 71.15, 1),
]

# Status/risk/document checks: (check_type, check_status, severity, safe_summary). Task E + G.
# Personal names from complaint/litigation/appeal sections are NOT stored — counts only.
STATUS_CHECKS = [
    ("building_wing_details_present", "present", "info",
     "MahaRERA PDF lists 2 building/wing records: Imperial Heights Wing C and Imperial Heights Wing D, each with 51 sanctioned floors."),
    ("project_completed", "present", "info", "MahaRERA PDF project status is Completed."),
    ("certificate_available", "present", "info", "MahaRERA PDF shows Certificate Download available."),
    ("land_area_details_present", "present", "info",
     "Land area, permissible built-up area and sanctioned built-up area are present in the official PDF snapshot."),
    ("carpet_area_records_present", "present", "info",
     "PDF lists 26 apartment/carpet-area rows totaling 213 apartments."),
    ("litigation_present", "present", "warning",
     "PDF marks litigation against the proposed project as Yes and lists 8 litigation rows. Names are not stored."),
    ("complaint_present", "present", "warning",
     "PDF complaint section lists 29 complaint rows. Complainant/respondent personal names are intentionally not stored."),
    ("appeal_present", "present", "info",
     "PDF appeal section lists 3 appeal rows. Personal names are not stored."),
    ("non_compliance_present", "present", "warning",
     "PDF non-compliance section lists 5 complaint-number rows. Personal names are not stored."),
    ("financial_encumbrance", "clear", "info", "PDF states financial encumbrance: No."),
    ("technical_documents_present", "present", "info",
     "PDF lists technical documents including building plan approval, layout approval and IOD."),
    ("promoter_documents_present", "present", "info",
     "PDF lists promoter documents including legal title report and declaration form B."),
    ("occupation_certificate_documents_present", "present", "info",
     "PDF lists occupation certificate related documents."),
]

PHASE_TABLES = [
    "rera_project_profiles",
    "rera_building_match_candidates",
    "rera_carpet_area_records",
    "rera_project_status_checks",
    "rera_area_mismatch_candidates",
    "rera_verification_review_items",
]
def tag_jsonb() -> str:
    return jsonb_lit(BASE_TAG)

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE raw_context->>'phase' = '{PHASE}' "
        f"AND raw_context->>'source' = '{SOURCE}'"
        for t in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def precheck_sql(args) -> str:
    return f"""
SELECT 'building_found' k, count(*)::text v FROM buildings WHERE id = {sql_literal(args.building_id)}
UNION ALL SELECT 'profile_found', count(*)::text FROM building_web_profiles WHERE profile_slug = {sql_literal(args.profile_slug)}
UNION ALL SELECT 'duplicate_anchor_found', count(*)::text FROM buildings
   WHERE id <> {sql_literal(args.building_id)} AND lower(name) LIKE '%imperial heights%'
UNION ALL SELECT 'registration_exists', count(*)::text FROM rera_project_profiles
   WHERE rera_registration_number = {sql_literal(args.rera_registration_number)}
ORDER BY k;"""

def insert_sql(args) -> str:
    bid = sql_literal(args.building_id)
    slug = sql_literal(args.profile_slug)
    reg = sql_literal(args.rera_registration_number)
    profile_rc = jsonb_lit({**BASE_TAG, **PROFILE_FACTS})
    dup = f"(SELECT id FROM buildings WHERE id <> {bid} AND lower(name) LIKE '%imperial heights%' ORDER BY created_at LIMIT 1)"
    profile = (f"(SELECT id FROM rera_project_profiles WHERE rera_registration_number = {reg} "
               f"AND raw_context->>'phase' = '{PHASE}' ORDER BY created_at LIMIT 1)")
    match_canon = (f"(SELECT id FROM rera_building_match_candidates WHERE building_id = {bid} "
                   f"AND raw_context->>'phase' = '{PHASE}' ORDER BY created_at LIMIT 1)")
    match_dup = (f"(SELECT id FROM rera_building_match_candidates WHERE building_id = {dup} "
                 f"AND raw_context->>'phase' = '{PHASE}' ORDER BY created_at LIMIT 1)")
    stmts = []

    # 1. RERA project profile (needs_human_review; RERA address columns left NULL).
    stmts.append(f"""
INSERT INTO rera_project_profiles
  (building_id, building_web_profile_id, rera_authority, rera_registration_number, official_project_name,
   promoter_name, project_type, project_status, registration_status, registration_date, completion_date,
   official_project_url, verification_status, confidence_score, raw_context)
VALUES ({bid}, (SELECT id FROM building_web_profiles WHERE profile_slug = {slug}),
   'MahaRERA', {reg}, {sql_literal(args.project_name)},
   'EPITOME RESIDENCY PRIVATE LIMITED', 'Residential / Group Housing', 'Completed',
   'registered_or_completed_needs_review', DATE '2017-08-05', DATE '2021-06-30',
   {sql_literal(args.official_project_url)}, 'needs_human_review', 0.85, {profile_rc});""")

    # 2. Two building-match candidates (candidate, NOT accepted).
    stmts.append(f"""
INSERT INTO rera_building_match_candidates
  (building_id, rera_project_profile_id, match_status, match_strength, match_reason, raw_context)
VALUES
  ({bid}, {profile}, 'candidate', 'strong',
   'Internal building name/code matches official RERA project Imperial Heights Wing C and D; this is the SEO profile anchor.', {tag_jsonb()}),
  ({dup}, {profile}, 'candidate', 'strong',
   'Duplicate internal Imperial Heights anchor also matches the same RERA project; building dedupe is pending.', {tag_jsonb()});""")

    # 3. 26 carpet-area records (needs_human_review; sqft computed from sqm).
    stmts.append(
        "INSERT INTO rera_carpet_area_records\n"
        "  (rera_project_profile_id, building_name, wing, apartment_type, carpet_area_sqm, carpet_area_sqft,\n"
        "   apartment_count, booked_count, source_label, verification_status, raw_context)\n"
        "VALUES\n  " + ",\n  ".join(
            f"({profile}, {sql_literal(b)}, NULL, {sql_literal(a)}, {s}, {round(s * SQM_TO_SQFT, 2)}, {c}, NULL, "
            f"{sql_literal(args.source_label)}, 'needs_human_review', {tag_jsonb()})"
            for (b, a, s, c) in CARPET_ROWS
        ) + ";"
    )

    # 4. 13 status/risk/document checks.
    stmts.append(
        "INSERT INTO rera_project_status_checks\n"
        "  (rera_project_profile_id, check_type, check_status, severity, safe_summary, checked_at, raw_context)\n"
        "VALUES\n  " + ",\n  ".join(
            f"({profile}, {sql_literal(ct)}, {sql_literal(cs)}, {sql_literal(sev)}, {sql_literal(summ)}, now(), {tag_jsonb()})"
            for (ct, cs, sev, summ) in STATUS_CHECKS
        ) + ";"
    )

    # 5. 6 pending review items (match x2, fact, carpet, status-risk[high], address[high]).
    stmts.append(f"""
INSERT INTO rera_verification_review_items
  (rera_project_profile_id, rera_building_match_candidate_id, rera_area_mismatch_candidate_id,
   review_type, status, priority, raw_context)
VALUES
  ({profile}, {match_canon}, NULL, 'rera_project_match_review', 'pending', 'normal', {tag_jsonb()}),
  ({profile}, {match_dup}, NULL, 'rera_project_match_review', 'pending', 'normal', {tag_jsonb()}),
  ({profile}, NULL, NULL, 'rera_fact_review', 'pending', 'normal', {tag_jsonb()}),
  ({profile}, NULL, NULL, 'rera_carpet_area_review', 'pending', 'normal', {tag_jsonb()}),
  ({profile}, NULL, NULL, 'rera_status_risk_review', 'pending', 'high', {tag_jsonb()}),
  ({profile}, NULL, NULL, 'rera_address_review', 'pending', 'high', {tag_jsonb()});""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Manual MahaRERA verification entry. Dry-run by default.")
    parser.add_argument("--building-id", required=True)
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--rera-registration-number", required=True)
    parser.add_argument("--official-project-url", required=True)
    parser.add_argument("--project-name", default="Imperial Heights Wing C and D")
    parser.add_argument("--source-label", default="official_maharera_pdf_snapshot_user_supplied")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()

    expected_carpet = len(CARPET_ROWS)
    expected_apartments = sum(c for _, _, _, c in CARPET_ROWS)
    print(f"Manual RERA verification entry. phase={PHASE}; source={SOURCE}; reg={args.rera_registration_number}; "
          f"project={args.project_name!r}. Counts only; review-gated; RERA address NOT trusted; no scrape/API; "
          "no building merge; no gap resolution; nothing verified/accepted/published/sent.")
    print(f"(carpet rows={expected_carpet}, apartment_count total={expected_apartments})")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real RERA data.")
        return 1

    code, found = run_psql(precheck_sql(args))
    if code != 0:
        print(found)
        return code
    checks = dict(line.split("|", 1) for line in found.splitlines() if "|" in line)
    if checks.get("building_found", "0") != "1":
        print(f"Refusing: building_id {args.building_id} not found.")
        return 1
    if checks.get("profile_found", "0") != "1":
        print(f"Refusing: profile_slug {args.profile_slug} not found.")
        return 1
    if checks.get("duplicate_anchor_found", "0") == "0":
        print("Refusing: could not resolve the duplicate Imperial Heights anchor for the second match.")
        return 1
    if int(checks.get("registration_exists", "0")) != 0 and not args.allow_existing:
        print(f"Refusing: RERA registration {args.rera_registration_number} already exists (use --allow-existing).")
        return 1

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("planned rows: rera_project_profiles +1, rera_building_match_candidates +2, "
              f"rera_carpet_area_records +{expected_carpet}, rera_project_status_checks +{len(STATUS_CHECKS)}, "
              "rera_area_mismatch_candidates +0, rera_verification_review_items +6.")
        print("verification_status=needs_human_review; match_status=candidate; carpet verification_status=needs_human_review; "
              "reviews=pending; ready_for_building_dedupe/ready_for_content_fact_use unchanged (false).")
        print("current phase-6.9 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.9 rows already exist. Run cleanup_manual_rera_verification.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args))
    print("Manual RERA verification rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
