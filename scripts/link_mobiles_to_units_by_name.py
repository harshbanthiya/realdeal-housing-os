#!/usr/bin/env python3
"""Phase 6.27 — attach MORE mobile numbers to Kalpataru apartments by name.

6.26 linked contacts to units by registration-party name (best single contact each). This pass is
phone-centric: it scans every contact that carries a mobile number (contact_methods), matches it to
the unit-registry party names, and links any (contact, unit) pair that isn't connected yet — picking
up (a) mobile-bearing contacts 6.26 skipped and (b) duplicate same-name contact records that hold a
*different* mobile for the same person ("another mobile phone you can link").

Match reuses 6.26's cross-script normalisation (transliterate -> a-z0-9, joint-name split, titles
stripped, difflib best-of full-blob/sorted-token). Precision-first:
    score >= 0.92 AND a single clear contact -> ACTIVE
    score >= 0.86 or ambiguous               -> PENDING_REVIEW
Roles: purchaser->owner, lessee->tenant, lessor->landlord (company party -> business_lead).
Only contacts WITH a mobile are considered. Existing (contact,unit,type) links are deduped.

Dry-run by default; --apply --real-ok; reversible --revert (raw_context source). NO external calls.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from parse_igr_index2_pdfs import run_psql, jb  # noqa: E402
from match_contacts_to_units_by_name import (  # noqa: E402
    blob, sorted_key, score, split_contact_names, COMPANY_RE, ROLE_TO_TYPE,
)
from parse_igr_index2_pdfs import translit  # noqa: E402

PHASE = "6.27"
SOURCE = "mobile_name_match_6_27"
BUILDING = "Kalpataru Radiance"
STRONG, REVIEW = 0.92, 0.86


def main() -> int:
    ap = argparse.ArgumentParser(description="Attach mobile-bearing contacts to Kalpataru units by name (dry-run default).")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    code, bid = run_psql(f"SELECT id FROM buildings WHERE name='{BUILDING}' ORDER BY created_at LIMIT 1;")
    if code or not bid:
        print(f"Refusing: building {BUILDING!r} not found."); return 1
    bid = bid.splitlines()[0]

    def counts() -> str:
        _, c = run_psql(f"SELECT count(*)::text FROM contact_property_relationships WHERE raw_context->>'source'='{SOURCE}';")
        return c + " relationships from this pass"

    if args.revert:
        if not (args.apply and args.real_ok):
            print("Revert dry-run — would delete " + counts()); return 0
        c, out = run_psql(f"DELETE FROM contact_property_relationships WHERE raw_context->>'source'='{SOURCE}';")
        print(("Revert failed:\n" + out) if c else "Reverted."); return c

    # contacts that HAVE a mobile, with their mobiles aggregated; index name-variants by prefix
    _, crows = run_psql(
        "SELECT c.id, coalesce(c.full_name,''), string_agg(distinct coalesce(m.normalized_value,m.raw_value),',') "
        "FROM contacts c JOIN contact_methods m ON m.contact_id=c.id AND m.method_type IN ('mobile','phone') "
        "WHERE coalesce(c.is_test,false)=false AND coalesce(c.canonical_status,'active')<>'merged' AND c.full_name<>'' "
        "GROUP BY c.id, c.full_name;")
    contact_index: dict[str, list] = defaultdict(list)
    n_contacts = 0
    for ln in crows.splitlines():
        cid, full, mobiles = (ln.split("|") + ["", "", ""])[:3]
        mob = [x for x in mobiles.split(",") if x]
        n_contacts += 1
        for nm in split_contact_names(full):
            b, s = blob(nm), sorted_key(nm)
            if len(b) >= 4:
                contact_index[b[:3]].append({"cid": cid, "full": full, "blob": b, "sort": s, "mob": mob})

    # registry parties on unit-linked records
    _, prows = run_psql(
        "SELECT p.id, p.party_role, coalesce(p.party_name_english,p.party_name_normalized,''), "
        "r.building_unit_id::text, coalesce(p.party_name_devanagari,'') "
        "FROM unit_registration_parties p JOIN unit_registration_records r ON r.id=p.unit_registration_record_id "
        f"WHERE r.building_id='{bid}' AND r.building_unit_id IS NOT NULL AND p.party_role IN ('purchaser','lessee','lessor');")

    # existing (contact,unit,type) + which units already have ANY linked contact-with-mobile
    _, erows = run_psql(
        "SELECT contact_id||'|'||building_unit_id||'|'||relationship_type FROM contact_property_relationships r "
        f"JOIN building_units bu ON bu.id=r.building_unit_id WHERE bu.building_id='{bid}';")
    existing = set(erows.splitlines())
    _, ureach = run_psql(
        "SELECT DISTINCT r.building_unit_id::text FROM contact_property_relationships r "
        "JOIN building_units bu ON bu.id=r.building_unit_id "
        "JOIN contact_methods m ON m.contact_id=r.contact_id AND m.method_type IN ('mobile','phone') "
        f"WHERE bu.building_id='{bid}';")
    reachable_units = set(x for x in ureach.splitlines() if x)

    plans = []
    for ln in prows.splitlines():
        pid, role, eng, unit, dev = (ln.split("|") + [""] * 5)[:5]
        rtype = ROLE_TO_TYPE.get(role)
        if not unit or not rtype:
            continue
        pb, ps = blob(eng), sorted_key(eng)
        if len(pb) < 4:
            continue
        if COMPANY_RE.search(eng) or COMPANY_RE.search(translit(dev)):
            rtype = "business_lead"
        cands = []
        for pre in {pb[:3], ps[:3]}:
            cands += contact_index.get(pre, [])
        scored = sorted(({"c": c, "s": score(pb, ps, c["blob"], c["sort"])} for c in cands), key=lambda x: -x["s"])
        if not scored or scored[0]["s"] < REVIEW:
            continue
        best = scored[0]
        near = {sc["c"]["cid"] for sc in scored if sc["s"] >= best["s"] - 0.03}
        key = f"{best['c']['cid']}|{unit}|{rtype}"
        if key in existing:
            continue
        existing.add(key)
        unique = len(near) == 1
        status = "active" if (best["s"] >= STRONG and unique) else "pending_review"
        plans.append({"pid": pid, "cid": best["c"]["cid"], "unit": unit, "role": role, "rtype": rtype,
                      "score": round(best["s"], 3), "status": status, "party": eng,
                      "contact": best["c"]["full"], "mob": best["c"]["mob"],
                      "new_for_unit": unit not in reachable_units})

    active = [p for p in plans if p["status"] == "active"]
    review = [p for p in plans if p["status"] == "pending_review"]
    new_unit_phone = [p for p in plans if p["new_for_unit"]]
    distinct_mobiles = {m for p in plans for m in p["mob"]}
    print(f"Mobile-bearing contacts scanned: {n_contacts}")
    print(f"New linkable (contact,unit) pairs: {len(plans)}   ACTIVE: {len(active)}   PENDING_REVIEW: {len(review)}")
    print(f"Units that gain a phone for the FIRST time: {len({p['unit'] for p in new_unit_phone})}")
    print(f"Distinct mobile numbers brought in: {len(distinct_mobiles)}")
    print("\n  status        score role->type      party -> contact            mobile(****)  new-unit?")
    for p in (active[:20] + review[:10]):
        m = ("****" + p["mob"][0][-4:]) if p["mob"] else "(none)"
        print(f"  {p['status']:<13} {p['score']:<5} {p['role']}->{p['rtype']:<11} {p['party'][:22]:<22} -> {p['contact'][:26]:<26} {m}  {'NEW' if p['new_for_unit'] else ''}")

    if not (args.apply and args.real_ok):
        print("\nDry run only — NO DB writes. To execute: --apply --real-ok  (reverse: --revert --apply --real-ok)")
        return 0

    stmts = ["BEGIN;"]
    for i, p in enumerate(plans):
        ctx = {"source": SOURCE, "phase": PHASE, "party_id": p["pid"], "role": p["role"],
               "score": p["score"], "brought_mobile": bool(p["mob"]), "new_for_unit": p["new_for_unit"]}
        stmts.append(
            "INSERT INTO contact_property_relationships (contact_id, building_id, building_unit_id, "
            "relationship_type, relationship_status, confidence, notes, raw_context) VALUES "
            f"('{p['cid']}','{bid}','{p['unit']}','{p['rtype']}','{p['status']}',{p['score']}, "
            f"'Mobile-bearing contact name-matched to IGR party ({p['role']}).', {jb(ctx)});")
        if (i + 1) % 100 == 0:
            stmts.append("COMMIT;")
            c, out = run_psql("\n".join(stmts))
            if c:
                print(f"Apply failed near {i+1}:\n{out}"); return c
            stmts = ["BEGIN;"]
    stmts.append("COMMIT;")
    c, out = run_psql("\n".join(stmts))
    if c:
        print("Apply failed:\n" + out); return c
    print(f"Applied {len(plans)} links. " + counts())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
