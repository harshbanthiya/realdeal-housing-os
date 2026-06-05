#!/usr/bin/env python3
"""Parse messy phonebook names without discarding the original value."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROLE_WORDS = {
    "owner": "owner",
    "broker": "broker",
    "agent": "agent",
    "tenant": "tenant",
    "buyer": "buyer",
    "seller": "seller",
    "landlord": "landlord",
    "reference": "reference",
    "existing customer": "existing_customer",
}

UNIT_PATTERNS = [
    re.compile(r"\b([A-Z])\s+Wing\s+(\d{3,5})\b", re.IGNORECASE),
    re.compile(r"\b([A-Z])\s*-\s*(\d{3,5})\b", re.IGNORECASE),
    re.compile(r"\b([A-Z])\s+(\d{3,5})\b", re.IGNORECASE),
    re.compile(r"\bFlat\s*[- ]?\s*(\d{3,5})\b", re.IGNORECASE),
    re.compile(r"\b(\d{3,5})\b", re.IGNORECASE),
]


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -,_")


def load_building_codes(project_root: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Load building-code mappings, preferring local private config if present."""

    root = project_root or PROJECT_ROOT
    candidates = [
        root / "config" / "building_codes.csv",
        root / "config" / "building_codes.csv.example",
    ]
    for path in candidates:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            mappings: Dict[str, Dict[str, str]] = {}
            for row in reader:
                code = (row.get("code") or "").strip().upper()
                if code:
                    mappings[code] = row
            return mappings
    return {}


def _find_building_code(raw_name: str, building_codes: Dict[str, Dict[str, str]]) -> Tuple[Optional[str], List[Tuple[int, int]], List[str]]:
    spans: List[Tuple[int, int]] = []
    hints: List[str] = []
    found: Optional[str] = None

    for code in sorted(building_codes, key=len, reverse=True):
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])", re.IGNORECASE)
        match = pattern.search(raw_name)
        if match:
            found = code.upper()
            spans.append(match.span())
            hints.append(match.group(0))
            break

    return found, spans, hints


def _find_role(raw_name: str) -> Tuple[Optional[str], List[Tuple[int, int]], List[str]]:
    for word, role in ROLE_WORDS.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        match = pattern.search(raw_name)
        if match:
            return role, [match.span()], [match.group(0)]
    return None, [], []


def _find_unit(raw_name: str) -> Tuple[Optional[str], Optional[str], List[Tuple[int, int]], List[str]]:
    for pattern in UNIT_PATTERNS:
        match = pattern.search(raw_name)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 2:
            wing = groups[0].upper()
            unit = groups[1]
        else:
            wing = None
            unit = groups[0]
        return wing, unit, [match.span()], [match.group(0)]
    return None, None, [], []


def _remove_spans(value: str, spans: Iterable[Tuple[int, int]]) -> str:
    chars = list(value)
    for start, end in spans:
        for index in range(start, end):
            chars[index] = " "
    return _clean_spaces("".join(chars))


def parse_phonebook_name(raw_name: str, building_codes: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, object]:
    """Extract structured hints from a raw phonebook name.

    The caller must keep raw_name separately. This function never mutates or
    discards that original source value.
    """

    source = raw_name or ""
    normalized = _clean_spaces(source)
    codes = building_codes if building_codes is not None else load_building_codes()

    spans: List[Tuple[int, int]] = []
    hint_parts: List[str] = []
    tags: List[str] = []

    building_code, code_spans, code_hints = _find_building_code(normalized, codes)
    spans.extend(code_spans)
    hint_parts.extend(code_hints)
    if building_code:
        tags.append(f"building_code:{building_code}")
    building_name = ""
    if building_code and building_code in codes:
        building_name = (codes[building_code].get("building_name") or "").strip()
        if building_name:
            tags.append(f"building_name:{building_name}")

    wing, unit_number, unit_spans, unit_hints = _find_unit(normalized)
    spans.extend(unit_spans)
    hint_parts.extend(unit_hints)
    if wing:
        tags.append(f"wing:{wing}")
    if unit_number:
        tags.append(f"unit:{unit_number}")

    role, role_spans, role_hints = _find_role(normalized)
    spans.extend(role_spans)
    hint_parts.extend(role_hints)
    if role:
        tags.append(f"role:{role}")

    display_name = _remove_spans(normalized, spans)
    display_name = re.sub(r"\b(Mobile|Phone|Contact)\b", " ", display_name, flags=re.IGNORECASE)
    display_name = _clean_spaces(display_name)

    if display_name.lower() in {"unknown", "unk", "no name", "noname", "n/a", "na"}:
        tags.append("unknown_name")

    confidence = 0.30
    if display_name and "unknown_name" not in tags:
        confidence += 0.25
    if building_code:
        confidence += 0.20
    if unit_number:
        confidence += 0.20
    if role:
        confidence += 0.10
    confidence = min(confidence, 0.95)

    needs_review = confidence < 0.70 or not display_name or "unknown_name" in tags

    return {
        "cleaned_display_name": display_name,
        "parsed_building_code": building_code or "",
        "parsed_building_name": building_name,
        "parsed_wing": wing or "",
        "parsed_unit_number": unit_number or "",
        "parsed_role": role or "",
        "parsed_tags": tags,
        "parse_confidence": round(confidence, 3),
        "raw_hint": _clean_spaces(" | ".join(hint_parts)),
        "needs_review": needs_review,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse raw phonebook names into reviewable hints.")
    parser.add_argument("names", nargs="+", help="Raw name values to parse.")
    args = parser.parse_args()

    building_codes = load_building_codes()
    for name in args.names:
        result = parse_phonebook_name(name, building_codes)
        print(json.dumps({"raw_name": name, **result}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
