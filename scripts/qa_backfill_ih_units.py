#!/usr/bin/env python3
"""Backfill the full authoritative apartment inventory for Imperial Heights.

`building_units` was only ever seeded from apartments that happened to appear in some
IGR registration document (415 rows). The real building, per the municipal Part
Occupation Certificate (BMC No.CHE/9430/BP(WS)/AP, 30-Nov-2012) and Fire NOC
(FB/HR/WS/183, 11-May-2012) -- both in
"RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/Imperial Heights/01. IH Society Documents/" --
has:
  - 4 wings (A, B, C, D), each with 1st-44th upper residential floors
  - Refuge floors (no regular units) at 9, 13, 17, 21, 23, 27, 31, 37
  - 5 units/floor in Wing A, 6 units/floor in Wings B/C/D (per the brochure floor plan,
    already encoded in web/src/lib/cockpit/data.ts's TOWER_PER_FLOOR)
  - Floor 43 has duplex units (non-standard layout) -- SKIPPED here pending the actual
    duplex unit numbering; do not guess at it.

That's ~36 standard residential floors x 5-6 units/floor x 4 wings =~ 800 apartments,
versus the 415 currently in the table -- roughly 400 real apartments were never even
entered into the registry (distinct from lacking a registration record).

Dry-run by default. Needs --apply --real-ok to write.
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

IH_BID = "0e72db71-8b93-4ecd-879c-17d8d8f2b206"
TOTAL_FLOORS = 44
REFUGE_FLOORS = {9, 13, 17, 21, 23, 27, 31, 37}
DUPLEX_FLOORS = {43}  # skipped -- unknown duplex unit numbering
PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
MAX_FLOOR = 55  # matches web/src/lib/cockpit/data.ts's parse cap


def derive_floor_pos(u: str) -> tuple[int, int] | None:
    """Mirror of web/src/lib/cockpit/data.ts's deriveFloorPos, for building the
    existing-units set in the same coordinate system the UI uses."""
    raw = re.sub(r"\D", "", u or "")
    if not raw:
        return None
    n = int(raw)
    if len(raw) == 3:
        fa3, pa3 = n // 100, n % 100
        if 1 <= fa3 <= 9 and 1 <= pa3 <= 12:
            return fa3, pa3
        fc, pc = n // 10, n % 10
        if 10 <= fc <= MAX_FLOOR and 1 <= pc <= 9:
            return fc, pc
    fa, pa = n // 100, n % 100
    if 1 <= fa <= MAX_FLOOR and 1 <= pa <= 12:
        return fa, pa
    fb, pb = n // 10, n % 10
    if 1 <= fb <= MAX_FLOOR:
        return fb, (pb or 10)
    return min(max(1, n), MAX_FLOOR), 1


def canonical_unit_number(floor: int, pos: int) -> str:
    return f"{floor}{pos:02d}"


def expected_apartments() -> list[tuple[str, int, int]]:
    out = []
    for wing, per_floor in PER_FLOOR.items():
        for floor in range(1, TOTAL_FLOORS + 1):
            if floor in REFUGE_FLOORS or floor in DUPLEX_FLOORS:
                continue
            for pos in range(1, per_floor + 1):
                out.append((wing, floor, pos))
    return out


def existing_set() -> set[tuple[str, int, int]]:
    _, out = run_psql(f"""
        SELECT wing, unit_number FROM building_units WHERE building_id='{IH_BID}';
    """)
    seen = set()
    for line in out.strip().splitlines():
        if "|" not in line:
            continue
        wing, unit = line.split("|", 1)
        fp = derive_floor_pos(unit)
        if fp:
            seen.add((wing, fp[0], fp[1]))
    return seen


def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"


def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    self_check()
    if args.selftest:
        return 0

    expected = expected_apartments()
    existing = existing_set()
    missing = [(w, f, p) for (w, f, p) in expected if (w, f, p) not in existing]

    print(f"Expected apartments (excl. refuge floors {sorted(REFUGE_FLOORS)}, "
          f"skipped floor(s) {sorted(DUPLEX_FLOORS)}): {len(expected)}")
    print(f"Already in building_units: {len(expected) - len(missing)}")
    print(f"To backfill: {len(missing)}")
    by_wing: dict[str, int] = {}
    for w, _, _ in missing:
        by_wing[w] = by_wing.get(w, 0) + 1
    for w in sorted(by_wing):
        print(f"  Wing {w}: {by_wing[w]} new rows")

    if not (args.apply and args.real_ok):
        print("\nDry run -- no DB writes. Add --apply --real-ok to insert.")
        sample = missing[:10]
        for w, f, p in sample:
            print(f"    Wing {w} floor {f} -> unit {canonical_unit_number(f, p)}")
        return 0

    tag = {
        "source": "qa_backfill_ih_units", "phase": "qa_2026_07_06",
        "note": "Structural placeholder from municipal OC/Fire NOC floor count -- "
                "no registration/ownership data yet, just confirms the apartment exists.",
        "authoritative_source": "BMC Part OC No.CHE/9430/BP(WS)/AP (30-Nov-2012); "
                                 "Mumbai Fire Brigade NOC FB/HR/WS/183 (11-May-2012)",
    }
    stmts = ["BEGIN;"]
    for w, f, p in missing:
        unit_no = canonical_unit_number(f, p)
        stmts.append(
            "INSERT INTO building_units (building_id, wing, unit_number, canonical_status, metadata) "
            f"VALUES ('{IH_BID}', {q(w)}, {q(unit_no)}, 'active', {jb(tag)});"
        )
    stmts.append("COMMIT;")
    code, out = run_psql("\n".join(stmts))
    print(f"Executed {len(stmts)} statements -> {out.strip() or 'ok'} (code {code})")
    return code


def self_check() -> None:
    """ponytail: smallest runnable check for the pieces unique to this script."""
    assert derive_floor_pos("102") == (1, 2)
    assert derive_floor_pos("2205") == (22, 5)
    assert derive_floor_pos("02") == (2, 1)  # matches the UI's (imperfect) parse -- see module docstring
    assert canonical_unit_number(1, 2) == "102"
    assert canonical_unit_number(22, 5) == "2205"

    exp = expected_apartments()
    assert all(f not in REFUGE_FLOORS for _, f, _ in exp)
    assert all(f not in DUPLEX_FLOORS for _, f, _ in exp)
    assert all(1 <= f <= TOTAL_FLOORS for _, f, _ in exp)
    n_a = sum(1 for w, _, _ in exp if w == "A")
    n_b = sum(1 for w, _, _ in exp if w == "B")
    residential_floors = TOTAL_FLOORS - len(REFUGE_FLOORS) - len(DUPLEX_FLOORS)
    assert n_a == residential_floors * PER_FLOOR["A"]
    assert n_b == residential_floors * PER_FLOOR["B"]

    print("self_check: all assertions passed")


if __name__ == "__main__":
    sys.exit(main())
