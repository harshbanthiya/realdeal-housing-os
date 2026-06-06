#!/usr/bin/env python3
"""Dry-run contact import planning for Real Deal Housing OS."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from duplicate_utils import duplicate_summary, parse_json_list


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


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


def dry_run(cleaned_csv: Path) -> int:
    postgres_user = read_env_value("POSTGRES_USER")
    postgres_password = read_env_value("POSTGRES_PASSWORD")
    postgres_db = read_env_value("POSTGRES_DB")
    if not postgres_user or not postgres_password or not postgres_db:
        print("Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env.")
        return 1

    rows = read_rows(cleaned_csv)
    dupes = duplicate_summary(rows)
    duplicate_candidate_count = int(dupes["duplicate_pairs_strong"]) + int(dupes["duplicate_pairs_medium"]) + int(dupes["duplicate_pairs_weak"])
    rows_with_mobile = sum(1 for row in rows if row.get("phone_type") == "mobile")
    rows_with_landline = sum(1 for row in rows if row.get("phone_type") == "landline")
    rows_with_email = sum(1 for row in rows if row.get("email_normalized"))
    rows_with_hints = sum(1 for row in rows if row.get("parsed_building_code") or row.get("parsed_building_name") or row.get("parsed_unit_number"))
    rows_needing_review = sum(1 for row in rows if str(row.get("needs_review", "")).lower() == "true")
    alias_rows = sum(1 for row in rows if row.get("raw_name") or row.get("aliases_json"))
    property_hint_rows = sum(
        1
        for row in rows
        if (row.get("parsed_building_code") or row.get("parsed_building_name") or row.get("parsed_unit_number") or row.get("inventory_hint_json"))
        and row.get("parsed_role") != "business_lead"
    )
    multi_phone_rows = sum(1 for row in rows if len(parse_json_list(row.get("phones_normalized_json", ""))) > 1)
    multi_email_rows = sum(1 for row in rows if len(parse_json_list(row.get("emails_normalized_json", ""))) > 1)

    print("Dry run only. No database rows were inserted.")
    print(f"Target database: {postgres_db}")
    print(f"Rows read: {len(rows)}")
    print(f"Rows with mobile phones: {rows_with_mobile}")
    print(f"Rows with likely landlines: {rows_with_landline}")
    print(f"Rows with normalized emails: {rows_with_email}")
    print(f"Rows with multiple phones: {multi_phone_rows}")
    print(f"Rows with multiple emails: {multi_email_rows}")
    print(f"Rows with parsed building/property hints: {rows_with_hints}")
    print(f"Rows needing review: {rows_needing_review}")
    print(f"Duplicate groups strong: {dupes['duplicate_groups_strong']}")
    print(f"Duplicate groups medium: {dupes['duplicate_groups_medium']}")
    print(f"Duplicate groups weak: {dupes['duplicate_groups_weak']}")
    print(f"Duplicate pairs strong: {dupes['duplicate_pairs_strong']}")
    print(f"Duplicate pairs medium: {dupes['duplicate_pairs_medium']}")
    print(f"Duplicate pairs weak: {dupes['duplicate_pairs_weak']}")
    print("Would create 1 import_batches row.")
    print(f"Would insert {len(rows)} contact_import_rows rows.")
    print(f"Would prepare up to {len(rows)} contacts rows for review/import.")
    print(f"Would insert {alias_rows} contact_aliases rows.")
    print(f"Would insert {property_hint_rows} contact_property_hints rows.")
    print(f"Would insert {duplicate_candidate_count} contact_duplicate_candidates rows.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan contact import into Postgres. Dry-run by default.")
    parser.add_argument("cleaned_csv", help="Cleaned CSV path.")
    parser.add_argument("--apply", action="store_true", help="Apply import to database. Not implemented in this MVP.")
    args = parser.parse_args()
    cleaned_csv = Path(args.cleaned_csv)
    if not cleaned_csv.exists():
        print("Cleaned CSV was not found.")
        return 1
    if args.apply:
        print("Apply mode not implemented yet. Dry-run first, review duplicates, then implement inserts with explicit approval.")
        return 1
    return dry_run(cleaned_csv)


if __name__ == "__main__":
    raise SystemExit(main())
