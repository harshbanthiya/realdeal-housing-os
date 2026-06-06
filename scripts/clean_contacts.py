#!/usr/bin/env python3
"""Clean normalized contact rows into reviewable contact import outputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from parse_phonebook_name import load_building_codes, parse_phonebook_name
from source_format_utils import safe_stem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CLEANED_FIELDS = [
    "source_file",
    "source_sheet",
    "source_row_number",
    "source_format",
    "raw_name",
    "cleaned_display_name",
    "raw_phone",
    "phone_normalized",
    "phone_type",
    "phones_normalized_json",
    "raw_email",
    "email_normalized",
    "emails_normalized_json",
    "parsed_building_code",
    "parsed_building_name",
    "parsed_wing",
    "parsed_unit_number",
    "parsed_role",
    "parsed_tags",
    "parse_confidence",
    "raw_hint",
    "needs_review",
    "raw_notes",
    "raw_payload_json",
    "raw_phones_json",
    "raw_emails_json",
    "aliases_json",
    "organization",
    "job_title",
    "source_category",
    "campaign_name",
    "lead_status",
    "requirement_json",
    "inventory_hint_json",
    "source_label",
    "website",
    "google_maps_link",
]

REJECTED_FIELDS = CLEANED_FIELDS + ["rejection_reason"]
PLACEHOLDER_VALUES = {"", "n/a", "na", "none", "null", "-", "--", "0"}


def parse_json_list(value: str) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [part for part in str(value).split("|") if part]


def normalize_phone(value: str) -> Tuple[str, str, str]:
    raw = (value or "").strip()
    if raw.lower() in PLACEHOLDER_VALUES:
        return "", "", "" if not raw else "placeholder_phone"
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return "", "", "invalid_phone"
    if len(set(digits)) == 1:
        return "", "", "placeholder_phone"
    if len(digits) == 12 and digits.startswith("91"):
        candidate = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        candidate = digits[1:]
    else:
        candidate = digits
    if len(candidate) == 10 and candidate[0] in "6789":
        return f"+91{candidate}", "mobile", ""
    if len(candidate) in {8, 9, 10, 11}:
        return f"+91{candidate}", "landline", ""
    return "", "", "invalid_phone"


def normalize_email(value: str) -> Tuple[str, str]:
    email = (value or "").strip().lower()
    if not email:
        return "", ""
    if EMAIL_PATTERN.match(email):
        return email, ""
    return "", "invalid_email"


def unique(values: Iterable[str]) -> List[str]:
    output = []
    seen = set()
    for value in values:
        value = str(value or "").strip()
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output


def row_get(row: Dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def compact_reason(parts: Iterable[str]) -> str:
    return "; ".join(part for part in parts if part)


def choose_hint(parsed_value: str, hint_value: str) -> str:
    return (hint_value or "").strip() or (parsed_value or "").strip()


def building_name_from_code(code: str, building_codes: Dict[str, Dict[str, str]]) -> str:
    if not code:
        return ""
    return (building_codes.get(code.upper(), {}).get("building_name") or "").strip()


def split_tags(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item for item in str(value or "").split("|") if item]


def normalized_phone_bundle(row: Dict[str, str]) -> Tuple[List[str], str, str, List[str]]:
    raw_values = unique([row_get(row, "raw_phone")] + parse_json_list(row_get(row, "raw_phones_json")))
    normalized = []
    phone_types = []
    errors = []
    for value in raw_values:
        phone, phone_type, error = normalize_phone(value)
        if phone:
            normalized.append(phone)
            phone_types.append(phone_type)
        elif error:
            errors.append(error)
    normalized = unique(normalized)
    primary = normalized[0] if normalized else ""
    primary_type = "mobile" if any(item == "mobile" for item in phone_types) and primary else (phone_types[0] if phone_types else "")
    return normalized, primary, primary_type, errors


def normalized_email_bundle(row: Dict[str, str]) -> Tuple[List[str], str, List[str]]:
    raw_values = unique([row_get(row, "raw_email")] + parse_json_list(row_get(row, "raw_emails_json")))
    normalized = []
    errors = []
    for value in raw_values:
        email, error = normalize_email(value)
        if email:
            normalized.append(email)
        elif error:
            errors.append(error)
    normalized = unique(normalized)
    return normalized, normalized[0] if normalized else "", errors


def write_csv(path: Path, fields: List[str], rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            serializable = dict(row)
            if isinstance(serializable.get("parsed_tags"), list):
                serializable["parsed_tags"] = "|".join(serializable["parsed_tags"])
            writer.writerow(serializable)


def clean_contacts(input_path: Path, output_dir: Path) -> Dict[str, object]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    building_codes = load_building_codes(PROJECT_ROOT)
    cleaned_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []
    rejection_counts: Dict[str, int] = {}

    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_name = row_get(row, "raw_name")
            phone_values, phone_primary, phone_type, phone_errors = normalized_phone_bundle(row)
            email_values, email_primary, email_errors = normalized_email_bundle(row)
            parsed = parse_phonebook_name(raw_name, building_codes)

            building_code = choose_hint(str(parsed["parsed_building_code"]), row_get(row, "building_code_hint")).upper()
            building_name = choose_hint(str(parsed["parsed_building_name"]), row_get(row, "building_name_hint"))
            if not building_name:
                building_name = building_name_from_code(building_code, building_codes)
            wing = choose_hint(str(parsed["parsed_wing"]), row_get(row, "wing_hint")).upper()
            unit_number = choose_hint(str(parsed["parsed_unit_number"]), row_get(row, "unit_number_hint"))
            role = choose_hint(str(parsed["parsed_role"]), row_get(row, "relationship_hint"))
            display_name = str(parsed["cleaned_display_name"]) or raw_name or row_get(row, "organization")

            tags = split_tags(parsed["parsed_tags"])
            for key, value in {
                "source_format": row_get(row, "source_format"),
                "source_label": row_get(row, "source_label"),
                "source_category": row_get(row, "source_category"),
                "building_code": building_code,
                "building_name": building_name,
                "organization": row_get(row, "organization"),
                "website": row_get(row, "website"),
            }.items():
                if value:
                    tags.append(f"{key}:{value}")

            hint_parts = [str(parsed["raw_hint"])]
            for value in [building_code, building_name, wing, unit_number, role]:
                if value and value not in hint_parts:
                    hint_parts.append(value)

            reasons: List[str] = []
            if not raw_name and not row_get(row, "organization") and not row_get(row, "website"):
                reasons.append("missing_name")
            if not phone_primary and not email_primary and not row_get(row, "website"):
                reasons.append("missing_valid_phone_or_email")
            if phone_errors and not phone_primary:
                reasons.append(phone_errors[0])
            if email_errors and not email_primary:
                reasons.append(email_errors[0])

            source_format = row_get(row, "source_format")
            structured_hint = bool(wing or unit_number or building_name or building_code)
            needs_review = bool(parsed["needs_review"]) or not display_name or bool(reasons)
            if structured_hint and source_format in {"structured_owner_workbook", "messy_phonebook_property_csv", "property_inventory_csv", "property_inventory_workbook"}:
                needs_review = bool(reasons)

            output_row: Dict[str, object] = {
                "source_file": row_get(row, "source_file"),
                "source_sheet": row_get(row, "source_sheet"),
                "source_row_number": row_get(row, "source_row_number"),
                "source_format": source_format,
                "raw_name": raw_name,
                "cleaned_display_name": display_name,
                "raw_phone": row_get(row, "raw_phone"),
                "phone_normalized": phone_primary,
                "phone_type": phone_type,
                "phones_normalized_json": json.dumps(phone_values, ensure_ascii=True),
                "raw_email": row_get(row, "raw_email"),
                "email_normalized": email_primary,
                "emails_normalized_json": json.dumps(email_values, ensure_ascii=True),
                "parsed_building_code": building_code,
                "parsed_building_name": building_name,
                "parsed_wing": wing,
                "parsed_unit_number": unit_number,
                "parsed_role": role,
                "parsed_tags": tags,
                "parse_confidence": parsed["parse_confidence"],
                "raw_hint": " | ".join(item for item in hint_parts if item),
                "needs_review": needs_review,
                "raw_notes": row_get(row, "raw_notes"),
                "raw_payload_json": row_get(row, "raw_payload_json"),
                "raw_phones_json": row_get(row, "raw_phones_json"),
                "raw_emails_json": row_get(row, "raw_emails_json"),
                "aliases_json": row_get(row, "aliases_json"),
                "organization": row_get(row, "organization"),
                "job_title": row_get(row, "job_title"),
                "source_category": row_get(row, "source_category"),
                "campaign_name": row_get(row, "campaign_name"),
                "lead_status": row_get(row, "lead_status"),
                "requirement_json": row_get(row, "requirement_json"),
                "inventory_hint_json": row_get(row, "inventory_hint_json"),
                "source_label": row_get(row, "source_label"),
                "website": row_get(row, "website"),
                "google_maps_link": row_get(row, "google_maps_link"),
            }

            if reasons:
                reason = compact_reason(reasons)
                output_row["rejection_reason"] = reason
                for item in reasons:
                    rejection_counts[item] = rejection_counts.get(item, 0) + 1
                rejected_rows.append(output_row)
            else:
                cleaned_rows.append(output_row)

    cleaned_path = output_dir / f"cleaned_contacts_{safe_stem(input_path)}_{timestamp}.csv"
    rejected_path = output_dir / f"rejected_contacts_{safe_stem(input_path)}_{timestamp}.csv"
    summary_path = output_dir / f"contact_import_summary_{safe_stem(input_path)}_{timestamp}.json"
    write_csv(cleaned_path, CLEANED_FIELDS, cleaned_rows)
    write_csv(rejected_path, REJECTED_FIELDS, rejected_rows)
    summary = {
        "input_file": str(input_path),
        "cleaned_file": str(cleaned_path),
        "rejected_file": str(rejected_path),
        "total_rows": len(cleaned_rows) + len(rejected_rows),
        "cleaned_rows": len(cleaned_rows),
        "rejected_rows": len(rejected_rows),
        "rows_with_mobile_phones": sum(1 for row in cleaned_rows if row.get("phone_type") == "mobile"),
        "rows_with_landlines": sum(1 for row in cleaned_rows if row.get("phone_type") == "landline"),
        "rows_with_email": sum(1 for row in cleaned_rows if row.get("email_normalized")),
        "rows_with_multiple_phones": sum(1 for row in cleaned_rows if len(parse_json_list(str(row.get("phones_normalized_json", "")))) > 1),
        "rows_with_multiple_emails": sum(1 for row in cleaned_rows if len(parse_json_list(str(row.get("emails_normalized_json", "")))) > 1),
        "rows_with_building_hints": sum(1 for row in cleaned_rows if row.get("parsed_building_code") or row.get("parsed_building_name") or row.get("parsed_unit_number")),
        "rows_needing_review": sum(1 for row in cleaned_rows if row.get("needs_review") is True),
        "rejection_counts": rejection_counts,
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    summary["summary_file"] = str(summary_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean normalized contact rows into review outputs.")
    parser.add_argument("normalized_csv", help="Standard intermediate CSV from normalize_contact_file.py.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "exports" / "contacts"), help="Output directory. Defaults to exports/contacts.")
    args = parser.parse_args()
    input_path = Path(args.normalized_csv)
    if not input_path.exists():
        print("Normalized CSV was not found.")
        return 1
    summary = clean_contacts(input_path, Path(args.output_dir))
    print(f"Rows read: {summary['total_rows']}")
    print(f"Cleaned rows written: {summary['cleaned_rows']}")
    print(f"Rejected rows written: {summary['rejected_rows']}")
    print(f"Rows needing review: {summary['rows_needing_review']}")
    print(f"Cleaned output: {summary['cleaned_file']}")
    print(f"Rejected output: {summary['rejected_file']}")
    print(f"Summary output: {summary['summary_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
