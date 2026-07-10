#!/usr/bin/env python3
"""Merge duplicate Kalpataru Radiance building_units sharing (wing letter, flat digits).

IGR imports created a second row for ~17 flats with a messy unit_number
("A -Ora/155,", "D-295Shop No:") alongside the clean one ("155", "295").
The duplicates make load_kalpataru_mygate.py non-idempotent: its canonical
unit pick can land on either twin, so every re-run re-inserts ~17 relationships.

Keeper per group = most relationships, then lowest id. Loser's registration
records are re-pointed at the keeper, then the loser row is deleted.

    python3 scripts/dedupe_kalpataru_units.py --dry-run   # counts, rolled back
    python3 scripts/dedupe_kalpataru_units.py             # commit
"""
from __future__ import annotations

import sys

from _db import run_psql

BUILDING_ID = "f63d75ab-2ef9-48a9-afe2-cab3c4283283"


def main() -> int:
    dry = "--dry-run" in sys.argv
    sql = f"""
BEGIN;

CREATE TEMP TABLE merge_map ON COMMIT DROP AS
WITH k AS (
  SELECT id,
         regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') w,
         regexp_replace(unit_number,'\\D','','g') d
  FROM building_units WHERE building_id='{BUILDING_ID}'),
dup AS (
  SELECT w,d FROM k WHERE d<>'' GROUP BY w,d HAVING count(*)>1),
scored AS (
  SELECT k.id, k.w, k.d,
         (SELECT count(*) FROM contact_property_relationships r
           WHERE r.building_unit_id=k.id) rels
  FROM k JOIN dup g ON g.w=k.w AND g.d=k.d),
ranked AS (
  SELECT id, w, d,
         row_number() OVER (PARTITION BY w,d ORDER BY rels DESC, id) rn,
         first_value(id) OVER (PARTITION BY w,d ORDER BY rels DESC, id) keeper
  FROM scored)
SELECT id AS loser, keeper FROM ranked WHERE rn>1;

-- registration records are the only child rows the losers hold; keep them
UPDATE unit_registration_records u SET building_unit_id=m.keeper
  FROM merge_map m WHERE u.building_unit_id=m.loser;

DELETE FROM building_units b USING merge_map m WHERE b.id=m.loser;

SELECT 'merged_losers', count(*) FROM merge_map;
SELECT 'units_total', count(*) FROM building_units WHERE building_id='{BUILDING_ID}';
SELECT 'dup_groups_left', count(*) FROM (
  SELECT 1 FROM (
    SELECT regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') w,
           regexp_replace(unit_number,'\\D','','g') d
    FROM building_units WHERE building_id='{BUILDING_ID}') t
  WHERE d<>'' GROUP BY w,d HAVING count(*)>1) x;

{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
