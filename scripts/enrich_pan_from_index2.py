#!/usr/bin/env python3
"""Phase 6.25 — MVP: populate PAN (+ age/address) on existing registration parties from Index II.

The canonical building's registration parties carry names (from the .xls list) but no PAN. The
operator-downloaded Index II PDFs hold the PAN/age/address per party. This script reads those PDFs,
matches each to its already-staged canonical record by (doc number, year), aligns the Index II
parties to the existing party rows (by role, then name similarity), and writes:

  unit_registration_parties.party_pan / party_age / party_address
  unit_registration_parties.pan_entity_type   (P=individual, C=company, F=firm/LLP, H=HUF, T=trust…)
  unit_registration_parties.pan_format_valid  (^[A-Z]{5}[0-9]{4}[A-Z]$)
  unit_registration_parties.pan_enriched_at

It also backfills the record's price / area / rent / licence-period when those are still NULL (Index II
is the authoritative source), and appends ONE row to pan_access_log (purpose-limitation audit).

NO external calls — no GST / Income-Tax / MCA lookups (entity type is pure PAN format). Reads local
PDFs only. Dry-run by default; writing needs --apply AND --real-ok; fully reversible via --revert
(only rows stamped raw_context.pan_enriched_phase='6.25'). Requires: pdftotext + indic-transliteration.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent

import difflib  # noqa: E402

from parse_igr_index2_pdfs import (  # noqa: E402
    parse_index2, translit, run_psql, ROLE_BY_CATEGORY, iso, q, jb,
    pdftext, split_fields, classify_doctype, num,
)

PHASE = "6.25"
ACTOR = "operator:harsh"
PURPOSE = "KYC-style party enrichment (entity-type signal) for lead qualification; consent-gated for outreach"
BUILDING = "Kalpataru Radiance"
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
ENTITY = {"P": "individual", "C": "company", "H": "huf", "F": "firm_llp", "A": "aop", "T": "trust",
          "B": "body_of_individuals", "L": "local_authority", "J": "artificial_juridical", "G": "government"}
# default inputs (operator's Index II drop)
DL = Path.home() / "Downloads"
DEFAULT_PATHS = [
    DL / "Index-II 999.pdf", DL / "Index-II 3052.pdf", DL / "Index-II 5055.pdf",
    DL / "Kalpataru Radiance Tower A" / "2026" / "Page 1",
]


def entity_type(pan: str) -> str | None:
    return ENTITY.get(pan[3], "other") if PAN_RE.match(pan or "") else None


def norm(name: str) -> str:
    """Cross-script name key: transliterate Devanagari->latin, drop everything but a-z0-9.

    Defeats both pdftotext's matra reordering and the .xls 'no-spaces' concatenation, and lets a
    Devanagari party name compare against an English Index II name."""
    return re.sub(r"[^a-z0-9]", "", translit(name or ""))


def confidence(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def parse_html_print(path: Path) -> dict | None:
    """Fallback for browser 'print to PDF' Index II (English labels: Name:/Age:/Address:/PAN:).

    Roles split on the (8) field marker; each name takes the nearest following PAN (PANs often spill
    past the field boundary in this layout)."""
    t = re.sub(r"\s+", " ", pdftext(path))
    m = re.search(r"Doc No\.?\s*:\s*(\d+)\s*/\s*(\d{4})", t)
    if not m:
        return None
    docno, year = m.group(1), m.group(2)
    fields = split_fields(t)
    cat = classify_doctype(t)[1]
    # PANs (with global positions) — licensee PAN often spills past its field boundary.
    pans = [(pm.start(), pm.group(1)) for pm in re.finditer(r"PAN\s*:\s*([A-Z]{5}[0-9]{4}[A-Z])", t)]

    def parties_in(seg: str) -> list[dict]:
        out = []
        for nm in re.finditer(r"Name\s*:\s*(.+?)\s*Age\s*:\s*(\d+)", seg):  # only real party blocks (Name->Age->digits)
            name = nm.group(1).strip()[:200]
            gpos = t.find(name)                                            # approx global position for PAN proximity
            follow = [p for p in pans if p[0] > gpos] if gpos >= 0 else []
            am = re.search(r"Address\s*:\s*(.+?)(?=\s*(?:PAN:|Name:)|$)", seg[nm.start():nm.start() + 400])
            out.append({"name": name, "age": nm.group(2),
                        "pan": follow[0][1] if follow else None,
                        "address": am.group(1).strip()[:400] if am else None})
        return out

    sellers = parties_in(fields.get(7, ""))
    purchasers = parties_in(fields.get(8, ""))
    return {"doc_no": docno, "year": year, "cat": cat, "wing": None,
            "consideration": num(fields.get(2, "")), "market_value": num(fields.get(3, "")),
            "stamp_duty": num(fields.get(12, "")), "reg_fee": num(fields.get(13, "")),
            "area": None, "date_exec": None, "date_reg": None,
            "sellers": sellers, "purchasers": purchasers,
            "prop_rent": None, "prop_deposit": None, "prop_tenure_months": None}


def parse_any(path: Path) -> dict | None:
    return parse_index2(path) or parse_html_print(path)


def gather(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files += [f for f in p.iterdir() if f.name.lower().startswith("index22")]
        elif p.exists():
            files.append(p)
    return sorted(set(files))


def doc_from_name(name: str) -> str | None:
    m = re.search(r"(\d{2,6})", name)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Enrich registration parties with PAN from Index II (dry-run default).")
    ap.add_argument("--path", action="append", default=[], help="file or dir (repeatable); defaults to operator drop")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    code, bid = run_psql(f"SELECT id FROM buildings WHERE name='{BUILDING}' ORDER BY created_at LIMIT 1;")
    if code or not bid:
        print(f"Refusing: building {BUILDING!r} not found."); return 1
    bid = bid.splitlines()[0]

    def coverage() -> str:
        _, c = run_psql(
            f"SELECT count(p.party_pan)||'/'||count(*)||' parties with PAN' FROM unit_registration_parties p "
            f"JOIN unit_registration_records r ON r.id=p.unit_registration_record_id WHERE r.building_id='{bid}';")
        return c

    if args.revert:
        if not (args.apply and args.real_ok):
            _, n = run_psql(f"SELECT count(*) FROM unit_registration_parties WHERE raw_context->>'pan_enriched_phase'='{PHASE}';")
            print(f"Revert dry-run: would clear PAN enrichment on {n} parties + delete this phase's access-log rows.")
            print("Coverage now: " + coverage()); return 0
        sql = ("BEGIN;\n"
               f"UPDATE unit_registration_parties SET party_pan=NULL, party_age=NULL, party_address=NULL, "
               f"pan_entity_type=NULL, pan_format_valid=NULL, pan_enriched_at=NULL, "
               f"raw_context = raw_context - 'pan_enriched_phase' - 'pan_name_match_conf' "
               f"WHERE raw_context->>'pan_enriched_phase'='{PHASE}';\n"
               f"DELETE FROM pan_access_log WHERE raw_context->>'phase'='{PHASE}';\nCOMMIT;")
        c, out = run_psql(sql)
        print(("Revert failed:\n" + out) if c else ("Reverted. Coverage now: " + coverage())); return c

    files = gather([Path(p) for p in args.path] or DEFAULT_PATHS)
    if not files:
        print("No Index II files found."); return 1

    plans = []          # per-party update plan
    record_backfill = []
    unmatched = []
    docs_seen = []
    for f in files:
        d = parse_any(f)
        if not d:
            print(f"  skip (not Index II): {f.name}"); continue
        docno = d["doc_no"] or doc_from_name(f.name)
        year = d["year"]
        if not docno:
            print(f"  skip (no doc number): {f.name}"); continue
        docs_seen.append(docno)
        # locate the canonical record (prefer wing match if several share the doc number)
        yflt = f"AND registration_year={year}" if year else ""
        _, recs = run_psql(
            f"SELECT id, coalesce(transaction_category,''), coalesce(wing_text,''), coalesce(unit_text,'') "
            f"FROM unit_registration_records WHERE building_id='{bid}' AND doc_number='{docno}' {yflt} ORDER BY created_at;")
        rlist = [ln.split("|") for ln in recs.splitlines() if ln]
        if not rlist:
            print(f"  doc {docno}/{year}: no canonical record (skip)"); continue
        rec = next((r for r in rlist if d["wing"] and d["wing"] in r[2]), rlist[0])
        rid, cat = rec[0], (rec[1] or d["cat"] or "other")
        srole, brole = ROLE_BY_CATEGORY.get(cat, ("seller", "purchaser"))

        # existing party rows for this record, grouped by role
        _, prows = run_psql(
            f"SELECT id, party_role, display_order, coalesce(party_name_devanagari,''), "
            f"coalesce(party_name_english,party_name_normalized,'') FROM unit_registration_parties "
            f"WHERE unit_registration_record_id='{rid}' ORDER BY display_order;")
        existing = {"_": []}
        for ln in prows.splitlines():
            pid, role, order, dev, eng = (ln.split("|") + [""] * 5)[:5]
            existing.setdefault(role, []).append({"id": pid, "name": dev or eng})

        for idx_parties, role in ((d["sellers"], srole), (d["purchasers"], brole)):
            pool = list(existing.get(role, []))
            for ip in idx_parties:
                pan = (ip.get("pan") or "").strip().upper()
                if not pool:
                    if pan:
                        unmatched.append((docno, role, ip.get("name"), pan))
                    continue
                # best name match in the role pool
                best = max(pool, key=lambda e: confidence(e["name"], ip.get("name", "")))
                conf = confidence(best["name"], ip.get("name", ""))
                # accept by name OR, if the role has exactly one party each side, by position
                if conf < 0.2 and not (len(idx_parties) == 1 and len(existing.get(role, [])) == 1):
                    if pan:
                        unmatched.append((docno, role, ip.get("name"), pan))
                    continue
                pool.remove(best)
                plans.append({"pid": best["id"], "doc": docno, "role": role, "exist": best["name"],
                              "idx_name": ip.get("name"), "pan": pan or None,
                              "etype": entity_type(pan), "valid": bool(PAN_RE.match(pan)),
                              "age": ip.get("age"), "addr": ip.get("address"), "conf": round(conf, 2)})
        # record-level backfill (only fills NULLs)
        record_backfill.append({"rid": rid, "doc": docno, "consideration": d["consideration"], "market": d["market_value"],
                                "stamp": d["stamp_duty"], "regfee": d["reg_fee"], "area": d["area"],
                                "rent": d.get("prop_rent"), "deposit": d.get("prop_deposit"),
                                "tenure": d.get("prop_tenure_months"), "dexec": iso(d["date_exec"]),
                                "cat": cat})

    pan_plans = [p for p in plans if p["pan"]]
    print(f"\nIndex II files parsed: {len(files)}   docs matched to canonical records: {len(set(docs_seen))}")
    print(f"Party PAN assignments: {len(pan_plans)}   unmatched PANs (flagged, not assigned): {len(unmatched)}")
    from collections import Counter
    et = Counter(p["etype"] for p in pan_plans)
    print(f"Entity-type breakdown: {dict(et)}")
    print("\n  doc   role      conf  existing-name -> index2-name           PAN(masked)   type")
    for p in sorted(pan_plans, key=lambda x: (x["doc"], x["role"]))[:60]:
        mask = p["pan"][:5] + "****" + p["pan"][9] if p["valid"] else "(bad)"
        print(f"  {p['doc']:>5} {p['role']:<9} {p['conf']:<4}  {p['exist'][:24]:<24} -> {p['idx_name'][:22]:<22} {mask}  {p['etype']}")
    if unmatched:
        print("\n  Unmatched PANs (operator review — name didn't align):")
        for doc, role, nm, pan in unmatched[:20]:
            print(f"    doc {doc} {role}: {nm[:30]} {pan[:5]}****{pan[9] if PAN_RE.match(pan) else ''}")

    if not (args.apply and args.real_ok):
        print("\nDry run only — NO DB writes. To execute: --apply --real-ok  (reverse: --revert --apply --real-ok)")
        return 0

    stmts = ["BEGIN;"]
    for p in pan_plans:
        ctx = {"pan_enriched_phase": PHASE, "pan_name_match_conf": p["conf"], "pan_source": "index2"}
        sets = [f"party_pan='{p['pan']}'", f"pan_entity_type={q(p['etype'])}", f"pan_format_valid={'true' if p['valid'] else 'false'}",
                "pan_enriched_at=now()", f"raw_context = coalesce(raw_context,'{{}}'::jsonb) || {jb(ctx)}"]
        if p["age"]:
            sets.append(f"party_age={int(p['age'])}")
        if p["addr"]:
            sets.append(f"party_address={q(p['addr'][:400])}")
        stmts.append(f"UPDATE unit_registration_parties SET {', '.join(sets)} WHERE id='{p['pid']}';")
    # record backfill — only overwrite NULLs
    for r in record_backfill:
        sets = []
        if r["consideration"]: sets.append(f"consideration_amount=coalesce(consideration_amount,{r['consideration']})")
        if r["market"]:        sets.append(f"market_value=coalesce(market_value,{r['market']})")
        if r["stamp"]:         sets.append(f"stamp_duty=coalesce(stamp_duty,{r['stamp']})")
        if r["regfee"]:        sets.append(f"registration_fee=coalesce(registration_fee,{r['regfee']})")
        if r["area"]:          sets.append(f"area_text=coalesce(area_text,{q(r['area'])})")
        if r["cat"] == "tenancy":
            if r["rent"]:    sets.append(f"tenancy_monthly_rent=coalesce(tenancy_monthly_rent,{int(r['rent'])})")
            if r["deposit"]: sets.append(f"tenancy_deposit=coalesce(tenancy_deposit,{int(r['deposit'])})")
            if r["dexec"] and r["tenure"]:
                sets.append(f"tenancy_start_date=coalesce(tenancy_start_date,'{r['dexec']}')")
                sets.append(f"tenancy_end_date=coalesce(tenancy_end_date,('{r['dexec']}'::date + interval '{int(r['tenure'])} months')::date)")
        if sets:
            stmts.append(f"UPDATE unit_registration_records SET {', '.join(sets)} WHERE id='{r['rid']}';")
    audit = {"phase": PHASE, "files": len(files), "unmatched": len(unmatched)}
    stmts.append(
        f"INSERT INTO pan_access_log (actor, purpose, source_script, doc_numbers, parties_touched, pan_count, raw_context) "
        f"VALUES ({q(ACTOR)}, {q(PURPOSE)}, 'enrich_pan_from_index2.py', "
        f"ARRAY[{','.join(q(x) for x in sorted(set(docs_seen)))}]::text[], {len(plans)}, {len(pan_plans)}, {jb(audit)});")
    stmts.append("COMMIT;")
    c, out = run_psql("\n".join(stmts))
    if c:
        print("Apply failed:\n" + out); return c
    print("Applied. Coverage now: " + coverage())
    _, summ = run_psql(
        "SELECT building_name, parties_with_pan, individuals, companies, firms_llp, other_entities, invalid_format "
        f"FROM vw_pan_enrichment_summary WHERE building_name='{BUILDING}';")
    print("Summary (with_pan|indiv|company|firm|other|invalid): " + summ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
