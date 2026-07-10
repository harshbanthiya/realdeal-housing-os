#!/usr/bin/env python3
"""Create Kalpataru apartments that have registrations but no building_unit.

MyGate lists only OCCUPIED flats, so a flat that was vacant at capture time has no
MyGate resident and — where IGR never seeded one either — no building_unit at all.
It then renders as an empty box in the Unit Registry even though the register knows
the apartment exists and who bought it.

This creates a unit for every (wing, flat) that a registration resolves to
unambiguously and that has no active unit today. "Unambiguously" means the record
carries an explicit floor (floor_text, or "माळा नं:" in the Devanagari), because a
bare 3-digit flat like "203" is floor 20 flat 3 OR floor 2 flat 03 and only the
floor decides. Flats that fail that bar are printed, not invented.

Units are created active with the true floor set, so the grid places them correctly.

    python3 scripts/create_missing_kalpataru_units.py --dry-run
    python3 scripts/create_missing_kalpataru_units.py
"""
from __future__ import annotations

import sys
from collections import defaultdict

from _db import lit, run_psql
from audit_kalpataru_registrations import (BU_FILTER_UNIT, BU_FILTER_WING, BU_UNIT_DIGITS,
                                           BU_WING_LETTER, DOC_NUMBER, MK_FILTER_WING, SEP,
                                           db, floor_of, one_line, to_mygate_flat,
                                           unit_digits, wing_of, TOWER)
from load_kalpataru_mygate import BUILDING_ID, BUILDING_NAME

PER = {"A": 5, "B": 6, "C": 6, "D": 6}
MAX_FLOOR = 31


def main() -> int:
    dry = "--dry-run" in sys.argv
    q = chr(39)

    have = set()
    for w, d in db(f"""
        SELECT concat_ws({q}{SEP}{q}, regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1'),
               regexp_replace(unit_number,'\\D','','g'))
        FROM building_units
        WHERE building_id='{BUILDING_ID}' AND canonical_status='active';"""):
        have.add((w.strip(), d.strip()))

    rows = db(f"""
        SELECT concat_ws({q}{SEP}{q}, {one_line('r.wing_text')}, {one_line('r.unit_text')},
               {one_line('r.floor_text')}, {one_line('r.property_description_raw')},
               {TOWER}, {DOC_NUMBER})
        FROM unit_registration_records r
        WHERE r.building_id='{BUILDING_ID}';""")

    wanted: dict[tuple[str, str], int] = defaultdict(int)
    floors: dict[tuple[str, str], str] = {}
    ambiguous = []
    for wt, ut, ft, desc, tower, doc in rows:
        w = wing_of(wt, desc, tower)
        fl = floor_of(ft, desc)
        u = unit_digits(ut, desc)
        if not w or not u:
            continue
        flat = to_mygate_flat(u, fl, PER.get(w, 6))
        if not flat or (w, flat) in have:
            continue
        if fl <= 0 or fl > MAX_FLOOR:
            ambiguous.append(f"doc {doc}: {w} flat {u!r} — no explicit floor, not created")
            continue
        wanted[(w, flat)] += 1
        floors[(w, flat)] = str(fl)

    print(f"apartments to create: {len(wanted)}  (from {sum(wanted.values())} registrations)")
    print(f"skipped, floor unknown: {len(ambiguous)}")
    for a in ambiguous[:10]:
        print(f"  {a}")
    if len(ambiguous) > 10:
        print(f"  … {len(ambiguous)-10} more")
    if not wanted:
        return 0
    for (w, f) in sorted(wanted)[:12]:
        print(f"  + {w}-{f}  (floor {floors[(w,f)]}, {wanted[(w,f)]} regs)")
    if len(wanted) > 12:
        print(f"  … {len(wanted)-12} more")

    vals = ",".join(
        f"({lit('KALPATARU RADIANCE  ' + w)},{lit(f)},{lit(floors[(w,f)])})"
        for (w, f) in sorted(wanted))
    sql = f"""
BEGIN;
CREATE TEMP TABLE mk(wing text, unit_number text, floor text) ON COMMIT DROP;
INSERT INTO mk VALUES {vals};

INSERT INTO building_units (building_id, building_name, wing, unit_number, floor,
                            canonical_status, confidence, metadata)
SELECT '{BUILDING_ID}', {lit(BUILDING_NAME)}, m.wing, m.unit_number, m.floor,
       'active', 0.6,
       jsonb_build_object('source','igr_registration_recovery',
                          'seeded_from','registration',
                          'note','flat has registrations but no MyGate resident')
FROM mk m
WHERE NOT EXISTS (
    SELECT 1 FROM building_units bu
     WHERE bu.building_id='{BUILDING_ID}' AND bu.canonical_status='active'
       AND regexp_replace(upper(bu.wing),'.*([A-Z])\\s*$','\\1')
           = regexp_replace(upper(m.wing),'.*([A-Z])\\s*$','\\1')
       AND regexp_replace(bu.unit_number,'\\D','','g') = m.unit_number);

SELECT 'created', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND metadata->>'source'='igr_registration_recovery';
SELECT 'active_units', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND canonical_status='active';
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("\nDRY-RUN (rolled back)\n" if dry else "\nCOMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
