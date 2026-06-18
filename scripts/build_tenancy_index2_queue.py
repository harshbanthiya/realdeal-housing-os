#!/usr/bin/env python3
"""Phase 6.28 — ALL Kalpataru Radiance flats with tenancy (Leave & License) -> Index II queue.

Generalises build_bwing_tenancy_index2_queue.py to every wing (A/B/C/D, E=shops) and, by default,
every year (use --recent for the last 2 years only). Reads the operator's IGR eSearch ".xls" result
exports, keeps the tenancy (Leave & License) rows on Kalpataru Radiance (CTS 260/5A), assigns each to
a wing (society name -> flat prefix -> 'wing X' text), cleans flat/floor, mines inline rent/period
where the result row is Marathi-formatted, and emits a per-wing Index II doc-search queue.

BHK / PAN / carpet area / licence period for English-formatted rows come from Index II (the queue).
Output (git-ignored exports/igr_tenancy/): tenancy_index2_queue.csv + TENANCY_SHORTLIST.md.
NO scrape / IGR / external call — local files only. Requires: indic-transliteration (via helpers).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent
OUT_DIR = PROJECT_ROOT / "exports" / "igr_tenancy"

from parse_igr_xls_exports import load, tcells, classify  # noqa: E402
from parse_igr_results_to_staging import parse_property as lprop, classify_doctype, detect_wing  # noqa: E402
from build_bwing_tenancy_index2_queue import (  # noqa: E402
    clean_floor, parse_inline_terms, iso, add_months, COLS, DISTRICT, REG_TYPE, REG_TYPE_FALLBACK,
)

RECENT_YEARS = {"2024", "2025", "2026"}
TOWER_OF = {"Wing A-Ora": "A", "Wing B-Brilliance": "B", "Wing C-Allura": "C", "Wing D-Lumina": "D"}


# Tower-name variants (English + Marathi), checked BEFORE flat prefix (the most reliable signal).
TOWER_WORDS = {
    "A": ("ora", "ओरा", "ऑरा"),
    "B": ("brilliance", "brillance", "ब्रिलिय", "ब्रिल्ली", "ब्रिलीय", "ब्रीलीय", "ब्रिलिअ", "ब्रीलिअ"),
    "C": ("allura", "allure", "alora", "ellora", "elura", "अल्ल", "अलोर", "एल्लूर", "एल्लोर", "एल्लुर", "एलुर"),
    "D": ("lumina", "lumIna", "ल्युमिन", "लुमिन", "लुमीन", "लूमिन", "ल्युमीन"),
}


def detect_letter(desc: str) -> str:
    """Wing for a Kalpataru tenancy row: A/B/C/D tower, E=shops, PATRA=MHADA rehab, '?' unknown.

    Priority: Patra/shops markers -> tower NAME (most reliable) -> flat prefix letter -> 'wing/tower X'."""
    low = desc.lower()
    if "patra chawl" in low or "पत्रा चाळ" in desc or re.search(r"b(?:l)?dg\s*no\s*1|building no 1[a-d]?\s*wing", low):
        return "PATRA"
    if re.search(r"शॉप|shop no\s*[0-9]|दुकान", desc, re.I) and not re.search(r"flat no:\s*[a-e0-9]", low):
        return "E"
    # tower name
    for letter, words in TOWER_WORDS.items():
        if any(w in low or w in desc for w in words):
            return letter
    w = detect_wing(desc)
    if w in TOWER_OF:
        return TOWER_OF[w]
    # English tower/wing — tolerate print-to-PDF field concatenation ("Tower DAddress", "C WingAddress")
    m = (re.search(r"Tower\s*[-:]?\s*([A-E])(?![a-z])", desc) or
         re.search(r"Radiance\s+([A-E])(?![a-z])", desc) or
         re.search(r"\b([A-E])\s*Wing", desc) or
         re.search(r"Flat No:\s*([A-Ea-e])[-/\s]?\d", desc, re.I) or
         re.search(r"\b\d+\s*/\s*([A-E])\b", desc))
    if m:
        return m.group(1).upper()
    # flat prefix: C/134, B-306 ; Marathi सि/सी/बी/डी/ए prefix
    flat = lprop(desc).get("flat") or ""
    m = re.match(r"\s*([A-Ea-e])[-/\s]?\d", flat)
    if m:
        return m.group(1).upper()
    DEV_LETTER = {"ए": "A", "बी": "B", "सी": "C", "सि": "C", "डी": "D"}
    m = re.search(r"(ए|बी|सी|सि|डी)\s*[-–]?\s*(?:विंग|टॉवर|\d)", desc) or \
        re.search(r"(?:विंग|टॉवर|प्रोजेकट|प्रोजेक्ट)\s*[-–]?\s*(ए|बी|सी|सि|डी)", desc)
    if m:
        return DEV_LETTER.get(m.group(1), "?")
    m = re.search(r"\b([A-E])[-\s]?wing\b|\bwing\s*[-:]?\s*([A-E])\b|\btower\s*[-:]?\s*([A-E])\b", desc, re.I)
    if m:
        return (m.group(1) or m.group(2) or m.group(3)).upper()
    return "?"


def clean_flat(desc: str, letter: str) -> str | None:
    m = re.search(r"Flat No:\s*(.*?)\s*(?:Shop No:|Floor No:|,|$)", desc, re.I)
    raw = m.group(1) if m else None
    if not raw:
        m = re.search(r"सदनिका\s*(?:क्रं|क्र|नं)\.?\s*([0-9][0-9A-Za-z\-/ ]*)", desc)
        raw = m.group(1) if m else None
    if not raw:
        raw = lprop(desc).get("flat")
    if not raw:
        return None
    raw = re.sub(r"\b([A-E][-\s]?wing|wing\s*[A-E]|tower\s*[A-E]|Brilliance|Ora|Allura|Lumina)\b", "", raw, flags=re.I)
    num = re.search(r"([0-9][0-9A-Za-z]*)", raw)
    if not num:
        return None
    return f"{letter}-{num.group(1)}" if letter != "?" else num.group(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="All Kalpataru tenancy -> Index II doc-search queue (read-only).")
    ap.add_argument("--xls-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--glob", default="SearchResult*.xls")
    ap.add_argument("--recent", action="store_true", help="last 2 years only (default: all years)")
    ap.add_argument("--wing", default="all", help="A|B|C|D|E|all (default all)")
    args = ap.parse_args()

    files = sorted(Path(args.xls_dir).glob(args.glob))
    if not files:
        print(f"No files matching {args.glob} in {args.xls_dir}")
        return 1

    seen: set = set()
    rows: list[dict] = []
    for f in files:
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", load(f), re.S)
        if len(trs) < 2:
            continue
        hdr = [h.lower() for h in tcells(trs[0])]
        H = {h: i for i, h in enumerate(hdr)}
        if "propertydescription" not in H or "docno" not in H:
            continue
        get = lambda c, k: c[H[k]] if k in H and H[k] < len(c) else ""
        for r in trs[1:]:
            c = tcells(r)
            if len(c) <= H["propertydescription"]:
                continue
            uid = get(c, "internaldocumentnumber") or f"{get(c,'srocode')}|{get(c,'docno')}|{get(c,'registrationdate')[-4:]}"
            if uid in seen:
                continue
            seen.add(uid)
            rec = {k: get(c, k) for k in COLS}
            yr = rec["registrationdate"][-4:]
            _et, cat = classify_doctype(rec["docname"])
            if cat != "tenancy" or classify(rec["propertydescription"]) != "kalpataru":
                continue
            if args.recent and yr not in RECENT_YEARS:
                continue
            rec["_letter"] = detect_letter(rec["propertydescription"])
            if args.wing != "all" and rec["_letter"] != args.wing.upper():
                continue
            rows.append(rec)

    out_rows: list[dict] = []
    flat_counts: dict[str, int] = {}
    for r in rows:
        fk = clean_flat(r["propertydescription"], r["_letter"])
        if fk:
            flat_counts[fk] = flat_counts.get(fk, 0) + 1
    WING_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "?": 9}
    for r in sorted(rows, key=lambda x: (WING_ORDER.get(x["_letter"], 9), x["registrationdate"][-4:], x["docno"])):
        desc = r["propertydescription"]
        letter = r["_letter"]
        flat = clean_flat(desc, letter)
        floor = clean_floor(desc)
        unit_digits = re.sub(r"\D", "", flat or "")
        derived_floor = str(int(unit_digits) // 10) if unit_digits and len(unit_digits) >= 2 else ""
        flat_floor_ok = "yes" if (derived_floor and floor and derived_floor == floor) else (
            "verify" if (floor and derived_floor) else "")
        rdate = iso(r["registrationdate"])
        edate = iso(r["dateofexecution"]) or rdate
        terms = parse_inline_terms(desc)
        expiry = add_months(edate, terms["tenure_months"]) if (edate and terms["tenure_months"]) else None
        active = (expiry >= date.today().isoformat()) if expiry else None
        out_rows.append({
            "wing": letter,
            "apartment_key": flat or "",
            "unit_number": re.sub(r"^[A-E]-", "", flat or ""),
            "floor": floor or "",
            "flat_floor_check": flat_floor_ok,
            "relet_count": flat_counts.get(flat or "", 1),
            "category": "tenancy",
            "document_type": "leave_and_license",
            "doc_number": r["docno"],
            "registration_year": r["registrationdate"][-4:],
            "registration_date": rdate or "",
            "date_of_execution": edate or "",
            "district": DISTRICT,
            "sro_code": r["srocode"],
            "sro_office": r["sroname"],
            "registration_type_primary": REG_TYPE,
            "registration_type_fallback": REG_TYPE_FALLBACK,
            "inline_monthly_rent": terms["rent"] or "",
            "inline_deposit": terms["deposit"] or (r["consideration_amt"] or ""),
            "inline_tenure_months": terms["tenure_months"] or "",
            "lease_expiry_est": expiry or "",
            "lease_active_est": "" if active is None else ("yes" if active else "expired"),
            "has_index22_pdf": False,
            "search_instruction": (
                f"Doc Search -> {REG_TYPE}; District {DISTRICT}; SRO {r['sroname']} (code {r['srocode']}); "
                f"Year {r['registrationdate'][-4:]}; Doc.No. {r['docno']}; solve CAPTCHA; open IndexII "
                f"(read PAN, monthly rent, licence period, carpet area)."),
            "property_description_raw": re.sub(r"\s+", " ", desc).strip(),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "tenancy_index2_queue.csv"
    fields = list(out_rows[0].keys()) if out_rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    from collections import Counter
    by_wing = Counter(o["wing"] for o in out_rows)
    by_year = Counter(o["registration_year"] for o in out_rows)
    active_n = sum(1 for o in out_rows if o["lease_active_est"] == "yes")
    span = "last 2 years" if args.recent else "all years"
    md = [f"# Kalpataru Radiance — ALL flats with tenancy (Leave & License, {span})", "",
          f"Source: {len(files)} IGR .xls exports · {len(out_rows)} tenancy registrations · CTS 260/5A, Goregaon West.",
          "", f"By wing: {dict(sorted(by_wing.items()))} · by year: {dict(sorted(by_year.items()))}",
          "", "Rent/term shown are inline from Marathi-formatted rows; PAN / carpet area / licence period for "
          "English rows come from **Index II** (queue CSV).", "",
          "| Wing | Flat | Floor | Doc / Year | Reg date | SRO | Re-let | Inline rent | Term | Est. expiry | Active? |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for o in out_rows:
        md.append(f"| {o['wing']} | {o['apartment_key']} | {o['floor']} | {o['doc_number']}/{o['registration_year']} | "
                  f"{o['registration_date']} | {o['sro_code']} | "
                  f"{('×'+str(o['relet_count'])) if o['relet_count'] > 1 else '—'} | "
                  f"{('₹'+format(int(o['inline_monthly_rent']),',')) if o['inline_monthly_rent'] else '—'} | "
                  f"{(str(o['inline_tenure_months'])+'mo') if o['inline_tenure_months'] else '—'} | "
                  f"{o['lease_expiry_est'] or '—'} | {o['lease_active_est'] or '—'} |")
    (OUT_DIR / "TENANCY_SHORTLIST.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Parsed {len(files)} files -> {len(seen)} unique rows -> {len(out_rows)} Kalpataru tenancy ({span}).")
    print(f"  by wing: {dict(sorted(by_wing.items()))}")
    print(f"  by year: {dict(sorted(by_year.items()))}")
    print(f"  inline rent/term present: {sum(1 for o in out_rows if o['inline_monthly_rent'] or o['inline_tenure_months'])}"
          f"   est. still ACTIVE: {active_n}")
    print(f"\nCSV:       {csv_path}")
    print(f"Shortlist: {OUT_DIR / 'TENANCY_SHORTLIST.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
