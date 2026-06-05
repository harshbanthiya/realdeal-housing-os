#!/usr/bin/env python3
"""Safely profile contact source files without printing private values."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


def normalize_column(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def has_all(columns: Sequence[str], expected: Sequence[str]) -> bool:
    normalized = {normalize_column(column) for column in columns}
    return all(normalize_column(item) in normalized for item in expected)


def has_any_prefix(columns: Sequence[str], prefix: str) -> bool:
    prefix = normalize_column(prefix)
    return any(normalize_column(column).startswith(prefix) for column in columns)


def guess_source_format(columns: Sequence[str]) -> str:
    if has_all(columns, ["Title", "Rating", "Reviews", "Phone", "Website", "Google Maps Link"]):
        return "google_maps_business_csv"
    if has_all(columns, ["Wing", "Flat No."]) and has_any_prefix(columns, "Contact Person") and has_any_prefix(columns, "Telephone"):
        return "structured_owner_sheet"
    if has_all(columns, ["Name", "Phone", "Flat No.", "N", "Telephone 1"]):
        return "messy_phonebook_property_csv"
    if has_all(columns, ["Name", "Phone Number"]):
        return "simple_phonebook_csv"
    return "unknown_contact_csv"


def profile_csv(path: Path) -> Dict[str, object]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        row_count = sum(1 for _ in reader)
    return {
        "file_type": "csv",
        "sheets": [],
        "row_counts": {"csv": row_count},
        "columns": {"csv": columns},
        "source_format": guess_source_format(columns),
    }


def profile_xlsx(path: Path) -> Dict[str, object]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise SystemExit("XLSX profiling needs openpyxl. Export workbook sheets to CSV or install openpyxl.")

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    row_counts: Dict[str, int] = {}
    columns_by_sheet: Dict[str, List[str]] = {}
    formats: List[str] = []
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        columns = [str(value).strip() for value in header if value is not None] if header else []
        count = sum(1 for row in rows if any(cell is not None and str(cell).strip() for cell in row))
        row_counts[sheet.title] = count
        columns_by_sheet[sheet.title] = columns
        formats.append(guess_source_format(columns))
    workbook.close()

    guessed = "structured_owner_workbook" if any(item == "structured_owner_sheet" for item in formats) else (formats[0] if formats else "unknown_contact_csv")
    return {
        "file_type": "xlsx",
        "sheets": list(row_counts),
        "row_counts": row_counts,
        "columns": columns_by_sheet,
        "source_format": guessed,
    }


def profile_file(path: Path) -> Dict[str, object]:
    suffix = path.suffix.lower()
    if suffix == ".csv" or path.name.endswith(".csv.example"):
        return profile_csv(path)
    if suffix == ".xlsx":
        return profile_xlsx(path)
    raise SystemExit("Unsupported file type. Use CSV or XLSX.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile contact source file shape without printing private values.")
    parser.add_argument("source_file", help="CSV or XLSX file to profile.")
    args = parser.parse_args()

    path = Path(args.source_file)
    if not path.exists():
        print("Source file was not found.")
        return 1

    profile = profile_file(path)
    print(f"Source file: {path.name}")
    print(f"Detected file type: {profile['file_type']}")
    if profile["sheets"]:
        print(f"Sheets: {', '.join(profile['sheets'])}")
    for sheet, count in profile["row_counts"].items():
        print(f"Rows in {sheet}: {count}")
        print(f"Columns in {sheet}: {', '.join(profile['columns'][sheet])}")
    print(f"Guessed source_format: {profile['source_format']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
