#!/usr/bin/env python3
"""Backfill building_units.floor for Kalpataru Radiance from the MyGate directory.

The Unit Registry grid places each flat by floor. Where floor is null the UI falls
back to deriveFloorPos(), a heuristic that reads "301" as floor 3 / unit 01 instead
of floor 30 / unit 1 — so flat 301 collides with flat 31 in the grid and the 30th
floor renders empty. MyGate carries the true floor for every occupied flat.

Verified against all 625 MyGate flats: flat_number = floor*10 + position, with
position 1..5 in wing A and 1..6 in B/C/D. No exceptions.

Units MyGate does not list keep floor null and fall back to the heuristic.

    python3 scripts/backfill_kalpataru_floors.py --dry-run
    python3 scripts/backfill_kalpataru_floors.py
"""
from __future__ import annotations

import sys

from _db import lit, run_psql
from load_kalpataru_mygate import BUILDING_ID, load_residents


def main() -> int:
    dry = "--dry-run" in sys.argv
    # (wing letter, flat digits) -> floor, from MyGate
    floors = {(r["wing"], r["flatd"]): r["floor"] for r in load_residents() if r["floor"]}
    vals = ",".join(f"({lit(w)},{lit(d)},{lit(f)})" for (w, d), f in sorted(floors.items()))

    sql = f"""
BEGIN;
CREATE TEMP TABLE mg_floor(w text, d text, floor text) ON COMMIT DROP;
INSERT INTO mg_floor VALUES {vals};

UPDATE building_units b SET floor = m.floor
  FROM mg_floor m
 WHERE b.building_id='{BUILDING_ID}'
   AND regexp_replace(upper(b.wing),'.*([A-Z])\\s*$','\\1') = m.w
   AND regexp_replace(b.unit_number,'\\D','','g') = m.d
   AND b.floor IS DISTINCT FROM m.floor;

SELECT 'mygate_flats', count(*) FROM mg_floor;
SELECT 'active_with_floor', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND canonical_status='active' AND floor IS NOT NULL;
SELECT 'active_without_floor', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND canonical_status='active' AND floor IS NULL;
-- sanity: floor must satisfy flat = floor*10 + position, position in 1..6
SELECT 'floor_rule_violations', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND floor IS NOT NULL
     AND regexp_replace(unit_number,'\\D','','g') <> ''
     AND (regexp_replace(unit_number,'\\D','','g')::int - floor::int*10) NOT BETWEEN 1 AND 6;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
