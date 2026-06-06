#!/usr/bin/env python3
"""Print safe aggregate summaries for cleaned contact CSVs."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from duplicate_utils import duplicate_summary, parse_json_list


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def cleaned_files(path: Path) -> List[Path]:
    if path.is_dir():
        return sorted(path.glob("cleaned_contacts_*.csv"))
    return [path]


def summarize_file(path: Path) -> Dict[str, object]:
    rows = read_rows(path)
    duplicates = duplicate_summary(rows)
    source_formats = Counter(row.get("source_format", "unknown") or "unknown" for row in rows)
    summary = {
        "file": str(path),
        "rows": len(rows),
        "valid_rows": len(rows),
        "rejected_rows": 0,
        "rows_by_source_format": dict(source_formats),
        "phone_count": sum(1 for row in rows if row.get("phone_normalized")),
        "email_count": sum(1 for row in rows if row.get("email_normalized")),
        "multiple_phone_rows": sum(1 for row in rows if len(parse_json_list(row.get("phones_normalized_json", ""))) > 1),
        "multiple_email_rows": sum(1 for row in rows if len(parse_json_list(row.get("emails_normalized_json", ""))) > 1),
        "building_hints_count": sum(1 for row in rows if row.get("parsed_building_code") or row.get("parsed_building_name")),
        "unit_hints_count": sum(1 for row in rows if row.get("parsed_unit_number")),
        "role_relationship_count": sum(1 for row in rows if row.get("parsed_role")),
        "business_lead_count": sum(1 for row in rows if row.get("parsed_role") == "business_lead" or row.get("source_format") == "google_maps_business_csv"),
        "portal_lead_count": sum(1 for row in rows if row.get("source_format") == "portal_property_leads_csv"),
        "inventory_hint_count": sum(1 for row in rows if row.get("inventory_hint_json")),
        "duplicate_counts": {
            "groups_strong": duplicates["duplicate_groups_strong"],
            "groups_medium": duplicates["duplicate_groups_medium"],
            "groups_weak": duplicates["duplicate_groups_weak"],
            "pairs_strong": duplicates["duplicate_pairs_strong"],
            "pairs_medium": duplicates["duplicate_pairs_medium"],
            "pairs_weak": duplicates["duplicate_pairs_weak"],
        },
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize cleaned contact CSVs without printing raw values.")
    parser.add_argument("path", help="Cleaned CSV or folder containing cleaned_contacts_*.csv.")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.exists():
        print("Path not found.")
        return 1
    for file_path in cleaned_files(path):
        summary = summarize_file(file_path)
        print(f"File: {file_path}")
        print(f"Rows: {summary['rows']}")
        print(f"Rows by source_format: {summary['rows_by_source_format']}")
        print(f"Phone count: {summary['phone_count']}")
        print(f"Email count: {summary['email_count']}")
        print(f"Multiple-phone rows: {summary['multiple_phone_rows']}")
        print(f"Multiple-email rows: {summary['multiple_email_rows']}")
        print(f"Building hints: {summary['building_hints_count']}")
        print(f"Unit hints: {summary['unit_hints_count']}")
        print(f"Role/relationship count: {summary['role_relationship_count']}")
        print(f"Business lead count: {summary['business_lead_count']}")
        print(f"Portal lead count: {summary['portal_lead_count']}")
        print(f"Inventory hint count: {summary['inventory_hint_count']}")
        print(f"Duplicate counts: {summary['duplicate_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
