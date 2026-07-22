#!/usr/bin/env python3
"""Parse Ekta Tripolis Index II targeted captures → tenancy dates on existing records.

Reads capture_*_doc*_r*.txt from exports/igr_index2_snapshots_ekta/*_bulk/
(produced by fetch_igr_docno_targeted.py --building ekta). All Ekta doc_numbers
already exist from the paid-search ingest (6.27), so this is UPDATE-only:
tenancy_start_date (= execution date), tenancy_end_date (= start + tenure months),
tenancy_monthly_rent, tenancy_deposit, plus PAN-bearing parties.

Once tenancy_end_date lands, vw_tenancy_expiring_soon picks Ekta up automatically.

Dry-run by default; --apply --real-ok to write. No external calls.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql
from parse_igr_index2_pdfs import (  # noqa: E402
    split_fields, classify_doctype, translit, parse_parties, parse_property,
    iso, q, jb, clean_frag, num, ROLE_BY_CATEGORY, DEVANAGARI,
)
from parse_igr_index2_bulk_snapshots import end_date_from_start_and_months  # noqa: E402
from ingest_igr_paid_search_ekta import EKTA_RE, EKTA_SUB  # noqa: E402

SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots_ekta"
SOURCE = "igr_index2_ekta_targeted"
PHASE = "6.28"


_EN_PARTY_RE = re.compile(
    r"Name:\s*(.+?)\s+Age:\s*(\d+)\s+Address:\s*(.+?)\s*PAN:\s*([A-Z]{5}\d{4}[A-Z])", re.S)


def parse_capture_english(text: str, fname: str) -> dict | None:
    """eSearch English Index-2 (eRegistration docs): rent schedule, deposit,
    'Leave and License Months:NN', PAN parties."""
    m = re.search(r"Doc No\.?\s*:\s*(\d+)\s*/\s*(\d{4})", text)
    if not m:
        return None
    if not EKTA_RE.search(text):
        return {"doc_no": m.group(1), "year": m.group(2), "file": fname, "_not_ekta": True}
    art = re.search(r"\(1\)\s*Article\s*(.+)", text)
    cat = "tenancy" if art and re.search(r"leave and licen", art.group(1), re.I) else "other"
    dep = re.search(r"\(2\)\s*Deposit\s*Rs\.?\s*([\d,]+)", text)
    rent = re.search(r"\(3\)\s*Rent.{0,40}?Rs\.?\s*([\d,]+)", text, re.S)
    months = re.search(r"Leave and License Months\s*:\s*(\d+)", text)
    de = re.search(r"\(9\)\s*Date of Execution\s*([0-3]?\d/[01]?\d/\d{4})", text)
    stamp = re.search(r"\(12\)\s*Stamp Duty\s*Rs\.?\s*([\d,]+)", text)
    fee = re.search(r"\(13\)\s*Registration Fee\s*Rs\.?\s*([\d,]+)", text)
    flat_m = re.search(r"Apartment/Flat No\s*:\s*([A-C])[\s\-/]*(\d{2,4})", text, re.I)
    d_exec = iso(de.group(1)) if de else None

    def sect(n): return re.search(rf"\({n}\)[^\n]*\n(.*?)(?=\(\d+\)|\Z)", text, re.S)
    parties = {"sellers": [], "purchasers": []}
    for key, n in (("sellers", 7), ("purchasers", 8)):
        s = sect(n)
        if s:
            for nm, age, addr, pan in _EN_PARTY_RE.findall(s.group(1)):
                parties[key].append({"name": nm.strip(), "age": age,
                                     "address": addr.strip()[:300], "pan": pan})
    return {
        "doc_no": m.group(1), "year": m.group(2), "file": fname, "cat": cat,
        "rent": rent.group(1).replace(",", "") if rent else None,
        "deposit": dep.group(1).replace(",", "") if dep else None,
        "start": d_exec,
        "end": end_date_from_start_and_months(d_exec, months.group(1) if months else None),
        "tenure_months": months.group(1) if months else None,
        "stamp": stamp.group(1).replace(",", "") if stamp else None,
        "regfee": fee.group(1).replace(",", "") if fee else None,
        "wing": flat_m.group(1).upper() if flat_m else None,
        "flat": flat_m.group(2) if flat_m else None,
        "sellers": parties["sellers"], "purchasers": parties["purchasers"],
    }


def parse_capture(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "दस्त क्रमांक" not in text and "सूची" not in text:
        return parse_capture_english(text, path.name)
    m = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    if not m:
        return None
    f = split_fields(text)
    prop_raw = f.get(4, "")
    if not EKTA_RE.search(prop_raw) and not EKTA_RE.search(text):
        return {"doc_no": m.group(1), "year": m.group(2), "file": path.name, "_not_ekta": True}
    dtype_raw = " ".join(clean_frag(f.get(1, "")).split()[:6])[:60]
    _, cat = classify_doctype(dtype_raw)
    prop = parse_property(prop_raw)
    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    d_exec = iso(de.group(1)) if de else None
    return {
        "doc_no": m.group(1), "year": m.group(2), "file": path.name,
        "cat": cat, "rent": prop["rent"], "deposit": prop["deposit"],
        "start": d_exec,
        "end": end_date_from_start_and_months(d_exec, prop["tenure_months"]),
        "tenure_months": prop["tenure_months"],
        "wing": None, "flat": None,
        "stamp": num(f.get(12, "")), "regfee": num(f.get(13, "")),
        "sellers": parse_parties(f.get(7, "")), "purchasers": parse_parties(f.get(8, "")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-root", default=str(SNAPSHOT_ROOT))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    root = Path(args.snapshot_root)
    txts = sorted(root.glob("*_bulk/capture_*_r*.txt"))
    if not txts:
        print(f"No captures under {root} — run fetch_igr_docno_targeted.py --building ekta --apply first.")
        return 0

    parsed, not_ekta, skipped = [], [], 0
    for p in txts:
        r = parse_capture(p)
        if r is None:
            skipped += 1
        elif r.get("_not_ekta"):
            not_ekta.append(r)
        else:
            parsed.append(r)

    print(f"Captures: {len(txts)}  parsed: {len(parsed)}  not-Ekta (set aside): {len(not_ekta)}  unreadable: {skipped}")
    for r in not_ekta:
        print(f"  NOT EKTA — doc {r['doc_no']}/{r['year']} ({r['file']}) — record left untouched")
    for r in parsed:
        print(f"  doc {r['doc_no']}/{r['year']}  cat={r['cat']}  rent={r['rent']}  "
              f"deposit={r['deposit']}  start={r['start']}  end={r['end']} ({r['tenure_months']} mo)")

    if not (args.apply and args.real_ok):
        print("\nDry run — add --apply --real-ok to write.")
        return 0
    if not parsed:
        print("Nothing to write.")
        return 0

    stmts = ["BEGIN;"]
    for r in parsed:
        tag = {"source": SOURCE, "phase": PHASE, "src_file": r["file"]}
        unit_fix = ""
        if r.get("wing") and r.get("flat"):
            unit_fix = (
                f"building_unit_id = COALESCE(building_unit_id, "
                f"(SELECT id FROM building_units WHERE building_id={EKTA_SUB} "
                f"AND unit_number={q(r['wing'] + '-' + r['flat'])} LIMIT 1)), "
                f"wing_text = COALESCE(wing_text, {q(r['wing'])}), "
                f"unit_text = COALESCE(unit_text, {q(r['flat'])}), ")
        stmts.append(
            "UPDATE unit_registration_records SET "
            f"{unit_fix}"
            f"tenancy_monthly_rent = COALESCE(tenancy_monthly_rent, {q(r['rent'])}), "
            f"tenancy_deposit = COALESCE(tenancy_deposit, {q(r['deposit'])}), "
            f"tenancy_start_date = COALESCE(tenancy_start_date, {q(r['start'])}), "
            f"tenancy_end_date = COALESCE(tenancy_end_date, {q(r['end'])}), "
            f"stamp_duty = COALESCE(stamp_duty, {q(r['stamp'])}), "
            f"registration_fee = COALESCE(registration_fee, {q(r['regfee'])}), "
            f"raw_context = raw_context || {jb({'index2_enriched': True, 'src_file': r['file']})} "
            f"WHERE building_id={EKTA_SUB} AND doc_number={q(r['doc_no'])} "
            f"AND registration_year = {r['year']};"
        )
        rec = (f"(SELECT id FROM unit_registration_records "
               f"WHERE building_id={EKTA_SUB} AND doc_number={q(r['doc_no'])} "
               f"AND registration_year = {r['year']} LIMIT 1)")
        srole, brole = ROLE_BY_CATEGORY.get(r["cat"], ("seller", "purchaser"))
        order = 200  # append after paid-search parties
        for party, role in [(p, srole) for p in r["sellers"]] + [(p, brole) for p in r["purchasers"]]:
            if not party.get("pan"):
                continue  # Index II adds value via PAN/address; names already loaded from paid search
            pdev = party["name"] if DEVANAGARI.search(party["name"]) else None
            stmts.append(
                "INSERT INTO unit_registration_parties "
                "(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
                "party_name_english, party_name_devanagari, party_pan, party_age, party_address, "
                "party_type, display_order, raw_context) "
                f"SELECT {rec}, {q(role)}, {q(party['name'])}, {q(translit(party['name']))}, "
                f"{q(translit(party['name']).title())}, {q(pdev)}, {q(party['pan'])}, "
                f"{'NULL' if not party.get('age') else party['age']}, {q(party.get('address'))}, "
                f"'individual', {order}, {jb(tag)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM unit_registration_parties "
                f"  WHERE unit_registration_record_id={rec} AND party_pan={q(party['pan'])});"
            )
            order += 1
    stmts.append("COMMIT;")

    code, out = run_psql("\n".join(stmts))
    if code != 0:
        print("DB error:\n" + out[-3000:])
        return 1
    _, chk = run_psql(
        f"SELECT count(*) FILTER (WHERE tenancy_end_date IS NOT NULL), count(*) "
        f"FROM unit_registration_records WHERE building_id={EKTA_SUB} AND transaction_category='tenancy';"
        f"SELECT count(*) FROM vw_tenancy_expiring_soon WHERE building_name='Ekta Tripolis';")
    lines = [l.strip() for l in chk.strip().splitlines() if l.strip()]
    print(f"Done. Ekta tenancy with end-date: {lines[0] if lines else '?'}  "
          f"| in expiring-soon view: {lines[1] if len(lines) > 1 else '?'}")
    return 0


def _demo() -> None:
    assert end_date_from_start_and_months("2026-01-15", "11") == "2026-12-15"
    assert end_date_from_start_and_months(None, "11") is None
    assert end_date_from_start_and_months("2026-01-15", None) is None
    print("parse_igr_index2_ekta self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        sys.exit(main())
