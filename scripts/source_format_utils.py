#!/usr/bin/env python3
"""Shared source-format detection helpers for contact imports."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JUNK_NAMES = {".DS_Store"}
JUNK_PREFIXES = ("__MACOSX/", "._")


def normalize_column(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower().replace("_", " "))


def normalized_set(columns: Sequence[str]) -> set:
    return {normalize_column(column) for column in columns if str(column).strip()}


def has_all(columns: Sequence[str], expected: Sequence[str]) -> bool:
    existing = normalized_set(columns)
    return all(normalize_column(item) in existing for item in expected)


def has_any(columns: Sequence[str], expected: Sequence[str]) -> bool:
    existing = normalized_set(columns)
    return any(normalize_column(item) in existing for item in expected)


def has_any_prefix(columns: Sequence[str], prefix: str) -> bool:
    prefix = normalize_column(prefix)
    return any(normalize_column(column).startswith(prefix) for column in columns)


def header_score(values: Sequence[object]) -> int:
    keywords = {
        "name",
        "flat",
        "flat no",
        "flat no.",
        "contact",
        "contact details",
        "contact no",
        "contact no.",
        "phone",
        "mobile",
        "email",
        "e-mail",
        "tower",
        "wing",
        "member",
        "premises",
        "occupied",
        "lessee",
        "broker",
        "type",
        "carpet area",
        "client name",
        "phone no",
    }
    score = 0
    for value in values:
        normalized = normalize_column(str(value or ""))
        if not normalized:
            continue
        if normalized in keywords:
            score += 2
        elif any(keyword in normalized for keyword in keywords):
            score += 1
    return score


def detect_header_row(rows: Sequence[Sequence[object]], max_scan_rows: int = 10) -> Tuple[int, List[str]]:
    best_index = 0
    best_score = -1
    best_columns: List[str] = []
    for index, row in enumerate(rows[:max_scan_rows]):
        columns = [str(value).strip() for value in row if value is not None and str(value).strip()]
        score = header_score(row)
        if score > best_score and columns:
            best_index = index
            best_score = score
            best_columns = columns
    return best_index, best_columns


def safe_stem(path: Path) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in path.stem).strip("_") or "source"


def is_junk_archive_member(name: str) -> bool:
    base = Path(name).name
    if base in JUNK_NAMES:
        return True
    if any(name.startswith(prefix) for prefix in JUNK_PREFIXES):
        return True
    if base.startswith("._"):
        return True
    return False


def detect_text_encoding(path: Path) -> Tuple[str, str]:
    with path.open("rb") as handle:
        sample = handle.read(8192)
    if sample.startswith(b"\xff\xfe"):
        return "utf-16", "\t"
    if sample.startswith(b"\xfe\xff"):
        return "utf-16", "\t"
    try:
        text = sample.decode("utf-8-sig")
        dialect = csv.Sniffer().sniff(text, delimiters=",\t;|")
        return "utf-8-sig", dialect.delimiter
    except Exception:
        try:
            sample.decode("latin-1")
            return "latin-1", ","
        except Exception:
            return "utf-8-sig", ","


def read_csv_header_and_count(path: Path) -> Tuple[List[str], int, str, str]:
    encoding, delimiter = detect_text_encoding(path)
    with path.open(newline="", encoding=encoding, errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        columns = reader.fieldnames or []
        row_count = sum(1 for _ in reader)
    return columns, row_count, encoding, delimiter


def read_csv_rows(path: Path) -> Tuple[List[Dict[str, object]], str, str]:
    encoding, delimiter = detect_text_encoding(path)
    with path.open(newline="", encoding=encoding, errors="replace") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    return rows, encoding, delimiter


def load_source_format_rules(project_root: Optional[Path] = None) -> Dict[str, object]:
    root = project_root or PROJECT_ROOT
    path = root / "config" / "source_format_rules.json"
    if not path.exists():
        path = root / "config" / "source_format_rules.json.example"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def guess_source_format(columns: Sequence[str], *, file_name: str = "", sheet_names: Optional[Sequence[str]] = None, delimiter: str = ",", encoding: str = "") -> str:
    name = file_name.lower()
    sheets = [sheet.lower() for sheet in (sheet_names or [])]

    if delimiter == "\t" and has_any(columns, ["phone_number", "full_name", "created_time", "ad_id"]):
        return "meta_facebook_leads_utf16_tsv"
    if has_all(columns, ["number", "Name", "Push Name"]):
        return "whatsapp_export_csv"
    if has_any(columns, ["First Name", "Last Name", "Display Name"]) and has_any(columns, ["E-mail Address", "Mobile Phone", "Home Phone", "Business Phone"]):
        return "google_contacts_csv"
    if has_any(columns, ["LeadID", "Lead ID"]) and has_any(columns, ["Mobile", "Phone"]) and has_any(columns, ["PropertyType", "Property Type", "Purpose", "Budget", "Visit"]):
        return "portal_property_leads_csv"
    if has_all(columns, ["Title", "Phone", "Industry", "Address", "Website"]) and (has_any(columns, ["Google Maps Link", "Rating", "Reviews"]) or "maps" in name):
        return "google_maps_business_csv"
    if has_all(columns, ["Name", "Phone", "Flat No.", "N", "Telephone 1"]):
        return "messy_phonebook_property_csv"
    if has_any(columns, ["SR.NO.", "SR.NO", "DATE"]) and has_any(columns, ["TOWER"]) and has_any(columns, ["FLAT NO.", "FLAT NO"]) and has_any(columns, ["CONTACT DETAILS", "CONTACT NO.", "CONTACT NO", "E-MAIL", "EMAIL"]):
        return "building_owner_tenant_workbook"
    if has_any(columns, ["Name of Lessee"]) and has_any(columns, ["PRIMARY CONTACT NO", "SECONDARY CONTACT NO", "OTHER CONTACT NO/S."]) and has_any(columns, ["PRIMARY EMAIL ID", "OTHER EMAIL ID'S"]):
        return "unit_resident_workbook"
    if has_any(columns, ["S.NO", "S.NO."]) and has_any(columns, ["FLAT DETAILS"]) and has_any(columns, ["CLIENT NAME"]) and has_any(columns, ["PHONE NO", "PHONE NO.", "EMAIL ID", "EMAID ID"]):
        return "project_customer_workbook"
    if has_any(columns, ["FLAT NO.", "FLAT NO"]) and has_any(columns, ["TYPE"]) and has_any(columns, ["carpet area", "CARPET AREA", "NEW carpet area"]) and has_any(columns, ["NAME OF THE PARTY"]) and has_any(columns, ["CONTACT NO.", "CONTACT NO", "CUSTOMERS NUMBER"]):
        return "imperial_unit_inventory_workbook"
    if has_any(columns, ["Premises Details"]) and has_any(columns, ["Member Name"]) and has_any(columns, ["Member Type"]) and has_any(columns, ["Occupied By"]) and has_any(columns, ["Mobile No.", "Mobile No"]) and has_any(columns, ["E-mail", "Email", "Email Id"]):
        return "society_member_details_workbook"
    if has_any(columns, ["Building Name", "Flat Number", "Flat No."]) and has_any(columns, ["SQFT", "CP", "Sell", "Rent Price", "Sale Price", "Rent"]) and has_any(columns, ["contact number", "Contact Number", "Phone"]):
        return "property_inventory_csv"
    if has_all(columns, ["Wing", "Flat No."]) and has_any_prefix(columns, "Contact Person") and has_any_prefix(columns, "Telephone"):
        return "structured_owner_sheet"
    if has_any(columns, ["Typology"]) and has_any(columns, ["Name", "Contact Number"]):
        return "multi_sheet_project_contacts_workbook"
    if has_any(columns, ["Typology", "Sale Price", "Rent", "Carpet Area", "Salable Area"]) and has_any(columns, ["Wing", "Flat No."]):
        return "property_inventory_workbook"
    if has_any(columns, ["Name"]) and has_any(columns, ["Phone", "Phone Number", "Mobile", "Phone 2", "Email", "Number"]):
        return "simple_phonebook_csv"
    if "broker" in name or any("broker" in sheet for sheet in sheets):
        return "broker_list_workbook"
    if any(sheet in {"imperial data", "kalpataru data", "oberoi esquire", "lodha"} for sheet in sheets):
        return "owner_tenant_all_projects_workbook"
    return "unknown_contact_csv"


def profile_vcf(path: Path) -> Dict[str, object]:
    count = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip().upper() == "BEGIN:VCARD":
                count += 1
    return {
        "file_type": "vcf",
        "sheets": [],
        "row_counts": {"vcf": count},
        "columns": {"vcf": ["BEGIN:VCARD", "FN", "N", "TEL", "EMAIL", "ORG", "NOTE"]},
        "source_format": "vcf_contacts_file",
    }


def extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            parts = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
            chunks = []
            for name in parts:
                text = archive.read(name).decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", text)
                chunks.append(re.sub(r"\s+", " ", text))
            return "\n".join(chunks)
    except Exception:
        return ""


def profile_pdf(path: Path) -> Dict[str, object]:
    text = ""
    page_count = None
    try:
        result = subprocess.run(["pdftotext", str(path), "-"], check=False, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            text = result.stdout or ""
    except Exception:
        text = ""
    try:
        result = subprocess.run(["pdfinfo", str(path)], check=False, capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            if line.lower().startswith("pages:"):
                page_count = int(line.split(":", 1)[1].strip())
                break
    except Exception:
        page_count = None
    non_empty = [line for line in text.splitlines() if line.strip()]
    source_format = "text_extractable_pdf_contacts" if len(" ".join(non_empty)) > 200 else "scanned_pdf_or_image_only"
    return {
        "file_type": "pdf",
        "sheets": [],
        "row_counts": {"pages": page_count if page_count is not None else 0, "text_lines": len(non_empty)},
        "columns": {"pdf": []},
        "source_format": source_format,
    }


def profile_text_file(path: Path) -> Dict[str, object]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        lines = [line for line in handle if line.strip()]
    return {
        "file_type": "txt",
        "sheets": [],
        "row_counts": {"txt": len(lines)},
        "columns": {"txt": []},
        "source_format": "txt_contacts" if len(lines) >= 5 else "unknown_text_file",
    }


def profile_docx(path: Path) -> Dict[str, object]:
    text = extract_docx_text(path)
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "file_type": "docx",
        "sheets": [],
        "row_counts": {"docx_text_lines": len(lines)},
        "columns": {"docx": []},
        "source_format": "docx_text_contacts" if len(text.strip()) > 100 else "unknown_docx_file",
    }
