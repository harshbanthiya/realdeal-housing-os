#!/usr/bin/env python3
"""Phase 6.26 — connect contacts to Kalpataru Radiance apartments by NAME (via registration parties).

The IGR registration parties tie a person's name to a specific apartment (the record's
building_unit_id) with a role. This matches those party names to CRM contacts and links each
matched contact to the apartment:

    purchaser -> owner      lessee -> tenant      lessor -> landlord

Names are noisy: party names are rough transliterations of Devanagari (often concatenated, with
'--' artefacts and company suffixes); contacts are clean-ish English, sometimes two people joined
by '/' or 'and'. We normalise both sides cross-script (transliterate -> a-z0-9), split joint
contact names into person variants, strip titles, and score with difflib (best of full-blob and
sorted-token comparison). Precision-first:

    score >= 0.90 AND a single clear best contact  -> link ACTIVE
    score >= 0.83 (or strong-but-ambiguous)        -> link PENDING_REVIEW (operator confirms)
    below 0.83                                      -> no link

Every link records a registration_party_contact_matches audit row (party<->contact, strength,
similarity) and a contact_property_relationships row (deduped against existing). Existing bulk-import
owner links are left untouched. Dry-run by default; writing needs --apply AND --real-ok; reversible
via --revert (raw_context source marker). NO external calls. Requires: indic-transliteration.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from parse_igr_index2_pdfs import translit, run_psql, q, jb  # noqa: E402

PHASE = "6.26"
SOURCE = "name_match_registration_6_26"
BUILDING = "Kalpataru Radiance"
ROLE_TO_TYPE = {"purchaser": "owner", "lessee": "tenant", "lessor": "landlord"}
TITLES = {"mr", "mrs", "ms", "dr", "smt", "shri", "sri", "ku", "kumari", "late", "m", "s", "messrs"}
COMPANY_RE = re.compile(r"\b(ltd|limited|llp|pvt|private|builder|developer|housing|construction|"
                        r"authority|bank|enterprise|associat|realt|infra|corporation|company)\b", re.I)
STRONG, REVIEW = 0.90, 0.83


def clean_tokens(name: str) -> list[str]:
    t = translit(name or "")
    toks = [w for w in re.split(r"[^a-z0-9]+", t) if len(w) >= 2 and w not in TITLES]
    return toks


def blob(name: str) -> str:
    return "".join(clean_tokens(name))


def sorted_key(name: str) -> str:
    return "".join(sorted(clean_tokens(name)))


def score(a_blob: str, a_sort: str, b_blob: str, b_sort: str) -> float:
    if not a_blob or not b_blob:
        return 0.0
    return max(difflib.SequenceMatcher(None, a_blob, b_blob).ratio(),
               difflib.SequenceMatcher(None, a_sort, b_sort).ratio())


def split_contact_names(full: str) -> list[str]:
    parts = re.split(r"\s*(?:/|&|;|\band\b|\bw/o\b|\bs/o\b|\bd/o\b)\s*", full or "", flags=re.I)
    return [p.strip() for p in parts if p and p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Match contacts to Kalpataru units by name (dry-run default).")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    code, bid = run_psql(f"SELECT id FROM buildings WHERE name='{BUILDING}' ORDER BY created_at LIMIT 1;")
    if code or not bid:
        print(f"Refusing: building {BUILDING!r} not found."); return 1
    bid = bid.splitlines()[0]

    def counts() -> str:
        _, c = run_psql(
            f"SELECT 'matches', count(*)::text FROM registration_party_contact_matches WHERE raw_context->>'source'='{SOURCE}' "
            f"UNION ALL SELECT 'relationships', count(*)::text FROM contact_property_relationships WHERE raw_context->>'source'='{SOURCE}' ORDER BY 1;")
        return c

    if args.revert:
        if not (args.apply and args.real_ok):
            print("Revert dry-run — would delete:\n" + counts()); return 0
        sql = ("BEGIN;\n"
               f"DELETE FROM registration_party_contact_matches WHERE raw_context->>'source'='{SOURCE}';\n"
               f"DELETE FROM contact_property_relationships WHERE raw_context->>'source'='{SOURCE}';\nCOMMIT;")
        c, out = run_psql(sql)
        print(("Revert failed:\n" + out) if c else ("Reverted. " + counts())); return c

    # contacts -> person-name variants, indexed by 3-char blob prefix
    _, crows = run_psql("SELECT id, coalesce(full_name,'') FROM contacts WHERE coalesce(is_test,false)=false "
                        "AND coalesce(canonical_status,'active')<>'merged' AND full_name<>'';")
    contact_index: dict[str, list] = defaultdict(list)
    nvar = 0
    for ln in crows.splitlines():
        cid, full = (ln.split("|", 1) + [""])[:2]
        for nm in split_contact_names(full):
            b, s = blob(nm), sorted_key(nm)
            if len(b) >= 4:
                contact_index[b[:3]].append({"cid": cid, "full": full, "nm": nm, "blob": b, "sort": s})
                nvar += 1

    # Kalpataru parties on unit-linked records
    _, prows = run_psql(
        "SELECT p.id, p.party_role, coalesce(p.party_name_english,p.party_name_normalized,''), "
        "r.building_unit_id::text, coalesce(p.party_name_devanagari,'') "
        "FROM unit_registration_parties p JOIN unit_registration_records r ON r.id=p.unit_registration_record_id "
        f"WHERE r.building_id='{bid}' AND r.building_unit_id IS NOT NULL "
        f"AND p.party_role IN ('purchaser','lessee','lessor');")

    # existing relationships to dedupe (contact, unit, type)
    _, erows = run_psql(
        f"SELECT contact_id||'|'||building_unit_id||'|'||relationship_type FROM contact_property_relationships r "
        f"JOIN building_units bu ON bu.id=r.building_unit_id WHERE bu.building_id='{bid}';")
    existing = set(erows.splitlines())

    plans = []
    ambiguous = 0
    for ln in prows.splitlines():
        pid, role, eng, unit, dev = (ln.split("|") + [""] * 5)[:5]
        if not unit:
            continue
        pb, ps = blob(eng), sorted_key(eng)
        if len(pb) < 4:
            continue
        is_company = bool(COMPANY_RE.search(eng) or COMPANY_RE.search(translit(dev)))
        # candidate contacts from neighbouring prefix buckets
        cands = []
        for pre in {pb[:3], ps[:3]}:
            cands += contact_index.get(pre, [])
        scored = sorted(({"c": c, "s": score(pb, ps, c["blob"], c["sort"])} for c in cands),
                        key=lambda x: -x["s"])
        if not scored or scored[0]["s"] < REVIEW:
            continue
        best = scored[0]
        # distinct contacts near the top -> ambiguous
        near = {sc["c"]["cid"] for sc in scored if sc["s"] >= best["s"] - 0.04}
        rtype = ROLE_TO_TYPE.get(role)
        if not rtype:
            continue
        if is_company:
            rtype = "business_lead"
        key = f"{best['c']['cid']}|{unit}|{rtype}"
        if key in existing:
            continue
        unique = len(near) == 1
        status = "active" if (best["s"] >= STRONG and unique) else "pending_review"
        strength = "strong" if best["s"] >= STRONG else "medium"
        if not unique:
            ambiguous += 1
        plans.append({"pid": pid, "cid": best["c"]["cid"], "unit": unit, "role": role, "rtype": rtype,
                      "score": round(best["s"], 3), "status": status, "strength": strength,
                      "party": eng, "contact": best["c"]["full"], "unique": unique})
        existing.add(key)  # avoid double-creating within this run

    active = [p for p in plans if p["status"] == "active"]
    review = [p for p in plans if p["status"] == "pending_review"]
    from collections import Counter
    by_type = Counter(p["rtype"] for p in plans)
    print(f"Building '{BUILDING}' — contacts indexed: {nvar} name-variants")
    print(f"Candidate links: {len(plans)}   ACTIVE (strong+unique): {len(active)}   PENDING_REVIEW: {len(review)}   ambiguous: {ambiguous}")
    print(f"By relationship type: {dict(by_type)}")
    print("\n  status        score role->type      party-name -> contact-name")
    for p in (active[:18] + review[:12]):
        print(f"  {p['status']:<13} {p['score']:<5} {p['role']}->{p['rtype']:<11} {p['party'][:26]:<26} -> {p['contact'][:34]}")

    if not (args.apply and args.real_ok):
        print("\nDry run only — NO DB writes. To execute: --apply --real-ok  (reverse: --revert --apply --real-ok)")
        return 0

    BATCH = 100
    stmts = ["BEGIN;"]
    n = 0
    for p in plans:
        ctx = {"source": SOURCE, "phase": PHASE, "party_id": p["pid"], "role": p["role"], "score": p["score"]}
        rel = (f"INSERT INTO contact_property_relationships (contact_id, building_id, building_unit_id, "
               f"relationship_type, relationship_status, confidence, notes, raw_context) VALUES "
               f"('{p['cid']}','{bid}','{p['unit']}','{p['rtype']}','{p['status']}',{p['score']}, "
               f"'Name match to IGR registration party ({p['role']}).', {jb(ctx)}) RETURNING id;")
        stmts.append(rel)
        mctx = {"source": SOURCE, "phase": PHASE, "score": p["score"]}
        stmts.append(
            "INSERT INTO registration_party_contact_matches (unit_registration_party_id, contact_id, building_id, "
            "building_unit_id, match_status, match_strength, name_similarity_score, match_reason, creates_relationship, raw_context) "
            f"VALUES ('{p['pid']}','{p['cid']}','{bid}','{p['unit']}', "
            f"'{'matched' if p['status']=='active' else 'needs_review'}','{p['strength']}',{p['score']}, "
            f"'cross-script name similarity', true, {jb(mctx)});")
        n += 1
        if n % BATCH == 0:
            stmts.append("COMMIT;")
            code, out = run_psql("\n".join(stmts))
            if code:
                print(f"Apply failed near {n}:\n{out}"); return code
            stmts = ["BEGIN;"]
    stmts.append("COMMIT;")
    code, out = run_psql("\n".join(stmts))
    if code:
        print("Apply failed (final):\n" + out); return code
    print(f"Applied {len(plans)} links. " + counts())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
