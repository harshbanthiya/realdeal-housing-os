#!/usr/bin/env python3
"""Dry-run contact import planning for Real Deal Housing OS."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


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


def normalize_name(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    return " ".join(value.split())


def duplicate_candidate_count(rows: List[Dict[str, str]]) -> int:
    seen_pairs = set()
    by_phone: Dict[str, List[int]] = defaultdict(list)
    by_email: Dict[str, List[int]] = defaultdict(list)
    by_hint: Dict[Tuple[str, str, str, str], List[int]] = defaultdict(list)

    for index, row in enumerate(rows):
        if row.get("phone_normalized"):
            by_phone[row["phone_normalized"]].append(index)
        if row.get("email_normalized"):
            by_email[row["email_normalized"]].append(index)
        name = normalize_name(row.get("cleaned_display_name", ""))
        building_code = row.get("parsed_building_code") or ""
        building_name = row.get("parsed_building_name") or ""
        unit = row.get("parsed_unit_number") or ""
        if name and (building_code or building_name) and unit:
            by_hint[(name, building_code, building_name, unit)].append(index)

    for groups in (by_phone, by_email, by_hint):
        for indexes in groups.values():
            if len(indexes) < 2:
                continue
            for left_pos, left in enumerate(indexes):
                for right in indexes[left_pos + 1 :]:
                    seen_pairs.add(tuple(sorted((left, right))))

    return len(seen_pairs)


def dry_run(cleaned_csv: Path) -> int:
    postgres_user = read_env_value("POSTGRES_USER")
    postgres_password = read_env_value("POSTGRES_PASSWORD")
    postgres_db = read_env_value("POSTGRES_DB")

    if not postgres_user or not postgres_password or not postgres_db:
        print("Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env.")
        return 1

    rows = read_rows(cleaned_csv)
    rows_with_mobile = sum(1 for row in rows if row.get("phone_type") == "mobile")
    rows_with_landline = sum(1 for row in rows if row.get("phone_type") == "landline")
    rows_with_email = sum(1 for row in rows if row.get("email_normalized"))
    rows_with_hints = sum(1 for row in rows if row.get("parsed_building_code") or row.get("parsed_building_name") or row.get("parsed_unit_number"))
    rows_needing_review = sum(1 for row in rows if str(row.get("needs_review", "")).lower() == "true")
    duplicate_candidates = duplicate_candidate_count(rows)
    alias_rows = sum(1 for row in rows if row.get("raw_name"))
    property_hint_rows = sum(1 for row in rows if row.get("parsed_building_code") or row.get("parsed_building_name") or row.get("parsed_unit_number") or row.get("parsed_role"))

    print("Dry run only. No database rows were inserted.")
    print(f"Target database: {postgres_db}")
    print(f"Rows read: {len(rows)}")
    print(f"Rows with mobile phones: {rows_with_mobile}")
    print(f"Rows with likely landlines: {rows_with_landline}")
    print(f"Rows with normalized emails: {rows_with_email}")
    print(f"Rows with parsed building/property hints: {rows_with_hints}")
    print(f"Rows needing review: {rows_needing_review}")
    print(f"Duplicate candidates: {duplicate_candidates}")
    print("Would create 1 import_batches row.")
    print(f"Would insert {len(rows)} contact_import_rows rows.")
    print(f"Would prepare up to {len(rows)} contacts rows for review/import.")
    print(f"Would insert {alias_rows} contact_aliases rows.")
    print(f"Would insert {property_hint_rows} contact_property_hints rows.")
    print(f"Would insert {duplicate_candidates} contact_duplicate_candidates rows.")
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
