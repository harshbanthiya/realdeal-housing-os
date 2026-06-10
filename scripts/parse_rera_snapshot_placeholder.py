#!/usr/bin/env python3
"""Phase 6.11 RERA snapshot parser PLACEHOLDER (prototype only). No DB, no trusted facts.

Reads a snapshot folder produced by fetch_rera_page_playwright.py (visible_text.txt /
page.html and any saved response_body_* files) and prints only coarse, NON-personal
signals to gauge whether the page rendered enough to parse later — e.g. how many RERA
registration-number-like tokens were detected, whether section labels are present, and
whether the snapshot was captured behind an external-warning/CAPTCHA gate.

It does NOT insert into the database, does NOT generate trusted facts, does NOT update any
RERA table, and does NOT print personal names or page contents. parsing_status is always
'prototype_only'. This is a feasibility stub, not a real parser.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# MahaRERA project registration numbers look like P + 11 digits (e.g. P51800003270).
REG_RE = re.compile(r"\bP\d{11}\b")

# Section/label signals — presence booleans only (never the surrounding values/names).
PROJECT_NAME_HINT_RE = re.compile(r"project\s*name", re.IGNORECASE)
CARPET_HINT_RE = re.compile(r"carpet\s*area", re.IGNORECASE)
PROMOTER_HINT_RE = re.compile(r"promoter", re.IGNORECASE)
COMPLAINT_HINT_RE = re.compile(r"complaint", re.IGNORECASE)
LITIGATION_HINT_RE = re.compile(r"litigation|court\s*case|legal\s*case", re.IGNORECASE)
CAPTCHA_HINT_RE = re.compile(r"captcha|enter the characters|i'?m not a robot", re.IGNORECASE)
EXTERNAL_WARNING_HINT_RE = re.compile(
    r"external website|about to proceed|click yes to proceed", re.IGNORECASE)


def load_text(folder: Path) -> tuple[str, str]:
    """Return (text, source_used) from visible_text.txt or page.html, whichever exists."""
    vt = folder / "visible_text.txt"
    html = folder / "page.html"
    if vt.exists():
        return vt.read_text(encoding="utf-8", errors="replace"), "visible_text.txt"
    if html.exists():
        raw = html.read_text(encoding="utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", raw), "page.html"
    return "", "(none)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prototype RERA snapshot parser. No DB writes.")
    parser.add_argument("--snapshot-folder", required=True)
    args = parser.parse_args()

    folder = Path(args.snapshot_folder)
    if not folder.is_dir():
        print(f"Refusing: snapshot folder not found: {folder}")
        return 1

    candidate_json_files = sorted(folder.glob("response_body_*.json"))
    text, source_used = load_text(folder)

    if not text:
        print(f"snapshot_source=(none found)  parsing_status=prototype_only")
        print(f"candidate_json_files_count={len(candidate_json_files)}")
        print("No visible_text.txt or page.html present (capture may have been gated/blocked). "
              "Nothing to parse.")
        return 0

    reg_count = len(set(REG_RE.findall(text)))

    # Counts / booleans ONLY — never the matched values, never personal names.
    print(f"snapshot_source={source_used}")
    print(f"registration_number_token_count={reg_count}")
    print(f"project_name_label_present={bool(PROJECT_NAME_HINT_RE.search(text))}")
    print(f"carpet_area_label_present={bool(CARPET_HINT_RE.search(text))}")
    print(f"promoter_label_present={bool(PROMOTER_HINT_RE.search(text))}")
    print(f"complaint_section_present={bool(COMPLAINT_HINT_RE.search(text))}")
    print(f"litigation_section_present={bool(LITIGATION_HINT_RE.search(text))}")
    print(f"captcha_detected_in_snapshot={bool(CAPTCHA_HINT_RE.search(text))}")
    print(f"external_warning_detected_in_snapshot={bool(EXTERNAL_WARNING_HINT_RE.search(text))}")
    print(f"candidate_json_files_count={len(candidate_json_files)}")
    print("parsing_status=prototype_only")
    print("note: counts/booleans only; no trusted facts generated; no DB writes; "
          "no personal names; no page text printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
