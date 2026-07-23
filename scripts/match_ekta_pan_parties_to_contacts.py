#!/usr/bin/env python3
"""Link PAN-bearing Ekta registration parties to canonical contacts.

The CTS-22A sweep pushed Ekta parties with a PAN from 111 to ~1,300. PAN lives on
unit_registration_parties (with pan_access_log + masked operator views around it) and is
deliberately NOT copied onto contacts — this script only creates the join rows in
registration_party_contact_matches, so a contact resolves to its PAN through
vw_contact_pan_operator instead of duplicating PII into a second table.

Matching reuses ingest_igr_paid_search_ekta.match_party (exact/fuzzy on the squashed name,
scoped by unit). Strong matches land 'matched'; anything weaker lands 'needs_review'.

Dry-run by default; --apply --real-ok to write. No external calls.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql  # noqa: E402
from parse_igr_index2_pdfs import q, jb  # noqa: E402
from ingest_igr_paid_search_ekta import (  # noqa: E402
    EKTA_SUB, squash, load_ekta_contacts, match_party,
)

SOURCE = "ekta_pan_party_contact_match"
PHASE = "6.29b"


def _fuzzy_in(token: str, blob: str, thresh: float = 0.82) -> bool:
    """Is `token` present in the squashed contact blob, allowing transliteration drift
    (SAHAJAVANI vs SAHAJWANI, VASHDEV vs VASHUDEV)? Slides a window over the blob.

    0.82, not 0.85: a single inserted schwa in a 10-letter surname (SAHAJAVANI/SAHAJWANI)
    scores 0.842. The given-name gate in the caller is what keeps this honest, not this number.
    """
    if token in blob:
        return True
    n = len(token)
    if n < 4 or n > len(blob):
        return False
    return any(difflib.SequenceMatcher(None, token, blob[i:i + w]).ratio() >= thresh
               for w in (n - 1, n, n + 1)
               for i in range(0, len(blob) - w + 1))


def match_party_tokenwise(name: str, unit_id: str | None,
                          by_unit: dict[str, list[tuple[str, str]]]) -> tuple[str, str, float] | None:
    """Second pass for names the squash comparison misses: the Devanagari transliteration
    keeps middle names the contact sheet drops, and vice versa.

    Requires BOTH the given name (as a prefix of the contact blob) and the surname to match.
    Demanding the given name is what stops a spouse on the same flat from being matched to the
    other spouse's contact — 'Vibhuti Akash Wakodkar' must not resolve to 'AKASHWAKODKAR'.
    Always returns 'medium', i.e. operator-reviewed; this pass never asserts a fact.
    """
    toks = [squash(t) for t in name.split()]
    toks = [t for t in toks if len(t) >= 3 and t not in ("MR", "MRS", "MS", "SHRI", "SMT")]
    if len(toks) < 2 or not unit_id:
        return None
    first, last = toks[0], toks[-1]
    best = None
    for cid, blob in by_unit.get(unit_id, []):
        head = blob[:len(first) + 1]
        if difflib.SequenceMatcher(None, first, head).ratio() < 0.85:
            continue
        if not _fuzzy_in(last, blob):
            continue
        score = difflib.SequenceMatcher(None, "".join(toks), blob).ratio()
        if best is None or score > best[2]:
            best = (cid, "medium", round(score, 3))
    return best


def load_unmatched_parties() -> list[dict]:
    """PAN-bearing Ekta parties that have no contact match row yet."""
    _, out = run_psql(f"""
        SELECT p.id, COALESCE(p.party_name_english, p.party_name_normalized, p.party_name_raw),
               COALESCE(r.building_unit_id::text, ''), p.party_pan, p.party_role
        FROM unit_registration_parties p
        JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
        WHERE r.building_id = {EKTA_SUB}
          AND p.party_pan IS NOT NULL
          AND p.party_type = 'individual'
          AND NOT EXISTS (SELECT 1 FROM registration_party_contact_matches m
                          WHERE m.unit_registration_party_id = p.id)""")
    rows = []
    for line in out.strip().splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 5:
            rows.append({"party_id": parts[0], "name": parts[1],
                         "unit_id": parts[2] or None, "pan": parts[3], "role": parts[4]})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    if args.revert:
        if not (args.apply and args.real_ok):
            print("Revert dry-run. Needs --revert --apply --real-ok.")
            return 0
        _, out = run_psql(
            f"DELETE FROM registration_party_contact_matches "
            f"WHERE raw_context->>'source'='{SOURCE}'; "
            f"SELECT count(*) FROM registration_party_contact_matches "
            f"WHERE building_id={EKTA_SUB};")
        print("After revert:\n" + out)
        return 0

    parties = load_unmatched_parties()
    contacts = load_ekta_contacts()
    print(f"Unmatched PAN parties: {len(parties)}   contact name components: {len(contacts)}")

    by_unit: dict[str, list[tuple[str, str]]] = {}
    for cid, uid, csq in contacts:
        by_unit.setdefault(uid, []).append((cid, csq))

    hits, stats = [], Counter()
    for p in parties:
        m = match_party(squash(p["name"]), p["unit_id"], contacts)
        if m:
            stats[m[1]] += 1
        else:
            m = match_party_tokenwise(p["name"], p["unit_id"], by_unit)
            if m:
                stats["tokenwise"] += 1
        if not m:
            stats["no_match"] += 1
            continue
        cid, strength, score = m
        hits.append({**p, "contact_id": cid, "strength": strength, "score": score})

    total = len(parties)
    print(f"\n  strong     {stats['strong']:5d}   (exact name, same unit → 'matched')"
          f"\n  medium     {stats['medium']:5d}   (fuzzy, same unit → 'needs_review')"
          f"\n  tokenwise  {stats['tokenwise']:5d}   (given+surname → 'needs_review')"
          f"\n  none       {stats['no_match']:5d}"
          f"\n  matched {len(hits)}/{total}"
          f" ({100*len(hits)/total if total else 0:.1f}%)")
    print(f"  distinct contacts gaining a PAN link: {len({h['contact_id'] for h in hits})}")

    if not (args.apply and args.real_ok):
        print("\nDry run — add --apply --real-ok to write.")
        return 0
    if not hits:
        print("Nothing to write.")
        return 0

    stmts = ["BEGIN;"]
    for h in hits:
        status = "matched" if h["strength"] == "strong" else "needs_review"
        tag = {"source": SOURCE, "phase": PHASE, "is_fake": False,
               "party_role": h["role"], "external_calls_made": False}
        stmts.append(
            "INSERT INTO registration_party_contact_matches "
            "(unit_registration_party_id, contact_id, building_id, building_unit_id, "
            "match_status, match_strength, name_similarity_score, match_reason, "
            "creates_relationship, raw_context) "
            f"SELECT {q(h['party_id'])}::uuid, {q(h['contact_id'])}::uuid, {EKTA_SUB}, "
            f"{q(h['unit_id']) + '::uuid' if h['unit_id'] else 'NULL'}, "
            f"{q(status)}, {q(h['strength'])}, {h['score']:.3f}, "
            f"'IGR CTS sweep PAN party matched to Ekta contact by name (unit-scoped).', "
            f"FALSE, {jb(tag)} "
            f"WHERE NOT EXISTS (SELECT 1 FROM registration_party_contact_matches "
            f"  WHERE unit_registration_party_id = {q(h['party_id'])}::uuid);")
    stmts.append("COMMIT;")
    code, out = run_psql("\n".join(stmts))
    if code != 0:
        print("DB error:\n" + out[-3000:])
        return 1
    _, chk = run_psql(
        "SELECT match_status, count(*) FROM registration_party_contact_matches "
        f"WHERE building_id={EKTA_SUB} GROUP BY 1 ORDER BY 1;"
        "SELECT count(DISTINCT contact_id) FROM vw_contact_pan_operator "
        "WHERE building_name='Ekta Tripolis';")
    print("\nAfter write:\n" + chk)
    return 0


def _demo() -> None:
    cs = [("c1", "u1", "AMITRAMAKANTVAIDYA"), ("c2", "u2", "SMRUTIAMITVAIDYA")]
    assert match_party("AMITRAMAKANTVAIDYA", "u1", cs) == ("c1", "strong", 1.0)
    assert match_party("AMITRAMAKANTVAIDYA", None, cs)[1] == "medium"
    assert match_party("NOSUCHPERSON", "u1", cs) is None
    assert match_party("SHORT", "u1", cs) is None  # too short to risk a match
    bu = {"u1": [("c1", "RAJANCHHABRIA"), ("c9", "AKASHWAKODKAR")]}
    assert match_party_tokenwise("Rajan Vasu Chhabria", "u1", bu)[0] == "c1"
    assert match_party_tokenwise("Megha Deora", "u1", {"u1": [("c2", "MEGHAANKURDEORA")]})[0] == "c2"
    assert match_party_tokenwise("Anila Sahajavani", "u1", {"u1": [("c3", "ANILSAHAJWANI")]})[0] == "c3"
    # a spouse on the same flat must NOT resolve to the other spouse's contact
    assert match_party_tokenwise("Vibhuti Akash Wakodkar", "u1", bu) is None
    assert match_party_tokenwise("Someone Else", "u1", bu) is None
    print("match_ekta_pan_parties_to_contacts self-check OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        sys.exit(main())
