#!/usr/bin/env python3
"""Normalize mixed contact sources into one standard intermediate CSV."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from profile_contact_file import guess_source_format


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STANDARD_FIELDS = [
    "source_file",
    "source_sheet",
    "source_row_number",
    "source_format",
    "raw_name",
    "raw_phone",
    "raw_email",
    "raw_notes",
    "raw_payload_json",
    "building_name_hint",
    "building_code_hint",
    "wing_hint",
    "unit_number_hint",
    "relationship_hint",
    "contact_person_1",
    "contact_person_2",
    "source_label",
    "website",
    "google_maps_link",
]


def row_get(row: Dict[str, object], *keys: str) -> str:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.strip().lower())
        if value is not None:
            return str(value).strip()
    return ""


def raw_payload(row: Dict[str, object]) -> str:
    return json.dumps({str(key): "" if value is None else str(value) for key, value in row.items()}, ensure_ascii=True, sort_keys=True)


def make_standard_row(
    source_file: Path,
    source_sheet: str,
    source_row_number: int,
    source_format: str,
    row: Dict[str, object],
    **values: str,
) -> Dict[str, str]:
    output = {field: "" for field in STANDARD_FIELDS}
    output.update(
        {
            "source_file": str(source_file),
            "source_sheet": source_sheet,
            "source_row_number": str(source_row_number),
            "source_format": source_format,
            "raw_payload_json": raw_payload(row),
        }
    )
    for key, value in values.items():
        output[key] = value or ""
    return output


def normalize_simple(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    return [
        make_standard_row(
            source_file,
            sheet,
            row_number,
            source_format,
            row,
            raw_name=row_get(row, "Name"),
            raw_phone=row_get(row, "Phone Number", "Phone"),
            source_label=row_get(row, "Source"),
        )
    ]


def normalize_messy(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    rows = normalize_simple(source_file, sheet, row_number, row, source_format)
    later_name = row_get(row, "N", "Name 2", "Contact Person", "Contact Person 1")
    later_phone = row_get(row, "Telephone 1", "Phone 2", "Mobile 1")
    flat = row_get(row, "Flat No.", "Flat", "Unit")
    if later_name or later_phone or flat:
        rows.append(
            make_standard_row(
                source_file,
                sheet,
                row_number,
                source_format,
                row,
                raw_name=later_name,
                raw_phone=later_phone,
                wing_hint=row_get(row, "Wing"),
                unit_number_hint=flat,
                relationship_hint=row_get(row, "Relationship", "Role"),
                source_label=row_get(row, "Source"),
            )
        )
    return rows


def normalize_structured(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    output: List[Dict[str, str]] = []
    wing = row_get(row, "Wing")
    flat = row_get(row, "Flat No.", "Flat", "Unit")
    email = row_get(row, "Email")
    source = row_get(row, "Source")
    person_1 = row_get(row, "Contact Person 1")
    person_2 = row_get(row, "Contact Person 2")
    phone_1 = row_get(row, "Telephone 1", "Phone 1", "Mobile 1")
    phone_2 = row_get(row, "Telephone 2", "Phone 2", "Mobile 2")

    if person_1 or phone_1:
        output.append(
            make_standard_row(
                source_file,
                sheet,
                row_number,
                source_format,
                row,
                raw_name=person_1,
                raw_phone=phone_1,
                raw_email=email,
                wing_hint=wing,
                unit_number_hint=flat,
                relationship_hint="owner",
                contact_person_1=person_1,
                contact_person_2=person_2,
                source_label=source,
            )
        )
    if person_2 or phone_2:
        output.append(
            make_standard_row(
                source_file,
                sheet,
                row_number,
                source_format,
                row,
                raw_name=person_2,
                raw_phone=phone_2,
                raw_email=email,
                wing_hint=wing,
                unit_number_hint=flat,
                relationship_hint="owner",
                contact_person_1=person_1,
                contact_person_2=person_2,
                source_label=source,
            )
        )
    return output


def normalize_google(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    notes = "; ".join(
        item
        for item in [
            f"industry={row_get(row, 'Industry')}" if row_get(row, "Industry") else "",
            f"rating={row_get(row, 'Rating')}" if row_get(row, "Rating") else "",
            f"reviews={row_get(row, 'Reviews')}" if row_get(row, "Reviews") else "",
            f"address={row_get(row, 'Address')}" if row_get(row, "Address") else "",
        ]
        if item
    )
    return [
        make_standard_row(
            source_file,
            sheet,
            row_number,
            source_format,
            row,
            raw_name=row_get(row, "Title"),
            raw_phone=row_get(row, "Phone"),
            raw_notes=notes,
            relationship_hint="business_lead",
            source_label=row_get(row, "Industry"),
            website=row_get(row, "Website"),
            google_maps_link=row_get(row, "Google Maps Link"),
        )
    ]


def normalize_unknown(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    return [
        make_standard_row(
            source_file,
            sheet,
            row_number,
            source_format,
            row,
            raw_name=row_get(row, "Name", "Title", "Contact Person 1"),
            raw_phone=row_get(row, "Phone", "Phone Number", "Telephone 1"),
            raw_email=row_get(row, "Email"),
            raw_notes=row_get(row, "Notes", "Source"),
            source_label=row_get(row, "Source"),
        )
    ]


def normalize_row(source_file: Path, sheet: str, row_number: int, row: Dict[str, object], source_format: str) -> List[Dict[str, str]]:
    if source_format == "simple_phonebook_csv":
        return normalize_simple(source_file, sheet, row_number, row, source_format)
    if source_format == "messy_phonebook_property_csv":
        return normalize_messy(source_file, sheet, row_number, row, source_format)
    if source_format in {"structured_owner_sheet", "structured_owner_workbook"}:
        return normalize_structured(source_file, sheet, row_number, row, source_format)
    if source_format == "google_maps_business_csv":
        return normalize_google(source_file, sheet, row_number, row, source_format)
    return normalize_unknown(source_file, sheet, row_number, row, source_format)


def read_csv_rows(path: Path) -> List[Dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_csv(path: Path) -> List[Dict[str, str]]:
    rows = read_csv_rows(path)
    columns = list(rows[0].keys()) if rows else []
    source_format = guess_source_format(columns)
    output: List[Dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        output.extend(normalize_row(path, "", index, row, source_format))
    return output


def normalize_xlsx(path: Path) -> List[Dict[str, str]]:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise SystemExit("XLSX normalization needs openpyxl. Export workbook sheets to CSV or install openpyxl.")

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    output: List[Dict[str, str]] = []
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if not header:
            continue
        columns = [str(value).strip() if value is not None else "" for value in header]
        sheet_format = guess_source_format(columns)
        if sheet_format == "structured_owner_sheet":
            sheet_format = "structured_owner_workbook"
        for row_number, values in enumerate(rows, start=2):
            row = {columns[index]: values[index] if index < len(values) else "" for index in range(len(columns)) if columns[index]}
            if not any(str(value or "").strip() for value in row.values()):
                continue
            output.extend(normalize_row(path, sheet.title, row_number, row, sheet_format))
    workbook.close()
    return output


def safe_stem(path: Path) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in path.stem).strip("_") or "source"


def write_output(rows: List[Dict[str, str]], source_file: Path, output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"normalized_contacts_{safe_stem(source_file)}_{timestamp}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize contact source files into a standard intermediate CSV.")
    parser.add_argument("source_file", help="CSV or XLSX source file.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "exports" / "contacts"), help="Output directory. Defaults to exports/contacts.")
    args = parser.parse_args()

    path = Path(args.source_file)
    if not path.exists():
        print("Source file was not found.")
        return 1

    suffix = path.suffix.lower()
    if suffix == ".csv" or path.name.endswith(".csv.example"):
        rows = normalize_csv(path)
    elif suffix == ".xlsx":
        rows = normalize_xlsx(path)
    else:
        print("Unsupported file type. Use CSV or XLSX.")
        return 1

    output_path = write_output(rows, path, Path(args.output_dir))
    print(f"Normalized rows written: {len(rows)}")
    print(f"Normalized output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
