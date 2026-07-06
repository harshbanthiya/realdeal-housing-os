#!/usr/bin/env python3
"""Safely insert MINIMAL identity records for apartments with zero DB rows, using only
the independent audit's own (already self-tested) extraction -- never the production
ingest scripts.

Why minimal: 2026-07-06, running the production `ingest_igr_bulk_snapshots.py` broadly
re-introduced 38 already-cleaned contaminated records, because that script globs every
`*_bulk/` folder under whatever root it's given (regardless of which building the folder
name claims), and keys its existing-record lookup on (building_id, doc_number) alone --
doc numbers recycle across years within one SRO, so a same-numbered but unrelated
document silently overwrites/merges into an existing row. This script fixes both:
  - only inserts a candidate whose independently-detected building matches the target
    building UNAMBIGUOUSLY (see qa_independent_audit.guess_building, already hardened
    against party-address false positives and cross-SRO doc-number collisions)
  - keys existing-record checks on (building_id, doc_number, registration_year), not
    (building_id, doc_number) alone

Only writes identity fields (doc/year/SRO/wing/unit/floor/raw property text) -- NOT
consideration/stamp_duty/parties, which need the richer per-field parser. Each inserted
record gets a review_item flagging it for financial/party enrichment via
fetch_igr_docno_targeted.py + ingest_igr_bulk_snapshots.py run SCOPED to that one doc
(not the whole shared root) once its wing/building is already locked in by this insert.

Usage:
    python scripts/qa_insert_verified_missing.py --selftest
    python scripts/qa_insert_verified_missing.py                 # dry run, both buildings
    python scripts/qa_insert_verified_missing.py --apply --real-ok
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql  # noqa: E402
from qa_independent_audit import (  # noqa: E402  -- reuse OUR OWN independent, self-tested code only
    BUILDINGS, OUT_DIR, extract_property_field, guess_building, guess_floor,
)

SOURCE = "qa_independent_verified_insert"
PHASE = "qa_2026_07_06"

DOCTYPE_KEYWORDS = [
    (r"leave\s*and\s*licen[cs]e|लिव्ह\s*अ?ॅ?ड\s*लायसन", "tenancy", "leave_and_license"),
    (r"agreement\s*to\s*sale|अ‍ॅग्रीमेंट\s*टू\s*सेल|करारनामा", "sale", "agreement_to_sell"),
    (r"gift\s*deed|बक्षीसपत्र", "gift", "gift_deed"),
    (r"mortgage|गहाण", "mortgage", "mortgage"),
    (r"cancel|रद्दलेख", "other", "cancellation"),
]


def classify_doctype(text: str) -> tuple[str, str]:
    for pat, cat, etype in DOCTYPE_KEYWORDS:
        if re.search(pat, text, re.I):
            return cat, etype
    return "other", "unclassified"


def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"


def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def load_candidates(key: str) -> list[dict]:
    path = OUT_DIR / f"missing_units_found_{key}.json"
    if not path.exists():
        print(f"{path} not found -- run qa_independent_audit.py then --search-missing first.")
        return []
    return json.load(open(path, encoding="utf-8"))


def build_inserts(key: str) -> tuple[list[dict], list[dict]]:
    """Return (to_insert, skipped) for one building."""
    cfg = BUILDINGS[key]
    units = load_candidates(key)

    _, existing_raw = run_psql(f"""
        SELECT doc_number, registration_year FROM unit_registration_records
        WHERE building_id={cfg['building_id_sql']};
    """)
    existing = {(ln.split("|")[0], ln.split("|")[1]) for ln in existing_raw.strip().splitlines() if "|" in ln}

    to_insert, skipped = [], []
    seen_this_run: set[tuple] = set()

    for u in units:
        # Prefer index2_txt candidates (full property field) over bare xls rows (no price/PAN
        # anyway -- xls-only units get flagged for a fresh docno-targeted capture instead).
        txt_candidates = [c for c in u["raw_candidates"]
                          if c["raw_kind"] == "index2_txt" and c["building_guess"] == key]
        if not txt_candidates:
            skipped.append({**u, "reason": "no index2_txt candidate agrees with this building"})
            continue

        for c in txt_candidates:
            dkey = (c["doc_no"], c["year"])
            if dkey in existing or dkey in seen_this_run:
                continue
            path = PROJECT_ROOT / c["raw_file"]
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            prop_field = extract_property_field(text)
            # Re-verify on the FULL text at insert time, not just the cached guess --
            # cheap re-check against regressions in raw_inventory.json going stale.
            bkey, _ = guess_building(prop_field)
            if bkey != key:
                continue
            cat, etype = classify_doctype(text)
            seen_this_run.add(dkey)
            to_insert.append({
                "building_unit_id": u["building_unit_id"],
                "wing": u["wing"], "unit_number": u["unit_number"],
                "doc_no": c["doc_no"], "year": c["year"], "sro_raw": c["sro_raw"],
                "floor": c.get("floor_guess") or guess_floor(prop_field),
                "prop_field": prop_field.strip()[:2000],
                "cat": cat, "etype": etype,
                "raw_file": c["raw_file"],
            })

    return to_insert, skipped


def apply_inserts(key: str, rows: list[dict]) -> None:
    cfg = BUILDINGS[key]
    stmts = ["BEGIN;"]
    for r in rows:
        tag = {
            "source": SOURCE, "phase": PHASE, "is_fake": False,
            "audit_verified": True, "raw_file": r["raw_file"],
            "external_calls_made": False,
            "note": "Identity-only insert from independent QA audit; needs financial/party "
                    "enrichment via a SCOPED docno-targeted capture (not a broad ingest run).",
        }
        stmts.append(
            "INSERT INTO unit_registration_records "
            "(building_id, building_unit_id, doc_number, registration_year, sro_office, "
            "document_type, transaction_category, property_description_raw, "
            "wing_text, unit_text, floor_text, parse_confidence, verification_status, "
            "source_label, raw_context) VALUES ("
            f"{cfg['building_id_sql']}, {q(r['building_unit_id'])}, {q(r['doc_no'])}, "
            f"{q(r['year'])}, {q(r['sro_raw'])}, {q(r['etype'])}, {q(r['cat'])}, "
            f"{q(r['prop_field'])}, {q(r['wing'])}, {q(r['unit_number'])}, {q(r['floor'])}, "
            f"0.60, 'parsed_candidate', {q(f'QA-verified identity insert ({SOURCE})')}, {jb(tag)});"
        )
        rec = (f"(SELECT id FROM unit_registration_records WHERE building_id={cfg['building_id_sql']} "
               f"AND doc_number={q(r['doc_no'])} AND registration_year={q(r['year'])} "
               f"ORDER BY created_at DESC LIMIT 1)")
        stmts.append(
            "INSERT INTO unit_registration_review_items "
            "(building_id, unit_registration_record_id, review_type, status, priority, "
            "decision_notes, raw_context) VALUES ("
            f"{cfg['building_id_sql']}, {rec}, 'registration_record_review', 'pending', 'normal', "
            f"'Identity confirmed by independent QA audit; financials/parties not yet parsed -- "
            f"needs docno-targeted capture + a SCOPED ingest for just this doc.', "
            f"{jb({'source': SOURCE, 'doc_no': r['doc_no'], 'year': r['year']})});"
        )
    stmts.append("COMMIT;")
    code, out = run_psql("\n".join(stmts))
    print(f"  {cfg['db_name']}: executed {len(stmts)} statements -> {out.strip() or 'ok'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    self_check()
    if args.selftest:
        return 0

    for key in BUILDINGS:
        to_insert, skipped = build_inserts(key)
        print(f"\n{BUILDINGS[key]['db_name']}: {len(to_insert)} verified inserts ready, "
              f"{len(skipped)} skipped (no agreeing index2_txt candidate -- needs fresh capture)")
        if not (args.apply and args.real_ok):
            for r in to_insert[:10]:
                print(f"    doc {r['doc_no']}/{r['year']}  {r['wing']}-{r['unit_number']}  "
                      f"floor={r['floor']}  cat={r['cat']}")
            if len(to_insert) > 10:
                print(f"    ... and {len(to_insert) - 10} more")
            continue
        apply_inserts(key, to_insert)

    if not (args.apply and args.real_ok):
        print("\nDry run -- no DB writes. Add --apply --real-ok to insert.")
    return 0


def self_check() -> None:
    """ponytail: smallest runnable check for the parts unique to this script."""
    assert classify_doctype("Leave and Licenses agreement") == ("tenancy", "leave_and_license")
    assert classify_doctype("36-अ-लिव्ह अॅड लायसन्सेस")[0] == "tenancy"
    assert classify_doctype("रद्दलेख")[0] == "other"
    print("self_check: all assertions passed")


if __name__ == "__main__":
    sys.exit(main())
