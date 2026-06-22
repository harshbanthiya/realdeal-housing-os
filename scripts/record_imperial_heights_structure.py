#!/usr/bin/env python3
"""Phase 6.17 — record REAL Imperial Heights (Wing C & D) building structure + IGR identifiers
from the operator-supplied MahaRERA print PDF (project P51800003270) and master-plan sheet.

Dry-run by default. Reading/writing the REAL building requires --apply AND --real-ok. Reversible
via --revert (deletes only the rows tagged with this phase's source marker).

Source: manually-supplied PDFs only (MahaRERA project page + master plan). This script does NOT
scrape MahaRERA/IGR, call any external API, browse the web, or solve a CAPTCHA — it records facts
a human read from the PDFs, exactly like the Phase 6.9 manual verification step. Every row is
review-gated (verification_status candidate / needs_human_review) and tagged for clean revert.

What it records (for the building the RERA profile P51800003270 is linked to):
  - 2 building_tower_structure rows: Wing C and Wing D, each 51 sanctioned floors.
    * Wing D total_units = 213 (from the RERA apartment summary).
    * Wing C total_units = NULL — the RERA summary does NOT itemize Wing C (KNOWN GAP).
  - building_property_identifiers: village=Borivali, taluka=Borivali, district=Mumbai Suburban,
    pincode=400047 (the PROJECT location; the Andheri/BKC address in the PDF is the promoter's
    office, not the project), plus a CTS placeholder row flagged needs_human_review because RERA
    shows only "1 part" — the real CTS/survey must come from the property card before any IGR search.
  - unit_registration_review_items: structure_review + identifier_review (pending), incl. notes
    on the Wing C count gap and the CTS gap.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.17"
SOURCE = "manual_rera_ih_structure_6_17"
RERA_REG = "P51800003270"
SRC_PDFS = "Maharashtra Real Estate Regulatory Authority.pdf; Imperial heights master plan .pdf"

TAGGED_TABLES = [
    ("building_tower_structure", "raw_context"),
    ("building_property_identifiers", "raw_context"),
    ("unit_registration_review_items", "raw_context"),
]
TAG = (
    "jsonb_build_object("
    f"'source', '{SOURCE}', 'phase', '{PHASE}', 'rera_reg', '{RERA_REG}', "
    f"'source_pdfs', '{SRC_PDFS}', 'external_calls_made', false, 'is_fake', false)"
)

PROFILE = f"(SELECT id FROM rera_project_profiles WHERE rera_registration_number = '{RERA_REG}' ORDER BY created_at LIMIT 1)"
BUILDING = f"(SELECT building_id FROM rera_project_profiles WHERE rera_registration_number = '{RERA_REG}' ORDER BY created_at LIMIT 1)"
WING_C = (
    f"(SELECT id FROM building_tower_structure WHERE raw_context->>'source' = '{SOURCE}' "
    "AND tower_label = 'Imperial Heights Wing C' ORDER BY created_at LIMIT 1)"
)
CTS_ID = (
    f"(SELECT id FROM building_property_identifiers WHERE raw_context->>'source' = '{SOURCE}' "
    "AND identifier_type = 'cts_number' ORDER BY created_at LIMIT 1)"
)

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} WHERE {col}->>'source' = '{SOURCE}'"
        for t, col in TAGGED_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def insert_sql() -> str:
    stmts = []
    # 2 tower structures (51 sanctioned floors each). Wing D total_units=213; Wing C unknown.
    stmts.append(f"""
INSERT INTO building_tower_structure
  (building_id, rera_project_profile_id, tower_label, tower_type, sanctioned_floors,
   units_per_typical_floor, total_units, source_label, source_type, confidence_score,
   verification_status, raw_context)
VALUES
  ({BUILDING}, {PROFILE}, 'Imperial Heights Wing C', 'residential', 51,
   NULL, NULL, 'MahaRERA project page P51800003270 (Building Details)', 'rera_filing', 0.80,
   'needs_human_review',
   {TAG} || jsonb_build_object(
     'sanctioned_floors_definition', 'Including Basement+Stilt+Podium+Service+Habitable excluding terrace',
     'apartment_breakdown_in_rera', false,
     'note', 'RERA apartment summary does NOT itemize Wing C; unit count unknown — obtain Wing C apartment summary / separate registration before treating 213 as the project total.')),
  ({BUILDING}, {PROFILE}, 'Imperial Heights Wing D', 'residential', 51,
   NULL, 213, 'MahaRERA project page P51800003270 (Building Details + Apartment Summary)', 'rera_filing', 0.85,
   'needs_human_review',
   {TAG} || jsonb_build_object(
     'sanctioned_floors_definition', 'Including Basement+Stilt+Podium+Service+Habitable excluding terrace',
     'apartment_breakdown_in_rera', true,
     'apartment_type_row_count', 26,
     'duplex_unit_count', 16,
     'note', '213 apartments across 26 type-rows. 16 DUP (duplex) units are unique top-floor units (count 1 each); regular types repeat on lower floors (e.g. 2.5 BHK A x42, 2.5 BHK B x32, 3.5 BHK A/G x24).'));""")

    # Property identifiers — PROJECT location (Borivali), not the promoter's Andheri office.
    stmts.append(f"""
INSERT INTO building_property_identifiers
  (building_id, rera_project_profile_id, identifier_type, identifier_value, district, village,
   is_igr_search_key, source_label, source_type, source_url, confidence_score, verification_status, raw_context)
VALUES
  ({BUILDING}, {PROFILE}, 'village', 'Borivali', 'Mumbai Suburban', 'Borivali',
   false, 'MahaRERA project page P51800003270 (Project Address Details)', 'rera_filing',
   'https://maharerait.maharashtra.gov.in/public/project/view/6231', 0.80, 'candidate',
   {TAG} || jsonb_build_object('note', 'Project village=Borivali. The Andheri/BKC address in the PDF is the promoter office, not the project.')),
  ({BUILDING}, {PROFILE}, 'district', 'Mumbai Suburban', 'Mumbai Suburban', 'Borivali',
   false, 'MahaRERA project page P51800003270', 'rera_filing',
   'https://maharerait.maharashtra.gov.in/public/project/view/6231', 0.80, 'candidate', {TAG}),
  ({BUILDING}, {PROFILE}, 'pincode', '400047', 'Mumbai Suburban', 'Borivali',
   false, 'MahaRERA project page P51800003270', 'rera_filing',
   'https://maharerait.maharashtra.gov.in/public/project/view/6231', 0.80, 'candidate', {TAG}),
  ({BUILDING}, {PROFILE}, 'cts_number', NULL, 'Mumbai Suburban', 'Borivali',
   false, 'MahaRERA shows "1 part" placeholder only', 'rera_filing',
   'https://maharerait.maharashtra.gov.in/public/project/view/6231', 0.20, 'needs_human_review',
   {TAG} || jsonb_build_object('note', 'RERA Land Area section shows only "1 part" — no real CTS/survey number. Obtain actual CTS/survey from the Mumbai Suburban property card / Mahabhumi before any IGR eSearch. is_igr_search_key stays false until a real CTS is recorded and verified.'));""")

    # Review items: structure + identifier, with the two known gaps called out.
    stmts.append(f"""
INSERT INTO unit_registration_review_items
  (building_id, building_tower_structure_id, building_property_identifier_id, review_type,
   status, priority, decision_notes, raw_context)
VALUES
  ({BUILDING}, {WING_C}, NULL, 'structure_review', 'pending', 'high',
   'Confirm Wing C/D = 51 floors each. KNOWN GAP: Wing C apartment count is not in the RERA summary; 213 is Wing D only.', {TAG}),
  ({BUILDING}, NULL, {CTS_ID}, 'identifier_review', 'pending', 'high',
   'Confirm Borivali village/pincode. BLOCKER for IGR: real CTS/survey number still required (RERA shows only "1 part").', {TAG});""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def delete_sql() -> str:
    order = [
        ("unit_registration_review_items", "raw_context"),
        ("building_property_identifiers", "raw_context"),
        ("building_tower_structure", "raw_context"),
    ]
    stmts = "\n".join(f"DELETE FROM {t} WHERE {col}->>'source' = '{SOURCE}';" for t, col in order)
    return f"BEGIN;\n{stmts}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Record REAL Imperial Heights structure + identifiers from RERA PDF. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()

    print(f"Imperial Heights structure recorder. phase={PHASE}; source={SOURCE}; rera_reg={RERA_REG}. "
          "From operator-supplied PDFs only; no MahaRERA/IGR/external call; review-gated; reversible.")

    code, building = run_psql(BUILDING.replace("(SELECT", "SELECT").rstrip(")") + ";")
    if code != 0:
        print(building)
        return code
    if not building:
        print(f"Refusing: no RERA profile found for {RERA_REG} (cannot resolve the building).")
        return 1
    print(f"Target building_id (from RERA profile {RERA_REG}): {building}")

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
        print("planned: 2 tower structures (Wing C/D, 51 floors; Wing D=213 units, Wing C unknown), "
              "4 property identifiers (village/district/pincode Borivali + CTS gap), 2 review items.")
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
