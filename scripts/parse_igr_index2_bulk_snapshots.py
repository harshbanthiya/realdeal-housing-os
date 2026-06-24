#!/usr/bin/env python3
"""Parse IGR Index II bulk snapshot captures → staging records for all Kalpataru wings.

Reads capture_*_r*.txt files from exports/igr_index2_snapshots/*_bulk/ (produced by
fetch_igr_index2_bulk.py).  The .txt captures are the same text as pdftotext output,
so all parsing logic is imported from parse_igr_index2_pdfs.py — only the file reader
changes (no pdftotext needed).

Covers 2020-2026 across all 4 wings (A-Ora / B-Brilliance / C-Allura / D-Lumina).
For each doc_number already in the DB for Kalpataru → UPDATE price + parties (don't
overwrite existing names).  New docs → INSERT record + parties + review item.

Parties are written with the migration-050 columns: party_pan, party_age, party_address,
party_name_english (transliterated), party_name_devanagari (original Devanagari raw).

Tenancy: tenancy_start_date = execution date; tenancy_end_date = start + tenure_months
         (if parseable from field 4).  tenancy_monthly_rent / tenancy_deposit from field 4.

Dry-run by default.  Writing needs --apply AND --real-ok.  --revert deletes by source label.
NO scrape / external call (reads local snapshot .txt files only).
"""
from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
import json
import re
import sys
from datetime import date
from dateutil.relativedelta import relativedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from parse_igr_index2_pdfs import (  # noqa: E402
    split_fields, classify_doctype, detect_wing, translit,
    parse_parties, parse_property, iso, q, jb, clean_frag, num,
    ROLE_BY_CATEGORY, DEVANAGARI, PAN_RE,
)

PHASE = "6.23b"
SOURCE = "igr_index2_bulk_snapshots"
BUILDING_NAME = "Kalpataru Radiance"
WING_TOWER = {"Wing A-Ora": "A", "Wing B-Brilliance": "B", "Wing C-Allura": "C", "Wing D-Lumina": "D"}

BUILDING_SUB = f"(SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%' ORDER BY created_at LIMIT 1)"


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_index2_txt(path: Path) -> dict | None:
    text = read_txt(path)
    if "दस्त क्रमांक" not in text and "सूची" not in text:
        return None
    m = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    docno = m.group(1) if m else None
    year  = m.group(2) if m else None
    f = split_fields(text)
    dtype_raw = " ".join(clean_frag(f.get(1, "")).split()[:6])[:60]
    etype, cat = classify_doctype(dtype_raw)
    consideration = num(f.get(2, ""))
    market_value  = num(f.get(3, ""))
    prop = parse_property(f.get(4, ""))
    area = clean_frag(f.get(5, ""))[:60]
    sellers    = parse_parties(f.get(7, ""))
    purchasers = parse_parties(f.get(8, ""))
    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    dr = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(10, ""))
    stamp  = num(f.get(12, ""))
    regfee = num(f.get(13, ""))
    wing   = detect_wing(f.get(4, "")) or detect_wing(text)
    sro_m  = re.search(r"दुय्यम निबंधक\s*[:：]?\s*(.+)", text)
    sro    = sro_m.group(1).strip()[:120] if sro_m else None
    return {
        "file": path.name, "doc_no": docno, "year": year,
        "dtype_raw": dtype_raw, "etype": etype, "cat": cat,
        "consideration": consideration, "market_value": market_value,
        "stamp_duty": stamp, "reg_fee": regfee, "sro": sro,
        "area": area, "wing": wing,
        "date_exec": de.group(1) if de else None,
        "date_reg":  dr.group(1) if dr else None,
        "sellers": sellers, "purchasers": purchasers,
        **{f"prop_{k}": v for k, v in prop.items()},
    }


def end_date_from_start_and_months(start_iso: str | None, months_str: str | None) -> str | None:
    if not start_iso or not months_str:
        return None
    try:
        d = date.fromisoformat(start_iso) + relativedelta(months=int(months_str))
        return d.isoformat()
    except Exception:  # noqa: BLE001
        return None


def party_name_devanagari(raw: str) -> str | None:
    return raw if DEVANAGARI.search(raw) else None


def party_name_english(raw: str) -> str:
    tr = translit(raw)
    # title-case the transliteration for readability
    return tr.title() if tr else raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-root", default=str(SNAPSHOT_ROOT))
    ap.add_argument("--year", help="Filter to a specific year folder (e.g. 2024)")
    ap.add_argument("--apply",   action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert",  action="store_true")
    args = ap.parse_args()

    snap_root = Path(args.snapshot_root)

    def counts_sql() -> str:
        return (
            f"SELECT 'records' AS what, count(*)::text FROM unit_registration_records"
            f"  WHERE raw_context->>'source'='{SOURCE}'\n"
            f"UNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties"
            f"  WHERE raw_context->>'source'='{SOURCE}'\n"
            f"UNION ALL SELECT 'with_pan', count(*)::text FROM unit_registration_parties"
            f"  WHERE raw_context->>'source'='{SOURCE}' AND party_pan IS NOT NULL\n"
            f"UNION ALL SELECT 'with_price', count(*)::text FROM unit_registration_records"
            f"  WHERE raw_context->>'source'='{SOURCE}' AND consideration_amount IS NOT NULL\n"
            f"ORDER BY 1;"
        )

    if args.revert:
        if not (args.apply and args.real_ok):
            _, cur = run_psql(counts_sql())
            print("Revert dry-run (would delete):\n" + cur + "\nNeeds --revert --apply --real-ok.")
            return 0
        sql = (
            "BEGIN;\n"
            f"DELETE FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}';\n"
            f"DELETE FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}';\n"
            "COMMIT;\n" + counts_sql()
        )
        _, out = run_psql(sql)
        print("After revert:\n" + out)
        return 0

    # Discover snapshot folders
    folders = sorted(snap_root.glob("*_bulk/"))
    if args.year:
        folders = [f for f in folders if f"_kalpataru_{args.year}_" in f.name]
    if not folders:
        print(f"No *_bulk/ folders in {snap_root}"); return 1

    # Parse all Index II .txt captures (capture_*_r*.txt = popup captures)
    all_parsed: list[dict] = []
    for folder in folders:
        txts = sorted(folder.glob("capture_*_r*.txt"))
        print(f"  {folder.name}: {len(txts)} Index II .txt captures")
        for p in txts:
            r = parse_index2_txt(p)
            if r:
                r["_folder"] = folder.name
                all_parsed.append(r)
            else:
                print(f"    SKIP (not Index II): {p.name}")

    # Count by wing
    by_wing: dict[str, int] = {}
    for r in all_parsed:
        k = r["wing"] or "undetected"
        by_wing[k] = by_wing.get(k, 0) + 1

    kalpataru = [r for r in all_parsed if r["wing"] in WING_TOWER]
    other     = [r for r in all_parsed if r["wing"] not in WING_TOWER]

    print(f"\nParsed {len(all_parsed)} Index II captures total")
    for k, v in sorted(by_wing.items(), key=lambda kv: -kv[1]):
        mark = " ← Kalpataru" if k in WING_TOWER else ""
        print(f"  {v:3d}  {k}{mark}")
    print(f"\nKalpataru (all wings): {len(kalpataru)}   Other/undetected: {len(other)}")

    if not (args.apply and args.real_ok):
        print("\nDry run — no DB writes. Add --apply --real-ok to stage.")
        print("\nSample (first 5 Kalpataru):")
        for r in kalpataru[:5]:
            print(f"  doc {r['doc_no']}/{r['year']}  {r['etype']:20s}  {r['wing']:20s}  "
                  f"flat={r['prop_flat']}  consid={r['consideration']}  "
                  f"stamp={r['stamp_duty']}  rent={r['prop_rent']}  deposit={r['prop_deposit']}  "
                  f"sellers={len(r['sellers'])}  purchasers={len(r['purchasers'])}")
        return 0

    # Find which doc_numbers already exist for this building
    if not kalpataru:
        print("Nothing to stage."); return 0

    docnos_q = ",".join(q(r["doc_no"]) for r in kalpataru if r["doc_no"])
    _, ex_out = run_psql(
        f"SELECT doc_number FROM unit_registration_records "
        f"WHERE building_id={BUILDING_SUB} AND doc_number IN ({docnos_q});"
    )
    existing = {l.strip() for l in ex_out.splitlines() if l.strip()}
    print(f"\nExisting records for these doc_numbers: {len(existing)} (will UPDATE price+parties only)")
    print(f"New records to INSERT: {len([r for r in kalpataru if r['doc_no'] not in existing])}")

    stmts = ["BEGIN;"]
    inserted = updated = 0

    for r in kalpataru:
        tower   = WING_TOWER.get(r["wing"], "A")
        flat    = r["prop_flat"]
        cons    = r["consideration"] if r["consideration"] not in (None, "0") else None
        rent    = r["prop_rent"]    if r["cat"] == "tenancy" else None
        dep     = r["prop_deposit"] if r["cat"] == "tenancy" else None
        d_exec  = iso(r["date_exec"])
        d_reg   = iso(r["date_reg"]) or d_exec
        t_end   = end_date_from_start_and_months(d_exec, r.get("prop_tenure_months"))

        tag = {
            "source": SOURCE, "phase": PHASE, "building_label": BUILDING_NAME,
            "is_fake": False, "src_file": r["file"], "folder": r["_folder"],
            "doctype_raw": r["dtype_raw"], "wing_label": r["wing"],
            "external_calls_made": False,
            "note": "IGR Index II bulk snapshot parse (2020-2026, all wings).",
        }

        srole, brole = ROLE_BY_CATEGORY.get(r["cat"], ("seller", "purchaser"))

        if r["doc_no"] in existing:
            # UPDATE: enrich existing record with price / tenancy fields / reg_fee
            stmts.append(
                "UPDATE unit_registration_records SET "
                f"consideration_amount = COALESCE({q(cons)}, consideration_amount), "
                f"market_value = COALESCE({q(r['market_value'])}, market_value), "
                f"stamp_duty = COALESCE({q(r['stamp_duty'])}, stamp_duty), "
                f"registration_fee = COALESCE({q(r['reg_fee'])}, registration_fee), "
                f"tenancy_monthly_rent = COALESCE({q(rent)}, tenancy_monthly_rent), "
                f"tenancy_deposit = COALESCE({q(dep)}, tenancy_deposit), "
                f"tenancy_start_date = COALESCE(tenancy_start_date, {q(d_exec)}), "
                f"tenancy_end_date = COALESCE(tenancy_end_date, {q(t_end)}), "
                f"area_text = COALESCE(area_text, {q(r['area'])}), "
                f"sro_office = COALESCE(sro_office, {q(r['sro'])}), "
                f"parse_confidence = 0.75, "
                f"raw_context = raw_context || {jb({'index2_bulk_enriched': True, 'source_snapshot': r['_folder']})} "
                f"WHERE building_id={BUILDING_SUB} AND doc_number={q(r['doc_no'])};"
            )
            # Add parties with PAN if not already present
            rec = (f"(SELECT id FROM unit_registration_records "
                   f"WHERE building_id={BUILDING_SUB} AND doc_number={q(r['doc_no'])} "
                   f"ORDER BY created_at LIMIT 1)")
            order = 100  # append after existing parties
            for party, role in ([(p, srole) for p in r["sellers"]] + [(p, brole) for p in r["purchasers"]]):
                if not party.get("pan"):
                    continue  # only insert parties that add new PAN data
                pdev = party_name_devanagari(party["name"])
                peng = party_name_english(party["name"])
                ptag = dict(tag); ptag.update({"age": party["age"], "pan": party["pan"]})
                stmts.append(
                    "INSERT INTO unit_registration_parties "
                    "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
                    "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
                    "party_type, display_order, raw_context) "
                    f"SELECT {rec}, {q(role)}, {q(party['name'])}, {q(translit(party['name']))}, "
                    f"{q(peng)}, {q(pdev)}, {q(party['pan'])}, "
                    f"{'NULL' if not party.get('age') else party['age']}, "
                    f"{q(party.get('address'))}, 'individual', {order}, {jb(ptag)} "
                    f"WHERE NOT EXISTS ("
                    f"  SELECT 1 FROM unit_registration_parties "
                    f"  WHERE unit_registration_record_id={rec} AND party_pan={q(party['pan'])}"
                    f");"
                )
                order += 1
            updated += 1
            continue

        # INSERT new record
        # Try to link to existing unit
        unit_sub = "NULL"
        if flat and tower:
            unit_sub = (
                f"(SELECT id FROM building_units "
                f"WHERE building_id={BUILDING_SUB} AND wing={q(tower)} AND unit_number={q(flat)} "
                f"ORDER BY created_at LIMIT 1)"
            )

        stmts.append(
            "INSERT INTO unit_registration_records "
            "(building_id, building_unit_id, doc_number, registration_year, registration_date, "
            "sro_office, document_type, transaction_category, property_description_raw, "
            "wing_text, unit_text, floor_text, area_text, "
            "consideration_amount, market_value, stamp_duty, registration_fee, "
            "tenancy_monthly_rent, tenancy_deposit, tenancy_start_date, tenancy_end_date, "
            "parse_confidence, verification_status, source_label, raw_context) VALUES ("
            f"{BUILDING_SUB}, {unit_sub}, {q(r['doc_no'])}, "
            f"{'NULL' if not r['year'] else r['year']}, {q(d_reg)}, {q(r['sro'])}, "
            f"{q(r['etype'])}, {q(r['cat'])}, {q(r['prop_raw'])}, "
            f"{q(r['wing'])}, {q(flat)}, {q(r['prop_floor'])}, {q(r['area'])}, "
            f"{q(cons)}, {q(r['market_value'])}, {q(r['stamp_duty'])}, {q(r['reg_fee'])}, "
            f"{q(rent)}, {q(dep)}, {q(d_exec)}, {q(t_end)}, "
            f"0.75, 'parsed_candidate', 'IGR Index II bulk 2020-2026', {jb(tag)});"
        )

        rec = (f"(SELECT id FROM unit_registration_records "
               f"WHERE building_id={BUILDING_SUB} AND doc_number={q(r['doc_no'])} "
               f"AND raw_context->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")

        order = 0
        for party, role in ([(p, srole) for p in r["sellers"]] + [(p, brole) for p in r["purchasers"]]):
            pdev = party_name_devanagari(party["name"])
            peng = party_name_english(party["name"])
            ptag = dict(tag); ptag.update({"age": party["age"], "pan": party["pan"]})
            ptype = "company" if re.search(
                r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा", party["name"].lower()
            ) else "individual"
            stmts.append(
                "INSERT INTO unit_registration_parties "
                "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
                "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
                "party_type, display_order, raw_context) VALUES ("
                f"{rec}, {q(role)}, {q(party['name'])}, {q(translit(party['name']))}, "
                f"{q(peng)}, {q(pdev)}, {q(party.get('pan'))}, "
                f"{'NULL' if not party.get('age') else party['age']}, "
                f"{q(party.get('address'))}, {q(ptype)}, {order}, {jb(ptag)});"
            )
            order += 1

        stmts.append(
            "INSERT INTO unit_registration_review_items "
            "(building_id, unit_registration_record_id, review_type, status, priority, decision_notes, raw_context) "
            f"VALUES ({BUILDING_SUB}, {rec}, 'registration_record_review', 'pending', 'normal', "
            f"'IGR Index II bulk parse (2020-2026); verify parties and PAN.', {jb(tag)});"
        )
        inserted += 1

    stmts.append("COMMIT;")
    stmts.append(counts_sql())

    print(f"\nAbout to run: {inserted} INSERTs + {updated} UPDATEs ({len(stmts)} SQL statements)")
    code, out = run_psql("\n".join(stmts))
    if code == 0:
        print("Done. Counts:\n" + out)
    else:
        print("DB error:\n" + out)
    return code


if __name__ == "__main__":
    sys.exit(main())
