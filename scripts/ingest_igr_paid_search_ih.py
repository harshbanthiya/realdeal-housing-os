#!/usr/bin/env python3
"""Ingest IGR paid-search XLS exports for Imperial Heights.

Paid search XLS files are UTF-16 HTML tables (not real Excel) with columns:
  srocode | internaldocumentnumber | docno | docname | registrationdate |
  sroname | micrno | bank_type | party_code | sellerparty | purchaserparty |
  propertydescription | areaname | consideration_amt | marketvalue |
  dateofexecution | stampdutypaid | registrationfees | status

706 unique doc numbers for IH across 8 files; 643 not yet in DB.
Financial data (consideration, market value, stamp duty, reg fee) is inline —
no separate Index II needed. No party PAN/address (still need Index II for that).

Usage:
  python scripts/ingest_igr_paid_search_ih.py               # dry-run
  python scripts/ingest_igr_paid_search_ih.py --apply --real-ok
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAID_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots_imperial_heights" / "paidsearch"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql

IH_BLDG_ID = "0e72db71-8b93-4ecd-879c-17d8d8f2b206"
IH_BLDG_SUB = f"'{IH_BLDG_ID}'::uuid"
SOURCE = "igr_paid_search_ih"
PHASE = "6.23d"

IH_RE = re.compile(
    r"imperial\s*heights|इम्पीरियल\s*हाईट्स|इंपीरियल\s*हाईट्स|इम्पिरिय"
    r"|imperial\s*ht|इम्पेरियल|imperial heights",
    re.I
)

# ── Wing detection ─────────────────────────────────────────────────────────────

_ML = {"ए": "A", "बी": "B", "सी": "C", "डी": "D"}

_MARATHI_WING_RE = re.compile(
    r"(?:टॉवर|टोवर|टावर)\s*[-–\s]*(ए|बी|सी|डी)"       # टॉवर ए / टॉवर-बी
    r"|(ए|बी|सी|डी)\s*[-–\s]*(?:टॉवर|टोवर|टावर)"       # ए-टॉवर
    r"|(?:विंग)\s*(ए|बी|सी|डी)"                         # विंग सी
    r"|(ए|बी|सी|डी)\s*[-–\s]*(?:विंग)"                  # डी-विंग
    r"|सदनिका\s*(?:(?:नं|क्रं\.?|क्र\.?)\s*:?\s*)?"    # सदनिका नं/क्रं (optional)
    r"(ए|बी|सी|डी)\s*[-/\s]\s*\d{2,4}"                 #   → सी-3701 or सी 3706
    r"|(ए|बी|सी|डी)\s*[-/\s]\s*\d{2,4}",               # standalone बी-3901 or बी 3901
    re.I
)

_EN_WING_RE = re.compile(
    r"(?:TOWER|WING)\s*[-–]?\s*([ABCD])"               # TOWER A, WING-B, Tower DAddress:
    r"|([ABCD])\s*[-–\s]*(?:TOWER|WING)"               # D WING, A-TOWER, A WINGAddress:
    r"|HEIGHTS\s+([ABCD])\s+(?:CHS|CHSL|CO|TOWER)\b"  # HEIGHTS C CHSL
    r"|(?<!\w)([ABCD])\s*[-/\s]\s*\d{2,4}"            # B-3503, D/2605, B 1304
    r"|\b(\d{2,4})\s*[/-]\s*([ABCD])(?![A-Za-z])",    # 3403/D
    re.I
)


def detect_wing(text: str) -> str | None:
    m = _MARATHI_WING_RE.search(text)
    if m:
        g = next((g for g in m.groups() if g), None)
        if g and g.upper() in _ML:
            return "Wing " + _ML[g.upper()]
    m = _EN_WING_RE.search(text)
    if m:
        # Last group pair is (num, suffix-letter) for "3403/D" — skip the num
        groups = m.groups()
        g = next((g for i, g in enumerate(groups) if g and i != len(groups) - 2), None)
        if g and g.upper() in "ABCD":
            return "Wing " + g.upper()
    return None


def extract_flat(text: str) -> str | None:
    """Pull flat/unit number from property description."""
    # English patterns
    m = re.search(r"Apartment/Flat\s*No:?([A-D]?[-/]?\d{1,4})", text, re.I)
    if m:
        raw = m.group(1).lstrip("ABCDabcd-/").strip()
        if re.match(r"^\d{1,4}$", raw):
            return raw

    # Paid search short format: "B-3503  IMPERIAL..." or "2802,28 वा" → take leading digits
    m = re.search(r"^[,\s]*(?:[ABCDabcdएबीसीडी][-/])?\s*(\d{2,4})", text.strip(), re.I)
    if m:
        return m.group(1)

    # Marathi: "फ्लॅट नं 2802" or "सदनिका नं: 1204" or "सदनिका क्रं. 3701"
    m = re.search(r"(?:फ्लॅट|सदनिका|flat)\s*(?:नं\.?|क्रं\.?|क्र\.?|no\.?|number\.?)?\s*:?\s*(?:[ABCDएबीसीडी][-/])?\s*(\d{2,4})", text, re.I)
    if m:
        return m.group(1)

    # Last resort: first 2-4 digit run
    m = re.search(r"\b(\d{2,4})\b", text)
    return m.group(1) if m else None


# ── HTML XLS parser ────────────────────────────────────────────────────────────

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell, self._in = [], [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
            self._in = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._row.append("".join(self._cell).strip())
            self._in = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = []

    def handle_data(self, data):
        if self._in:
            self._cell.append(data)

    def handle_entityref(self, name):
        if self._in and name == "nbsp":
            self._cell.append(" ")


def parse_xls(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-16", errors="replace")
    p = TableParser()
    p.feed(text)
    if not p.rows:
        return []
    headers = [h.lower().strip() for h in p.rows[0]]
    return [dict(zip(headers, row)) for row in p.rows[1:]]


# ── Field helpers ──────────────────────────────────────────────────────────────

def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"


def parse_money(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"[,\s]", "", str(s))
    try:
        v = float(s)
        return str(int(v)) if v >= 1 else None
    except ValueError:
        return None


def parse_date(s: str | None) -> str | None:
    if not s:
        return None
    # "19/06/2026" or "19-06-2026 00:00:00"
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", str(s))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


_CATEGORY_MAP = {
    "leave and licenses":      "tenancy",
    "leave and license":       "tenancy",
    "36-अ-लिव्ह अॅड लायसन्सेस": "tenancy",
    "agreement relating to deposit of title d": "mortgage",
    "करारनामा":                "agreement_to_sell",
    "सेल डीड":                 "sale",
    "sale deed":               "sale",
    "रिलीज डीड":              "release",
    "बक्षीसपत्र":              "gift",
    "gift":                    "gift",
}


def classify(docname: str) -> tuple[str, str]:
    lower = docname.lower().strip()
    for key, cat in _CATEGORY_MAP.items():
        if key in lower:
            return docname, cat
    return docname, "other"


# ── Main ───────────────────────────────────────────────────────────────────────

def load_existing_docs() -> set[str]:
    _, out = run_psql(
        f"SELECT doc_number FROM unit_registration_records "
        f"WHERE building_id = {IH_BLDG_SUB}"
    )
    return {l.strip() for l in out.strip().splitlines() if l.strip()}


def find_or_create_unit_sql(wing: str, flat: str) -> str:
    return (
        f"(SELECT id FROM building_units "
        f"WHERE building_id = {IH_BLDG_SUB} "
        f"AND wing = {q(wing)} AND unit_number = {q(flat)} LIMIT 1)"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest IGR paid search XLS for Imperial Heights.")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    # Parse all XLS files
    ih_rows: list[dict] = []
    for f in sorted(PAID_ROOT.glob("SearchResult4*.xls")):
        rows = parse_xls(f)
        for r in rows:
            desc = r.get("propertydescription", "") or ""
            if IH_RE.search(desc):
                r["_source_file"] = f.name
                ih_rows.append(r)

    print(f"Total IH rows in paid search: {len(ih_rows)}")

    # Deduplicate by (docno, srocode) — take first occurrence
    seen: dict[str, dict] = {}
    dupes = 0
    for r in ih_rows:
        key = f"{r.get('srocode','')}/{r.get('docno','')}"
        if key not in seen:
            seen[key] = r
        else:
            dupes += 1
    unique_rows = list(seen.values())
    print(f"Unique (srocode/docno): {len(unique_rows)}  (dupes skipped: {dupes})")

    existing_docs = load_existing_docs()
    print(f"Already in DB: {len(existing_docs)}")

    # Classify each row
    new_records: list[dict] = []
    update_records: list[dict] = []
    no_wing: list[dict] = []
    not_ih: list[dict] = []

    wing_counts: dict[str, int] = defaultdict(int)

    for r in unique_rows:
        desc = r.get("propertydescription", "") or ""
        docno = (r.get("docno") or "").strip()
        docname = (r.get("docname") or "").strip()
        _, cat = classify(docname)

        wing = detect_wing(desc)
        flat = extract_flat(desc) if wing else None

        if wing:
            wing_counts[wing] += 1

        rec = {
            "docno": docno,
            "srocode": (r.get("srocode") or "").strip(),
            "sroname": (r.get("sroname") or "").strip(),
            "docname": docname,
            "cat": cat,
            "regdate": parse_date(r.get("registrationdate")),
            "execdate": parse_date(r.get("dateofexecution")),
            "consideration": parse_money(r.get("consideration_amt")),
            "market_value": parse_money(r.get("marketvalue")),
            "stamp": parse_money(r.get("stampdutypaid")),
            "regfee": parse_money(r.get("registrationfees")),
            "desc": desc[:2000],
            "wing": wing,
            "flat": flat,
            "sellers": (r.get("sellerparty") or "").strip(),
            "buyers": (r.get("purchaserparty") or "").strip(),
            "_src": r["_source_file"],
        }

        if docno in existing_docs:
            update_records.append(rec)
        elif wing:
            new_records.append(rec)
        else:
            no_wing.append(rec)

    print(f"\n── Classification ──")
    print(f"  New records (with wing): {len(new_records)}")
    print(f"  Existing to enrich:      {len(update_records)}")
    print(f"  No wing detected:        {len(no_wing)}")
    print(f"\n── Wing breakdown (new) ──")
    for w in ("Wing A", "Wing B", "Wing C", "Wing D"):
        n = sum(1 for r in new_records if r["wing"] == w)
        print(f"  {w}: {n}")
    print(f"\n── No-wing sample (first 10) ──")
    for r in no_wing[:10]:
        print(f"  doc={r['docno']:6}  [{r['docname'][:30]}]  {r['desc'][:100]}")

    if not (args.apply and args.real_ok):
        print("\nDry run — add --apply --real-ok to write.")
        return 0

    # ── Apply ──────────────────────────────────────────────────────────────────
    stmts: list[str] = []

    # 1. Ensure building_units exist for all new wing+flat combos
    units_needed: set[tuple[str, str]] = set()
    for r in new_records:
        if r["wing"] and r["flat"]:
            units_needed.add((r["wing"][-1], r["flat"]))  # e.g. ("A", "2802")

    for wing_letter, flat in sorted(units_needed):
        stmts.append(
            f"INSERT INTO building_units (building_id, wing, unit_number, canonical_status) "
            f"VALUES ({IH_BLDG_SUB}, {q(wing_letter)}, {q(flat)}, 'active') "
            f"ON CONFLICT DO NOTHING;"
        )

    # 2. Insert new records
    for r in new_records:
        wing_letter = r["wing"][-1] if r["wing"] else None
        unit_sub = (
            find_or_create_unit_sql(wing_letter, r["flat"])
            if wing_letter and r["flat"] else "NULL"
        )
        raw_ctx = f"{{\"source\":\"{SOURCE}\",\"phase\":\"{PHASE}\",\"file\":\"{r['_src']}\"}}"
        stmts.append(
            f"INSERT INTO unit_registration_records "
            f"(building_id, building_unit_id, doc_number, registration_year, registration_date, "
            f"sro_office, document_type, transaction_category, property_description_raw, "
            f"wing_text, unit_text, "
            f"consideration_amount, market_value, stamp_duty, registration_fee, "
            f"parse_confidence, verification_status, source_label, raw_context) "
            f"VALUES ("
            f"{IH_BLDG_SUB}, {unit_sub}, {q(r['docno'])}, "
            f"{'NULL' if not r['regdate'] else r['regdate'][:4]}, "
            f"{q(r['regdate'])}, {q(r['sroname'])}, "
            f"{q(r['docname'])}, {q(r['cat'])}, {q(r['desc'])}, "
            f"{q(r['wing'])}, {q(r['flat'])}, "
            f"{q(r['consideration'])}, {q(r['market_value'])}, "
            f"{q(r['stamp'])}, {q(r['regfee'])}, "
            f"0.75, 'parsed_candidate', {q(SOURCE)}, '{raw_ctx}'::jsonb) "
            f"ON CONFLICT DO NOTHING;"
        )
        # Review item
        rec_sub = (
            f"(SELECT id FROM unit_registration_records "
            f"WHERE building_id={IH_BLDG_SUB} AND doc_number={q(r['docno'])} LIMIT 1)"
        )
        wing_label = r["wing"] or "unknown"
        stmts.append(
            f"INSERT INTO unit_registration_review_items "
            f"(building_id, unit_registration_record_id, review_type, status, priority, decision_notes, raw_context) "
            f"VALUES ({IH_BLDG_SUB}, {rec_sub}, 'registration_record_review', 'pending', 'normal', "
            f"'Paid search ingest ({wing_label}); verify parties, financials.', '{raw_ctx}'::jsonb) "
            f"ON CONFLICT DO NOTHING;"
        )

    # 3. Enrich existing records with financial data
    for r in update_records:
        if not any([r["consideration"], r["market_value"], r["stamp"], r["regfee"]]):
            continue
        stmts.append(
            f"UPDATE unit_registration_records SET "
            f"consideration_amount = COALESCE(consideration_amount, {q(r['consideration'])}), "
            f"market_value = COALESCE(market_value, {q(r['market_value'])}), "
            f"stamp_duty = COALESCE(stamp_duty, {q(r['stamp'])}), "
            f"registration_fee = COALESCE(registration_fee, {q(r['regfee'])}), "
            f"updated_at = now() "
            f"WHERE building_id = {IH_BLDG_SUB} AND doc_number = {q(r['docno'])};"
        )

    # Execute in one transaction
    sql = "BEGIN;\n" + "\n".join(stmts) + "\nCOMMIT;"
    code, out = run_psql(sql)
    if code != 0:
        print(f"ERROR:\n{out}")
        return 1

    # Counts
    _, craw = run_psql(
        f"SELECT count(*) FROM unit_registration_records WHERE building_id={IH_BLDG_SUB}; "
        f"SELECT count(*) FROM unit_registration_records "
        f"WHERE building_id={IH_BLDG_SUB} AND building_unit_id IS NOT NULL; "
        f"SELECT count(*) FROM building_units WHERE building_id={IH_BLDG_SUB};"
    )
    lines = [l.strip() for l in craw.strip().splitlines() if l.strip()]
    records_total = lines[0] if lines else "?"
    linked = lines[1] if len(lines) > 1 else "?"
    units = lines[2] if len(lines) > 2 else "?"
    print(f"\nDone. IH records={records_total}  linked={linked}  building_units={units}")
    print(f"Inserted {len(new_records)} new  |  enriched up to {len(update_records)} existing  |  {len(no_wing)} no-wing skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
