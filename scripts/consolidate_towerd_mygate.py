#!/usr/bin/env python3
"""Consolidate MyGate Tower D screenshots (scratchpad/mygate_raw.jsonl) into a
reviewable per-unit CSV, validate units against wing-D building_units, and
fuzzy-match owner names to the Tower D WhatsApp xlsx phones.

Human-in-the-middle: writes scratchpad/towerd_review.csv for operator review.
NO DB writes. Run the load step separately after the CSV is approved.

    python3 scripts/consolidate_towerd_mygate.py          # build + validate + report
    python3 scripts/consolidate_towerd_mygate.py --test   # self-check only
"""
from __future__ import annotations

import csv
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from _db import run_psql

BUILDING_ID = "0e72db71-8b93-4ecd-879c-17d8d8f2b206"
WING = "D"
SCRATCH = Path("/private/tmp/claude-501/-Volumes-RDH-5TB-Real-Deal-Housing-OS"
               "/7f3e0882-9b88-4ef8-ba7b-84bab78ea73f/scratchpad")
RAW = SCRATCH / "mygate_raw.jsonl"
XLSX = SCRATCH / "xlsx_contacts.json"
OUT = SCRATCH / "towerd_review.csv"

ROLE_MAP = {
    "owner": "owner",
    "owner family": "owner_family",
    "tenant": "tenant",
    "tenant family": "tenant_family",
}


def norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", s.lower())).strip()


def name_key(role: str, name: str) -> str:
    return f"{ROLE_MAP.get(role.lower(), role.lower())}|{norm_name(name)}"


def consolidate(rows: list[dict]) -> tuple[dict, list[dict]]:
    """Merge overlapping cards per clean unit; keep ambiguous ('?') aside."""
    units: dict[str, dict] = {}
    ambiguous: list[dict] = []
    for r in rows:
        u = r["unit"]
        if "?" in u or "or" in u:
            ambiguous.append(r)
            continue
        slot = units.setdefault(u, {"floor": r["floor"], "seen": {}, "people": []})
        for role, name in r["people"]:
            k = name_key(role, name)
            if k not in slot["seen"]:
                slot["seen"][k] = True
                slot["people"].append((ROLE_MAP.get(role.lower(), role.lower()), name))
    return units, ambiguous


def best_phone_match(name: str, contacts: list[dict]) -> tuple[str, str, float]:
    """Return (matched_xlsx_name, phone, score) for the closest xlsx name.

    Token-aware: a full-name string-similarity, boosted only when the shorter
    name's token set is fully contained in the other AND anchored by a
    distinctive (len>=4) shared token. This stops single-letter/initial xlsx
    entries (e.g. "G") and lone common surnames from matching everything.
    """
    n = norm_name(name)
    nt = set(n.split())
    best = ("", "", 0.0)
    for c in contacts:
        cn = norm_name(c["name"])
        if len(cn) < 4:  # skip initials / single-letter xlsx entries
            continue
        ct = set(cn.split())
        score = SequenceMatcher(None, n, cn).ratio()
        shared = nt & ct
        subset = nt <= ct or ct <= nt
        if subset and any(len(t) >= 4 for t in shared):
            score = max(score, 0.9)
        if score > best[2]:
            best = (c["name"], c["phone"], score)
    return best


def build():
    raw = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    contacts = json.loads(XLSX.read_text())
    units, ambiguous = consolidate(raw)

    # which wing-D unit_numbers actually exist
    code, out = run_psql(
        f"select unit_number from building_units "
        f"where building_id='{BUILDING_ID}' and wing='{WING}';")
    if code != 0:
        sys.exit(f"DB error: {out}")
    valid = {x for x in out.splitlines() if x}

    rows_out = []
    for unit in sorted(units, key=lambda x: (len(x), x)):
        u = units[unit]
        exists = unit in valid
        for role, name in u["people"]:
            mname, phone, score = best_phone_match(name, contacts)
            rows_out.append({
                "unit": unit,
                "floor": u["floor"],
                "role": role,
                "name": name,
                "unit_in_db": "yes" if exists else "NO-REVIEW",
                "phone": phone if score >= 0.85 else "",
                "phone_match_name": mname if score >= 0.85 else "",
                "phone_score": f"{score:.2f}" if score >= 0.85 else "",
            })

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    # report
    missing = sorted(u for u in units if u not in valid)
    people = sum(len(v["people"]) for v in units.values())
    matched = sum(1 for r in rows_out if r["phone"])
    print(f"units consolidated : {len(units)}  (people rows: {people})")
    print(f"ambiguous units    : {len(ambiguous)}  -> need operator disambiguation")
    print(f"units NOT in wing D : {len(missing)}  {missing}")
    print(f"phone matched >=.85 : {matched}/{people}")
    print(f"CSV written         : {OUT}")
    if ambiguous:
        print("\nambiguous (review manually):")
        for a in ambiguous:
            print(f"  img {a['img']} unit={a['unit']} "
                  f"{[n for _, n in a['people']]}")


def test():
    # self-check: consolidation dedups overlap, ambiguous split, role map
    sample = [
        {"img": "1", "floor": "5", "unit": "501", "people": [["Owner", "Asha  Rao"]]},
        {"img": "2", "floor": "5", "unit": "501", "people": [["Owner", "asha rao"], ["Tenant", "Ben"]]},
        {"img": "3", "floor": "5", "unit": "502or503?", "people": [["Owner", "X"]]},
    ]
    units, amb = consolidate(sample)
    assert set(units) == {"501"}, units
    assert len(units["501"]["people"]) == 2, units["501"]  # Asha deduped, Ben kept
    assert units["501"]["people"][0][0] == "owner"
    assert len(amb) == 1 and amb[0]["unit"] == "502or503?"
    assert name_key("Owner Family", "A.B") == "owner_family|ab"
    # fuzzy: first-name entry matches full xlsx name
    _, _, sc = best_phone_match("Rajiv", [{"name": "Rajiv Jhangiani", "phone": "+91 1"}])
    assert sc >= 0.85, sc
    print("self-check OK")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        test()
        build()
