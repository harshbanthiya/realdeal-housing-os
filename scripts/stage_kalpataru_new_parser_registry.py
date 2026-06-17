#!/usr/bin/env python3
"""Stage the refined Kalpataru XLS parser output as a separate Cockpit building.

Creates a new comparison building named "Kalpataru Radiance New Parser" and
loads:

  - the full expected physical inventory: A = 31 x 5, B/C/D = 31 x 6
  - only the refined parser's confident XLS registration events

Everything is tagged with source='igr_xls_kalpataru_new_parser_v1' and is
reversible. Dry-run by default; writing requires --apply.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
TIMELINE_JSON = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_radiance_timelines.json"
INDEX22_MAPPING_JSON = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_page1_index22_mapping.json"

SOURCE = "igr_xls_kalpataru_new_parser_v1"
BUILDING_NAME = "Kalpataru Radiance New Parser"
BASE_BUILDING_NAME = "Kalpataru Radiance"
PHASE = "kalpataru_radiance_new_parser_registry_v1"
TOWER_UNITS_PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
FLOORS = 31
ROLE_BY_CATEGORY = {
    "ownership": ("seller", "purchaser"),
    "tenancy": ("lessor", "lessee"),
    "encumbrance": ("mortgagee", "mortgagor"),
    "other": ("seller", "purchaser"),
}


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


def q(value: Any) -> str:
    if value in (None, ""):
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def qn(value: Any) -> str:
    if value in (None, ""):
        return "NULL"
    try:
        return str(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return "NULL"


def qi(value: Any) -> str:
    if value in (None, ""):
        return "NULL"
    try:
        return str(int(float(str(value).replace(",", ""))))
    except (TypeError, ValueError):
        return "NULL"


def jb(value: dict[str, Any]) -> str:
    return "'" + json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def row_id() -> str:
    return str(uuid.uuid4())


def load_events() -> list[dict[str, Any]]:
    with TIMELINE_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    events: list[dict[str, Any]] = []
    for unit in payload["units"]:
        events.extend(unit["events"])
    return sorted(events, key=lambda e: (e.get("registration_date") or "", e.get("wing") or "", e.get("unit_number") or "", e.get("doc_number") or ""))


def load_index22_details() -> dict[str, dict[str, Any]]:
    if not INDEX22_MAPPING_JSON.exists():
        return {}
    with INDEX22_MAPPING_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(row.get("doc_number")): row for row in payload.get("rows", []) if row.get("doc_number")}


def unit_number(floor: int, stack: int) -> str:
    return f"{floor}{stack}"


def base_tag(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    tag = {
        "source": SOURCE,
        "phase": PHASE,
        "base_building_name": BASE_BUILDING_NAME,
        "comparison_building": True,
        "is_fake": False,
        "is_sample": False,
        "external_calls_made": False,
    }
    if extra:
        tag.update(extra)
    return tag


DELETE_ORDER = [
    ("unit_registration_review_items", "raw_context"),
    ("registration_party_contact_matches", "raw_context"),
    ("unit_registration_parties", "raw_context"),
    ("unit_registration_records", "raw_context"),
    ("igr_registration_search_jobs", "raw_context"),
    ("building_property_identifiers", "raw_context"),
    ("building_tower_structure", "raw_context"),
    ("rera_carpet_area_records", "raw_context"),
    ("rera_project_profiles", "raw_context"),
    ("building_aliases", "metadata"),
    ("building_units", "metadata"),
    ("buildings", "metadata"),
]


def counts_sql() -> str:
    parts = [
        f"SELECT '{table}' AS item, count(*)::text AS val FROM {table} WHERE {column}->>'source' = '{SOURCE}'"
        for table, column in DELETE_ORDER
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def delete_sql() -> str:
    deletes = "\n".join(f"DELETE FROM {table} WHERE {column}->>'source' = '{SOURCE}';" for table, column in DELETE_ORDER)
    return f"BEGIN;\n{deletes}\nCOMMIT;\n{counts_sql()}"


def build_insert_sql(events: list[dict[str, Any]]) -> str:
    index22_details = load_index22_details()
    building_id = row_id()
    profile_id = row_id()
    search_job_id = row_id()
    unit_ids: dict[tuple[str, str], str] = {}
    statements = ["BEGIN;"]

    statements.append(
        """
INSERT INTO buildings
  (id, name, developer, project_name, address_line_1, address_line_2, area, locality, city, state, postal_code, notes, metadata)
VALUES
  ({building_id}, {name}, 'Keyana Estate LLP', {project}, 'CTS 260/5A', 'Off Post Office Road',
   'Goregaon West', 'Goregaon West', 'Mumbai', 'Maharashtra', '400104',
   'Comparison building generated from refined Kalpataru Radiance XLS parser; confident events only.',
   {metadata});
""".format(
            building_id=q(building_id),
            name=q(BUILDING_NAME),
            project=q(BASE_BUILDING_NAME),
            metadata=jb(base_tag({"loaded_from": str(TIMELINE_JSON)})),
        )
    )
    statements.append(
        f"""
INSERT INTO building_aliases
  (building_id, alias_text, alias_type, normalized_alias, confidence, status, notes, metadata)
VALUES
  ({q(building_id)}, 'Kalpataru Radiance New Parser', 'comparison_alias', 'kalpataru radiance new parser',
   1.000, 'approved', 'Operator comparison building for refined XLS parser output.', {jb(base_tag())});
"""
    )
    statements.append(
        f"""
INSERT INTO rera_project_profiles
  (id, building_id, rera_authority, rera_registration_number, official_project_name, promoter_name,
   project_type, project_status, registration_status, district, locality, pincode,
   verification_status, confidence_score, raw_context)
VALUES
  ({q(profile_id)}, {q(building_id)}, 'MahaRERA', 'P51800000591', {q(BUILDING_NAME)}, 'Keyana Estate LLP',
   'Residential', 'Completed / imported for comparison', 'Registered', 'Mumbai Suburban', 'Goregaon West',
   '400104', 'verified', 0.95, {jb(base_tag({"expected_units": 713}))});
"""
    )

    for wing, per_floor in TOWER_UNITS_PER_FLOOR.items():
        total = FLOORS * per_floor
        statements.append(
            f"""
INSERT INTO building_tower_structure
  (building_id, rera_project_profile_id, tower_label, tower_type, floors_above_ground,
   units_per_typical_floor, total_units, sanctioned_floors, source_label, source_type,
   confidence_score, verification_status, raw_context)
VALUES
  ({q(building_id)}, {q(profile_id)}, {q(wing)}, 'residential', {FLOORS}, {per_floor}, {total}, {FLOORS},
   'Operator supplied structure: Kalpataru Radiance A/B/C/D', 'manual', 0.95, 'verified',
   {jb(base_tag({"wing": wing, "units_per_floor": per_floor, "floors": FLOORS, "total_units": total}))});
"""
        )
        statements.append(
            f"""
INSERT INTO rera_carpet_area_records
  (rera_project_profile_id, building_name, wing, apartment_type, apartment_count, source_label,
   verification_status, raw_context)
VALUES
  ({q(profile_id)}, {q(BUILDING_NAME)}, {q(wing)}, 'Apartment', {total},
   'Operator supplied physical inventory for parser comparison', 'verified',
   {jb(base_tag({"wing": wing, "apartment_count": total}))});
"""
        )
        for floor in range(1, FLOORS + 1):
            for stack in range(1, per_floor + 1):
                flat = unit_number(floor, stack)
                uid = row_id()
                unit_ids[(wing, flat)] = uid
                statements.append(
                    f"""
INSERT INTO building_units
  (id, building_id, building_name, wing, unit_number, floor, typology, canonical_status, confidence, metadata)
VALUES
  ({q(uid)}, {q(building_id)}, {q(BUILDING_NAME)}, {q(wing)}, {q(flat)}, {q(str(floor))}, 'apartment',
   'active', 0.95, {jb(base_tag({"wing": wing, "floor": floor, "stack": stack, "unit_number": flat}))});
"""
                )

    statements.append(
        f"""
INSERT INTO building_property_identifiers
  (building_id, rera_project_profile_id, identifier_type, identifier_value, district, village, sro_office,
   is_igr_search_key, source_label, source_type, confidence_score, verification_status, raw_context)
VALUES
  ({q(building_id)}, {q(profile_id)}, 'cts_number', '260/5A', 'Mumbai Suburban', 'Pahadi Goregaon',
   'Borivali / Goregaon IGR offices', true, 'Operator supplied XLS search key', 'manual', 0.95, 'verified',
   {jb(base_tag({"identifier": "CTS 260/5A"}))});
"""
    )
    statements.append(
        f"""
INSERT INTO igr_registration_search_jobs
  (id, building_id, search_year, district, village, property_number, job_status, captcha_required,
   external_call_made, result_record_count, completed_at, raw_context)
VALUES
  ({q(search_job_id)}, {q(building_id)}, 2026, 'Mumbai Suburban', 'Pahadi Goregaon', '260/5A',
   'parsed', true, false, {len(events)}, now(), {jb(base_tag({"source_files": "operator supplied XLS exports"}))});
"""
    )

    for event in events:
        record_id = row_id()
        detail = index22_details.get(str(event.get("doc_number") or ""))
        wing = str(event.get("wing") or "")
        flat = str(event.get("unit_number") or "")
        unit_id = unit_ids.get((wing, flat))
        event_key = "|".join([
            str(event.get("source_file") or ""),
            str(event.get("internal_document_number") or ""),
            str(event.get("doc_number") or ""),
            wing,
            flat,
        ])
        event_tag = base_tag({
            "event_key": event_key,
            "source_file": event.get("source_file"),
            "internal_document_number": event.get("internal_document_number"),
            "date_of_execution": event.get("date_of_execution"),
            "parser_phase": event.get("phase"),
            "parse_notes": event.get("parse_notes") or [],
            "property_description_english": event.get("property_description_english"),
            "property_tokens": event.get("property_tokens") or [],
            "index22_file": detail.get("index_file") if detail else None,
            "index22_enriched": bool(detail),
        })
        area_text: Any = event.get("property", {}).get("primary_area") or event.get("area_name")
        if detail and detail.get("area_text"):
            area_text = detail.get("area_text")
        statements.append(
            f"""
INSERT INTO unit_registration_records
  (id, building_id, building_unit_id, rera_project_profile_id, igr_registration_search_job_id,
   doc_number, registration_year, registration_date, sro_office, document_type, transaction_category,
   property_description_raw, wing_text, unit_text, floor_text, area_text, consideration_amount,
   market_value, stamp_duty, registration_fee, tenancy_start_date, tenancy_end_date,
   tenancy_monthly_rent, tenancy_deposit, parse_confidence, verification_status, source_label, raw_context)
VALUES
  ({q(record_id)}, {q(building_id)}, {q(unit_id)}, {q(profile_id)}, {q(search_job_id)},
   {q(event.get("doc_number"))}, {qi(event.get("registration_year"))}, {q(event.get("registration_date"))},
   {q(event.get("sro_office"))}, {q(event.get("document_type"))}, {q(event.get("category"))},
   {q(event.get("property_description_raw"))}, {q(wing)}, {q(flat)}, {q(event.get("floor"))},
   {q(area_text)},
   {qn(detail.get("consideration_amount") if detail and detail.get("consideration_amount") else event.get("consideration_amount"))},
   {qn(detail.get("market_value") if detail and detail.get("market_value") else event.get("market_value"))},
   {qn(detail.get("stamp_duty") if detail and detail.get("stamp_duty") else event.get("stamp_duty"))},
   {qn(detail.get("registration_fee") if detail and detail.get("registration_fee") else event.get("registration_fee"))},
   {q(event.get("tenancy_start_date"))}, {q(event.get("tenancy_end_date"))},
   {qn(detail.get("tenancy_monthly_rent") if detail and detail.get("tenancy_monthly_rent") else event.get("tenancy_monthly_rent"))},
   {qn(detail.get("tenancy_deposit") if detail and detail.get("tenancy_deposit") else event.get("tenancy_deposit"))},
   {qn(event.get("tower_parse_confidence") or 0.95)}, 'parsed_candidate',
   'Refined Kalpataru Radiance XLS parser (confident A/B/C/D events)', {jb(event_tag)});
"""
        )
        event_parties = event.get("parties") or []
        if detail and detail.get("parties"):
            seller_role, purchaser_role = ROLE_BY_CATEGORY.get(str(event.get("category") or "other"), ROLE_BY_CATEGORY["other"])
            event_parties = []
            order = 0
            for role, group in ((seller_role, "sellers"), (purchaser_role, "purchasers")):
                for party in detail.get("parties", {}).get(group, []):
                    event_parties.append(
                        {
                            "role": role,
                            "name_raw": party.get("name"),
                            "name_english": party.get("name"),
                            "name_devanagari": party.get("name"),
                            "pan": party.get("pan"),
                            "age": party.get("age"),
                            "address": party.get("address"),
                            "party_type": "unknown",
                            "display_order": order,
                        }
                    )
                    order += 1
        for index, party in enumerate(event_parties):
            party_tag = base_tag({
                "event_key": event_key,
                "source_file": event.get("source_file"),
                "internal_document_number": event.get("internal_document_number"),
            })
            statements.append(
                f"""
INSERT INTO unit_registration_parties
  (unit_registration_record_id, party_role, party_name_raw, party_name_normalized, party_name_english,
   party_name_devanagari, party_pan, party_age, party_address, party_type, display_order, raw_context)
VALUES
  ({q(record_id)}, {q(party.get("role"))}, {q(party.get("name_raw"))},
   {q((party.get("name_english") or party.get("name_raw") or "").lower())},
   {q(party.get("name_english"))}, {q(party.get("name_devanagari"))}, {q(party.get("pan"))},
   {qi(party.get("age"))}, {q(party.get("address"))}, {q(party.get("party_type") or "unknown")},
   {qi(party.get("display_order") if party.get("display_order") is not None else index)}, {jb(party_tag)});
"""
            )
        statements.append(
            f"""
INSERT INTO unit_registration_review_items
  (building_id, unit_registration_record_id, review_type, status, priority, decision_notes, raw_context)
VALUES
  ({q(building_id)}, {q(record_id)}, 'registration_record_review', 'pending', 'normal',
   'Confident parser event staged to comparison building; verify before promoting to canonical building.',
   {jb(base_tag({"event_key": event_key}))});
"""
        )

    statements.append("COMMIT;")
    statements.append(counts_sql())
    return "\n".join(statements)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage Kalpataru Radiance New Parser comparison building. Dry-run by default.")
    parser.add_argument("--apply", action="store_true", help="Write tagged rows to Postgres.")
    parser.add_argument("--revert", action="store_true", help="Delete only rows tagged with this script's source.")
    args = parser.parse_args()

    events = load_events()
    unit_count = sum(FLOORS * per_floor for per_floor in TOWER_UNITS_PER_FLOOR.values())
    print(f"source={SOURCE}")
    print(f"comparison building={BUILDING_NAME}")
    print(f"would stage units={unit_count}, confident registration events={len(events)}")

    if args.revert:
        if not args.apply:
            code, current = run_psql(counts_sql())
            print("Revert dry-run. Current tagged rows:")
            print(current)
            print("Deleting requires --revert --apply.")
            return code
        code, output = run_psql(delete_sql())
        print("Remaining tagged rows after revert:")
        print(output)
        return code

    if not args.apply:
        code, current = run_psql(counts_sql())
        print("Dry run only. Current tagged rows:")
        print(current)
        print("Writing requires --apply.")
        return code

    code, deleted = run_psql(delete_sql())
    if code != 0:
        print("Failed during cleanup:")
        print(deleted)
        return code
    code, output = run_psql(build_insert_sql(events))
    if code != 0:
        print("Failed during insert:")
        print(output)
        return code
    print("Staged tagged rows:")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
