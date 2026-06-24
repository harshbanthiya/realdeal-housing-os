#!/usr/bin/env python3
"""Ingest IGR bulk snapshot captures — BOTH sources, merged & cross-validated.

Two source types per snapshot folder (exports/igr_index2_snapshots/*_bulk/):

  capture_NNN_p{P}_results.html   — IGR eSearch results grid (9 columns):
                                    DocNo | Type | RegDate | SRO | Sellers | Purchasers
                                    | PropertyDesc | SROCode | Status
                                    Has: party names, flat/wing/floor/area, L&L rent/deposit/tenure.
                                    Does NOT have: prices, PAN, ages, addresses.

  capture_NNN_p{P}_r{R}.txt      — Index II popup for row R on results page P.
                                    Has: ALL financial fields (consideration/market-value/stamp/
                                    reg-fee), party PAN + age + address, execution date,
                                    CTS number. Text identical to pdftotext output.

Pipeline:
  1. Parse ALL results pages from HTML (parse_grid → rows by doc_no)
  2. Parse ALL Index II TXTs (split_fields → full detail by doc_no)
  3. Merge on doc_no: results names + Index II prices/PAN → one record per doc
  4. Cross-validate: flag wing/flat/doctype discrepancies between sources
  5. Filter: Kalpataru only (all 4 wings); Patra Chawl and unrelated buildings skipped
  6. DB upsert: UPDATE existing records, INSERT new; parties with PAN deduped by name
  7. Audit summary to stdout

Dry-run by default. --apply --real-ok to write. --revert --apply --real-ok to undo.
No external calls. Reads local files only.

Requires: indic-transliteration (already installed for other IGR scripts).
"""
from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from html import unescape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# ── Import shared utilities ────────────────────────────────────────────────────
from parse_igr_results_to_staging import (  # noqa: E402
    parse_grid, parse_name_array, parse_property as results_parse_prop,
    translit_name, classify_doctype as results_classify,
)
from parse_igr_index2_pdfs import (  # noqa: E402
    split_fields, detect_wing, translit as iast_translit,
    parse_parties, iso, clean_frag, num, ROLE_BY_CATEGORY, PAN_RE, DEVANAGARI,
    classify_doctype as idx2_classify,
)

# Common L&L tenures in months (Maharashtra L&L agreements are almost always one of these)
_COMMON_TENURES = (11, 12, 22, 24, 33, 36, 48, 60, 66)

def _snap_tenure(months_float: float) -> int:
    return min(_COMMON_TENURES, key=lambda t: abs(t - months_float))

def derive_ll_fields(
    rent: str | None, deposit: str | None, stamp: str | None, cat: str
) -> tuple[str | None, str | None, str | None, bool]:
    """
    For L&L docs: field2=monthly_rent, field3=deposit, field12=stamp_duty.
    Maharashtra stamp formula:
      stamp = 0.25% × (rent × months + 10%/yr interest on deposit × months/12)
      => months = stamp_base / (rent + 0.1 × deposit / 12)
    Returns (monthly_rent, deposit, tenure_months, is_derived).
    Only used when rent/deposit/tenure not found in description text.
    """
    if cat != "tenancy":
        return rent, deposit, None, False
    try:
        r = float(str(rent or "").replace(",", "")) if rent else None
        d = float(str(deposit or "").replace(",", "")) if deposit else None
        s = float(str(stamp or "").replace(",", "")) if stamp else None
        if not s:
            return rent, deposit, None, False
        stamp_base = s / 0.0025
        # If rent unknown: field2 IS the monthly rent for L&L in Maharashtra IGR
        if r is None:
            return rent, deposit, None, False
        # If deposit unknown: field3 IS the deposit
        if d is None:
            monthly_base = r
        else:
            monthly_base = r + 0.1 * d / 12
        if monthly_base <= 0:
            return rent, deposit, None, False
        months_float = stamp_base / monthly_base
        if not (6 <= months_float <= 120):
            return rent, deposit, None, False
        return rent, deposit, str(_snap_tenure(months_float)), True
    except (TypeError, ValueError):
        return rent, deposit, None, False

PHASE = "6.23c"
SOURCE = "igr_ingest_bulk_2020_2026"
BUILDING_SUB = "(SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%' ORDER BY created_at LIMIT 1)"
KALPATARU_WINGS = {"Wing A-Ora", "Wing B-Brilliance", "Wing C-Allura", "Wing D-Lumina"}
WING_TOWER = {"Wing A-Ora": "A", "Wing B-Brilliance": "B", "Wing C-Allura": "C", "Wing D-Lumina": "D"}

# Additional wing needles not in the existing detect_wing (covers more Marathi variants)
_WING_EXTRA = re.compile(
    r"ओरा|ऑरा|अलोर|अल्लुर|एल्लूर|लुमिन|लुमीन|ब्रिलिय|ब्रिल्ली|ब्रिलीय"
    r"|\bora\b|allur|allor|lumina|brillian", re.I
)
KALPATARU_RE = re.compile(
    r"कल्पतर|kalpataru|रेडियंस|रेडीयंस|रेिडयंस|radiance", re.I
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"

def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"

def to_iso(d: str | None) -> str | None:
    if not d:
        return None
    m = re.match(r"([0-3]?\d)[/\-]([01]?\d)[/\-](\d{4})", d.strip())
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None

def add_months(d_iso: str | None, months: str | None) -> str | None:
    """Stdlib-only month arithmetic (avoids dateutil dependency)."""
    if not d_iso or not months:
        return None
    try:
        d = date.fromisoformat(d_iso)
        total = d.month - 1 + int(months)
        return d.replace(year=d.year + total // 12, month=total % 12 + 1).isoformat()
    except Exception:  # noqa: BLE001
        return None

def normalize_name(raw: str) -> str:
    """Transliterate → lowercase → collapse whitespace + punctuation."""
    s = iast_translit(raw)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def is_company(name: str) -> bool:
    return bool(re.search(
        r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा|llc|corp",
        name.lower()
    ))

def clean_party_name(raw: str) -> str:
    """Strip trailing dashes and whitespace (results page appends '--' to names)."""
    return re.sub(r"[-\s]+$", "", raw).strip()

# ── Phase 1: Parse results HTML pages ─────────────────────────────────────────

def parse_results_folder(folder: Path) -> dict[str, dict]:
    """Return {doc_no: results_row} for all Kalpataru rows in this folder."""
    out: dict[str, dict] = {}
    html_files = sorted(folder.glob("capture_*_results.html"))
    for hf in html_files:
        for cells in parse_grid(hf.read_text(encoding="utf-8", errors="replace")):
            if len(cells) < 7:
                continue
            doc_no, dname, rdate, sro, seller_cell, purchaser_cell, propdesc = (cells + [""] * 10)[:7]
            if not re.match(r"^\d+$", doc_no.strip()):
                continue

            doc_no = doc_no.strip()
            wing = detect_wing(propdesc) or detect_wing(dname)
            if not wing and not KALPATARU_RE.search(propdesc):
                continue  # skip non-Kalpataru rows

            etype, cat = results_classify(dname)
            # Run both parsers; take any non-null value from either.
            # results_parse_prop misses महिन्यासाठी; _parse_idx2_property catches all महिन* variants.
            prop_r = results_parse_prop(propdesc)
            prop_i = _parse_idx2_property(propdesc)
            prop = {
                "flat":          prop_r.get("flat")          or prop_i.get("flat"),
                "floor":         prop_r.get("floor")         or prop_i.get("floor"),
                "area_text":     prop_r.get("area_text"),
                "rent":          prop_r.get("rent")          or prop_i.get("rent"),
                "deposit":       prop_r.get("deposit")       or prop_i.get("deposit"),
                "tenure_months": prop_r.get("tenure_months") or prop_i.get("tenure_months"),
            }
            sellers = [clean_party_name(nm) for nm in parse_name_array(seller_cell) if nm.strip("-")]
            purchasers = [clean_party_name(nm) for nm in parse_name_array(purchaser_cell) if nm.strip("-")]
            out[doc_no] = {
                "doc_no": doc_no, "doc_type": etype, "cat": cat, "dname_raw": dname,
                "reg_date": to_iso(rdate), "sro": sro,
                "sellers": sellers, "purchasers": purchasers,
                "prop_desc_raw": propdesc,
                "flat": prop.get("flat"), "floor": prop.get("floor"),
                "area": prop.get("area_text"), "wing": wing,
                "rent": prop.get("rent"), "deposit": prop.get("deposit"),
                "tenure_months": prop.get("tenure_months"),
                "_src_html": hf.name, "_folder": folder.name,
            }
    return out

# ── Phase 2: Parse Index II TXT files ─────────────────────────────────────────

def parse_index2_txt(path: Path) -> dict | None:
    """Parse one Index II .txt capture (same format as pdftotext output)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if "दस्त क्रमांक" not in text and "सूची" not in text:
        return None

    m = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    if not m:
        return None
    doc_no, year = m.group(1), m.group(2)

    f = split_fields(text)
    dtype_raw = " ".join(clean_frag(f.get(1, "")).split()[:8])[:80]
    etype, cat = idx2_classify(dtype_raw)

    # Field 4: property (flat, floor, rent, deposit, tenure, CTS)
    f4 = f.get(4, "")
    prop = _parse_idx2_property(f4)
    cts_m = re.search(r"C\.T\.S\.\s*(?:Number|No\.?)\s*[:\-]?\s*([0-9/A-Za-z]+)", f4, re.I)
    cts = cts_m.group(1).strip() if cts_m else None

    # L&L: field2 = monthly rent, field3 = deposit (Maharashtra IGR convention).
    # Use as fallbacks when not found in field 4 description.
    _f2 = num(f.get(2, ""))
    _f3 = num(f.get(3, ""))
    etype_tmp, cat_tmp = idx2_classify(dtype_raw)
    if cat_tmp == "tenancy":
        if not prop.get("rent")    and _f2: prop["rent"]    = _f2
        if not prop.get("deposit") and _f3: prop["deposit"] = _f3

    wing = detect_wing(f4) or detect_wing(text)
    area = clean_frag(f.get(5, ""))[:80]

    sellers    = parse_parties(f.get(7, ""))
    purchasers = parse_parties(f.get(8, ""))

    sro_m = re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text)
    sro = sro_m.group(1).strip()[:120] if sro_m else None

    village_m = re.search(r"गाव\s*[:：]?\s*(.+)", text)
    village = village_m.group(1).strip()[:80] if village_m else None

    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    dr = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(10, ""))

    remarks = clean_frag(f.get(14, ""))[:500]
    stamp  = num(f.get(12, ""))
    regfee = num(f.get(13, ""))

    # Derive tenure from stamp duty math when not in text
    tenure_derived = False
    if not prop.get("tenure_months") and cat == "tenancy":
        _, _, derived_t, tenure_derived = derive_ll_fields(
            prop.get("rent"), prop.get("deposit"), stamp, cat
        )
        if derived_t:
            prop["tenure_months"] = derived_t

    return {
        "doc_no": doc_no, "year": year, "doc_type": etype, "cat": cat, "dtype_raw": dtype_raw,
        "sro": sro, "village": village, "cts": cts,
        "consideration": num(f.get(2, "")), "market_value": num(f.get(3, "")),
        "stamp_duty": stamp, "reg_fee": regfee,
        "area": area if area else None,
        "flat": prop.get("flat"), "floor": prop.get("floor"),
        "rent": prop.get("rent"), "deposit": prop.get("deposit"),
        "tenure_months": prop.get("tenure_months"),
        "tenure_derived": tenure_derived,
        "date_exec": to_iso(de.group(1)) if de else None,
        "date_reg":  to_iso(dr.group(1)) if dr else None,
        "sellers":    sellers,
        "purchasers": purchasers,
        "wing": wing, "remarks": remarks,
        "_src_txt": path.name, "_folder": path.parent.name,
    }

def _parse_idx2_property(field4: str) -> dict:
    """Extended version of parse_igr_index2_pdfs.parse_property — also catches महिन्यासाठी."""
    t = clean_frag(field4)
    d: dict = {}
    m = re.search(r"(?:सदनिका|फ्लॅट|दुकान)[^0-9\n]{0,30}?([0-9][0-9A-Za-z\-/]*)", t)
    if not m:
        m = re.search(r"सद\s?िनका\s*(?:नं|क्रं|क्र|क्रमांक)?\.?\s*[:]?\s*([0-9][0-9A-Za-z\-/]*)", t)
    if m:
        d["flat"] = m.group(1)[:40]
    # Floor
    if re.search(r"पिहला मजला|पहिला मजला", t):
        d["floor"] = "1"
    else:
        fm = re.search(r"([0-9]+)\s*(?:वा|व्या|था|ला|वी)?(?:\s*हॅब[ीि]टेबल)?\s*मजल", t)
        d["floor"] = fm.group(1) if fm else ("ground" if "तळ मजल" in t else None)
    # Rent
    rm = re.search(r"मा[सि]िक\s*भाडे\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", t)
    d["rent"] = rm.group(1).replace(",", "") if rm else None
    # Deposit
    dm = re.search(r"अनामत(?:\s*रक्[कमी]+)?\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", t)
    d["deposit"] = dm.group(1).replace(",", "") if dm else None
    # Tenure — handle महिने, महिन्या, महिन्यासाठी
    tm = re.search(r"कालावधी\s*([0-9]+)\s*महिन", t)
    d["tenure_months"] = tm.group(1) if tm else None
    return d

def parse_index2_folder(folder: Path) -> dict[str, dict]:
    """Return {doc_no: index2_data} for all Index II .txt files in folder."""
    out: dict[str, dict] = {}
    for p in sorted(folder.glob("capture_*_r*.txt")):
        r = parse_index2_txt(p)
        if r and r["doc_no"]:
            # If we see the same doc_no twice (shouldn't happen), take the first
            out.setdefault(r["doc_no"], r)
    return out

# ── Phase 3: Merge sources per doc_no ─────────────────────────────────────────

def merge(res: dict | None, idx2: dict | None) -> dict:
    """Merge results-page row and Index II record for the same doc_no."""
    m: dict = {}

    # Prefer results page for: party names (cleaner HTML), date (reg_date)
    # Prefer Index II for: prices, PAN, exec_date, CTS, area, wing (more fields parsed)
    if res:
        m.update(res)
    if idx2:
        # Financial fields — Index II is authoritative
        for k in ("consideration", "market_value", "stamp_duty", "reg_fee"):
            if idx2.get(k):
                m[k] = idx2[k]
        # Wing: Index II may see it in full text when results only had Marathi description
        if idx2.get("wing") and not m.get("wing"):
            m["wing"] = idx2["wing"]
        # Flat/floor: take whichever is non-null
        if idx2.get("flat") and not m.get("flat"):
            m["flat"] = idx2["flat"]
        if idx2.get("floor") and not m.get("floor"):
            m["floor"] = idx2["floor"]
        # Rent/deposit: take whichever is non-null
        if idx2.get("rent") and not m.get("rent"):
            m["rent"] = idx2["rent"]
        if idx2.get("deposit") and not m.get("deposit"):
            m["deposit"] = idx2["deposit"]
        if idx2.get("tenure_months") and not m.get("tenure_months"):
            m["tenure_months"] = idx2["tenure_months"]
        # Area: Index II field 5 is cleaner
        if idx2.get("area") and not m.get("area"):
            m["area"] = idx2["area"]
        # Dates
        m["date_exec"] = idx2.get("date_exec")
        m["year"] = idx2.get("year")
        m["cts"] = idx2.get("cts")
        m["sro"] = m.get("sro") or idx2.get("sro")
        m["village"] = idx2.get("village")
        m["remarks"] = idx2.get("remarks")
        m["_src_idx2"] = idx2.get("_src_txt")
        m["tenure_derived"] = idx2.get("tenure_derived", False)
        # Index II parties (have PAN/age/address)
        m["idx2_sellers"]    = idx2.get("sellers", [])
        m["idx2_purchasers"] = idx2.get("purchasers", [])
        # Doc type — prefer Index II (more rules)
        m["doc_type"] = idx2.get("doc_type") or m.get("doc_type")
        m["cat"] = idx2.get("cat") or m.get("cat")

    # Cross-validation flags
    checks: list[str] = []
    if res and idx2:
        r_wing = res.get("wing"); i_wing = idx2.get("wing")
        if r_wing and i_wing and r_wing != i_wing:
            checks.append(f"wing_mismatch:results={r_wing},idx2={i_wing}")
        r_flat = res.get("flat"); i_flat = idx2.get("flat")
        if r_flat and i_flat and r_flat.lower() != i_flat.lower():
            checks.append(f"flat_mismatch:results={r_flat},idx2={i_flat}")
        r_cat = res.get("cat"); i_cat = idx2.get("cat")
        if r_cat and i_cat and r_cat != i_cat:
            checks.append(f"cat_mismatch:results={r_cat},idx2={i_cat}")
    elif res and not idx2:
        checks.append("no_index2_capture")
    elif idx2 and not res:
        checks.append("no_results_row")

    m["_cross_checks"] = checks
    m["_has_results"] = res is not None
    m["_has_index2"] = idx2 is not None
    return m

# ── Phase 4: Party merging ─────────────────────────────────────────────────────

def build_parties(merged: dict) -> list[dict]:
    """Build final party list: results names as primary, Index II PAN/age/address overlaid."""
    srole, brole = ROLE_BY_CATEGORY.get(merged.get("cat", ""), ("seller", "purchaser"))

    # Start from results page names (cleaner, no matra scramble)
    results_sellers    = merged.get("sellers", [])
    results_purchasers = merged.get("purchasers", [])
    idx2_sellers       = merged.get("idx2_sellers", [])
    idx2_purchasers    = merged.get("idx2_purchasers", [])

    def overlay(res_names: list[str], idx2_parties: list[dict], role: str) -> list[dict]:
        """Overlay PAN/age/address from Index II onto results page name list."""
        out = []
        # Build normalized-name → idx2 party map
        idx2_by_norm = {}
        for p in idx2_parties:
            nn = normalize_name(p["name"])
            idx2_by_norm[nn] = p

        # Use results names as base; try to match idx2 for enrichment
        seen_norms: set[str] = set()
        for i, raw_name in enumerate(res_names):
            nn = normalize_name(raw_name)
            if nn in seen_norms:
                continue
            seen_norms.add(nn)
            # Find best idx2 match by normalized name (exact or prefix)
            matched_idx2 = idx2_by_norm.get(nn) or _fuzzy_match(nn, idx2_by_norm)
            dev = raw_name if DEVANAGARI.search(raw_name) else (matched_idx2["name"] if matched_idx2 else None)
            eng = normalize_name(raw_name).title() if not DEVANAGARI.search(raw_name) else (
                iast_translit(raw_name).title() if raw_name else ""
            )
            out.append({
                "role": role,
                "raw": raw_name,
                "name_english": eng,
                "name_devanagari": dev,
                "normalized": nn,
                "pan": matched_idx2.get("pan") if matched_idx2 else None,
                "age": matched_idx2.get("age") if matched_idx2 else None,
                "address": matched_idx2.get("address") if matched_idx2 else None,
                "ptype": "company" if is_company(raw_name) else "individual",
                "order": i,
            })

        # Add any idx2 parties with PAN not already matched (captures edge cases)
        for p in idx2_parties:
            nn = normalize_name(p["name"])
            if nn not in seen_norms and p.get("pan"):
                seen_norms.add(nn)
                dev = p["name"] if DEVANAGARI.search(p["name"]) else None
                out.append({
                    "role": role,
                    "raw": p["name"],
                    "name_english": iast_translit(p["name"]).title(),
                    "name_devanagari": dev,
                    "normalized": nn,
                    "pan": p.get("pan"), "age": p.get("age"), "address": p.get("address"),
                    "ptype": "company" if is_company(p["name"]) else "individual",
                    "order": len(out),
                })
        return out

    parties = (
        overlay(results_sellers,    idx2_sellers,    srole) +
        overlay(results_purchasers, idx2_purchasers, brole)
    )
    # If no results names at all, fall back to idx2 directly
    if not parties:
        for role, idx2_list in [(srole, idx2_sellers), (brole, idx2_purchasers)]:
            for i, p in enumerate(idx2_list):
                nn = normalize_name(p["name"])
                dev = p["name"] if DEVANAGARI.search(p["name"]) else None
                parties.append({
                    "role": role, "raw": p["name"],
                    "name_english": iast_translit(p["name"]).title(),
                    "name_devanagari": dev, "normalized": nn,
                    "pan": p.get("pan"), "age": p.get("age"), "address": p.get("address"),
                    "ptype": "company" if is_company(p["name"]) else "individual", "order": i,
                })
    return parties

def _fuzzy_match(nn: str, pool: dict[str, dict]) -> dict | None:
    """Match by longest common prefix ≥ 6 chars (handles spelling variants)."""
    best, best_key = None, None
    for k in pool:
        prefix_len = 0
        for a, b in zip(nn, k):
            if a == b:
                prefix_len += 1
            else:
                break
        if prefix_len >= 6 and (best_key is None or prefix_len > len(best_key)):
            best, best_key = pool[k], k
    return best

# ── SQL generation ─────────────────────────────────────────────────────────────

def record_sql(m: dict, existing_doc_nos: set[str]) -> list[str]:
    """Return SQL statements for one merged registration record."""
    doc_no = m["doc_no"]
    wing = m.get("wing")
    tower = WING_TOWER.get(wing, "")
    flat = m.get("flat")
    cat = m.get("cat", "other")
    d_exec = m.get("date_exec")
    d_reg = m.get("reg_date") or m.get("date_exec")
    year = m.get("year") or (d_reg[:4] if d_reg else None)
    rent = m.get("rent") if cat == "tenancy" else None
    dep  = m.get("deposit") if cat == "tenancy" else None
    t_start = d_exec if cat == "tenancy" else None
    t_end   = add_months(d_exec, m.get("tenure_months")) if cat == "tenancy" else None

    tag = {
        "source": SOURCE, "phase": PHASE, "is_fake": False,
        "wing_label": wing, "cts": m.get("cts"),
        "village": m.get("village"),
        "has_results_page": m["_has_results"],
        "has_index2": m["_has_index2"],
        "cross_checks": m["_cross_checks"],
        "tenure_derived": m.get("tenure_derived", False),
        "src_results": m.get("_src_html"),
        "src_index2": m.get("_src_idx2"),
        "folder": m.get("_folder"),
        "external_calls_made": False,
    }

    stmts: list[str] = []

    if doc_no in existing_doc_nos:
        # UPDATE: enrich existing record — never overwrite names/type already set
        stmts.append(
            "UPDATE unit_registration_records SET "
            f"consideration_amount = COALESCE(consideration_amount, {q(m.get('consideration'))}), "
            f"market_value         = COALESCE(market_value,         {q(m.get('market_value'))}), "
            f"stamp_duty           = COALESCE(stamp_duty,           {q(m.get('stamp_duty'))}), "
            f"registration_fee     = COALESCE(registration_fee,     {q(m.get('reg_fee'))}), "
            f"tenancy_monthly_rent = COALESCE(tenancy_monthly_rent, {q(rent)}), "
            f"tenancy_deposit      = COALESCE(tenancy_deposit,      {q(dep)}), "
            f"tenancy_start_date   = COALESCE(tenancy_start_date,   {q(t_start)}), "
            f"tenancy_end_date     = COALESCE(tenancy_end_date,     {q(t_end)}), "
            f"sro_office           = COALESCE(sro_office,           {q(m.get('sro'))}), "
            f"area_text            = COALESCE(area_text,            {q(m.get('area'))}), "
            f"parse_confidence     = GREATEST(COALESCE(parse_confidence,0), 0.80), "
            f"raw_context          = raw_context || {jb({'ingest_bulk_enriched': True, 'cross_checks': m['_cross_checks']})} "
            f"WHERE building_id = {BUILDING_SUB} AND doc_number = {q(doc_no)};"
        )
        return stmts  # parties handled separately in party_sql

    # INSERT
    unit_sub = "NULL"
    if flat and tower:
        unit_sub = (
            f"(SELECT id FROM building_units WHERE building_id={BUILDING_SUB} "
            f"AND wing={q(tower)} AND unit_number={q(flat)} ORDER BY created_at LIMIT 1)"
        )

    stmts.append(
        "INSERT INTO unit_registration_records "
        "(building_id, building_unit_id, doc_number, registration_year, registration_date, "
        "sro_office, document_type, transaction_category, property_description_raw, "
        "wing_text, unit_text, floor_text, area_text, "
        "consideration_amount, market_value, stamp_duty, registration_fee, "
        "tenancy_monthly_rent, tenancy_deposit, tenancy_start_date, tenancy_end_date, "
        "parse_confidence, verification_status, source_label, raw_context) "
        f"VALUES ({BUILDING_SUB}, {unit_sub}, {q(doc_no)}, "
        f"{'NULL' if not year else year}, {q(d_reg)}, {q(m.get('sro'))}, "
        f"{q(m.get('doc_type'))}, {q(cat)}, "
        f"{q((m.get('prop_desc_raw') or '')[:2000])}, "
        f"{q(wing)}, {q(flat)}, {q(m.get('floor'))}, {q(m.get('area'))}, "
        f"{q(m.get('consideration'))}, {q(m.get('market_value'))}, "
        f"{q(m.get('stamp_duty'))}, {q(m.get('reg_fee'))}, "
        f"{q(rent)}, {q(dep)}, {q(t_start)}, {q(t_end)}, "
        f"0.80, 'parsed_candidate', 'IGR bulk ingest 2020-2026', {jb(tag)}) "
        f"ON CONFLICT DO NOTHING;"
    )

    rec = (
        f"(SELECT id FROM unit_registration_records "
        f"WHERE building_id={BUILDING_SUB} AND doc_number={q(doc_no)} "
        f"ORDER BY created_at LIMIT 1)"
    )
    for p in build_parties(m):
        stmts.append(
            "INSERT INTO unit_registration_parties "
            "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
            "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
            "party_type, display_order, raw_context) "
            f"VALUES ({rec}, {q(p['role'])}, {q(p['raw'])}, {q(p['normalized'])}, "
            f"{q(p['name_english'])}, {q(p['name_devanagari'])}, {q(p.get('pan'))}, "
            f"{'NULL' if not p.get('age') else p['age']}, "
            f"{q(p.get('address'))}, {q(p['ptype'])}, {p['order']}, "
            f"{jb({'source': SOURCE, 'pan': p.get('pan'), 'age': p.get('age')})}) "
            f"ON CONFLICT DO NOTHING;"
        )

    stmts.append(
        "INSERT INTO unit_registration_review_items "
        "(building_id, unit_registration_record_id, review_type, status, priority, "
        "decision_notes, raw_context) "
        f"VALUES ({BUILDING_SUB}, {rec}, 'registration_record_review', 'pending', 'normal', "
        f"'IGR bulk ingest 2020-2026 ({wing}); verify parties, PAN, financials.', "
        f"{jb({'source': SOURCE, 'doc_no': doc_no, 'cross_checks': m['_cross_checks']})}) "
        f"ON CONFLICT DO NOTHING;"
    )
    return stmts

def party_sql_for_update(m: dict, existing_doc_nos: set[str]) -> list[str]:
    """For already-existing records: add PAN-bearing parties not yet in DB."""
    if m["doc_no"] not in existing_doc_nos:
        return []
    stmts: list[str] = []
    rec = (
        f"(SELECT id FROM unit_registration_records "
        f"WHERE building_id={BUILDING_SUB} AND doc_number={q(m['doc_no'])} "
        f"ORDER BY created_at LIMIT 1)"
    )
    for p in build_parties(m):
        if not p.get("pan"):
            continue  # only add new parties that bring PAN data
        stmts.append(
            "INSERT INTO unit_registration_parties "
            "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
            "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
            "party_type, display_order, raw_context) "
            f"SELECT {rec}, {q(p['role'])}, {q(p['raw'])}, {q(p['normalized'])}, "
            f"{q(p['name_english'])}, {q(p['name_devanagari'])}, {q(p.get('pan'))}, "
            f"{'NULL' if not p.get('age') else p['age']}, "
            f"{q(p.get('address'))}, {q(p['ptype'])}, {p['order']}, "
            f"{jb({'source': SOURCE, 'pan': p.get('pan')})} "
            f"WHERE NOT EXISTS ("
            f"  SELECT 1 FROM unit_registration_parties "
            f"  WHERE unit_registration_record_id={rec} AND party_pan={q(p['pan'])}"
            f");"
        )
        # Also UPDATE existing party row with PAN if matched by name
        stmts.append(
            f"UPDATE unit_registration_parties SET "
            f"party_pan = COALESCE(party_pan, {q(p.get('pan'))}), "
            f"party_age = COALESCE(party_age, {'NULL' if not p.get('age') else p['age']}), "
            f"party_address = COALESCE(party_address, {q(p.get('address'))}) "
            f"WHERE unit_registration_record_id = {rec} "
            f"AND party_name_normalized = {q(p['normalized'])} "
            f"AND party_pan IS NULL;"
        )
    return stmts

def counts_sql() -> str:
    return (
        f"SELECT 'records' AS w, count(*)::text FROM unit_registration_records"
        f"  WHERE raw_context->>'source'='{SOURCE}'\n"
        f"UNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties"
        f"  WHERE raw_context->>'source'='{SOURCE}'\n"
        f"UNION ALL SELECT 'with_pan', count(*)::text FROM unit_registration_parties"
        f"  WHERE raw_context->>'source'='{SOURCE}' AND party_pan IS NOT NULL\n"
        f"UNION ALL SELECT 'with_price', count(*)::text FROM unit_registration_records"
        f"  WHERE raw_context->>'source'='{SOURCE}' AND consideration_amount IS NOT NULL\n"
        f"UNION ALL SELECT 'tenancy_complete', count(*)::text FROM unit_registration_records"
        f"  WHERE raw_context->>'source'='{SOURCE}'"
        f"  AND transaction_category='tenancy' AND tenancy_monthly_rent IS NOT NULL\n"
        f"ORDER BY 1;"
    )

# ── main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Ingest IGR bulk snapshots (results + Index II) into staging."
    )
    ap.add_argument("--snapshot-root", default=str(SNAPSHOT_ROOT))
    ap.add_argument("--year", help="Filter to one year, e.g. 2024")
    ap.add_argument("--apply",   action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert",  action="store_true")
    args = ap.parse_args()

    snap_root = Path(args.snapshot_root)

    if args.revert:
        if not (args.apply and args.real_ok):
            _, cur = run_psql(counts_sql())
            print("Revert dry-run (would delete):\n" + cur)
            print("Needs --revert --apply --real-ok.")
            return 0
        sql = (
            "BEGIN;\n"
            f"DELETE FROM unit_registration_review_items WHERE raw_context->>'source'='{SOURCE}';\n"
            f"DELETE FROM unit_registration_parties     WHERE raw_context->>'source'='{SOURCE}';\n"
            f"DELETE FROM unit_registration_records     WHERE raw_context->>'source'='{SOURCE}';\n"
            "COMMIT;\n" + counts_sql()
        )
        _, out = run_psql(sql)
        print("After revert:\n" + out)
        return 0

    # Discover folders
    folders = sorted(snap_root.glob("*_bulk/"))
    if args.year:
        folders = [f for f in folders if f"_kalpataru_{args.year}_" in f.name]
    if not folders:
        print(f"No *_bulk/ folders in {snap_root}")
        return 1

    # Parse both sources per folder
    all_results: dict[str, dict] = {}   # doc_no → results row
    all_index2:  dict[str, dict] = {}   # doc_no → index2 record
    folder_labels: dict[str, str] = {}  # doc_no → folder name

    for folder in folders:
        year_label = folder.name  # e.g. 20260623T191641Z_kalpataru_2024_bulk
        print(f"\n── {folder.name} ──")

        res_map  = parse_results_folder(folder)
        idx2_map = parse_index2_folder(folder)

        print(f"  results rows (Kalpataru): {len(res_map)}")
        print(f"  Index II captures:        {len(idx2_map)}")

        for doc_no in set(res_map) | set(idx2_map):
            folder_labels[doc_no] = year_label

        all_results.update(res_map)
        all_index2.update(idx2_map)

    # Merge
    all_doc_nos = set(all_results) | set(all_index2)
    merged_all: list[dict] = []
    counts_by_wing: dict[str, int] = {}
    cross_issues: list[str] = []

    for doc_no in sorted(all_doc_nos):
        m = merge(all_results.get(doc_no), all_index2.get(doc_no))
        m["doc_no"] = doc_no
        if m.get("_folder") is None:
            m["_folder"] = folder_labels.get(doc_no, "")
        wing = m.get("wing")
        if not wing or wing not in KALPATARU_WINGS:
            # Skip Patra Chawl and truly unknown
            counts_by_wing[wing or "undetected"] = counts_by_wing.get(wing or "undetected", 0) + 1
            continue
        counts_by_wing[wing] = counts_by_wing.get(wing, 0) + 1
        if m["_cross_checks"]:
            cross_issues.extend([f"doc {doc_no}: {c}" for c in m["_cross_checks"]])
        merged_all.append(m)

    print(f"\n── Summary ──")
    print(f"Total unique doc_nos seen: {len(all_doc_nos)}")
    print(f"Kalpataru (all wings): {len(merged_all)}")
    for k, v in sorted(counts_by_wing.items(), key=lambda kv: -kv[1]):
        mark = " ✓" if k in KALPATARU_WINGS else ""
        print(f"  {v:4d}  {k}{mark}")
    print(f"Only in results (no Index II capture): "
          f"{sum(1 for m in merged_all if not m['_has_index2'])}")
    print(f"Only in Index II (no results row):     "
          f"{sum(1 for m in merged_all if not m['_has_results'])}")
    print(f"Cross-validation issues: {len(cross_issues)}")
    for issue in cross_issues[:10]:
        print(f"  {issue}")
    if len(cross_issues) > 10:
        print(f"  ... and {len(cross_issues)-10} more")

    pan_count = sum(
        1 for m in merged_all
        for p in (m.get("idx2_sellers", []) + m.get("idx2_purchasers", []))
        if p.get("pan")
    )
    rent_count = sum(1 for m in merged_all if m.get("rent") and m.get("cat") == "tenancy")
    print(f"Party PANs found: {pan_count}")
    print(f"L&L records with rent amount: {rent_count}")

    if not (args.apply and args.real_ok):
        print("\nDry run — no DB writes. Add --apply --real-ok to stage.")
        print("\nSample (first 8 merged records):")
        for m in merged_all[:8]:
            parties = build_parties(m)
            print(
                f"  doc {str(m.get('doc_no','?')):6s}  "
                f"{str(m.get('doc_type',''))[:18]:18s}  "
                f"{str(m.get('wing',''))[:20]:20s}  "
                f"flat={str(m.get('flat') or '?')[:6]:6s}  "
                f"consid={str(m.get('consideration') or ''):>8}  "
                f"stamp={str(m.get('stamp_duty') or ''):>6}  "
                f"rent={str(m.get('rent') or ''):>7}  "
                f"parties={len(parties)} "
                f"PANs={sum(1 for p in parties if p.get('pan'))}"
            )
        return 0

    # Fetch existing doc_numbers for Kalpataru building
    all_doc_q = ",".join(q(m["doc_no"]) for m in merged_all)
    _, ex_out = run_psql(
        f"SELECT doc_number FROM unit_registration_records "
        f"WHERE building_id={BUILDING_SUB} AND doc_number IN ({all_doc_q});"
    )
    existing = {ln.strip() for ln in ex_out.splitlines() if ln.strip()}
    to_insert = [m for m in merged_all if m["doc_no"] not in existing]
    to_update = [m for m in merged_all if m["doc_no"] in existing]
    print(f"\nDB: {len(existing)} existing | {len(to_insert)} to INSERT | {len(to_update)} to UPDATE")

    stmts = ["BEGIN;"]
    for m in to_insert:
        stmts.extend(record_sql(m, existing))
    for m in to_update:
        stmts.extend(record_sql(m, existing))
        stmts.extend(party_sql_for_update(m, existing))
    stmts.append("COMMIT;")
    stmts.append(counts_sql())

    print(f"Executing {len(stmts)} SQL statements …")
    code, out = run_psql("\n".join(stmts))
    if code == 0:
        print("Done. Source counts:\n" + out)
    else:
        print("DB error:\n" + out)
    return code


if __name__ == "__main__":
    sys.exit(main())
