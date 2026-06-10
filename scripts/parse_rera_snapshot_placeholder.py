#!/usr/bin/env python3
"""Phase 6.10 RERA snapshot parser PLACEHOLDER (prototype only). No DB, no trusted facts.

Reads a snapshot folder produced by fetch_rera_page_playwright.py (visible_text.txt /
page.html if present) and prints only coarse, NON-personal signals to gauge whether the
page rendered enough to parse later: how many RERA registration-number-like tokens were
detected, whether a project-name label is present, and a rough carpet-table row estimate.

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
# Generic carpet-area row signal: a "Carpet Area" mention or sqm/sqmtr unit occurrences.
CARPET_HINT_RE = re.compile(r"carpet\s*area", re.IGNORECASE)
SQM_RE = re.compile(r"\b\d{2,4}\.\d{1,2}\s*(sq\.?\s*m|sqm|sq\.?mtr)", re.IGNORECASE)
PROJECT_NAME_HINT_RE = re.compile(r"project\s*name", re.IGNORECASE)


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

    text, source_used = load_text(folder)
    if not text:
        print(f"snapshot_source=(none found)  parsing_status=prototype_only")
        print("No visible_text.txt or page.html present (capture may have been blocked). Nothing to parse.")
        return 0

    reg_count = len(set(REG_RE.findall(text)))
    project_name_present = bool(PROJECT_NAME_HINT_RE.search(text))
    carpet_label_present = bool(CARPET_HINT_RE.search(text))
    carpet_row_estimate = len(SQM_RE.findall(text))

    # Counts / booleans ONLY — never the matched values, never personal names.
    print(f"snapshot_source={source_used}")
    print(f"detected_registration_number_count={reg_count}")
    print(f"project_name_label_present={project_name_present}")
    print(f"carpet_area_label_present={carpet_label_present}")
    print(f"carpet_table_row_estimate={carpet_row_estimate}")
    print("parsing_status=prototype_only")
    print("note: counts only; no trusted facts generated; no DB writes; no personal names; no values printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
