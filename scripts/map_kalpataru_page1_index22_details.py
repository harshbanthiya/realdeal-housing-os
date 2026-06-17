#!/usr/bin/env python3
"""Map IGR Page 1 search results to downloaded Index II PDFs.

Reads:
  - Search results of Page 1.pdf
  - index22_1 ... index22_10.pdf/detail files

Outputs a CSV/JSON/Markdown summary showing which search-result document each
Index II file belongs to, with richer Index II fields such as PAN, age, address,
area, market value, stamp duty, and parsed tower/unit.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGE_DIR = Path("/Users/sheeed/Downloads/Kalpataru Radiance Tower A/2026/Page 1")
DEFAULT_BROCHURE = Path("/Users/sheeed/Downloads/brochure kalpataru .pdf")
OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines"
PARSER_EVENTS_CSV = OUTPUT_DIR / "kalpataru_radiance_events.csv"

TOWER_LABELS = {
    "A": "Wing A-Ora",
    "B": "Wing B-Brilliance",
    "C": "Wing C-Allura",
    "D": "Wing D-Lumina",
}
TOWER_ALIASES = {
    "A": ("wing a", "a wing", "tower a", "a ora", "a-ora", "ora", "ओरा", "ऑरा", "टॉवर ए", "विंग ए", "ए विंग"),
    "B": ("wing b", "b wing", "tower b", "brilliance", "ब्रिलियन्स", "ब्रिल्लीयन्स", "ब्रिलीयन्स", "विंग बी", "बी विंग"),
    "C": (
        "wing c", "c wing", "tower c", "allura", "allure", "alora", "allora",
        "अलुरा", "अलोरा", "अल्लुरा", "अल्लोरा", "एल्लूरा", "ॲलुरा", "विंग सी", "सी विंग",
    ),
    "D": ("wing d", "d wing", "tower d", "lumina", "लुमिना", "लुमीना", "विंग डी", "डी विंग"),
}
DOC_TYPES = [
    ("लिव्ह", "leave_and_license", "tenancy"),
    ("िलव्ह", "leave_and_license", "tenancy"),
    ("लायस", "leave_and_license", "tenancy"),
    ("leave and licen", "leave_and_license", "tenancy"),
    ("करारनामा", "agreement_to_sell", "ownership"),
    ("सेल डीड", "sale_deed", "ownership"),
    ("sale deed", "sale_deed", "ownership"),
    ("चुक", "correction_deed", "other"),
]
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")


def skeleton(text: str) -> str:
    return "".join(c for c in (text or "") if unicodedata.category(c)[0] != "M" and not c.isspace()).lower()


def pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text(x_tolerance=1, y_tolerance=3) or "" for page in pdf.pages)


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    # pdf extraction interleaves the "For Preview Only" watermark letters.
    text = re.sub(r"(?<=\s)[A-Za-z](?=\s)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def money(text: str | None) -> str:
    if not text:
        return ""
    match = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?", text)
    if not match:
        return ""
    value = match.group(0).replace(",", "")
    if value.endswith(".0"):
        value = value[:-2]
    return value


def classify_doc(text: str) -> tuple[str, str]:
    sk = skeleton(text)
    low = (text or "").lower()
    for needle, doc_type, category in DOC_TYPES:
        if skeleton(needle) in sk or needle in low:
            return doc_type, category
    return "other", "other"


def detect_tower(text: str) -> tuple[str, str, str]:
    sk = skeleton(text)
    low = (text or "").lower()
    for wing in ("C", "B", "D", "A"):
        for alias in TOWER_ALIASES[wing]:
            if skeleton(alias) in sk or alias.lower() in low:
                return wing, TOWER_LABELS[wing], alias
    return "", "", ""


def field(text: str, n: int) -> str:
    parts = re.split(r"\((1[0-4]|[1-9])\)", text)
    for i in range(1, len(parts) - 1, 2):
        if parts[i] == str(n):
            return parts[i + 1]
    return ""


def first(patterns: list[str], text: str, flags: int = re.I | re.S) -> str:
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            return clean(match.group(1))
    return ""


def parse_parties(block: str) -> list[dict[str, str]]:
    block = clean(block)
    chunks = re.split(r"\b\d+\)\s*:", block)
    parties = []
    for chunk in chunks:
        if "नाव" not in chunk:
            continue
        name = first([r"नाव\s*:\-?\s*(.+?)\s*वय\s*:", r"नाव\s*:\-?\s*(.+?)\s*(?:पत्ता|पॅन|$)"], chunk)
        if not name:
            continue
        age = first([r"वय\s*:\-?\s*([0-9]+)"], chunk)
        pan_match = PAN_RE.search(chunk)
        address = first([r"पत्ता\s*:\-?\s*(.+?)(?:\s*पॅन|\s*$)"], chunk)
        parties.append({"name": name, "age": age, "pan": pan_match.group(0) if pan_match else "", "address": address})
    return parties


def possible_wings_for_unit(unit: str) -> str:
    digits = re.sub(r"\D", "", unit or "")
    if not digits:
        return ""
    stack = int(digits[-1])
    wings = []
    if 1 <= stack <= 5:
        wings.append("A")
    if 1 <= stack <= 6:
        wings.extend(["B", "C", "D"])
    return ",".join(wings)


def parse_property_money(field4: str) -> dict[str, str]:
    text = clean(field4)
    rent = first(
        [
            r"(?:मािसक|मासिक)\s*भाड\s*े?\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)",
            r"monthly\s*rent[^0-9]{0,30}([0-9,]+)",
        ],
        text,
    )
    deposit = first(
        [
            r"अनामत\s*रक्कम\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)",
            r"deposit[^0-9]{0,30}([0-9,]+)",
        ],
        text,
    )
    tenure = first(
        [
            r"कालावधी[^0-9]{0,25}([0-9]+)\s*मिहन",
            r"कालावधी[^0-9]{0,25}([0-9]+)\s*महिन",
            r"([0-9]+)\s*months?",
        ],
        text,
    )
    return {
        "tenancy_monthly_rent": rent.replace(",", "") if rent else "",
        "tenancy_deposit": deposit.replace(",", "") if deposit else "",
        "tenure_months": tenure,
    }


def load_parser_events() -> dict[str, dict[str, str]]:
    if not PARSER_EVENTS_CSV.exists():
        return {}
    with PARSER_EVENTS_CSV.open(newline="", encoding="utf-8") as handle:
        return {row["doc_number"]: row for row in csv.DictReader(handle)}


def parse_index_file(path: Path, index_number: int) -> dict[str, Any]:
    text = pdf_text(path)
    doc_match = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    doc_number = doc_match.group(1) if doc_match else ""
    year = doc_match.group(2) if doc_match else ""

    f1, f2, f3, f4, f5 = field(text, 1), field(text, 2), field(text, 3), field(text, 4), field(text, 5)
    f7, f8, f9, f10, f12, f13 = field(text, 7), field(text, 8), field(text, 9), field(text, 10), field(text, 12), field(text, 13)
    doc_type, category = classify_doc(f1)
    wing, wing_label, matched_alias = detect_tower(f4 or text)
    unit = first(
        [
            r"सद\s?िनका\s*(?:नं|क्रं|क्र|क्रमांक)?\.?\s*[:]?\s*([A-Z]?\-?[0-9][0-9A-Za-z\-/]*)",
            r"सद\S{0,8}नका[^0-9]{0,80}([A-Z]?\-?[0-9][0-9A-Za-z\-/]*)",
            r"फ्लॅट\s*नं?\.?\s*([A-Z]?\-?[0-9][0-9A-Za-z\-/]*)",
            r"Apartment/Flat No\s*:?\s*([A-Z]?\-?[0-9][0-9A-Za-z\-/]*)",
            r"Flat No\s*:?\s*([A-Z]?\-?[0-9][0-9A-Za-z\-/]*)",
        ],
        f4,
    )
    unit = re.sub(r"^[A-D][- ]", "", unit, flags=re.I)
    floor = first([r"([0-9]+)\s*(?:वा|व्या|था|ला)?\s*मजल", r"Floor No\s*:?\s*([0-9]+)"], f4)
    if not floor:
        floor_words = {"पिहला": "1", "पहिला": "1", "दुसरा": "2", "तिसरा": "3", "चौथा": "4"}
        floor = next((num for word, num in floor_words.items() if word in f4), "")
    cts = first([r"C\.?T\.?S\.?\s*Number\s*:\s*([0-9/ A-Za-z.]+)", r"(260\s*/\s*5\s*[Aए]?)"], f4)
    prop_money = parse_property_money(f4)
    referenced_doc = first([r"(?:मुंबई|mumbai)\s*r?\s*21\s*/\s*([0-9]+)\s*/\s*[0-9]{4}", r"\b([0-9]{3,6})/[0-9]{4}"], f4)
    sellers = parse_parties(f7)
    purchasers = parse_parties(f8)
    date_execution = first([r"([0-3]?\d/[01]?\d/[0-9]{4})"], f9)
    date_registration = first([r"([0-3]?\d/[01]?\d/[0-9]{4})"], f10)

    return {
        "index_file": path.name,
        "index_number": index_number,
        "doc_number": doc_number,
        "year": year,
        "document_type": doc_type,
        "category": category,
        "wing": wing,
        "wing_label": wing_label,
        "matched_alias": matched_alias,
        "unit_number": unit,
        "floor": floor,
        "cts": cts,
        "consideration_amount": money(f2),
        "market_value": money(f3),
        "area_text": clean(f5),
        "stamp_duty": money(f12),
        "registration_fee": money(f13),
        "tenancy_monthly_rent": prop_money["tenancy_monthly_rent"],
        "tenancy_deposit": prop_money["tenancy_deposit"],
        "tenure_months": prop_money["tenure_months"],
        "date_of_execution": date_execution,
        "registration_date": date_registration,
        "referenced_doc_number": referenced_doc,
        "possible_wings_from_unit": possible_wings_for_unit(unit),
        "seller_count": len(sellers),
        "purchaser_count": len(purchasers),
        "pan_count": sum(1 for p in sellers + purchasers if p["pan"]),
        "seller_names": "; ".join(p["name"] for p in sellers),
        "purchaser_names": "; ".join(p["name"] for p in purchasers),
        "seller_pans": "; ".join(p["pan"] for p in sellers if p["pan"]),
        "purchaser_pans": "; ".join(p["pan"] for p in purchasers if p["pan"]),
        "seller_ages": "; ".join(p["age"] for p in sellers if p["age"]),
        "purchaser_ages": "; ".join(p["age"] for p in purchasers if p["age"]),
        "property_description": clean(f4),
        "parties": {"sellers": sellers, "purchasers": purchasers},
    }


def parse_search_result_docs(path: Path) -> list[str]:
    text = pdf_text(path)
    # Keep order of displayed result rows. Exclude page/footer/user-guide numbers by
    # requiring known doc-name words soon after the number.
    docs = []
    for match in re.finditer(r"\b([0-9]{2,6})\s+(?:करारनामा|सेल\s+डीड|36-अ|65-चुक)", text):
        doc = match.group(1)
        if doc not in docs:
            docs.append(doc)
    return docs


def brochure_alias_notes(path: Path) -> dict[str, str]:
    notes = {}
    if not path.exists():
        return notes
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    for line in text.splitlines():
        compact = re.sub(r"\s+", "", line).lower()
        if re.search(r"WING\s+A", line, re.I) and "ora" in compact:
            notes["A"] = "Wing A-Ora (brochure text: WING A - O R A)"
        if re.search(r"WING\s+B", line, re.I) and "brilliance" in compact:
            notes["B"] = "Wing B-Brilliance (brochure text: WING B - Brilliance)"
        if re.search(r"WING\s+C", line, re.I) and "allura" in compact:
            notes["C"] = "Wing C-Allura (brochure text: WING C - ALLURA)"
    notes.setdefault("D", "Wing D-Lumina (seen in IGR descriptions; not text-extracted from supplied brochure)")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Map Page 1 search results to Index II details.")
    parser.add_argument("--page-dir", type=Path, default=DEFAULT_PAGE_DIR)
    parser.add_argument("--brochure", type=Path, default=DEFAULT_BROCHURE)
    args = parser.parse_args()

    search_pdf = args.page_dir / "Search results of Page 1.pdf"
    index_files = sorted(
        [p for p in args.page_dir.glob("index22*")],
        key=lambda p: int(re.search(r"index22_([0-9]+)", p.name).group(1)),
    )
    search_docs = parse_search_result_docs(search_pdf)
    parser_docs = load_parser_events()
    parsed = []
    for path in index_files:
        idx = int(re.search(r"index22_([0-9]+)", path.name).group(1))
        row = parse_index_file(path, idx)
        row["search_result_doc_at_same_position"] = search_docs[idx - 1] if idx - 1 < len(search_docs) else ""
        row["matches_search_result_position"] = row["doc_number"] == row["search_result_doc_at_same_position"]
        parser_row = parser_docs.get(row["doc_number"])
        row["refined_parser_found"] = bool(parser_row)
        row["refined_parser_apartment_key"] = parser_row.get("apartment_key", "") if parser_row else ""
        row["refined_parser_category"] = parser_row.get("category", "") if parser_row else ""
        parsed.append(row)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "kalpataru_page1_index22_mapping.csv"
    json_path = OUTPUT_DIR / "kalpataru_page1_index22_mapping.json"
    md_path = OUTPUT_DIR / "KALPATARU_PAGE1_INDEX22_MAPPING.md"
    fieldnames = [
        "index_number", "index_file", "doc_number", "search_result_doc_at_same_position", "matches_search_result_position",
        "registration_date", "date_of_execution", "document_type", "category", "wing", "wing_label", "matched_alias",
        "unit_number", "floor", "possible_wings_from_unit", "cts", "consideration_amount", "market_value", "stamp_duty", "registration_fee",
        "tenancy_monthly_rent", "tenancy_deposit", "tenure_months", "referenced_doc_number",
        "refined_parser_found", "refined_parser_apartment_key", "refined_parser_category",
        "area_text", "seller_count", "purchaser_count", "pan_count", "seller_names", "purchaser_names",
        "seller_pans", "purchaser_pans", "seller_ages", "purchaser_ages", "property_description",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in parsed:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    json_path.write_text(json.dumps({"brochure_alias_notes": brochure_alias_notes(args.brochure), "rows": parsed}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Kalpataru Page 1 Index II Mapping",
        "",
        "## Brochure / Alias Notes",
    ]
    for wing, note in brochure_alias_notes(args.brochure).items():
        lines.append(f"- {wing}: {note}")
    lines.extend(["", "## Search Result Row To Index II File"])
    for row in parsed:
        ok = "yes" if row["matches_search_result_position"] else "NO"
        lines.append(
            f"- Search row {row['index_number']} -> `{row['index_file']}` -> doc `{row['doc_number']}` "
            f"(position match: {ok}) -> {row['wing_label'] or 'unclassified'} flat `{row['unit_number']}`; "
            f"{row['document_type']} / {row['category']}; PANs `{row['pan_count']}`; "
            f"parser match `{row['refined_parser_apartment_key'] or 'none'}`"
        )
    lines.extend(
        [
            "",
            "## Outputs",
            f"- CSV: `{csv_path}`",
            f"- JSON: `{json_path}`",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Parsed {len(parsed)} Index II PDFs.")
    print(f"Search-result docs detected: {search_docs}")
    print(f"All positional doc matches: {all(row['matches_search_result_position'] for row in parsed)}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    for row in parsed:
        print(f"{row['index_number']:02d} {row['index_file']} doc={row['doc_number']} wing={row['wing']} unit={row['unit_number']} pans={row['pan_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
