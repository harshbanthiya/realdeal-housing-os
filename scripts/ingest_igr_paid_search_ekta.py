#!/usr/bin/env python3
"""Ingest IGR paid-search XLS exports for Ekta Tripolis (imports/ektaPaidIgr).

Same UTF-16 HTML-table format as the IH paid search (reuses its parser).
Creates unit_registration_records + unit_registration_parties, links units by
wing+flat (Ekta unit_number format "A-1002"), and matches party names against
existing Ekta contacts (owner sheet) into registration_party_contact_matches.

Usage:
  python3 scripts/ingest_igr_paid_search_ekta.py               # dry-run
  python3 scripts/ingest_igr_paid_search_ekta.py --apply --real-ok
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql
from ingest_igr_paid_search_ih import parse_xls, parse_money, parse_date, classify, q

PAID_ROOT = PROJECT_ROOT / "imports" / "ektaPaidIgr"
EKTA_ID = "2032514a-adef-4d2f-a12c-6ecf06853243"
EKTA_SUB = f"'{EKTA_ID}'::uuid"
SOURCE = "igr_paid_search_ekta"
PHASE = "6.27"

# Devanagari variants seen across IGR scripts: ट्रिपोलिस / ट्रायपॉलीस / त्रिपोलिस; एकता only with ट्र…
EKTA_RE = re.compile(r"tripolis|ट्रिपोलि|त्रिपोलि|ट्रायप[ॉो]ल[ीि]|ट्रीपोलि|एकता\s*ट्र", re.I)
COMPANY_RE = re.compile(
    r"\bbank\b|\bltd\b|limited|\bllp\b|\bpvt\b|finance|corporation|housing|"
    r"\bhdfc\b|\bicici\b|\bsbi\b|\baxis\b|\bkotak\b|nbfc|co-?op|society|branch", re.I)

# wing from "TOWER-B", "TOWER A", "A 2305", "B-1201", 'टॉवर "ए"', "बी टॉवर", "ए विंग"
_WING_RE = re.compile(
    r"(?:TOWER|WING)\s*[-–]?\s*([ABC])\b"
    r"|\b([ABC])\s*[-–\s]*(?:TOWER|WING)\b"
    r"|(?:टॉवर|टोवर|टावर|विंग)\s*[-–\s]*(ए|ऐ|बी|सी)"
    r"|(ए|ऐ|बी|सी)\s*[-–\s]*(?:टॉवर|टोवर|टावर|विंग)"
    r"|^\s*([ABC])[-\s/]\s*\d{2,4}", re.I)
_ML = {"ए": "A", "ऐ": "A", "बी": "B", "सी": "C"}
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def norm_desc(desc: str) -> str:
    return desc.translate(_DEV_DIGITS).replace('"', " ").replace("“", " ").replace("”", " ").replace("'", " ")

# role mapping per doc category: (sellerparty role, purchaserparty role)
_ROLES = {
    "tenancy": ("lessor", "lessee"),
    "mortgage": ("mortgagee", "mortgagor"),
    "sale": ("seller", "purchaser"),
    "agreement_to_sell": ("seller", "purchaser"),
    "gift": ("seller", "purchaser"),
    "release": ("seller", "purchaser"),
    "other": ("seller", "purchaser"),
}


def detect_wing(desc: str) -> str | None:
    m = _WING_RE.search(desc)
    if not m:
        return None
    g = next((g for g in m.groups() if g), None)
    if not g:
        return None
    g = _ML.get(g, g).upper()
    return g if g in "ABC" else None


def extract_flat(desc: str) -> str | None:
    m = re.search(r"^\s*(?:[ABCabc][-\s/])?\s*(\d{3,4})\b", desc.strip())
    if m:
        return m.group(1)
    m = re.search(r"(?:फ्लॅट|सदनिका|flat)\s*(?:नं\.?|क्रं\.?|no\.?)?\s*:?\s*(?:[ABCabc][-/])?\s*(\d{3,4})", desc, re.I)
    return m.group(1) if m else None


def split_parties(raw: str) -> list[str]:
    """'{\"A B\",\"C D\"}' / '{X,Y}' / plain string -> list of names."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
        parts = re.findall(r'"([^"]*)"|([^,]+)', raw)
        names = [(a or b).strip() for a, b in parts]
    else:
        names = [raw]
    return [n for n in names if n and n.lower() not in ("null", "")]


def squash(name: str) -> str:
    return re.sub(r"[^A-Z]", "", name.upper())


def load_ekta_contacts() -> list[tuple[str, str, str]]:
    """[(contact_id, unit_id, name_component), ...] — owner names split on '/'."""
    _, out = run_psql(f"""
        SELECT cpr.contact_id, cpr.building_unit_id, REPLACE(c.full_name, '|', ' ')
        FROM contact_property_relationships cpr
        JOIN contacts c ON c.id = cpr.contact_id
        WHERE cpr.building_id = {EKTA_SUB}""")
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        cid, uid, full = parts[0].strip(), parts[1].strip(), "|".join(parts[2:])
        for comp in full.split("/"):
            s = squash(comp)
            if len(s) >= 6:
                rows.append((cid, uid, s))
    return rows


def load_units() -> dict[str, str]:
    # ponytail: some seed rows have empty wing; unit_number ("A-1002") is the reliable key
    _, out = run_psql(f"SELECT unit_number, id FROM building_units WHERE building_id = {EKTA_SUB}")
    units = {}
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 2:
            units[p[0]] = p[1]
    return units


def match_party(name_sq: str, unit_id: str | None,
                contacts: list[tuple[str, str, str]]) -> tuple[str, str, float] | None:
    """-> (contact_id, strength, score) or None."""
    if len(name_sq) < 6:
        return None
    # exact squash, same unit -> strong
    for cid, uid, csq in contacts:
        if csq == name_sq and unit_id and uid == unit_id:
            return cid, "strong", 1.0
    # fuzzy >= 0.9, same unit -> medium (paid-search names come smushed/typo'd)
    if unit_id:
        best = None
        for cid, uid, csq in contacts:
            if uid != unit_id:
                continue
            r = difflib.SequenceMatcher(None, csq, name_sq).ratio()
            if r >= 0.9 and (best is None or r > best[2]):
                best = (cid, "medium", r)
        if best:
            return best
    # exact squash anywhere in building -> medium
    hits = {cid for cid, _, csq in contacts if csq == name_sq}
    if len(hits) == 1:
        return hits.pop(), "medium", 1.0
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    rows = []
    for f in sorted(p for p in PAID_ROOT.glob("*.xls") if not p.name.startswith("._")):
        for r in parse_xls(f):
            if EKTA_RE.search(r.get("propertydescription", "") or ""):
                r["_src"] = f.name
                rows.append(r)
    print(f"Ekta Tripolis rows: {len(rows)}")

    seen: dict[str, dict] = {}
    for r in rows:
        year = (parse_date(r.get("registrationdate")) or "????")[:4]
        key = f"{r.get('srocode','')}/{r.get('docno','')}/{year}"
        seen.setdefault(key, r)
    recs = list(seen.values())
    print(f"Unique (srocode/docno/year): {len(recs)}")

    _, out = run_psql(f"SELECT doc_number FROM unit_registration_records WHERE building_id = {EKTA_SUB}")
    existing = {l.strip() for l in out.strip().splitlines() if l.strip()}

    units = load_units()
    contacts = load_ekta_contacts()
    print(f"Units: {len(units)}  contact name components: {len(contacts)}")

    parsed, matched_strong, matched_med, unmatched_parties = [], 0, 0, 0
    unit_linked = 0
    for r in recs:
        desc = r.get("propertydescription", "") or ""
        docno = (r.get("docno") or "").strip()
        docname = (r.get("docname") or "").strip()
        _, cat = classify(docname)
        nd = norm_desc(desc)
        wing = detect_wing(nd)
        flat = extract_flat(nd)
        unit_id = units.get(f"{wing}-{flat}") if wing and flat else None
        if unit_id:
            unit_linked += 1
        srole, prole = _ROLES.get(cat, _ROLES["other"])
        parties = []
        for role, col in ((srole, "sellerparty"), (prole, "purchaserparty")):
            for name in split_parties(r.get(col, "")):
                ptype = "company" if COMPANY_RE.search(name) else "individual"
                m = match_party(squash(name), unit_id, contacts) if ptype == "individual" else None
                if m:
                    if m[1] == "strong":
                        matched_strong += 1
                    else:
                        matched_med += 1
                elif ptype == "individual":
                    unmatched_parties += 1
                parties.append({"role": role, "name": name, "type": ptype, "match": m})
        parsed.append({
            "docno": docno, "sro": (r.get("sroname") or "").strip(),
            "docname": docname, "cat": cat,
            "regdate": parse_date(r.get("registrationdate")),
            "consideration": parse_money(r.get("consideration_amt")),
            "market_value": parse_money(r.get("marketvalue")),
            "stamp": parse_money(r.get("stampdutypaid")),
            "regfee": parse_money(r.get("registrationfees")),
            "desc": desc[:2000], "wing": wing, "flat": flat,
            "unit_id": unit_id, "parties": parties, "src": r["_src"],
            "is_new": docno not in existing,
        })

    new = [p for p in parsed if p["is_new"]]
    print(f"\nNew records: {len(new)} (already in DB: {len(parsed) - len(new)})")
    print(f"Unit-linked: {unit_linked}/{len(parsed)}")
    by_cat = {}
    for p in parsed:
        by_cat[p["cat"]] = by_cat.get(p["cat"], 0) + 1
    print(f"Categories: {by_cat}")
    print(f"Party matches: {matched_strong} strong, {matched_med} medium; unmatched individuals: {unmatched_parties}")
    print("\n── No-unit sample ──")
    for p in [x for x in parsed if not x["unit_id"]][:8]:
        print(f"  doc={p['docno']:>6}  wing={p['wing']} flat={p['flat']}  {p['desc'][:90]}")
    print("\n── Match sample ──")
    shown = 0
    for p in parsed:
        for pa in p["parties"]:
            if pa["match"] and shown < 8:
                print(f"  {pa['name'][:40]:<40} -> contact {pa['match'][0][:8]} ({pa['match'][1]} {pa['match'][2]:.2f})")
                shown += 1

    if not (args.apply and args.real_ok):
        print("\nDry run — add --apply --real-ok to write.")
        return 0

    stmts = []
    # create seed-missing units (Tower C / Skypolis coverage is partial) so records can link
    needed = {(p["wing"], p["flat"]) for p in new if p["wing"] and p["flat"] and not p["unit_id"]}
    for wing, flat in sorted(needed):
        stmts.append(
            f"INSERT INTO building_units (building_id, wing, unit_number, canonical_status) "
            f"VALUES ({EKTA_SUB}, {q(wing)}, {q(wing + '-' + flat)}, 'active') ON CONFLICT DO NOTHING;")
    for p in new:
        raw_ctx = f'{{"source":"{SOURCE}","phase":"{PHASE}","file":"{p["src"]}"}}'
        if p["unit_id"]:
            unit_sub = f"'{p['unit_id']}'::uuid"
        elif p["wing"] and p["flat"]:
            unit_sub = (f"(SELECT id FROM building_units WHERE building_id={EKTA_SUB} "
                        f"AND unit_number={q(p['wing'] + '-' + p['flat'])} LIMIT 1)")
        else:
            unit_sub = "NULL"
        stmts.append(
            f"INSERT INTO unit_registration_records "
            f"(building_id, building_unit_id, doc_number, registration_year, registration_date, "
            f"sro_office, document_type, transaction_category, property_description_raw, "
            f"wing_text, unit_text, consideration_amount, market_value, stamp_duty, registration_fee, "
            f"parse_confidence, verification_status, source_label, raw_context) VALUES ("
            f"{EKTA_SUB}, {unit_sub}, {q(p['docno'])}, "
            f"{'NULL' if not p['regdate'] else p['regdate'][:4]}, {q(p['regdate'])}, {q(p['sro'])}, "
            f"{q(p['docname'])}, {q(p['cat'])}, {q(p['desc'])}, {q(p['wing'])}, {q(p['flat'])}, "
            f"{q(p['consideration'])}, {q(p['market_value'])}, {q(p['stamp'])}, {q(p['regfee'])}, "
            f"0.75, 'parsed_candidate', {q(SOURCE)}, '{raw_ctx}'::jsonb) ON CONFLICT DO NOTHING;")
        rec_sub = (f"(SELECT id FROM unit_registration_records "
                   f"WHERE building_id={EKTA_SUB} AND doc_number={q(p['docno'])} "
                   f"AND source_label={q(SOURCE)} LIMIT 1)")
        for i, pa in enumerate(p["parties"]):
            stmts.append(
                f"INSERT INTO unit_registration_parties "
                f"(unit_registration_record_id, party_role, party_name_raw, party_name_normalized, "
                f"party_type, display_order, raw_context) VALUES ("
                f"{rec_sub}, {q(pa['role'])}, {q(pa['name'])}, {q(squash(pa['name']))}, "
                f"{q(pa['type'])}, {i}, '{raw_ctx}'::jsonb);")
            if pa["match"]:
                cid, strength, score = pa["match"]
                status = "matched" if strength == "strong" else "needs_review"
                party_sub = (f"(SELECT id FROM unit_registration_parties "
                             f"WHERE unit_registration_record_id={rec_sub} AND display_order={i} LIMIT 1)")
                stmts.append(
                    f"INSERT INTO registration_party_contact_matches "
                    f"(unit_registration_party_id, contact_id, building_id, building_unit_id, "
                    f"match_status, match_strength, name_similarity_score, match_reason, "
                    f"creates_relationship, raw_context) VALUES ("
                    f"{party_sub}, '{cid}'::uuid, {EKTA_SUB}, "
                    f"{'NULL' if not p['unit_id'] else repr(p['unit_id']) + '::uuid'}, "
                    f"{q(status)}, {q(strength)}, {score:.2f}, "
                    f"'paid-search squashed-name match ({strength})', false, '{raw_ctx}'::jsonb);")
        stmts.append(
            f"INSERT INTO unit_registration_review_items "
            f"(building_id, unit_registration_record_id, review_type, status, priority, decision_notes, raw_context) "
            f"VALUES ({EKTA_SUB}, {rec_sub}, 'registration_record_review', 'pending', 'normal', "
            f"'Ekta paid search ingest; verify parties/unit link.', '{raw_ctx}'::jsonb) ON CONFLICT DO NOTHING;")

    sql = "BEGIN;\n" + "\n".join(stmts) + "\nCOMMIT;"
    code, out = run_psql(sql)
    if code != 0:
        print(f"ERROR:\n{out[-3000:]}")
        return 1

    _, c = run_psql(
        f"SELECT count(*) FROM unit_registration_records WHERE building_id={EKTA_SUB};"
        f"SELECT count(*) FROM unit_registration_records WHERE building_id={EKTA_SUB} AND building_unit_id IS NOT NULL;"
        f"SELECT count(*) FROM unit_registration_parties p JOIN unit_registration_records r "
        f"ON r.id=p.unit_registration_record_id WHERE r.building_id={EKTA_SUB};"
        f"SELECT count(*) FROM registration_party_contact_matches WHERE building_id={EKTA_SUB};")
    print("Done. records|linked|parties|matches:")
    print(c.strip())
    return 0


def _demo() -> None:
    assert detect_wing("2202  EKTA TRIPOLIS, TOWER-B SIDDHARTH") == "B"
    assert detect_wing("1504  EKTA TRIPOLIS,TOWER A ROAD") == "A"
    assert detect_wing("A 2305  EKTA TRIPOLIS  SIDDHARTH") == "A"
    assert detect_wing("B-1201   EKTA TRIPOLIS TOWER B") == "B"
    assert extract_flat("2202  EKTA TRIPOLIS, TOWER-B") == "2202"
    assert extract_flat("A 2305  EKTA TRIPOLIS") == "2305"
    assert extract_flat("B-1201   EKTA TRIPOLIS") == "1201"
    assert split_parties('{"MRS  UCHITARJHAVERI","MR  RAHULAJHAVERI"}') == ["MRS  UCHITARJHAVERI", "MR  RAHULAJHAVERI"]
    assert split_parties("{HARSHAPRABHATSSHETTY,MEDHAHARSHAPRABHATSHETTY}") == ["HARSHAPRABHATSSHETTY", "MEDHAHARSHAPRABHATSHETTY"]
    assert split_parties("HDFC Limited CHURCH GATE") == ["HDFC Limited CHURCH GATE"]
    assert squash("Mr. Harsh A Shetty") == "MRHARSHASHETTY"
    assert detect_wing(norm_desc('सदनिका नं: 205,टॉवर "ए", माळा नं: 2')) == "A"
    assert detect_wing(norm_desc("सदनिका नं: 2802, बी टॉवर , माळा नं: 28")) == "B"
    assert detect_wing(norm_desc("901, माळा नं: 9 वा मजला, ए विंग, इमारत")) == "A"
    assert detect_wing(norm_desc('सदनिका नं: १५०४, माळा नं: १५ वा, "ऐ" टॉवर')) == "A"
    assert extract_flat(norm_desc("सदनिका नं: १५०४, माळा नं: १५ वा")) == "1504"
    print("ekta paid-search self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        sys.exit(main())
