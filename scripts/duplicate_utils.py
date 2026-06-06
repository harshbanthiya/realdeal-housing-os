#!/usr/bin/env python3
"""Shared duplicate-candidate logic for cleaned contact CSVs."""

from __future__ import annotations

import itertools
import json
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple


MAX_PAIRS_PER_GROUP = 25


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


def parse_json_list(value: str) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
    except Exception:
        pass
    return [part for part in str(value).split("|") if part]


def row_phones(row: Dict[str, str]) -> Set[str]:
    values = set(parse_json_list(row.get("phones_normalized_json", "")))
    if row.get("phone_normalized"):
        values.add(row["phone_normalized"])
    return {value for value in values if value}


def row_emails(row: Dict[str, str]) -> Set[str]:
    values = set(parse_json_list(row.get("emails_normalized_json", "")))
    if row.get("email_normalized"):
        values.add(row["email_normalized"])
    return {value for value in values if value}


def same_source_row(a: Dict[str, str], b: Dict[str, str]) -> bool:
    return (
        a.get("source_file") == b.get("source_file")
        and a.get("source_sheet") == b.get("source_sheet")
        and a.get("source_row_number") == b.get("source_row_number")
    )


def candidate_row(rows: List[Dict[str, str]], left: int, right: int, strength: str, reason: str, group_key: str, group_size: int) -> Dict[str, str]:
    a = rows[left]
    b = rows[right]
    return {
        "duplicate_strength": strength,
        "reason": reason,
        "duplicate_group_key": group_key,
        "duplicate_group_size": str(group_size),
        "row_a": a.get("source_row_number", ""),
        "row_b": b.get("source_row_number", ""),
        "raw_name_a": a.get("raw_name", ""),
        "raw_name_b": b.get("raw_name", ""),
        "cleaned_display_name_a": a.get("cleaned_display_name", ""),
        "cleaned_display_name_b": b.get("cleaned_display_name", ""),
        "parsed_building_code": a.get("parsed_building_code") or b.get("parsed_building_code") or "",
        "parsed_building_name": a.get("parsed_building_name") or b.get("parsed_building_name") or "",
        "parsed_unit_number": a.get("parsed_unit_number") or b.get("parsed_unit_number") or "",
    }


def grouped_indexes(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, List[int]]]:
    groups: Dict[str, Dict[str, List[int]]] = {
        "strong": defaultdict(list),
        "medium": defaultdict(list),
        "weak": defaultdict(list),
    }
    for index, row in enumerate(rows):
        for phone in row_phones(row):
            groups["strong"][f"phone:{phone}"].append(index)
        for email in row_emails(row):
            groups["medium"][f"email:{email}"].append(index)
        building = row.get("parsed_building_code") or row.get("parsed_building_name") or ""
        unit = row.get("parsed_unit_number") or ""
        name = normalize_name(row.get("cleaned_display_name", ""))
        if building and unit and name:
            groups["weak"][f"property:{building}:{unit}:{name[:20]}"].append(index)
        website = (row.get("website") or "").strip().lower()
        if website and row.get("source_format") == "google_maps_business_csv":
            groups["weak"][f"business:{normalize_name(row.get('cleaned_display_name', ''))}:{website}"].append(index)
    return groups


def duplicate_summary(rows: List[Dict[str, str]], max_pairs_per_group: int = MAX_PAIRS_PER_GROUP) -> Dict[str, object]:
    groups = grouped_indexes(rows)
    summary = {
        "duplicate_groups_strong": 0,
        "duplicate_groups_medium": 0,
        "duplicate_groups_weak": 0,
        "duplicate_pairs_strong": 0,
        "duplicate_pairs_medium": 0,
        "duplicate_pairs_weak": 0,
        "reported_pairs_strong": 0,
        "reported_pairs_medium": 0,
        "reported_pairs_weak": 0,
        "candidates": [],
    }
    seen_pairs: Set[Tuple[int, int, str]] = set()
    candidates: List[Dict[str, str]] = []

    reasons = {
        "strong": "matching normalized phone; review before merge",
        "medium": "matching normalized email; review before merge",
        "weak": "similar name/business/property hints; review before merge",
    }

    for strength, by_key in groups.items():
        for group_key, indexes in by_key.items():
            unique_indexes = sorted(set(indexes))
            if len(unique_indexes) < 2:
                continue
            pairs = []
            for left, right in itertools.combinations(unique_indexes, 2):
                if same_source_row(rows[left], rows[right]):
                    continue
                if strength == "weak" and group_key.startswith("property:") and not similar_name(rows[left].get("cleaned_display_name", ""), rows[right].get("cleaned_display_name", "")):
                    continue
                pairs.append((left, right))
            if not pairs:
                continue
            summary[f"duplicate_groups_{strength}"] += 1
            summary[f"duplicate_pairs_{strength}"] += len(pairs)
            for left, right in pairs[:max_pairs_per_group]:
                key = tuple(sorted((left, right))) + (strength,)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                candidates.append(candidate_row(rows, left, right, strength, reasons[strength], group_key, len(unique_indexes)))
                summary[f"reported_pairs_{strength}"] += 1

    summary["candidates"] = candidates
    return summary


def build_duplicate_candidates(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return list(duplicate_summary(rows).get("candidates", []))


def duplicate_counts(rows: List[Dict[str, str]]) -> Dict[str, int]:
    summary = duplicate_summary(rows)
    return {
        "strong": int(summary["duplicate_pairs_strong"]),
        "medium": int(summary["duplicate_pairs_medium"]),
        "weak": int(summary["duplicate_pairs_weak"]),
    }
