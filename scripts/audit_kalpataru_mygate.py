#!/usr/bin/env python3
"""Unit-by-unit reconciliation of the MyGate directory against the canonical DB.

Answers one question per apartment: does the Unit Registry UI show this flat with
every resident MyGate lists, under the right role?

For each (wing, flat) in captures/mygate_directory/*.json it checks:
  1. a single active, on-grid building_unit exists for that wing+flat;
  2. every resident (keyed on mygate_ruid) has a contact carrying mygate_unit,
     which is what web/src/lib/cockpit/data.ts gates the UI query on;
  3. every resident has a relationship to THAT unit with the expected
     owner/tenant role.

Exit code is non-zero if any flat is untouched or any resident is unrepresented,
so this doubles as the regression check for load_kalpataru_mygate.py.

    python3 scripts/audit_kalpataru_mygate.py           # summary + first gaps
    python3 scripts/audit_kalpataru_mygate.py --all     # list every gap
"""
from __future__ import annotations

import sys
from collections import defaultdict

from _db import run_psql
from load_kalpataru_mygate import BUILDING_ID, BUILDING_NAME, load_residents


def db_rows(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(f"psql failed:\n{out}")
    return [ln.split("|") for ln in out.strip().splitlines() if ln.strip()]


def main() -> int:
    show_all = "--all" in sys.argv
    residents = load_residents()

    # MyGate truth: (wing, flat_digits) -> {ruid: (name, role)}
    mygate: dict[tuple[str, str], dict[str, tuple[str, str]]] = defaultdict(dict)
    for r in residents:
        mygate[(r["wing"], r["flatd"])][r["ruid"]] = (r["name"], r["rel"])

    # DB units, keyed the way the UI keys them (wing letter + flat digits), and only
    # the ones the Unit Registry actually renders.
    unit_rows = db_rows(f"""
        SELECT regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1'),
               regexp_replace(unit_number,'\\D','','g'), id::text
        FROM building_units
        WHERE building_id='{BUILDING_ID}'
          AND canonical_status='active'
          AND (metadata->>'offgrid') IS DISTINCT FROM 'true';""")
    units: dict[tuple[str, str], list[str]] = defaultdict(list)
    for w, d, uid in unit_rows:
        if d:
            units[(w.strip(), d.strip())].append(uid.strip())

    # DB relationships as the UI sees them: mygate_unit set on the contact.
    rel_rows = db_rows(f"""
        SELECT bu.id::text, c.metadata->>'mygate_ruid', r.relationship_type
        FROM contact_property_relationships r
        JOIN contacts c ON c.id=r.contact_id
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE bu.building_id='{BUILDING_ID}'
          AND c.metadata->>'mygate_unit' IS NOT NULL
          AND c.metadata->>'mygate_ruid' IS NOT NULL;""")
    # A contact can hold several relationships to one unit (e.g. both 'owner' and the
    # 'landlord' row phase 6.26 added), so collect a SET of roles, never overwrite.
    rel: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for uid, ruid, role in rel_rows:
        rel[uid.strip()][ruid.strip()].add(role.strip())
    # 'landlord' is how IGR records an owner who leases out; treat it as satisfying 'owner'.
    ROLE_ALIASES = {"owner": {"owner", "landlord"}, "tenant": {"tenant"}}

    missing_unit, dup_unit, missing_res, wrong_role = [], [], [], []
    ok_flats = 0

    for key in sorted(mygate):
        w, d = key
        uids = units.get(key, [])
        if not uids:
            missing_unit.append(f"{w}-{d}")
            continue
        if len(uids) > 1:
            dup_unit.append(f"{w}-{d} ({len(uids)} units)")
        have: dict[str, set[str]] = defaultdict(set)
        for uid in uids:
            for ruid, roles in rel.get(uid, {}).items():
                have[ruid] |= roles
        flat_ok = True
        for ruid, (name, role) in mygate[key].items():
            if ruid not in have:
                missing_res.append(f"{w}-{d} {name} ({role})")
                flat_ok = False
            elif not (have[ruid] & ROLE_ALIASES[role]):
                got = "/".join(sorted(have[ruid]))
                wrong_role.append(f"{w}-{d} {name}: db={got} mygate={role}")
                flat_ok = False
        if flat_ok and len(uids) == 1:
            ok_flats += 1

    total = len(mygate)
    print(f"{BUILDING_NAME} — MyGate reconciliation")
    print(f"  flats in MyGate       {total}")
    print(f"  residents in MyGate   {sum(len(v) for v in mygate.values())}")
    print(f"  flats fully reconciled{ok_flats:>6}   ({ok_flats*100//max(total,1)}%)")
    print(f"  flats with no unit    {len(missing_unit)}")
    print(f"  flats w/ dup units    {len(dup_unit)}")
    print(f"  residents not linked  {len(missing_res)}")
    print(f"  role mismatches       {len(wrong_role)}")

    for label, rows in (("NO UNIT", missing_unit), ("DUP UNITS", dup_unit),
                        ("RESIDENT NOT LINKED", missing_res), ("ROLE MISMATCH", wrong_role)):
        if rows:
            print(f"\n{label} ({len(rows)}):")
            for x in (rows if show_all else rows[:15]):
                print(f"  {x}")
            if not show_all and len(rows) > 15:
                print(f"  … {len(rows)-15} more (--all)")

    # --- grid placement, mirroring web/src/lib/cockpit/data.ts floorPos() ---------------
    # The Unit Registry lays flats out at (floor, flat - floor*10). Two flats landing on one
    # slot means one is invisible; that is what made tower A's 30th floor look empty.
    PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
    grid_rows = db_rows(f"""
        SELECT regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1'),
               regexp_replace(unit_number,'\\D','','g'), coalesce(floor,'')
        FROM building_units
        WHERE building_id='{BUILDING_ID}' AND canonical_status='active'
          AND (metadata->>'offgrid') IS DISTINCT FROM 'true';""")
    slots: dict[str, dict[tuple[int, int], str]] = defaultdict(dict)
    collisions, offgrid = [], defaultdict(int)
    top: dict[str, int] = defaultdict(int)
    for w, d, fl in grid_rows:
        w, d, fl = w.strip(), d.strip(), fl.strip()
        if not d or w not in PER_FLOOR:
            continue
        if not fl.isdigit():
            offgrid[w] += 1
            continue
        f = int(fl)
        p = int(d) - f * 10
        if not 1 <= p <= PER_FLOOR[w]:
            offgrid[w] += 1
            continue
        if (f, p) in slots[w]:
            collisions.append(f"{w} floor {f} pos {p}: {slots[w][(f,p)]} vs {d}")
        slots[w][(f, p)] = d
        top[w] = max(top[w], f)

    print("\ngrid placement (as the Unit Registry lays it out)")
    print("  wing  floors  flats  boxes  empty  off-grid")
    for w in sorted(PER_FLOOR):
        boxes = top[w] * PER_FLOOR[w]
        print(f"   {w}     {top[w]:>3}   {len(slots[w]):>4}   {boxes:>4}   {boxes-len(slots[w]):>4}   {offgrid[w]:>4}")
    print(f"  collisions {len(collisions)}")
    for c in (collisions if show_all else collisions[:10]):
        print(f"    {c}")
    print("  empty boxes are flats MyGate does not list (unoccupied); off-grid units keep a"
          "\n  null floor and are placed by the data.ts heuristic instead.")

    clean = not (missing_unit or dup_unit or missing_res or wrong_role or collisions)
    print("\nEVERY APARTMENT TOUCHED" if clean else "\nGAPS FOUND — see above")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
