#!/usr/bin/env python3
"""Create a conservative duplicate-candidate report from a cleaned contacts CSV."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FIELDS = [
    "duplicate_strength",
    "reason",
    "row_a",
    "row_b",
    "raw_name_a",
    "raw_name_b",
    "cleaned_display_name_a",
    "cleaned_display_name_b",
    "parsed_building_code",
    "parsed_building_name",
    "parsed_unit_number",
]


def normalize_name(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    stopwords = {"mr", "mrs", "ms", "miss", "shri", "smt"}
    tokens = [token for token in value.split() if token and token not in stopwords]
    return " ".join(tokens)


def similar_name(a: str, b: str) -> bool:
    left = set(normalize_name(a).split())
    right = set(normalize_name(b).split())
    if not left or not right:
        return False
    overlap = len(left & right)
    return overlap >= min(len(left), len(right), 2)


def add_pairs(
    candidates: List[Dict[str, str]],
    rows: List[Dict[str, str]],
    strength: str,
    reason: str,
    seen: set,
) -> None:
    for index, row_a in enumerate(rows):
        for row_b in rows[index + 1 :]:
            key = tuple(sorted((row_a["source_row_number"], row_b["source_row_number"]))) + (strength,)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "duplicate_strength": strength,
                    "reason": reason,
                    "row_a": row_a["source_row_number"],
                    "row_b": row_b["source_row_number"],
                    "raw_name_a": row_a["raw_name"],
                    "raw_name_b": row_b["raw_name"],
                    "cleaned_display_name_a": row_a["cleaned_display_name"],
                    "cleaned_display_name_b": row_b["cleaned_display_name"],
                    "parsed_building_code": row_a.get("parsed_building_code") or row_b.get("parsed_building_code") or "",
                    "parsed_building_name": row_a.get("parsed_building_name") or row_b.get("parsed_building_name") or "",
                    "parsed_unit_number": row_a.get("parsed_unit_number") or row_b.get("parsed_unit_number") or "",
                }
            )


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_report(cleaned_csv: Path, output_dir: Path) -> Tuple[Path, int]:
    rows = read_rows(cleaned_csv)
    candidates: List[Dict[str, str]] = []
    seen = set()

    by_phone: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    by_email: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    by_property: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)

    for row in rows:
        if row.get("phone_normalized"):
            by_phone[row["phone_normalized"]].append(row)
        if row.get("email_normalized"):
            by_email[row["email_normalized"]].append(row)
        building = row.get("parsed_building_code") or ""
        building_name = row.get("parsed_building_name") or ""
        unit = row.get("parsed_unit_number") or ""
        if (building or building_name) and unit:
            by_property[(building, building_name, unit)].append(row)

    for grouped in by_phone.values():
        if len(grouped) > 1:
            add_pairs(candidates, grouped, "strong", "same phone_normalized", seen)

    for grouped in by_email.values():
        if len(grouped) > 1:
            add_pairs(candidates, grouped, "medium", "same email_normalized", seen)

    for grouped in by_property.values():
        if len(grouped) < 2:
            continue
        weak_rows: List[Dict[str, str]] = []
        for index, row_a in enumerate(grouped):
            for row_b in grouped[index + 1 :]:
                if similar_name(row_a.get("cleaned_display_name", ""), row_b.get("cleaned_display_name", "")):
                    weak_rows = [row_a, row_b]
                    add_pairs(candidates, weak_rows, "weak", "similar name and same building/unit", seen)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"duplicate_report_{timestamp}.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(candidates)

    return report_path, len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a duplicate-candidate report from cleaned contacts.")
    parser.add_argument("cleaned_csv", help="Cleaned CSV path.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "exports" / "contacts"), help="Output directory. Defaults to exports/contacts.")
    args = parser.parse_args()

    cleaned_csv = Path(args.cleaned_csv)
    if not cleaned_csv.exists():
        print("Cleaned CSV was not found.")
        return 1

    report_path, count = build_report(cleaned_csv, Path(args.output_dir))
    print(f"Duplicate candidates: {count}")
    print(f"Duplicate report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
