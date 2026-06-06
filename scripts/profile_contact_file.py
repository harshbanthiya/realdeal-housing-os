#!/usr/bin/env python3
"""Safely profile contact source files without printing private values."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from source_format_utils import (
    detect_header_row,
    guess_source_format,
    profile_docx,
    profile_pdf,
    profile_text_file,
    profile_vcf,
    read_csv_header_and_count,
)


def profile_csv(path: Path) -> Dict[str, object]:
    columns, row_count, encoding, delimiter = read_csv_header_and_count(path)
    source_format = guess_source_format(columns, file_name=path.name, delimiter=delimiter, encoding=encoding)
    return {
        "file_type": "csv",
        "sheets": [],
        "row_counts": {"csv": row_count},
        "columns": {"csv": columns},
        "source_format": source_format,
        "encoding": encoding,
        "delimiter": "\\t" if delimiter == "\t" else delimiter,
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
        all_rows = list(sheet.iter_rows(values_only=True))
        header_index, columns = detect_header_row(all_rows)
        data_rows = all_rows[header_index + 1 :] if all_rows else []
        count = sum(1 for row in data_rows if any(cell is not None and str(cell).strip() for cell in row))
        row_counts[sheet.title] = count
        columns_by_sheet[sheet.title] = columns
        formats.append(guess_source_format(columns, file_name=path.name, sheet_names=[sheet.title]))
    sheet_names = list(row_counts)
    workbook.close()

    lower_sheets = {name.lower() for name in sheet_names}
    if any(name in {"imperial data", "kalpataru data", "oberoi esquire", "lodha"} for name in lower_sheets):
        guessed = "owner_tenant_all_projects_workbook"
    elif "broker" in path.name.lower() or any("broker" in name.lower() for name in sheet_names):
        guessed = "broker_list_workbook"
    elif any(item in {"building_owner_tenant_workbook", "unit_resident_workbook", "project_customer_workbook", "imperial_unit_inventory_workbook", "society_member_details_workbook"} for item in formats):
        priority = ["society_member_details_workbook", "imperial_unit_inventory_workbook", "project_customer_workbook", "unit_resident_workbook", "building_owner_tenant_workbook"]
        guessed = next(item for item in priority if item in formats)
    elif any(item == "property_inventory_workbook" for item in formats):
        guessed = "property_inventory_workbook"
    elif any(item == "multi_sheet_project_contacts_workbook" for item in formats):
        guessed = "multi_sheet_project_contacts_workbook"
    elif any(item == "structured_owner_sheet" for item in formats):
        guessed = "structured_owner_workbook"
    else:
        guessed = formats[0] if formats else "unknown_contact_csv"

    return {
        "file_type": "xlsx",
        "sheets": sheet_names,
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
    if suffix == ".xls":
        return {
            "file_type": "xls",
            "sheets": [],
            "row_counts": {},
            "columns": {"xls": []},
            "source_format": "old_xls_workbook",
            "note": "unsupported_xls_needs_conversion",
        }
    if suffix == ".vcf" or path.name.endswith(".vcf.example"):
        return profile_vcf(path)
    if suffix == ".pdf":
        return profile_pdf(path)
    if suffix == ".docx":
        return profile_docx(path)
    if suffix in {".txt", ".text"}:
        return profile_text_file(path)
    if suffix in {".jpg", ".jpeg", ".png", ".heic", ".gif", ".tiff"}:
        return {
            "file_type": suffix.lstrip("."),
            "sheets": [],
            "row_counts": {},
            "columns": {"image": []},
            "source_format": "image_only_needs_ocr",
        }
    return {
        "file_type": suffix.lstrip(".") or "unknown",
        "sheets": [],
        "row_counts": {},
        "columns": {"unknown": []},
        "source_format": "unsupported_file",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile contact source file shape without printing private values.")
    parser.add_argument("source_file", help="Source file to profile.")
    args = parser.parse_args()

    path = Path(args.source_file)
    if not path.exists():
        print("Source file was not found.")
        return 1

    profile = profile_file(path)
    print(f"Source file: {path.name}")
    print(f"Detected file type: {profile['file_type']}")
    if profile.get("encoding"):
        print(f"Encoding: {profile['encoding']}")
    if profile.get("delimiter"):
        print(f"Delimiter: {profile['delimiter']}")
    if profile.get("sheets"):
        print(f"Sheets: {', '.join(profile['sheets'])}")
    for sheet, count in profile.get("row_counts", {}).items():
        print(f"Rows in {sheet}: {count}")
        columns = profile.get("columns", {}).get(sheet, [])
        if columns:
            print(f"Columns in {sheet}: {', '.join(columns)}")
    print(f"Guessed source_format: {profile['source_format']}")
    if profile.get("note"):
        print(f"Note: {profile['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
