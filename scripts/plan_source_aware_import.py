#!/usr/bin/env python3
"""Build a source-aware dry-run import plan without writing to Postgres."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from duplicate_utils import duplicate_summary, parse_json_list


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "contacts"
LEAD_FORMATS = {
    "google_maps_business_csv",
    "portal_property_leads_csv",
    "meta_facebook_leads_utf16_tsv",
}
INVENTORY_FORMATS = {
    "property_inventory_csv",
    "property_inventory_workbook",
    "imperial_unit_inventory_workbook",
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def cleaned_files(path: Path) -> List[Path]:
    if path.is_dir():
        return sorted(path.glob("cleaned_contacts_*.csv"))
    return [path]


def row_has_contact_value(row: Dict[str, str]) -> bool:
    return bool(row.get("cleaned_display_name") or row.get("phone_normalized") or row.get("email_normalized"))


def row_has_property_hint(row: Dict[str, str]) -> bool:
    return bool(
        row.get("parsed_building_code")
        or row.get("parsed_building_name")
        or row.get("parsed_unit_number")
        or row.get("inventory_hint_json")
    )


def contact_method_count(row: Dict[str, str]) -> int:
    phones = set(parse_json_list(row.get("phones_normalized_json", "")))
    emails = set(parse_json_list(row.get("emails_normalized_json", "")))
    if row.get("phone_normalized"):
        phones.add(row["phone_normalized"])
    if row.get("email_normalized"):
        emails.add(row["email_normalized"])
    count = len(phones) + len(emails)
    if row.get("website"):
        count += 1
    if row.get("google_maps_link"):
        count += 1
    return count


def is_lead_requirement(row: Dict[str, str]) -> bool:
    source_format = row.get("source_format", "")
    return bool(source_format in LEAD_FORMATS or row.get("requirement_json"))


def is_inventory_row(row: Dict[str, str]) -> bool:
    source_format = row.get("source_format", "")
    return bool(source_format in INVENTORY_FORMATS or row.get("inventory_hint_json"))


def review_item_count(row: Dict[str, str]) -> int:
    count = 0
    if str(row.get("needs_review", "")).lower() == "true":
        count += 1
    if not row.get("cleaned_display_name"):
        count += 1
    if row.get("rejection_reason"):
        count += 1
    if row_has_property_hint(row):
        count += 1
    if is_lead_requirement(row):
        count += 1
    if is_inventory_row(row):
        count += 1
    if row.get("source_format") in {"unknown_contact_csv", "unknown"}:
        count += 1
    return count


def summarize_rows(files: Iterable[Path]) -> Dict[str, object]:
    all_rows: List[Dict[str, str]] = []
    file_count = 0
    for file_path in files:
        file_count += 1
        all_rows.extend(read_rows(file_path))

    source_keys = {
        (
            row.get("source_file", ""),
            row.get("source_sheet", ""),
            row.get("source_format", ""),
        )
        for row in all_rows
        if row.get("source_file") or row.get("source_sheet") or row.get("source_format")
    }
    dupes = duplicate_summary(all_rows)
    duplicate_candidate_count = (
        int(dupes["duplicate_pairs_strong"])
        + int(dupes["duplicate_pairs_medium"])
        + int(dupes["duplicate_pairs_weak"])
    )
    source_formats = Counter(row.get("source_format", "unknown") or "unknown" for row in all_rows)
    contact_rows = sum(1 for row in all_rows if row_has_contact_value(row))
    property_hint_rows = sum(1 for row in all_rows if row_has_property_hint(row))
    lead_rows = sum(1 for row in all_rows if is_lead_requirement(row))
    inventory_rows = sum(1 for row in all_rows if is_inventory_row(row))
    review_rows = sum(review_item_count(row) for row in all_rows) + duplicate_candidate_count

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run_only": True,
        "input_cleaned_file_count": file_count,
        "source_format_counts": dict(source_formats),
        "planned_counts": {
            "import_batches": 1 if all_rows else 0,
            "source_files": len(source_keys),
            "contact_import_rows": len(all_rows),
            "contacts_for_review": contact_rows,
            "contact_methods": sum(contact_method_count(row) for row in all_rows),
            "contact_aliases": sum(1 for row in all_rows if row.get("raw_name") or row.get("aliases_json")),
            "contact_property_hints": property_hint_rows,
            "lead_requirements": lead_rows,
            "inventory_import_rows": inventory_rows,
            "contact_duplicate_candidates": duplicate_candidate_count,
            "import_review_items": review_rows,
        },
        "duplicate_counts": {
            "strong_pairs": dupes["duplicate_pairs_strong"],
            "medium_pairs": dupes["duplicate_pairs_medium"],
            "weak_pairs": dupes["duplicate_pairs_weak"],
            "strong_groups": dupes["duplicate_groups_strong"],
            "medium_groups": dupes["duplicate_groups_medium"],
            "weak_groups": dupes["duplicate_groups_weak"],
        },
        "privacy_note": "This plan contains aggregate counts only. It intentionally omits full phone numbers and emails.",
    }


def write_plan(plan: Dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"source_aware_import_plan_{timestamp}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(plan, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a source-aware import plan. No database writes.")
    parser.add_argument("path", help="Cleaned CSV or folder containing cleaned_contacts_*.csv files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for the JSON plan.")
    args = parser.parse_args()

    input_path = Path(args.path)
    if not input_path.exists():
        print("Input path not found.")
        return 1

    files = cleaned_files(input_path)
    if not files:
        print("No cleaned contact CSV files found.")
        return 1

    plan = summarize_rows(files)
    output_path = write_plan(plan, Path(args.output_dir))
    counts = plan["planned_counts"]

    print("Dry run only. No database rows were inserted.")
    print(f"Cleaned files read: {plan['input_cleaned_file_count']}")
    print(f"Rows read: {counts['contact_import_rows']}")
    print(f"Would plan source_files: {counts['source_files']}")
    print(f"Would plan contact_methods: {counts['contact_methods']}")
    print(f"Would plan lead_requirements: {counts['lead_requirements']}")
    print(f"Would plan inventory_import_rows: {counts['inventory_import_rows']}")
    print(f"Would plan import_review_items: {counts['import_review_items']}")
    print(f"Plan written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
