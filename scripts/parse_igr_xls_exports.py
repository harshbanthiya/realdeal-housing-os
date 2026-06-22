#!/usr/bin/env python3
"""Phase 6.22 — bulk parser for IGR eSearch ".xls" result exports (the best source).

IGR's "Download as .xls" produces an HTML table (UTF-16, id=ctl00_MainContent_GrdResult) with 19
structured columns INCLUDING consideration_amt / marketvalue / stampdutypaid / registrationfees +
clean proper-order Devanagari party names. This is the primary loader: price IS in the export and
names are NOT matra-scrambled. (PAN/age/address still only come from Index II PDFs.)

Goal: ingest EVERY Kalpataru Radiance registration from a CTS-260 search across all years, missing
none. Detection is high-recall — a row is Kalpataru if its property mentions the society
(कल्पतर / radiance), the CTS 260/5A (any separator), OR a tower (Ora/Allura/Lumina/Brilliance and
not another named building). Neighbour plots (260/4, 260/6, 260/5B) and other buildings (Oberoi,
Esquire, Ekta, MHADA, …) are reported but not staged. Everything that is neither is written to a
REVIEW CSV (exports/igr_review/, git-ignored) so "nothing missed" is auditable, not assumed.

Kalpataru rows are staged onto the canonical "Kalpataru Radiance" building (add-only, reversible),
linked to existing units by tower-letter + number. Supersedes earlier IGR staging sources.

Dry-run by default; writing needs --apply AND --real-ok. NO scrape/IGR/external call (local files).
Requires: indic-transliteration.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
import csv
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent
REVIEW_DIR = PROJECT_ROOT / "exports" / "igr_review"

from parse_igr_results_to_staging import parse_name_array, parse_property as list_prop  # noqa: E402
from parse_igr_index2_pdfs import classify_doctype, detect_wing, translit as iast, skeleton  # noqa: E402

PHASE = "6.22"
SOURCE = "igr_xls_kalpataru"
OLD_SOURCES = ("igr_kalpataru_2026", "igr_parse_kalpataru_2026", "igr_index2_kalpataru")
TARGET_BUILDING_NAME = "Kalpataru Radiance"
TOWER_OF = {"Wing A-Ora": "A", "Wing B-Brilliance": "B", "Wing C-Allura": "C", "Wing D-Lumina": "D"}
ROLE_BY_CATEGORY = {"ownership": ("seller", "purchaser"), "tenancy": ("lessor", "lessee"),
                    "encumbrance": ("mortgagee", "mortgagor"), "other": ("seller", "purchaser")}
DEV = re.compile(r"[ऀ-ॿ]")

KALP = re.compile(r"कल्पतर|kalpataru|रेडियंस|रेडीयंस|रेिडयंस|रेिडअन्स|radiance", re.I)
TOWER = re.compile(r"ओरा|अलोर|अल्ल|एल्लूर|लुमिन|लुमीन|ब्रिलिय|ब्रिल्ली|ब्रिलीय|\bora\b|allur|allor|lumina|brilliance", re.I)
CTS5A = re.compile(r"260\s*[/\-]?\s*5\s*(?:a|अ|ए)", re.I)
NEIGH = re.compile(r"260\s*[/\-]?\s*(?:4|6|5\s*(?:b|ब))", re.I)
OTHERB = re.compile(r"एस्क्वायर|एस्क्वा|एक्सवायर|esquire|ओबेरॉय|oberoi|शीतल|एलिसियन|elysian|एकता|ekta|"
                    r"म्हाडा|mhada|अनमोल|anmol|34 पार्क|park estate|वूड्स|woods|एक्सक्यू|एक्सक्झ|exquisite|एक्क्झ|"
                    r"यश एन्क्लेव|सद्गुरू|ओशिवरा|क्रिथार्थ|कृतार्थ", re.I)
def load(f: Path) -> str:
    raw = f.read_bytes()
    for enc in ("utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:  # noqa: BLE001
            pass
    return raw.decode("utf-8", "replace")

def tcells(r: str) -> list[str]:
    return [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]

def to_english(raw: str) -> str:
    if not raw:
        return ""
    s = iast(raw)
    s = re.sub(r"[^a-z0-9 .&/-]", "", s)
    return re.sub(r"\s+", " ", s).strip().title()

def to_int(v: str | None) -> int | None:
    if not v:
        return None
    try:
        n = int(round(float(str(v).replace(",", ""))))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None

def iso(d: str | None) -> str | None:
    if not d:
        return None
    m = re.search(r"([0-3]?\d)[/\-]([01]?\d)[/\-](\d{4})", d)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None

# Skeleton needles (Devanagari marks/spaces stripped) so spelling variants match:
# कल्पतर/कल्पतारु -> कलपतर ; रेडियंस/रेडियँस/रेिडयंस -> रडयस ; latin kept.
KALP_SK = ("कलपतर", "रडयस", "kalpataru", "radiance")

def classify(desc: str) -> str:
    sk = skeleton(desc)
    if any(n in sk for n in KALP_SK) or CTS5A.search(desc):
        return "kalpataru"
    if detect_wing(desc) and not OTHERB.search(desc):
        return "kalpataru"
    if NEIGH.search(desc):
        return "neighbour"
    if OTHERB.search(desc):
        return "other"
    return "uncertain"

def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"

def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"

def counts_sql() -> str:
    return (f"SELECT 'records', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'priced', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND consideration_amount IS NOT NULL"
            f"\nUNION ALL SELECT 'units_created', count(*)::text FROM building_units WHERE metadata->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'linked_records', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND building_unit_id IS NOT NULL\nORDER BY 1;")

def revert_sql() -> str:
    srcs = "', '".join((SOURCE,) + OLD_SOURCES)
    return (f"BEGIN;\n"
            f"DELETE FROM unit_registration_review_items WHERE raw_context->>'source' IN ('{srcs}');\n"
            f"DELETE FROM registration_party_contact_matches WHERE raw_context->>'source' IN ('{srcs}');\n"
            f"DELETE FROM unit_registration_parties WHERE raw_context->>'source' IN ('{srcs}');\n"
            f"DELETE FROM unit_registration_records WHERE raw_context->>'source' IN ('{srcs}');\n"
            f"DELETE FROM building_units WHERE metadata->>'source' IN ('{srcs}');\nCOMMIT;\n" + counts_sql())

def main() -> int:
    ap = argparse.ArgumentParser(description="Parse IGR .xls exports -> Kalpataru staging. Dry-run by default.")
    ap.add_argument("--xls-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--glob", default="SearchResult*.xls")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    BUILDING_Q = f"SELECT id FROM buildings WHERE name = {q(TARGET_BUILDING_NAME)} ORDER BY created_at LIMIT 1;"

    if args.revert:
        if not (args.apply and args.real_ok):
            _, c = run_psql(counts_sql()); print("Revert dry-run (deletes igr_xls + earlier IGR sources):\n" + c); return 0
        _, out = run_psql(revert_sql()); print("After revert:\n" + out); return 0

    files = sorted(Path(args.xls_dir).glob(args.glob))
    if not files:
        print(f"No files matching {args.glob} in {args.xls_dir}"); return 1

    COLS = ["srocode", "internaldocumentnumber", "docno", "docname", "registrationdate", "sroname",
            "sellerparty", "purchaserparty", "propertydescription", "areaname",
            "consideration_amt", "marketvalue", "dateofexecution", "stampdutypaid", "registrationfees", "status"]
    seen: set = set()
    kalp: list[dict] = []
    buckets = {"kalpataru": 0, "neighbour": 0, "other": 0, "uncertain": 0}
    uncertain_rows: list[list[str]] = []
    for f in files:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", load(f), re.S)
        if len(rows) < 2:
            continue
        hdr = [h.lower() for h in tcells(rows[0])]
        H = {h: i for i, h in enumerate(hdr)}
        if "propertydescription" not in H or "docno" not in H:
            continue
        get = lambda c, k: c[H[k]] if k in H and H[k] < len(c) else ""
        for r in rows[1:]:
            c = tcells(r)
            if len(c) <= H["propertydescription"]:
                continue
            uid = get(c, "internaldocumentnumber") or f"{get(c,'srocode')}|{get(c,'docno')}|{get(c,'registrationdate')[-4:]}"
            if uid in seen:
                continue
            seen.add(uid)
            desc = get(c, "propertydescription")
            b = classify(desc)
            buckets[b] += 1
            if b == "kalpataru":
                kalp.append({k: get(c, k) for k in COLS})
            elif b == "uncertain":
                uncertain_rows.append([get(c, "docno"), get(c, "registrationdate"), get(c, "sroname"), desc[:200]])

    # write uncertain review file (audit: confirm none are Kalpataru)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    review_path = REVIEW_DIR / "kalpataru_uncertain_review.csv"
    with review_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["docno", "registration_date", "sro", "property_description"])
        w.writerows(sorted(uncertain_rows, key=lambda r: r[1][-4:], reverse=True))

    yrs: dict[str, int] = {}
    towers: dict[str, int] = {}
    for r in kalp:
        yrs[r["registrationdate"][-4:]] = yrs.get(r["registrationdate"][-4:], 0) + 1
        w = detect_wing(r["propertydescription"])
        towers[w or "no-tower"] = towers.get(w or "no-tower", 0) + 1
    print(f"Parsed {len(files)} files -> {len(seen)} unique registrations.")
    print(f"buckets: {buckets}")
    print(f"KALPATARU: {len(kalp)} | by year: {dict(sorted(yrs.items()))}")
    print(f"  by tower: { {k: towers[k] for k in sorted(towers)} }")
    print(f"uncertain review CSV (verify none Kalpataru): {review_path} ({len(uncertain_rows)} rows)")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No DB writes. Writing requires --apply --real-ok.")
        return 0

    code, bid = run_psql(BUILDING_Q)
    if code or not bid:
        print(f"Refusing: building {TARGET_BUILDING_NAME!r} not found."); return 1
    bid = bid.splitlines()[0].strip()
    _, ux = run_psql(f"select id::text, coalesce(wing,''), coalesce(unit_number,'') from building_units where building_id='{bid}' and canonical_status='active';")
    existing: dict[tuple, str] = {}
    wlabel: dict[str, str] = {}
    for line in ux.splitlines():
        uid, wing, unum = (line.split("|") + ["", "", ""])[:3]
        letter = re.sub(r"[^A-Za-z]", "", wing)[-1:].upper() if wing else ""
        if unum:
            existing[(letter, unum.strip())] = uid
        if letter:
            wlabel.setdefault(letter, wing.strip())

    run_psql(revert_sql())
    BATCH = 60
    staged = 0
    for start in range(0, len(kalp), BATCH):
        chunk = kalp[start:start + BATCH]
        stmts = ["BEGIN;"]
        for r in chunk:
            desc = r["propertydescription"]
            wing = detect_wing(desc)
            letter = TOWER_OF.get(wing or "", "")
            pp = list_prop(desc)
            flat = pp.get("flat")
            etype, cat = classify_doctype(r["docname"])
            tag = {"source": SOURCE, "phase": PHASE, "wing": wing, "tower": letter or None, "doctype_raw": r["docname"],
                   "sro_raw": r["sroname"], "internal_doc": r["internaldocumentnumber"], "area": r["areaname"],
                   "is_fake": False, "is_sample": False, "external_calls_made": False,
                   "note": "IGR .xls export (price incl.); review-gated."}
            unit_ref = "NULL"
            if flat and letter and (letter, flat) in existing:
                unit_ref = f"'{existing[(letter, flat)]}'"
            elif flat and letter:
                wl = wlabel.get(letter, f"Tower {letter}")
                stmts.append(
                    f"INSERT INTO building_units (building_id, building_name, wing, unit_number, canonical_status, metadata) "
                    f"SELECT '{bid}', {q(TARGET_BUILDING_NAME)}, {q(wl)}, {q(flat)}, 'active', {jb(tag)} "
                    f"WHERE NOT EXISTS (SELECT 1 FROM building_units WHERE building_id='{bid}' AND wing={q(wl)} AND unit_number={q(flat)} AND metadata->>'source'='{SOURCE}');")
                unit_ref = (f"(SELECT id FROM building_units WHERE building_id='{bid}' AND wing={q(wl)} AND unit_number={q(flat)} "
                            f"AND metadata->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
            rdate = iso(r["registrationdate"])
            cons = to_int(r["consideration_amt"]) if cat != "tenancy" else to_int(r["consideration_amt"])
            stmts.append(
                "INSERT INTO unit_registration_records (building_id, building_unit_id, doc_number, registration_year, "
                "registration_date, sro_office, document_type, transaction_category, property_description_raw, wing_text, "
                "unit_text, floor_text, area_text, consideration_amount, market_value, stamp_duty, registration_fee, "
                "parse_confidence, verification_status, source_label, raw_context) VALUES ("
                f"'{bid}', {unit_ref}, {q(r['docno'])}, {(rdate[:4] if rdate else 'NULL')}, {q(rdate)}, {q(r['sroname'])}, "
                f"{q(etype)}, {q(cat)}, {q(desc)}, {q(wing)}, {q(flat)}, {q(pp.get('floor'))}, {q(pp.get('area_text'))}, "
                f"{q(to_int(r['consideration_amt']))}, {q(to_int(r['marketvalue']))}, {q(to_int(r['stampdutypaid']))}, "
                f"{q(to_int(r['registrationfees']))}, 0.7, 'parsed_candidate', 'IGR .xls export (CTS 260)', {jb(tag)});")
            rec = (f"(SELECT id FROM unit_registration_records WHERE doc_number={q(r['docno'])} AND building_id='{bid}' "
                   f"AND raw_context->>'internal_doc'={q(r['internaldocumentnumber'])} AND raw_context->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
            srole, brole = ROLE_BY_CATEGORY[cat]
            order = 0
            for nm, role in [(n, srole) for n in parse_name_array(r["sellerparty"])] + [(n, brole) for n in parse_name_array(r["purchaserparty"])]:
                eng = to_english(nm); dev = nm if DEV.search(nm) else None
                ptype = "company" if re.search(r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा|डेव्हलपर|बिल्डर", nm.lower()) else "individual"
                stmts.append(
                    "INSERT INTO unit_registration_parties (unit_registration_record_id, party_role, party_name_raw, "
                    "party_name_normalized, party_name_english, party_name_devanagari, party_type, display_order, raw_context) VALUES ("
                    f"{rec}, '{role}', {q(nm)}, {q(eng.lower())}, {q(eng)}, {q(dev)}, '{ptype}', {order}, {jb(tag)});")
                order += 1
            staged += 1
        stmts.append("COMMIT;")
        code, out = run_psql("\n".join(stmts))
        if code != 0:
            print(f"DB error in batch {start//BATCH}:\n{out}"); return code
        print(f"  staged {min(start+BATCH, len(kalp))}/{len(kalp)}")
    code, out = run_psql(counts_sql())
    print("Final (counts):\n" + out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
