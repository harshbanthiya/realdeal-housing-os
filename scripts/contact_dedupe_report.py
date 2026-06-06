#!/usr/bin/env python3
"""Create a conservative duplicate-candidate report from a cleaned contacts CSV."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from duplicate_utils import duplicate_summary
from source_format_utils import safe_stem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FIELDS = [
    "duplicate_strength",
    "reason",
    "duplicate_group_key",
    "duplicate_group_size",
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


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_report(cleaned_csv: Path, output_dir: Path) -> Tuple[Path, int, Dict[str, int]]:
    rows = read_rows(cleaned_csv)
    summary = duplicate_summary(rows)
    candidates = list(summary["candidates"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"duplicate_report_{safe_stem(cleaned_csv)}_{timestamp}.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)
    counts = {
        "groups_strong": int(summary["duplicate_groups_strong"]),
        "groups_medium": int(summary["duplicate_groups_medium"]),
        "groups_weak": int(summary["duplicate_groups_weak"]),
        "pairs_strong": int(summary["duplicate_pairs_strong"]),
        "pairs_medium": int(summary["duplicate_pairs_medium"]),
        "pairs_weak": int(summary["duplicate_pairs_weak"]),
        "reported_strong": int(summary["reported_pairs_strong"]),
        "reported_medium": int(summary["reported_pairs_medium"]),
        "reported_weak": int(summary["reported_pairs_weak"]),
    }
    return report_path, len(candidates), counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a duplicate-candidate report from cleaned contacts.")
    parser.add_argument("cleaned_csv", help="Cleaned CSV path.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "exports" / "contacts"), help="Output directory. Defaults to exports/contacts.")
    args = parser.parse_args()
    cleaned_csv = Path(args.cleaned_csv)
    if not cleaned_csv.exists():
        print("Cleaned CSV was not found.")
        return 1
    report_path, count, counts = build_report(cleaned_csv, Path(args.output_dir))
    print(f"Duplicate candidates: {count}")
    print(f"Duplicate groups strong: {counts['groups_strong']}")
    print(f"Duplicate groups medium: {counts['groups_medium']}")
    print(f"Duplicate groups weak: {counts['groups_weak']}")
    print(f"Duplicate pairs strong: {counts['pairs_strong']}")
    print(f"Duplicate pairs medium: {counts['pairs_medium']}")
    print(f"Duplicate pairs weak: {counts['pairs_weak']}")
    print(f"Reported pairs strong: {counts['reported_strong']}")
    print(f"Reported pairs medium: {counts['reported_medium']}")
    print(f"Reported pairs weak: {counts['reported_weak']}")
    print(f"Duplicate report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
