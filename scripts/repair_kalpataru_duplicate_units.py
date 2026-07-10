#!/usr/bin/env python3
"""Restore Kalpataru units wrongly left canonical_status='duplicate'.

Background: dedupe_kalpataru_units.py originally ranked the keeper of each
duplicate (wing, flat) pair by relationship count alone. For 14 flats the messy
IGR row ("C/146") held the relationships while the clean row ("146") was the one
phase 6.24 had marked active. The messy row won, the active row was deleted, and
those 14 flats disappeared from the Unit Registry — their superseded_by now points
at a unit that no longer exists, and 36 relationships sit on rows the UI filters out.

This restores exactly the rows that satisfy all four conditions:
  * canonical_status = 'duplicate'
  * superseded_by does not resolve to an existing building_unit
  * no active sibling on the same (wing letter, flat digits)
  * MyGate lists that flat as occupied

The 8 other duplicate rows (A-603, D-803, …) have no relationships and no MyGate
flat, so they stay retired. The 4 rows superseded by a *different* flat
(A-604 -> A-64) resolve to a live target and are left alone — that is a separate
phase 6.24 merge to review, not this script's business.

Restored rows also get unit_number normalised to the flat digits, because the UI
renders unit_number verbatim and "212, Wing A Aura, Radiance A," is not a flat
number. The original is preserved in metadata.unit_number_raw.

    python3 scripts/repair_kalpataru_duplicate_units.py --dry-run
    python3 scripts/repair_kalpataru_duplicate_units.py
"""
from __future__ import annotations

import sys

from _db import lit, run_psql
from load_kalpataru_mygate import BUILDING_ID, load_residents


def main() -> int:
    dry = "--dry-run" in sys.argv
    occupied = sorted({(r["wing"], r["flatd"]) for r in load_residents()})
    keys = ",".join(f"({lit(w)},{lit(d)})" for w, d in occupied)

    sql = f"""
BEGIN;

CREATE TEMP TABLE mygate_flat(w text, d text) ON COMMIT DROP;
INSERT INTO mygate_flat VALUES {keys};

CREATE TEMP TABLE restore ON COMMIT DROP AS
WITH k AS (
  SELECT id, canonical_status st, metadata->>'superseded_by' sb,
         regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') w,
         regexp_replace(unit_number,'\\D','','g') d
  FROM building_units WHERE building_id='{BUILDING_ID}')
SELECT k.id, k.d
FROM k
JOIN mygate_flat mf ON mf.w=k.w AND mf.d=k.d
WHERE k.st='duplicate'
  AND NOT EXISTS (SELECT 1 FROM building_units t WHERE t.id::text=k.sb)
  AND NOT EXISTS (SELECT 1 FROM k a WHERE a.w=k.w AND a.d=k.d AND a.st='active');

UPDATE building_units b
   SET canonical_status='active',
       unit_number=r.d,
       metadata = (coalesce(b.metadata,'{{}}'::jsonb) - 'superseded_by')
                  || jsonb_build_object('unit_number_raw', b.unit_number,
                                        'restored_by','mygate_reconciliation_2026-07-10')
  FROM restore r WHERE b.id=r.id;

SELECT 'restored', count(*) FROM restore;
SELECT 'active_units', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND canonical_status='active';
SELECT 'still_duplicate', count(*) FROM building_units
   WHERE building_id='{BUILDING_ID}' AND canonical_status='duplicate';
SELECT 'rels_now_visible', count(*) FROM contact_property_relationships r
   JOIN restore x ON x.id=r.building_unit_id;

{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
