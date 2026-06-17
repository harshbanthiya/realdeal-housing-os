#!/usr/bin/env python3
"""Parse downloaded Kalpataru Index II PDFs and match them to parser docs.

Use this after manually fetching documents from the IGR Document Number search
tab. Point it at a folder of PDFs (recursive); it extracts the document number,
Index II details, and matches them to the refined parser timeline by doc number.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines"
DEFAULT_SEARCH_ROOT = Path("/Users/sheeed/Downloads")

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from map_kalpataru_page1_index22_details import load_parser_events, parse_index_file  # noqa: E402


def looks_like_pdf(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def find_pdf_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if looks_like_pdf(root) else []
    files = []
    for path in root.rglob("*"):
        if path.is_file() and looks_like_pdf(path):
            files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse and match downloaded Kalpataru Index II PDFs.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_SEARCH_ROOT, help="PDF file or folder to scan recursively")
    parser.add_argument("--label", default="manual_doc_search", help="label used in output filenames")
    args = parser.parse_args()

    parser_events = load_parser_events()
    files = find_pdf_files(args.path)
    rows = []
    for idx, path in enumerate(files, 1):
        try:
            row = parse_index_file(path, idx)
        except Exception as exc:  # noqa: BLE001
            rows.append({"source_path": str(path), "parse_error": type(exc).__name__})
            continue
        if not row.get("doc_number"):
            continue
        parser_row = parser_events.get(str(row["doc_number"]))
        row["source_path"] = str(path)
        row["refined_parser_found"] = bool(parser_row)
        row["refined_parser_apartment_key"] = parser_row.get("apartment_key", "") if parser_row else ""
        row["refined_parser_category"] = parser_row.get("category", "") if parser_row else ""
        row["refined_parser_registration_date"] = parser_row.get("registration_date", "") if parser_row else ""
        rows.append(row)

    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", args.label).strip("_") or "manual_doc_search"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / f"kalpataru_index22_{safe_label}.csv"
    json_path = OUTPUT_DIR / f"kalpataru_index22_{safe_label}.json"
    fieldnames = [
        "source_path", "index_file", "doc_number", "year", "registration_date", "date_of_execution",
        "document_type", "category", "wing", "wing_label", "matched_alias", "unit_number", "floor",
        "consideration_amount", "market_value", "stamp_duty", "registration_fee", "tenancy_monthly_rent",
        "tenancy_deposit", "tenure_months", "seller_count", "purchaser_count", "pan_count",
        "seller_names", "purchaser_names", "seller_pans", "purchaser_pans",
        "refined_parser_found", "refined_parser_apartment_key", "refined_parser_category",
        "refined_parser_registration_date", "parse_error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    matched = sum(1 for row in rows if row.get("refined_parser_found"))
    print(f"Scanned PDF files: {len(files)}")
    print(f"Parsed Index II rows: {len(rows)}")
    print(f"Matched refined parser docs: {matched}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
