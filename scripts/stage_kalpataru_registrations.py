#!/usr/bin/env python3
"""Phase 6.21 — consolidate + enrich Kalpataru Radiance registrations onto the canonical building.

Merges the two capture levels into ONE complete, review-gated dataset attached to the REAL
"Kalpataru Radiance" building (towers A/B/C/D), add-only:

  - LIST snapshot (all result pages)  -> every registration across all towers, with clean
    (proper-order) party names: English (romanized, primary) + Devanagari (original).
  - INDEX II PDFs (the pages we have)  -> consideration / market value / stamp duty / reg fee /
    area, and party PAN / age / address, matched to the list record by document number.

Each flat is linked to its EXISTING building_unit (matched by tower-letter + unit number); a unit
is created only if missing. The 636 existing owner relationships are NEVER touched. Records are
verification_status='parsed_candidate' (review-gated), tagged source='igr_kalpataru_2026', and
fully reversible (--revert). Also reverts the earlier per-tower staging so nothing is duplicated.

Dry-run by default; writing needs --apply AND --real-ok. NO scrape/IGR/external call (local files).
Requires: pdftotext (poppler) + indic-transliteration.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent

from parse_igr_results_to_staging import parse_grid, parse_name_array, to_iso_date, parse_property as list_prop  # noqa: E402
from parse_igr_index2_pdfs import parse_index2, classify_doctype, detect_wing, translit as iast  # noqa: E402

PHASE = "6.21"
SOURCE = "igr_kalpataru_2026"
OLD_SOURCES = ("igr_parse_kalpataru_2026", "igr_index2_kalpataru")
TARGET_BUILDING_NAME = "Kalpataru Radiance"
LIST_DIR = PROJECT_ROOT / "exports" / "igr_snapshots" / "20260616T135127Z_kalpataru-260-5A-2023"
TOWER_OF = {"Wing A-Ora": "A", "Wing B-Brilliance": "B", "Wing C-Allura": "C", "Wing D-Lumina": "D"}
ROLE_BY_CATEGORY = {"ownership": ("seller", "purchaser"), "tenancy": ("lessor", "lessee"),
                    "encumbrance": ("mortgagee", "mortgagor"), "other": ("seller", "purchaser")}
DEV = re.compile(r"[ऀ-ॿ]")
def to_english(raw: str) -> str:
    if not raw:
        return ""
    s = iast(raw)  # ascii-folded lowercase IAST (Devanagari) or pass-through (Latin)
    s = re.sub(r"[^a-z0-9 .&/-]", "", s)  # drop residual Devanagari marks the translit left
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()

def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"

def qn(v) -> str:
    if v in (None, ""):
        return "NULL"
    try:
        return str(int(float(str(v).replace(",", ""))))
    except (TypeError, ValueError):
        return "NULL"

def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"

def counts_sql() -> str:
    return (f"SELECT 'records', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'parties_with_pan', count(*)::text FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}' AND party_pan IS NOT NULL"
            f"\nUNION ALL SELECT 'units_created', count(*)::text FROM building_units WHERE metadata->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'priced_records', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND consideration_amount IS NOT NULL\nORDER BY 1;")

def revert_sql() -> str:
    srcs = "', '".join((SOURCE,) + OLD_SOURCES)
    return (
        f"BEGIN;\n"
        f"DELETE FROM unit_registration_review_items WHERE raw_context->>'source' IN ('{srcs}');\n"
        f"DELETE FROM registration_party_contact_matches WHERE raw_context->>'source' IN ('{srcs}');\n"
        f"DELETE FROM unit_registration_parties WHERE raw_context->>'source' IN ('{srcs}');\n"
        f"DELETE FROM unit_registration_records WHERE raw_context->>'source' IN ('{srcs}');\n"
        f"DELETE FROM building_units WHERE metadata->>'source' IN ('{srcs}');\n"
        f"COMMIT;\n" + counts_sql())

def main() -> int:
    ap = argparse.ArgumentParser(description="Consolidate Kalpataru registrations onto the canonical building. Dry-run by default.")
    ap.add_argument("--index2-dir", action="append", default=[], help="folder of Index II PDFs (repeatable)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        if not (args.apply and args.real_ok):
            _, c = run_psql(counts_sql()); print("Revert dry-run (would delete tagged rows incl. old per-tower staging):\n" + c)
            return 0
        _, out = run_psql(revert_sql()); print("After revert:\n" + out); return 0

    # Resolve canonical building.
    code, bid = run_psql(f"SELECT id FROM buildings WHERE name = {q(TARGET_BUILDING_NAME)} ORDER BY created_at LIMIT 1;")
    if code or not bid:
        print(f"Refusing: building {TARGET_BUILDING_NAME!r} not found."); return 1
    bid = bid.splitlines()[0].strip()

    # Existing units in the canonical building -> map (towerLetter, unitNumber) -> id.
    _, ux = run_psql(f"SELECT id, coalesce(wing,''), coalesce(unit_number,'') FROM building_units WHERE building_id='{bid}';")
    existing: dict[tuple, str] = {}
    for line in ux.splitlines():
        uid, wing, unum = (line.split("|") + ["", "", ""])[:3]
        letter = re.sub(r"[^A-Za-z]", "", wing)[-1:].upper() if wing else ""
        if unum:
            existing[(letter, unum.strip())] = uid
    tower_wing_label = {}  # letter -> existing wing label, for consistent unit creation
    for (letter, _), uid in existing.items():
        pass
    _, wl = run_psql(f"SELECT DISTINCT coalesce(wing,'') FROM building_units WHERE building_id='{bid}' AND wing IS NOT NULL;")
    for w in wl.splitlines():
        letter = re.sub(r"[^A-Za-z]", "", w)[-1:].upper()
        if letter:
            tower_wing_label[letter] = w.strip()

    # ---- LIST: all towers ----
    list_files = sorted(LIST_DIR.glob("capture_*.html"))
    seen: dict[tuple, dict] = {}
    for f in list_files:
        for cells in parse_grid(f.read_text(encoding="utf-8", errors="replace")):
            docno, dname, rdate, sro, seller, purch, prop, srocode, status = (cells + [""] * 10)[:9]
            key = (docno, srocode)
            if key in seen:
                continue
            etype, cat = classify_doctype(dname)
            wing = detect_wing(prop) or detect_wing(dname)
            pp = list_prop(prop)
            seen[key] = dict(docno=docno, dname=dname, rdate=rdate, sro=sro, seller=seller, purch=purch,
                             prop=prop, etype=etype, cat=cat, wing=wing, **{f"p_{k}": v for k, v in pp.items()})
    rows = list(seen.values())

    # ---- INDEX II: by doc number ----
    idx: dict[str, dict] = {}
    for d in args.index2_dir:
        for p in sorted([x for x in Path(d).iterdir() if x.name.lower().startswith("index22")]):
            r = parse_index2(p)
            if r and r["doc_no"]:
                idx[r["doc_no"]] = r

    target = [r for r in rows if r["wing"] in TOWER_OF]
    by_wing: dict[str, int] = {}
    for r in rows:
        by_wing[r["wing"] or "other/unknown"] = by_wing.get(r["wing"] or "other/unknown", 0) + 1

    print(f"Canonical building '{TARGET_BUILDING_NAME}' = {bid} ({len(existing)} existing numbered units).")
    print(f"LIST: {len(rows)} unique registrations. INDEX II detail loaded for {len(idx)} docs.")
    for k, v in sorted(by_wing.items(), key=lambda kv: -kv[1]):
        print(f"  {v:3d}  {k}")
    matched_units = sum(1 for r in target if (TOWER_OF[r["wing"]], r["p_flat"]) in existing)
    print(f"Towers A-D to stage: {len(target)}  (will link {matched_units} to existing units, create {len(target) - matched_units})")
    print(f"Index II price/PAN available for {sum(1 for r in target if r['docno'] in idx)} of them.")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No DB writes. Writing requires --apply --real-ok.")
        return 0

    # Clean slate for our + old sources, then insert.
    run_psql(revert_sql())
    stmts = ["BEGIN;"]
    for r in target:
        letter = TOWER_OF[r["wing"]]
        flat = r["p_flat"]
        det = idx.get(r["docno"])
        tag = {"source": SOURCE, "phase": PHASE, "wing": r["wing"], "tower": letter, "doctype_raw": r["dname"],
               "sro_raw": r["sro"], "is_fake": False, "is_sample": False, "external_calls_made": False,
               "index2": bool(det), "note": "IGR Kalpataru consolidated (list + Index II); review-gated."}
        # unit link: existing or create
        unit_ref = "NULL"
        if flat and (letter, flat) in existing:
            unit_ref = f"'{existing[(letter, flat)]}'"
        elif flat:
            wlabel = tower_wing_label.get(letter, f"Tower {letter}")
            stmts.append(
                f"INSERT INTO building_units (building_id, building_name, wing, unit_number, canonical_status, metadata) "
                f"SELECT '{bid}', {q(TARGET_BUILDING_NAME)}, {q(wlabel)}, {q(flat)}, 'active', {jb(tag)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM building_units WHERE building_id='{bid}' AND wing={q(wlabel)} AND unit_number={q(flat)} AND metadata->>'source'='{SOURCE}');")
            unit_ref = (f"(SELECT id FROM building_units WHERE building_id='{bid}' AND wing={q(wlabel)} AND unit_number={q(flat)} "
                        f"AND metadata->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        iso = to_iso_date(r["rdate"])
        cons = qn(det["consideration"]) if det and det["consideration"] not in (None, "0") else "NULL"
        mkt = qn(det["market_value"]) if det else "NULL"
        stamp = qn(det["stamp_duty"]) if det else "NULL"
        regfee = qn(det["reg_fee"]) if det else "NULL"
        area = q(det["area"]) if det and det.get("area") else q(r["p_area_text"])
        rent = qn(r["p_rent"]) if r["cat"] == "tenancy" else "NULL"
        dep = qn(r["p_deposit"]) if r["cat"] == "tenancy" else "NULL"
        stmts.append(
            "INSERT INTO unit_registration_records (building_id, building_unit_id, doc_number, registration_year, "
            "registration_date, sro_office, document_type, transaction_category, property_description_raw, wing_text, "
            "unit_text, floor_text, area_text, consideration_amount, market_value, stamp_duty, registration_fee, "
            "tenancy_monthly_rent, tenancy_deposit, parse_confidence, verification_status, source_label, raw_context) VALUES ("
            f"'{bid}', {unit_ref}, {q(r['docno'])}, {iso[:4] if iso else 'NULL'}, {q(iso)}, {q(r['sro'])}, "
            f"{q(r['etype'])}, {q(r['cat'])}, {q(r['prop'])}, {q(r['wing'])}, {q(flat)}, {q(r['p_floor'])}, "
            f"{area}, {cons}, {mkt}, {stamp}, {regfee}, {rent}, {dep}, {0.75 if det else 0.55}, 'parsed_candidate', "
            f"{q('IGR ' + ('list+Index II' if det else 'list') + ' 2026 (CTS 260/5A)')}, {jb(tag)});")
        rec = (f"(SELECT id FROM unit_registration_records WHERE doc_number={q(r['docno'])} AND building_id='{bid}' "
               f"AND raw_context->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        srole, brole = ROLE_BY_CATEGORY[r["cat"]]
        # list parties (clean names) + index II detail (pan/age/address) matched by role+order
        groups = [("seller", parse_name_array(r["seller"]), srole, (det["sellers"] if det else [])),
                  ("purchaser", parse_name_array(r["purch"]), brole, (det["purchasers"] if det else []))]
        order = 0
        for _, names, role, dparties in groups:
            for i, nm in enumerate(names):
                dp = dparties[i] if i < len(dparties) else {}
                eng = to_english(nm)
                dev = nm if DEV.search(nm) else None
                ptype = "company" if re.search(r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा", nm.lower()) else "individual"
                ptag = dict(tag); ptag.update({"pan": dp.get("pan"), "age": dp.get("age")})
                stmts.append(
                    "INSERT INTO unit_registration_parties (unit_registration_record_id, party_role, party_name_raw, "
                    "party_name_normalized, party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
                    f"party_type, display_order, raw_context) VALUES ({rec}, '{role}', {q(nm)}, {q(eng.lower())}, "
                    f"{q(eng)}, {q(dev)}, {q(dp.get('pan'))}, {qn(dp.get('age'))}, {q(dp.get('address'))}, '{ptype}', {order}, {jb(ptag)});")
                order += 1
        stmts.append(
            "INSERT INTO unit_registration_review_items (building_id, unit_registration_record_id, review_type, status, "
            f"priority, decision_notes, raw_context) VALUES ('{bid}', {rec}, 'registration_record_review', 'pending', "
            f"'normal', 'IGR consolidated parse; verify parties + PAN.', {jb(tag)});")
    stmts.append("COMMIT;")
    stmts.append(counts_sql())
    code, out = run_psql("\n".join(stmts))
    print("Staged (counts):\n" + out if code == 0 else "DB error:\n" + out)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
