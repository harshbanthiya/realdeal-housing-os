#!/usr/bin/env python3
"""Ingest the Ekta Tripolis CTS-22A sweep captures → unit_registration_records/_parties.

Reads capture_*_r*.txt from exports/igr_cts_sweep/*/ (produced by fetch_igr_cts_sweep.py).
Three document layouts appear in one sweep and all three are handled:

  A. Devanagari "सूची क्र.2"  (दस्त क्रमांक, numbered fields (1)-(14))   — the bulk
  B. English eSearch Index-2 (Doc No., same field numbering, Latin labels)
  C. Notice-of-Intimation mortgage filings (फाईल क्रमांक, fields (1)-(8), own schema)
     — stored with doc_number 'NOI-<n>' so they cannot collide with real doc numbers.

Unit extraction runs a cascade (combined 'B-2701' forms → tower+flat in the property field →
flat + tower recovered from elsewhere in the doc) and falls back to classifying the row as
commercial/parking/no-unit rather than silently dropping it. Every capture is accounted for in
the coverage report, which reconciles against the total file count.

Tenancy rows get tenancy_start_date / _end_date (start + tenure months) so they surface in
vw_tenancy_expiring_soon. Parties are written with PAN / age / address.

Dry-run by default; --apply --real-ok to write. --revert removes this source's rows.
NO external calls (reads local snapshot .txt only).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql  # noqa: E402
from parse_igr_index2_pdfs import (  # noqa: E402
    split_fields, classify_doctype, translit, parse_parties, parse_property,
    iso, q, jb, clean_frag, num, ROLE_BY_CATEGORY, DEVANAGARI, PAN_RE,
)
from parse_igr_index2_bulk_snapshots import end_date_from_start_and_months  # noqa: E402

SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_cts_sweep"
EKTA_ID = "2032514a-adef-4d2f-a12c-6ecf06853243"
EKTA_SUB = f"'{EKTA_ID}'::uuid"
SOURCE = "igr_cts_sweep_ekta"
PHASE = "6.29"

# 'Skypolis' is the marketing name of Tower C; 'एकटा' is a common misspelling of 'एकता'.
EKTA_RE = re.compile(
    r"tripolis|tripolls|ट्रिपोलि|त्रिपोलि|ट्रायप[ॉो]ल[ीि]|ट्रीपोलि|ट्रिपोली|"
    r"एकता\s*ट्र|एकटा\s*ट्र|skypolis|स्कायपोल", re.I)

DEV_TOWER = {"ए": "A", "बी": "B", "सी": "C", "डी": "D"}
TOWERS = {"A", "B", "C"}  # Ekta Tripolis has three towers

# Cascade step 1 — flat number already carries its tower.
COMBO_PATS = [
    ("combo_en", re.compile(
        r"(?:Apartment\s*/\s*)?Flat\s*No\s*[:.]?\s*([A-D])\s*[-/ ]?\s*(\d{3,4})", re.I), "TF"),
    ("combo_dev", re.compile(
        r"सदनिका\s*(?:/\s*टेनामेंट)?\s*(?:नं|न|क्र|क्रमांक)?\.?\s*[:.]?\s*"
        r"(ए|बी|सी|डी)\s*[-–— ]\s*(\d{3,4})"), "TF"),
    ("combo_dev_rev", re.compile(
        r"सदनिका\s*(?:नं|न|क्र|क्रमांक)?\.?\s*[:.]?\s*(\d{3,4})\s*[-–—]\s*(ए|बी|सी|डी)"), "FT"),
]
# Tower is written a dozen ways across SROs: टॉवर / टाॅवर / टावर / विंग, before or after
# the letter, and in Latin as 'TOWER B' or 'C WING'. All of them, both orders.
TOWER_RE = re.compile(
    r"ट[ाॉो]*वर\s*[:\-]?\s*(ए|बी|सी|डी)|"
    r"(?:TOWER|TWR)\s*[:\-]?\s*([A-D])\b|"
    r"(ए|बी|सी|डी)\s*विंग|"
    r"विंग\s*[:\-]?\s*(ए|बी|सी|डी)|"
    r"WING\s*[:\-]?\s*([A-D])\b|"
    r"\b([A-D])\s*[-, ]?\s*WING\b", re.I)
FLAT_RE = re.compile(
    r"सदनिका\s*(?:/\s*टेनामेंट)?\s*(?:नं|न|क्र|क्रमांक)?\.?\s*[:.]?\s*(\d{3,4})|"
    r"Flat\s*No\s*[:.]?\s*(\d{3,4})|फ्लॅट\s*(?:नं)?\.?\s*[:.]?\s*(\d{3,4})", re.I)
NONRESI_RE = re.compile(
    r"शॉप\s*नं|दुकान\s*नं|Shop\s*No|SHOP\s*\d|ऑफिस\s*नं|Office\s*No|"
    r"पार्किंग|parking|टेनमेंट", re.I)

# NOI (format C) — Latin-labelled, own field numbering.
NOI_PARTY_RE = re.compile(
    r"Name\s*:\s*(.+?)\s+Age\s*:\s*(\d+)\s*,?\s*Address\s*:\s*(.+?)\s*,?\s*PAN\s*:\s*"
    r"([A-Z]{5}\d{4}[A-Z])", re.S)
EN_PARTY_RE = re.compile(
    r"Name\s*:\s*(.+?)\s+Age\s*:\s*(\d+)\s*,?\s*Address\s*:\s*(.+?)\s*,?\s*PAN\s*:\s*"
    r"([A-Z]{5}\d{4}[A-Z])", re.S)

COMPANY_RE = re.compile(
    r"llp|ltd|limited|private|pvt|bank|builder|developer|authority|realty|infra|"
    r"एलएलपी|लिमिटेड|बँक|प्रा|मेसर्स|डेव्हलपर", re.I)


# ── unit extraction ───────────────────────────────────────────────────────────

def extract_unit(prop: str, full_text: str) -> tuple[str | None, str | None, str]:
    """Return (tower, flat, how). `how` names the cascade step for the coverage report."""
    for name, rx, order in COMBO_PATS:
        m = rx.search(prop)
        if m:
            a, b = (m.group(1), m.group(2)) if order == "TF" else (m.group(2), m.group(1))
            t = DEV_TOWER.get(a, a).upper()
            if t in TOWERS:
                return t, b, name

    def _tower(s: str) -> str | None:
        m = TOWER_RE.search(s)
        if not m:
            return None
        g = next((x for x in m.groups() if x), None)
        t = DEV_TOWER.get(g, (g or "")).upper()
        return t if t in TOWERS else None

    def _flat(s: str) -> str | None:
        m = FLAT_RE.search(s)
        return next((x for x in m.groups() if x), None) if m else None

    t, f = _tower(prop), _flat(prop)
    if t and f:
        return t, f, "tower+flat"
    if f:
        # Tower is often only in the party address block ("टॉवर ए, एकता ट्रायपॉलीस").
        t2 = _tower(full_text)
        if t2:
            return t2, f, "flat+tower_from_doc"
        return None, f, "flat_only"
    if NONRESI_RE.search(prop):
        return None, None, "commercial_or_parking"
    if t:
        return t, None, "tower_only"
    return None, None, "no_unit"


# ── per-format parsers ────────────────────────────────────────────────────────

def parse_noi(text: str, fname: str) -> dict | None:
    """Format C — Notice of intimation of mortgage. Encumbrance, not a transfer."""
    m = re.search(r"फाईल क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    if not m:
        return None
    f = split_fields(text)
    prop = clean_frag(f.get(3, ""))
    loan = num(f.get(2, ""))
    dm = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(7, ""))
    tower, flat, how = extract_unit(prop, text)
    parties = [{"name": n.strip()[:200], "age": a, "address": ad.strip()[:400], "pan": p}
               for n, a, ad, p in NOI_PARTY_RE.findall(f.get(5, ""))]
    bank = re.search(r"Bank Name\s*:\s*(.+?)(?:Address|$)", f.get(6, ""), re.S)
    return {
        "fmt": "noi", "file": fname, "doc_no": f"NOI-{m.group(1)}", "year": m.group(2),
        "etype": "notice_of_intimation", "cat": "encumbrance",
        "consideration": None, "market_value": loan, "stamp": None, "regfee": None,
        "rent": None, "deposit": None, "start": None, "end": None, "tenure": None,
        "date_reg": iso(dm.group(1)) if dm else None,
        "sro": (re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text).group(1).strip()[:120]
                if re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text) else None),
        "area": clean_frag(f.get(4, ""))[:60], "prop_raw": prop[:1200],
        "tower": tower, "flat": flat, "unit_how": how, "floor": None,
        # Explicit roles: the flat owner borrows (mortgagor), the bank lends (mortgagee).
        # ROLE_BY_CATEGORY['encumbrance'] maps sellers→mortgagee, which is backwards here.
        "roles": ("mortgagor", "mortgagee"),
        "sellers": parties,
        "purchasers": ([{"name": bank.group(1).strip()[:200], "age": None,
                         "address": None, "pan": None}] if bank else []),
    }


def english_tenure_months(text: str, f: dict) -> str | None:
    """L&L tenure. Either stated outright, or implied by the rent schedule
    ('Rs.X for the first 12 months, b) Rs.Y for the next 12 months' = 24)."""
    m = re.search(r"Leave and License Months\s*[:.]?\s*(\d+)", text)
    if m:
        return m.group(1)
    steps = re.findall(r"for the (?:first|next|last|remaining)\s*(\d{1,3})\s*months?",
                       f.get(3, ""), re.I)
    return str(sum(int(s) for s in steps)) if steps else None


def parse_english(text: str, fname: str) -> dict | None:
    """Format B — English eSearch Index-2 (eRegistration). Field numbering differs from
    the Devanagari layout: (2) Deposit, (3) Rent schedule, (4) Property Description."""
    m = re.search(r"Doc No\.?\s*[:.]?\s*(\d+)\s*/\s*(\d{4})", text)
    if not m:
        return None
    f = split_fields(text)
    prop = clean_frag(f.get(4, ""))
    art = clean_frag(f.get(1, ""))[:80]
    etype, cat = classify_doctype(art)
    tenure = english_tenure_months(text, f)
    if tenure or re.search(r"leave and licen", art, re.I):
        cat, etype = "tenancy", "leave_and_license"
    dep = re.search(r"Rs\.?\s*([\d,]+)", f.get(2, ""))
    rent = re.search(r"Rs\.?\s*([\d,]+)", f.get(3, ""))
    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    dr = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(10, ""))
    d_exec = iso(de.group(1)) if de else None
    tower, flat, how = extract_unit(prop, text)
    parties = {7: [], 8: []}
    for n in (7, 8):
        for nm, age, addr, pan in EN_PARTY_RE.findall(f.get(n, "")):
            parties[n].append({"name": nm.strip()[:200], "age": age,
                               "address": addr.strip()[:400], "pan": pan})
    return {
        "fmt": "english", "file": fname, "doc_no": m.group(1), "year": m.group(2),
        "etype": etype, "cat": cat,
        "consideration": None if cat == "tenancy" else num(f.get(2, "")),
        "market_value": None,
        "stamp": num(f.get(12, "")), "regfee": num(f.get(13, "")),
        "rent": rent.group(1).replace(",", "") if rent else None,
        "deposit": dep.group(1).replace(",", "") if dep else None,
        "start": d_exec if cat == "tenancy" else None,
        "end": end_date_from_start_and_months(d_exec, tenure),
        "tenure": tenure,
        "date_reg": (iso(dr.group(1)) if dr else None) or d_exec,
        "sro": (re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text).group(1).strip()[:120]
                if re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text) else None),
        "area": clean_frag(f.get(5, ""))[:60], "prop_raw": prop[:1200],
        "tower": tower, "flat": flat, "unit_how": how, "floor": None,
        "sellers": parties[7], "purchasers": parties[8],
    }


def parse_devanagari(text: str, fname: str) -> dict | None:
    """Format A — Devanagari सूची क्र.2."""
    m = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    if not m:
        return None
    f = split_fields(text)
    prop_raw = f.get(4, "")
    prop = clean_frag(prop_raw)
    dtype_raw = " ".join(clean_frag(f.get(1, "")).split()[:6])[:60]
    etype, cat = classify_doctype(dtype_raw)
    p = parse_property(prop_raw)
    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    dr = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(10, ""))
    d_exec = iso(de.group(1)) if de else None
    tower, flat, how = extract_unit(prop, text)
    if not flat and p["flat"] and re.fullmatch(r"\d{3,4}", p["flat"]) \
            and not NONRESI_RE.search(prop):
        # legacy fallback, but never for 'शॉप क्र 13' — a shop is not flat 13
        flat, how = p["flat"], "flat_from_legacy_parser"
    sro = re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text)
    return {
        "fmt": "devanagari", "file": fname, "doc_no": m.group(1), "year": m.group(2),
        "etype": etype, "cat": cat,
        "consideration": num(f.get(2, "")), "market_value": num(f.get(3, "")),
        "stamp": num(f.get(12, "")), "regfee": num(f.get(13, "")),
        "rent": p["rent"] if cat == "tenancy" else None,
        "deposit": p["deposit"] if cat == "tenancy" else None,
        "start": d_exec if cat == "tenancy" else None,
        "end": (end_date_from_start_and_months(d_exec, p["tenure_months"])
                if cat == "tenancy" else None),
        "tenure": p["tenure_months"],
        "date_reg": (iso(dr.group(1)) if dr else None) or d_exec,
        "sro": sro.group(1).strip()[:120] if sro else None,
        "area": clean_frag(f.get(5, ""))[:60], "prop_raw": prop[:1200],
        "tower": tower, "flat": flat, "unit_how": how, "floor": p["floor"],
        "sellers": parse_parties(f.get(7, "")), "purchasers": parse_parties(f.get(8, "")),
    }


def parse_capture(path: Path) -> dict:
    """Always returns a dict — an unparseable capture is reported, never dropped."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if "फाईल क्रमांक" in text:
        r = parse_noi(text, path.name)
    elif "दस्त क्रमांक" in text:
        r = parse_devanagari(text, path.name)
    elif re.search(r"Doc No", text):
        r = parse_english(text, path.name)
    else:
        r = None
    if r is None:
        return {"fmt": "unparsed", "file": path.name, "doc_no": None, "year": None}
    r["is_ekta"] = bool(EKTA_RE.search(text))
    return r


def resolve_towers_from_db(rows: list[dict]) -> int:
    """Last cascade step: a doc that names a flat but no tower may already be linked to a
    unit by an earlier ingest. Adopt that wing — but only when the flat numbers agree, so a
    mis-keyed older row cannot drag the sweep off target. Flat numbers repeat across all
    three towers here, so this is the only safe inference left."""
    gap = [r for r in rows if r.get("flat") and not r.get("tower")]
    if not gap:
        return 0
    keys = ",".join(f"({q(r['doc_no'])},{r['year']})" for r in gap)
    code, out = run_psql(
        f"SELECT r.doc_number, r.registration_year, bu.wing, bu.unit_number "
        f"FROM unit_registration_records r "
        f"JOIN building_units bu ON bu.id = r.building_unit_id "
        f"WHERE r.building_id={EKTA_SUB} AND (r.doc_number, r.registration_year) IN ({keys});")
    if code != 0:
        return 0
    known: dict[tuple[str, str], tuple[str, str]] = {}
    for line in out.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4 and parts[2]:
            known[(parts[0], parts[1])] = (parts[2], parts[3])
    n = 0
    for r in gap:
        hit = known.get((r["doc_no"], r["year"]))
        if hit and hit[1] == f"{hit[0]}-{r['flat']}":
            r["tower"], r["unit_how"] = hit[0], "tower_from_existing_link"
            n += 1
    return n


# ── coverage report ───────────────────────────────────────────────────────────

def report(files: list[Path], parsed: list[dict]) -> None:
    n = len(files)
    fmt = Counter(r["fmt"] for r in parsed)
    ekta = [r for r in parsed if r.get("is_ekta")]
    other = [r for r in parsed if r["fmt"] != "unparsed" and not r.get("is_ekta")]
    unparsed = [r for r in parsed if r["fmt"] == "unparsed"]
    how = Counter(r["unit_how"] for r in ekta)
    with_unit = sum(1 for r in ekta if r["tower"] and r["flat"])
    pan = sum(1 for r in ekta for p in r["sellers"] + r["purchasers"] if p.get("pan"))
    parties = sum(len(r["sellers"]) + len(r["purchasers"]) for r in ekta)
    ten = [r for r in ekta if r["cat"] == "tenancy"]
    ten_end = sum(1 for r in ten if r["end"])
    money = sum(1 for r in ekta if r["consideration"] or r["market_value"])
    docs = {(r["doc_no"], r["year"]) for r in ekta}

    def pct(a, b):
        return f"{a:4d}/{b:<4d} {100*a/b if b else 0:5.1f}%"

    print(f"\n{'═'*66}\nCOVERAGE — every capture accounted for\n{'═'*66}")
    print(f"  Index II .txt captures on disk        {n}")
    print(f"    parsed by layout                    " + "  ".join(
        f"{k}={v}" for k, v in fmt.most_common()))
    print(f"    → Ekta Tripolis                     {pct(len(ekta), n)}")
    print(f"    → other building on same CTS        {len(other):4d}   (skipped, not written)")
    print(f"    → unparseable                       {len(unparsed):4d}")
    assert len(ekta) + len(other) + len(unparsed) == n, "capture accounting does not reconcile"
    print(f"  unique (doc_no, year) among Ekta      {len(docs)}  "
          f"({len(ekta) - len(docs)} duplicate captures collapse)")
    print(f"\n  Ekta extraction quality (of {len(ekta)}):")
    print(f"    tower + flat resolved               {pct(with_unit, len(ekta))}")
    for k, v in how.most_common():
        print(f"        via {k:<24s}    {v:4d}")
    print(f"    price/value present                 {pct(money, len(ekta))}")
    print(f"    parties extracted                   {parties}  (with PAN: {pan})")
    print(f"    tenancy rows                        {len(ten)}")
    print(f"    tenancy with computable end date    {pct(ten_end, len(ten)) if ten else 'n/a'}")
    if unparsed:
        print("\n  UNPARSED (inspect these by hand):")
        for r in unparsed:
            print(f"    {r['file']}")
    nounit = [r for r in ekta if not (r["tower"] and r["flat"])
              and r["unit_how"] not in ("commercial_or_parking",)]
    if nounit:
        print(f"\n  Ekta rows with no resolvable flat ({len(nounit)}) — "
              f"written without a unit link:")
        for r in nounit[:20]:
            print(f"    {r['doc_no']}/{r['year']}  {r['unit_how']:<22s} {r['file']}")
        if len(nounit) > 20:
            print(f"    … and {len(nounit)-20} more")


# ── DB write ──────────────────────────────────────────────────────────────────

def counts_sql() -> str:
    return (
        f"SELECT 'records_this_source', count(*)::text FROM unit_registration_records"
        f" WHERE raw_context->>'source'='{SOURCE}'\n"
        f"UNION ALL SELECT 'parties_this_source', count(*)::text FROM unit_registration_parties"
        f" WHERE raw_context->>'source'='{SOURCE}'\n"
        f"UNION ALL SELECT 'ekta_records_total', count(*)::text FROM unit_registration_records"
        f" WHERE building_id={EKTA_SUB}\n"
        f"UNION ALL SELECT 'ekta_records_unit_linked', count(*)::text FROM unit_registration_records"
        f" WHERE building_id={EKTA_SUB} AND building_unit_id IS NOT NULL\n"
        f"UNION ALL SELECT 'ekta_parties_with_pan', count(*)::text FROM unit_registration_parties p"
        f" JOIN unit_registration_records r ON r.id=p.unit_registration_record_id"
        f" WHERE r.building_id={EKTA_SUB} AND p.party_pan IS NOT NULL\n"
        f"UNION ALL SELECT 'ekta_tenancy_with_end_date', count(*)::text FROM unit_registration_records"
        f" WHERE building_id={EKTA_SUB} AND transaction_category='tenancy'"
        f" AND tenancy_end_date IS NOT NULL\n"
        f"UNION ALL SELECT 'ekta_in_expiring_view', count(*)::text FROM vw_tenancy_expiring_soon"
        f" WHERE building_name='Ekta Tripolis'\nORDER BY 1;"
    )


def build_sql(rows: list[dict], existing: set[tuple[str, str]]) -> tuple[list[str], int, int]:
    stmts, ins, upd = ["BEGIN;"], 0, 0
    for r in rows:
        unit_no = f"{r['tower']}-{r['flat']}" if r["tower"] and r["flat"] else None
        tag = {"source": SOURCE, "phase": PHASE, "is_fake": False, "src_file": r["file"],
               "layout": r["fmt"], "unit_how": r["unit_how"], "doctype_raw": r["etype"],
               "external_calls_made": False}
        # Create the unit if the registry does not have it yet — the sweep is authoritative
        # on which flats exist, and an unlinked record is a dead end for the operator.
        if unit_no:
            stmts.append(
                "INSERT INTO building_units (building_id, wing, unit_number) "
                f"SELECT {EKTA_SUB}, {q(r['tower'])}, {q(unit_no)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM building_units "
                f"  WHERE building_id={EKTA_SUB} AND unit_number={q(unit_no)});")
            unit_sub = (f"(SELECT id FROM building_units WHERE building_id={EKTA_SUB} "
                        f"AND unit_number={q(unit_no)} ORDER BY created_at LIMIT 1)")
        else:
            unit_sub = "NULL"

        key = (r["doc_no"], r["year"])
        rec = (f"(SELECT id FROM unit_registration_records WHERE building_id={EKTA_SUB} "
               f"AND doc_number={q(r['doc_no'])} AND registration_year={r['year']} "
               f"ORDER BY created_at LIMIT 1)")

        if key in existing:
            stmts.append(
                "UPDATE unit_registration_records SET "
                f"building_unit_id = COALESCE(building_unit_id, {unit_sub}), "
                f"wing_text = COALESCE(wing_text, {q(r['tower'])}), "
                f"unit_text = COALESCE(unit_text, {q(r['flat'])}), "
                f"floor_text = COALESCE(floor_text, {q(r['floor'])}), "
                f"area_text = COALESCE(area_text, {q(r['area'])}), "
                f"sro_office = COALESCE(sro_office, {q(r['sro'])}), "
                f"consideration_amount = COALESCE(consideration_amount, {q(r['consideration'])}), "
                f"market_value = COALESCE(market_value, {q(r['market_value'])}), "
                f"stamp_duty = COALESCE(stamp_duty, {q(r['stamp'])}), "
                f"registration_fee = COALESCE(registration_fee, {q(r['regfee'])}), "
                f"tenancy_monthly_rent = COALESCE(tenancy_monthly_rent, {q(r['rent'])}), "
                f"tenancy_deposit = COALESCE(tenancy_deposit, {q(r['deposit'])}), "
                f"tenancy_start_date = COALESCE(tenancy_start_date, {q(r['start'])}), "
                f"tenancy_end_date = COALESCE(tenancy_end_date, {q(r['end'])}), "
                f"property_description_raw = COALESCE(property_description_raw, {q(r['prop_raw'])}), "
                f"raw_context = raw_context || {jb({'cts_sweep_enriched': True, 'src_file': r['file']})} "
                f"WHERE building_id={EKTA_SUB} AND doc_number={q(r['doc_no'])} "
                f"AND registration_year={r['year']};")
            upd += 1
            order = 300
        else:
            stmts.append(
                "INSERT INTO unit_registration_records "
                "(building_id, building_unit_id, doc_number, registration_year, registration_date, "
                "sro_office, document_type, transaction_category, property_description_raw, "
                "wing_text, unit_text, floor_text, area_text, consideration_amount, market_value, "
                "stamp_duty, registration_fee, tenancy_monthly_rent, tenancy_deposit, "
                "tenancy_start_date, tenancy_end_date, parse_confidence, verification_status, "
                "source_label, raw_context) VALUES ("
                f"{EKTA_SUB}, {unit_sub}, {q(r['doc_no'])}, {r['year']}, {q(r['date_reg'])}, "
                f"{q(r['sro'])}, {q(r['etype'])}, {q(r['cat'])}, {q(r['prop_raw'])}, "
                f"{q(r['tower'])}, {q(r['flat'])}, {q(r['floor'])}, {q(r['area'])}, "
                f"{q(r['consideration'])}, {q(r['market_value'])}, {q(r['stamp'])}, {q(r['regfee'])}, "
                f"{q(r['rent'])}, {q(r['deposit'])}, {q(r['start'])}, {q(r['end'])}, "
                f"0.75, 'parsed_candidate', 'IGR CTS 22A sweep 2019-2026', {jb(tag)});")
            stmts.append(
                "INSERT INTO unit_registration_review_items (building_id, "
                "unit_registration_record_id, review_type, status, priority, decision_notes, raw_context) "
                f"VALUES ({EKTA_SUB}, {rec}, 'registration_record_review', 'pending', 'normal', "
                f"'IGR CTS 22A sweep parse; verify unit link, parties and PAN.', {jb(tag)});")
            ins += 1
            order = 0

        srole, brole = r.get("roles") or ROLE_BY_CATEGORY.get(r["cat"], ("seller", "purchaser"))

        # Backfill PAN onto party rows an earlier ingest left blank. This MUST run before the
        # inserts below: those dedupe on PAN, so a row that is still PAN-less at insert time
        # would not match and we would end up with the same person twice on one record.
        # Matched on the normalized name — the raw Devanagari spacing differs between ingests.
        for party in r["sellers"] + r["purchasers"]:
            if not party.get("pan"):
                continue
            stmts.append(
                "UPDATE unit_registration_parties SET "
                f"party_pan = {q(party['pan'])}, pan_format_valid = TRUE, pan_enriched_at = now(), "
                f"party_age = COALESCE(party_age, {party['age'] if party.get('age') else 'NULL'}), "
                f"party_address = COALESCE(party_address, {q(party.get('address'))}) "
                f"WHERE unit_registration_record_id={rec} AND party_pan IS NULL "
                f"AND party_name_normalized = {q(translit(party['name'].strip()))};")

        for party, role in ([(p, srole) for p in r["sellers"]]
                            + [(p, brole) for p in r["purchasers"]]):
            name = (party.get("name") or "").strip()
            if not name:
                continue
            pan = party.get("pan")
            ptype = "company" if COMPANY_RE.search(name) else "individual"
            pdev = name if DEVANAGARI.search(name) else None
            ptag = dict(tag); ptag.update({"age": party.get("age"), "pan": pan})
            # Dedupe on PAN when we have one, else on the raw name — re-runs and the
            # paid-search rows must not double up.
            dedupe = (f"AND party_pan={q(pan)}" if pan
                      else f"AND party_name_raw={q(name)} AND party_role={q(role)}")
            stmts.append(
                "INSERT INTO unit_registration_parties "
                "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
                "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
                "party_type, display_order, raw_context) "
                f"SELECT {rec}, {q(role)}, {q(name)}, {q(translit(name))}, "
                f"{q(translit(name).title())}, {q(pdev)}, {q(pan)}, "
                f"{party['age'] if party.get('age') else 'NULL'}, {q(party.get('address'))}, "
                f"{q(ptype)}, {order}, {jb(ptag)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM unit_registration_parties "
                f"  WHERE unit_registration_record_id={rec} {dedupe});")
            order += 1

    stmts.append("COMMIT;")
    return stmts, ins, upd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-root", default=str(SNAPSHOT_ROOT))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        if not (args.apply and args.real_ok):
            print("Revert dry-run. Current:\n" + run_psql(counts_sql())[1])
            print("Needs --revert --apply --real-ok.")
            return 0
        _, out = run_psql(
            "BEGIN;\n"
            f"DELETE FROM unit_registration_review_items WHERE raw_context->>'source'='{SOURCE}';\n"
            f"DELETE FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}';\n"
            f"DELETE FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}';\n"
            "COMMIT;\n" + counts_sql())
        print("After revert:\n" + out)
        return 0

    files = sorted(Path(args.snapshot_root).glob("*/capture_*_r[0-9]*.txt"))
    if not files:
        print(f"No Index II captures under {args.snapshot_root}")
        return 1

    parsed = [parse_capture(p) for p in files]
    rescued = resolve_towers_from_db([r for r in parsed if r.get("is_ekta")])
    report(files, parsed)
    if rescued:
        print(f"\n  (+{rescued} towers recovered from an existing unit link in the DB)")

    rows = [r for r in parsed if r.get("is_ekta")]
    # Collapse duplicate captures of the same registration, keeping the richest one.
    best: dict[tuple[str, str], dict] = {}
    for r in rows:
        k = (r["doc_no"], r["year"])
        score = (bool(r["tower"] and r["flat"]), len(r["sellers"]) + len(r["purchasers"]),
                 sum(1 for p in r["sellers"] + r["purchasers"] if p.get("pan")))
        prev = best.get(k)
        if prev is None or score > prev["_score"]:
            r["_score"] = score
            best[k] = r
    rows = list(best.values())

    if not (args.apply and args.real_ok):
        print(f"\nDry run — {len(rows)} unique Ekta registrations would be written. "
              f"Add --apply --real-ok.")
        return 0

    keys = ",".join(f"({q(r['doc_no'])},{r['year']})" for r in rows)
    _, ex = run_psql(
        f"SELECT doc_number, registration_year FROM unit_registration_records "
        f"WHERE building_id={EKTA_SUB} AND (doc_number, registration_year) IN ({keys});")
    existing = {tuple(l.split("|")) for l in (x.strip() for x in ex.splitlines()) if "|" in l}
    print(f"\nAlready in DB: {len(existing)}   new: {len(rows) - len(existing)}")

    stmts, ins, upd = build_sql(rows, existing)
    print(f"Executing {len(stmts)} statements ({ins} INSERT, {upd} UPDATE)…")
    code, out = run_psql("\n".join(stmts))
    if code != 0:
        print("DB error:\n" + out[-4000:])
        return 1
    print("\nAfter write:\n" + run_psql(counts_sql())[1])
    return 0


def _demo() -> None:
    assert extract_unit("Apartment/Flat No:B-2701Floor No:27", "")[:2] == ("B", "2701")
    assert extract_unit("सदनिका नं: बी-3402, माळा नं: 34", "")[:2] == ("B", "3402")
    assert extract_unit("सदनिका न. 2806-ए,28 वा मजला", "")[:2] == ("A", "2806")
    assert extract_unit("सदनिका नं: 2306, माळा नं: 23 वा मजला,टॉवर ए", "")[:2] == ("A", "2306")
    # tower missing from the property field but present in the party block
    assert extract_unit("सदनिका नं: 1002, माळा नं: 10", "टॉवर ए, एकता")[:2] == ("A", "1002")
    assert extract_unit("सदनिका नं: शॉप नं. 75", "")[2] == "commercial_or_parking"
    assert extract_unit("only cts numbers here", "")[2] == "no_unit"
    # a tower letter outside A/B/C must not invent a unit
    assert extract_unit("Flat No:Z-101", "")[2] != "combo_en"
    print("parse_igr_cts_sweep_ekta self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        sys.exit(main())
