#!/usr/bin/env python3
"""Apply fake source-aware import rows for Phase 3.4 testing only."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Iterable, List

from duplicate_utils import duplicate_summary, parse_json_list
from plan_source_aware_import import is_inventory_row, is_lead_requirement, row_has_property_hint, summarize_rows


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
BATCH_LABEL = "FAKE_PHASE_3_4_TEST"
FAKE_SOURCE_MARKER = "FAKE_EXAMPLE_ONLY"
BLOCKED_INPUT_PARTS = {
    ("imports", "contacts", "raw_samples"),
    ("imports", "contacts", "raw_archives"),
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


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def path_has_parts(path: Path, parts: Iterable[str]) -> bool:
    path_parts = tuple(path.parts)
    needle = tuple(parts)
    return any(path_parts[index : index + len(needle)] == needle for index in range(len(path_parts) - len(needle) + 1))


def validate_fake_input(path: Path, rows: List[Dict[str, str]]) -> List[str]:
    errors: List[str] = []
    resolved = path.resolve()
    for blocked in BLOCKED_INPUT_PARTS:
        if path_has_parts(resolved, blocked):
            errors.append("input_path_is_real_raw_sample_or_archive")
    if "exports" not in resolved.parts or "contacts" not in resolved.parts:
        errors.append("input_must_be_generated_under_exports_contacts")
    if not path.name.startswith("cleaned_contacts_"):
        errors.append("input_must_be_cleaned_contacts_output")
    if rows:
        unsafe_sources = [
            row.get("source_file", "")
            for row in rows
            if not (".example" in row.get("source_file", "") or "/sample_" in row.get("source_file", "") or "sample_" in Path(row.get("source_file", "")).name)
        ]
        if unsafe_sources:
            errors.append("source_rows_do_not_look_like_fake_example_data")
    return errors


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def sql_numeric(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "NULL"
    try:
        float(text)
    except ValueError:
        return "NULL"
    return text


def json_value(value: str, default: object) -> object:
    if not value:
        return default
    try:
        parsed = json.loads(value)
        return parsed
    except Exception:
        return default


def json_sql(value: object) -> str:
    return sql_literal(json.dumps(value, ensure_ascii=True, sort_keys=True)) + "::jsonb"


def allowed_value(value: object, allowed: set[str], default: str) -> str:
    cleaned = str(value or "").strip().lower().replace(" ", "_")
    return cleaned if cleaned in allowed else default


def array_sql(values: Iterable[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return "'{}'::text[]"
    return "ARRAY[" + ",".join(sql_literal(item) for item in items) + "]::text[]"


def psql(sql: str) -> int:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        print("Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env.")
        return 1
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
    return subprocess.run(command, input=sql, text=True, check=False).returncode


def source_key(row: Dict[str, str]) -> tuple[str, str, str]:
    return (row.get("source_file", ""), row.get("source_sheet", ""), row.get("source_format", ""))


def method_rows(row: Dict[str, str], import_row_id: str, source_file_id: str) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    phones = set(parse_json_list(row.get("phones_normalized_json", "")))
    if row.get("phone_normalized"):
        phones.add(row["phone_normalized"])
    for phone in sorted(phones):
        output.append(
            {
                "id": str(uuid.uuid4()),
                "contact_import_row_id": import_row_id,
                "source_file_id": source_file_id,
                "method_type": "mobile" if row.get("phone_type") == "mobile" else "phone",
                "raw_value": "",
                "normalized_value": phone,
                "label": row.get("phone_type") or "phone",
                "is_primary": phone == row.get("phone_normalized"),
                "validation_status": "valid",
                "raw_payload": {"fake_phase": BATCH_LABEL},
            }
        )
    emails = set(parse_json_list(row.get("emails_normalized_json", "")))
    if row.get("email_normalized"):
        emails.add(row["email_normalized"])
    for email in sorted(emails):
        output.append(
            {
                "id": str(uuid.uuid4()),
                "contact_import_row_id": import_row_id,
                "source_file_id": source_file_id,
                "method_type": "email",
                "raw_value": "",
                "normalized_value": email,
                "label": "email",
                "is_primary": email == row.get("email_normalized"),
                "validation_status": "valid",
                "raw_payload": {"fake_phase": BATCH_LABEL},
            }
        )
    for key, method_type in [("website", "website"), ("google_maps_link", "google_maps")]:
        if row.get(key):
            output.append(
                {
                    "id": str(uuid.uuid4()),
                    "contact_import_row_id": import_row_id,
                    "source_file_id": source_file_id,
                    "method_type": method_type,
                    "raw_value": "",
                    "normalized_value": row[key],
                    "label": key,
                    "is_primary": False,
                    "validation_status": "unverified",
                    "raw_payload": {"fake_phase": BATCH_LABEL},
                }
            )
    return output


def review_types(row: Dict[str, str]) -> List[str]:
    types = []
    if row.get("cleaned_display_name") or row.get("raw_name"):
        types.append("merge_candidate")
    if str(row.get("needs_review", "")).lower() == "true":
        types.append("merge_candidate")
    if not row.get("cleaned_display_name"):
        types.append("missing_name")
    if row.get("rejection_reason", "").find("phone") >= 0:
        types.append("invalid_phone")
    if row.get("rejection_reason", "").find("email") >= 0:
        types.append("invalid_email")
    if row_has_property_hint(row):
        types.append("property_hint_review")
    if is_inventory_row(row):
        types.append("inventory_match_review")
    if is_lead_requirement(row):
        types.append("lead_requirement_review")
    if row.get("source_format") in {"unknown_contact_csv", "unknown"}:
        types.append("source_format_unknown")
    return sorted(set(types))


def build_sql(cleaned_csv: Path, rows: List[Dict[str, str]]) -> tuple[str, Dict[str, int]]:
    batch_id = str(uuid.uuid4())
    source_ids = {key: str(uuid.uuid4()) for key in sorted({source_key(row) for row in rows})}
    row_ids = [str(uuid.uuid4()) for _ in rows]
    counts = {
        "import_batches": 1 if rows else 0,
        "source_files": len(source_ids),
        "contact_import_rows": len(rows),
        "contact_methods": 0,
        "contact_aliases": 0,
        "contact_property_hints": 0,
        "lead_requirements": 0,
        "inventory_import_rows": 0,
        "contact_duplicate_candidates": 0,
        "import_review_items": 0,
    }

    statements = ["BEGIN;"]
    statements.append(
        """
INSERT INTO import_batches (
  id, source_name, source_type, source_file_path, status, total_rows, processed_rows, notes, metadata, started_at, completed_at
) VALUES (
  {batch_id}, {source_name}, 'contacts', {source_path}, 'completed', {total_rows}, {processed_rows},
  {notes}, {metadata}, now(), now()
);
""".format(
            batch_id=sql_literal(batch_id),
            source_name=sql_literal(BATCH_LABEL),
            source_path=sql_literal(str(cleaned_csv)),
            total_rows=len(rows),
            processed_rows=len(rows),
            notes=sql_literal("Fake Phase 3.4 source-aware import test. Safe to clean up."),
            metadata=json_sql({"batch_label": BATCH_LABEL, "is_test": True, "source_marker": FAKE_SOURCE_MARKER}),
        )
    )

    for (source_file, source_sheet, source_format), source_id in source_ids.items():
        column_names = list(rows[0].keys()) if rows else []
        source_rows = [row for row in rows if source_key(row) == (source_file, source_sheet, source_format)]
        statements.append(
            """
INSERT INTO source_files (
  id, import_batch_id, original_file_name, stored_relative_path, file_ext, detected_source_format,
  sheet_name, row_count, column_names, profile_summary, processing_status, processing_notes
) VALUES (
  {id}, {batch_id}, {original_file_name}, {stored_relative_path}, {file_ext}, {source_format},
  {sheet_name}, {row_count}, {column_names}, {profile_summary}, 'planned', {notes}
);
""".format(
                id=sql_literal(source_id),
                batch_id=sql_literal(batch_id),
                original_file_name=sql_literal(FAKE_SOURCE_MARKER),
                stored_relative_path=sql_literal(source_file),
                file_ext=sql_literal(Path(source_file).suffix),
                source_format=sql_literal(source_format),
                sheet_name=sql_literal(source_sheet or None),
                row_count=len(source_rows),
                column_names=json_sql(column_names),
                profile_summary=json_sql({"fake_phase": BATCH_LABEL, "original_source_file": source_file}),
                notes=sql_literal("Fake example source only."),
            )
        )

    for index, row in enumerate(rows):
        import_row_id = row_ids[index]
        source_id = source_ids[source_key(row)]
        raw_payload = json_value(row.get("raw_payload_json", ""), {})
        raw_payload["_fake_phase"] = BATCH_LABEL
        tags = [part for part in str(row.get("parsed_tags", "")).split("|") if part]
        needs_review = str(row.get("needs_review", "")).lower() == "true"
        statements.append(
            """
INSERT INTO contact_import_rows (
  id, import_batch_id, source_file, source_sheet, source_row_number, source_format,
  raw_name, raw_phone, raw_email, raw_notes, raw_payload, cleaned_display_name,
  phone_normalized, email_normalized, parsed_building_code, parsed_building_name,
  parsed_wing, parsed_unit_number, parsed_role, parsed_tags, parse_confidence,
  rejection_reason, needs_review
) VALUES (
  {id}, {batch_id}, {source_file}, {source_sheet}, {source_row_number}, {source_format},
  {raw_name}, {raw_phone}, {raw_email}, {raw_notes}, {raw_payload}, {cleaned_display_name},
  {phone_normalized}, {email_normalized}, {parsed_building_code}, {parsed_building_name},
  {parsed_wing}, {parsed_unit_number}, {parsed_role}, {parsed_tags}, {parse_confidence},
  {rejection_reason}, {needs_review}
);
""".format(
                id=sql_literal(import_row_id),
                batch_id=sql_literal(batch_id),
                source_file=sql_literal(FAKE_SOURCE_MARKER),
                source_sheet=sql_literal(row.get("source_sheet") or None),
                source_row_number=row.get("source_row_number") or "NULL",
                source_format=sql_literal(row.get("source_format")),
                raw_name=sql_literal(row.get("raw_name")),
                raw_phone=sql_literal(row.get("raw_phone")),
                raw_email=sql_literal(row.get("raw_email")),
                raw_notes=sql_literal(row.get("raw_notes")),
                raw_payload=json_sql(raw_payload),
                cleaned_display_name=sql_literal(row.get("cleaned_display_name")),
                phone_normalized=sql_literal(row.get("phone_normalized")),
                email_normalized=sql_literal(row.get("email_normalized")),
                parsed_building_code=sql_literal(row.get("parsed_building_code")),
                parsed_building_name=sql_literal(row.get("parsed_building_name")),
                parsed_wing=sql_literal(row.get("parsed_wing")),
                parsed_unit_number=sql_literal(row.get("parsed_unit_number")),
                parsed_role=sql_literal(row.get("parsed_role")),
                parsed_tags=array_sql(tags),
                parse_confidence=sql_numeric(row.get("parse_confidence", "")),
                rejection_reason=sql_literal(row.get("rejection_reason") or None),
                needs_review=sql_bool(needs_review),
            )
        )

        for method in method_rows(row, import_row_id, source_id):
            counts["contact_methods"] += 1
            statements.append(
                """
INSERT INTO contact_methods (
  id, contact_import_row_id, source_file_id, method_type, raw_value, normalized_value,
  label, is_primary, validation_status, source_file, source_sheet, source_row_number, raw_payload
) VALUES (
  {id}, {contact_import_row_id}, {source_file_id}, {method_type}, {raw_value}, {normalized_value},
  {label}, {is_primary}, {validation_status}, {source_file}, {source_sheet}, {source_row_number}, {raw_payload}
);
""".format(
                    id=sql_literal(method["id"]),
                    contact_import_row_id=sql_literal(import_row_id),
                    source_file_id=sql_literal(source_id),
                    method_type=sql_literal(method["method_type"]),
                    raw_value=sql_literal(method["raw_value"]),
                    normalized_value=sql_literal(method["normalized_value"]),
                    label=sql_literal(method["label"]),
                    is_primary=sql_bool(bool(method["is_primary"])),
                    validation_status=sql_literal(method["validation_status"]),
                    source_file=sql_literal(FAKE_SOURCE_MARKER),
                    source_sheet=sql_literal(row.get("source_sheet") or None),
                    source_row_number=row.get("source_row_number") or "NULL",
                    raw_payload=json_sql(method["raw_payload"]),
                )
            )

        aliases = parse_json_list(row.get("aliases_json", ""))
        if row.get("raw_name"):
            aliases.append(row["raw_name"])
        for alias in sorted({item for item in aliases if item}):
            counts["contact_aliases"] += 1
            statements.append(
                """
INSERT INTO contact_aliases (id, alias_text, alias_type, source_file)
VALUES ({id}, {alias_text}, 'source_raw_name', {source_file});
""".format(id=sql_literal(str(uuid.uuid4())), alias_text=sql_literal(alias), source_file=sql_literal(FAKE_SOURCE_MARKER))
            )

        if row_has_property_hint(row) and row.get("parsed_role") != "business_lead":
            counts["contact_property_hints"] += 1
            relationship_type = allowed_value(
                row.get("parsed_role"),
                {"owner", "broker", "agent", "tenant", "buyer", "seller", "landlord", "reference", "existing_customer", "business_lead", "unknown", "other"},
                "unknown",
            )
            statements.append(
                """
INSERT INTO contact_property_hints (
  id, contact_import_row_id, building_code, building_name, wing, unit_number,
  relationship_type, confidence, raw_hint, needs_review
) VALUES (
  {id}, {contact_import_row_id}, {building_code}, {building_name}, {wing}, {unit_number},
  {relationship_type}, {confidence}, {raw_hint}, true
);
""".format(
                    id=sql_literal(str(uuid.uuid4())),
                    contact_import_row_id=sql_literal(import_row_id),
                    building_code=sql_literal(row.get("parsed_building_code")),
                    building_name=sql_literal(row.get("parsed_building_name")),
                    wing=sql_literal(row.get("parsed_wing")),
                    unit_number=sql_literal(row.get("parsed_unit_number")),
                    relationship_type=sql_literal(relationship_type),
                    confidence=sql_numeric(row.get("parse_confidence", "")),
                    raw_hint=sql_literal(row.get("raw_hint")),
                )
            )

        if is_lead_requirement(row):
            counts["lead_requirements"] += 1
            requirement = json_value(row.get("requirement_json", ""), {})
            purpose = allowed_value(requirement.get("purpose") or requirement.get("listing_purpose"), {"buy", "rent", "sell", "lease_out", "unknown", "other"}, "unknown")
            statements.append(
                """
INSERT INTO lead_requirements (
  id, contact_import_row_id, source_file_id, source, source_format, campaign_name,
  platform, lead_status, purpose, property_type, locality, city, requirement_text,
  raw_payload, needs_review
) VALUES (
  {id}, {contact_import_row_id}, {source_file_id}, {source}, {source_format}, {campaign_name},
  {platform}, {lead_status}, {purpose}, {property_type}, {locality}, {city}, {requirement_text},
  {raw_payload}, true
);
""".format(
                    id=sql_literal(str(uuid.uuid4())),
                    contact_import_row_id=sql_literal(import_row_id),
                    source_file_id=sql_literal(source_id),
                    source=sql_literal(row.get("source_label") or FAKE_SOURCE_MARKER),
                    source_format=sql_literal(row.get("source_format")),
                    campaign_name=sql_literal(row.get("campaign_name")),
                    platform=sql_literal(row.get("source_category") or row.get("source_label")),
                    lead_status=sql_literal(row.get("lead_status")),
                    purpose=sql_literal(purpose),
                    property_type=sql_literal(requirement.get("property_type")),
                    locality=sql_literal(requirement.get("locality")),
                    city=sql_literal(requirement.get("city")),
                    requirement_text=sql_literal(row.get("raw_notes")),
                    raw_payload=json_sql({"fake_phase": BATCH_LABEL, "requirement": requirement}),
                )
            )

        if is_inventory_row(row):
            counts["inventory_import_rows"] += 1
            inventory_hint = json_value(row.get("inventory_hint_json", ""), {})
            listing_purpose = allowed_value(inventory_hint.get("listing_purpose"), {"rent", "sale", "both", "unknown", "other"}, "unknown")
            statements.append(
                """
INSERT INTO inventory_import_rows (
  id, import_batch_id, source_file_id, source_file, source_sheet, source_row_number,
  source_format, building_name, building_code, wing, unit_number, typology, bhk,
  availability_status, listing_purpose, owner_contact_import_row_id, raw_payload, needs_review
) VALUES (
  {id}, {batch_id}, {source_file_id}, {source_file}, {source_sheet}, {source_row_number},
  {source_format}, {building_name}, {building_code}, {wing}, {unit_number}, {typology}, {bhk},
  {availability_status}, {listing_purpose}, {owner_contact_import_row_id}, {raw_payload}, true
);
""".format(
                    id=sql_literal(str(uuid.uuid4())),
                    batch_id=sql_literal(batch_id),
                    source_file_id=sql_literal(source_id),
                    source_file=sql_literal(FAKE_SOURCE_MARKER),
                    source_sheet=sql_literal(row.get("source_sheet") or None),
                    source_row_number=row.get("source_row_number") or "NULL",
                    source_format=sql_literal(row.get("source_format")),
                    building_name=sql_literal(row.get("parsed_building_name") or inventory_hint.get("building_name")),
                    building_code=sql_literal(row.get("parsed_building_code") or inventory_hint.get("building_code")),
                    wing=sql_literal(row.get("parsed_wing") or inventory_hint.get("wing")),
                    unit_number=sql_literal(row.get("parsed_unit_number") or inventory_hint.get("unit_number")),
                    typology=sql_literal(inventory_hint.get("typology")),
                    bhk=sql_literal(inventory_hint.get("bhk")),
                    availability_status=sql_literal(inventory_hint.get("availability_status")),
                    listing_purpose=sql_literal(listing_purpose),
                    owner_contact_import_row_id=sql_literal(import_row_id),
                    raw_payload=json_sql({"fake_phase": BATCH_LABEL, "inventory_hint": inventory_hint}),
                )
            )

        for review_type in review_types(row):
            counts["import_review_items"] += 1
            statements.append(
                """
INSERT INTO import_review_items (
  id, import_batch_id, source_file_id, contact_import_row_id, review_type,
  priority, status, title, summary, recommended_action, raw_context
) VALUES (
  {id}, {batch_id}, {source_file_id}, {contact_import_row_id}, {review_type},
  'normal', 'pending', {title}, {summary}, {recommended_action}, {raw_context}
);
""".format(
                    id=sql_literal(str(uuid.uuid4())),
                    batch_id=sql_literal(batch_id),
                    source_file_id=sql_literal(source_id),
                    contact_import_row_id=sql_literal(import_row_id),
                    review_type=sql_literal(review_type),
                    title=sql_literal(f"Fake review: {review_type}"),
                    summary=sql_literal("Fake Phase 3.4 review queue item."),
                    recommended_action=sql_literal("Review in NocoDB; do not merge automatically."),
                    raw_context=json_sql({"fake_phase": BATCH_LABEL, "source_format": row.get("source_format")}),
                )
            )

    duplicate_summary_data = duplicate_summary(rows)
    for candidate in duplicate_summary_data.get("candidates", []):
        row_a = str(candidate.get("row_a", ""))
        row_b = str(candidate.get("row_b", ""))
        left_index = next((index for index, row in enumerate(rows) if str(row.get("source_row_number", "")) == row_a), None)
        right_index = next((index for index, row in enumerate(rows) if str(row.get("source_row_number", "")) == row_b and index != left_index), None)
        if left_index is None or right_index is None:
            continue
        duplicate_id = str(uuid.uuid4())
        counts["contact_duplicate_candidates"] += 1
        counts["import_review_items"] += 1
        statements.append(
            """
INSERT INTO contact_duplicate_candidates (
  id, import_batch_id, candidate_type, duplicate_strength,
  contact_import_row_id_1, contact_import_row_id_2, reason, status
) VALUES (
  {id}, {batch_id}, 'fake_source_aware_import', {duplicate_strength},
  {left_id}, {right_id}, {reason}, 'pending_review'
);
""".format(
                id=sql_literal(duplicate_id),
                batch_id=sql_literal(batch_id),
                duplicate_strength=sql_literal(candidate.get("duplicate_strength")),
                left_id=sql_literal(row_ids[left_index]),
                right_id=sql_literal(row_ids[right_index]),
                reason=sql_literal(candidate.get("reason")),
            )
        )
        statements.append(
            """
INSERT INTO import_review_items (
  id, import_batch_id, duplicate_candidate_id, review_type, priority, status,
  title, summary, recommended_action, raw_context
) VALUES (
  {id}, {batch_id}, {duplicate_candidate_id}, 'duplicate_contact', 'normal', 'pending',
  'Fake duplicate review', 'Fake Phase 3.4 duplicate candidate.', 'Review before any merge.',
  {raw_context}
);
""".format(
                id=sql_literal(str(uuid.uuid4())),
                batch_id=sql_literal(batch_id),
                duplicate_candidate_id=sql_literal(duplicate_id),
                raw_context=json_sql({"fake_phase": BATCH_LABEL, "duplicate_strength": candidate.get("duplicate_strength")}),
            )
        )

    statements.append("COMMIT;")
    return "\n".join(statements), counts


def print_counts(prefix: str, counts: Dict[str, int]) -> None:
    print(prefix)
    for key in [
        "import_batches",
        "source_files",
        "contact_import_rows",
        "contact_methods",
        "contact_aliases",
        "contact_property_hints",
        "lead_requirements",
        "inventory_import_rows",
        "contact_duplicate_candidates",
        "import_review_items",
    ]:
        print(f"{key}: {counts.get(key, 0)}")


def main() -> int:
    global BATCH_LABEL
    parser = argparse.ArgumentParser(description="Apply fake Phase 3.4 source-aware import rows. Fake data only.")
    parser.add_argument("cleaned_csv", help="Cleaned CSV generated from fake .example data.")
    parser.add_argument("--apply", action="store_true", help="Write fake rows to Postgres.")
    parser.add_argument("--fake-ok", action="store_true", help="Confirm this is fake .example data only.")
    parser.add_argument("--batch-label", default=BATCH_LABEL, help="Required fake batch label.")
    args = parser.parse_args()

    cleaned_csv = Path(args.cleaned_csv)
    if not cleaned_csv.exists():
        print("Cleaned CSV was not found.")
        return 1
    if not args.batch_label.startswith("FAKE_"):
        print("Refusing to run: fake batch label must start with FAKE_.")
        return 1
    BATCH_LABEL = args.batch_label
    if not read_env_value("POSTGRES_USER") or not read_env_value("POSTGRES_PASSWORD") or not read_env_value("POSTGRES_DB"):
        print("Refusing to run: docker/.env cannot be read safely.")
        return 1

    rows = read_rows(cleaned_csv)
    errors = validate_fake_input(cleaned_csv, rows)
    if errors:
        print("Refusing to run:")
        for error in errors:
            print(f"- {error}")
        return 1

    plan = summarize_rows([cleaned_csv])
    sql, counts = build_sql(cleaned_csv, rows)
    if not args.apply or not args.fake_ok:
        print("Dry run only. No database rows were inserted.")
        print("Writing fake rows requires both --apply and --fake-ok.")
        print_counts("Planned fake source-aware rows:", counts)
        print(f"Planner source_files: {plan['planned_counts']['source_files']}")
        return 0

    result = psql(sql)
    if result != 0:
        print("Fake apply failed.")
        return result
    print("Fake apply completed. No canonical contacts were created.")
    print_counts("Applied fake source-aware rows:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
