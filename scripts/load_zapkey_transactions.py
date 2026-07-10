#!/usr/bin/env python3
"""Load Zapkey transaction listings into zapkey_transactions.

Zapkey indexes every registration for a project with its date, type and unit — but NOT the
IGR document number. So it fills coverage ("flat A-105 sold in 2019") for apartments our IGR
ingest has no document for at all; it is not a substitute for an Index II.

The two buildings number flats differently and must never be conflated:

    Kalpataru Radiance   flat = floor*10  + position   (floor 29 flat 1 = 291)
    Imperial Heights     flat = floor*100 + position   (floor 11 flat 3 = 1103)

Zapkey's floor and tower columns are dirty. Kalpataru unit "224" comes back with floor 2
though 224 is floor 22; Imperial Heights returns bare positions ("unit=1, floor=17" = 1703)
alongside full numbers and outright junk ("032603"). So each row is resolved against the
building's scheme and the stated floor, and anything that does not check out is loaded
UNLINKED for review rather than guessed onto a flat.

Imperial Heights is indexed by Zapkey under three names — "Wadhwa Imperial Heights"
(township), "Imperial Heights The Epitome" and "Imperial Heights Phase 2" — all the same
building over the years, per the operator. They are merged here, deduped on comps_id.

Everything lands link_status='pending_review'.

    python3 scripts/load_zapkey_transactions.py --building kalpataru --dry-run
    python3 scripts/load_zapkey_transactions.py --building imperial_heights
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from _db import lit, run_psql

ROOT = Path(__file__).resolve().parents[1] / "imports" / "zapkey"

BUILDINGS = {
    "kalpataru": {
        "name": "Kalpataru Radiance",
        "csv": ROOT / "kalpataru_transactions.csv",
        "scheme": "floor10",
        "per_floor": {"A": 5, "B": 6, "C": 6, "D": 6},
        "max_floor": 31,
    },
    "imperial_heights": {
        "name": "Imperial Heights",
        "csv": ROOT / "imperial_heights_transactions.csv",
        "scheme": "floor100",
        "per_floor": {"A": 12, "B": 12, "C": 12, "D": 12},
        "max_floor": 50,
    },
}


def wing_of(unit: str, tower: str) -> str:
    m = re.match(r"\s*([A-D])\s*[-/]", unit or "")
    if m:
        return m.group(1)
    # tower is free text: "B B", "Ellora C", "D Imperial Heights", "-, B B". Last bare A-D wins.
    tokens = re.findall(r"\b([A-D])\b", (tower or "").upper())
    return tokens[-1] if tokens else ""


def resolve(cfg: dict, unit: str, floor_raw: str, wing: str) -> tuple[str, int | None]:
    """-> (flat number as the DB stores it, floor) or ("", None) when it does not check out."""
    d = re.sub(r"\D", "", unit or "")
    if not d or len(d) > 4:
        return "", None
    n = int(d)
    per = cfg["per_floor"].get(wing, 6)
    fl = int(floor_raw) if floor_raw.strip().isdigit() else 0
    floor = fl if 1 <= fl <= cfg["max_floor"] else None

    if cfg["scheme"] == "floor10":
        # The unit digits ARE the flat number; the stated floor is unreliable, so derive it.
        f, pos = n // 10, n % 10
        if 1 <= f <= cfg["max_floor"] and 1 <= pos <= per:
            return d, f
        return d, None                                  # digits kept, floor unproven
    # floor100: the register writes the full number, or a bare position with the floor beside it.
    if floor is None:
        return (d, n // 100) if len(d) >= 3 and 1 <= n % 100 <= per and 1 <= n // 100 <= cfg["max_floor"] else ("", None)
    if 1 <= n <= per:
        return str(floor * 100 + n), floor              # position only
    if n // 100 == floor and 1 <= n % 100 <= per:
        return d, floor                                 # already full
    return "", None


def main() -> int:
    dry = "--dry-run" in sys.argv
    key = "kalpataru"
    if "--building" in sys.argv:
        key = sys.argv[sys.argv.index("--building") + 1]
    if key not in BUILDINGS:
        sys.exit(f"--building must be one of {list(BUILDINGS)}")
    cfg = BUILDINGS[key]
    if not cfg["csv"].exists():
        sys.exit(f"missing {cfg['csv']}")

    bid = run_psql(f"select id::text from buildings where name={lit(cfg['name'])} "
                   f"order by (select count(*) from building_units u where u.building_id=buildings.id) desc limit 1;")[1].strip()
    if not bid:
        sys.exit(f"no building row for {cfg['name']}")

    rows = list(csv.DictReader(cfg["csv"].open()))
    vals, unresolved = [], 0
    for r in rows:
        wing = wing_of(r["unit"], r["tower"])
        flat, floor = resolve(cfg, r["unit"], r["floor"], wing) if wing else ("", None)
        if not wing or not flat:
            unresolved += 1
        vals.append(
            f"({lit(r['comps_id'])},{lit(r['transaction_type'])},{lit(to_iso(r['reg_date']))},"
            f"{lit(r['unit'])},{lit(r['floor'])},{lit(r['tower'])},{lit(r['reg_date'])},"
            f"{lit(wing or None)},{lit(flat or None)},{('NULL' if floor is None else str(floor))})")

    print(f"{cfg['name']}: rows={len(rows)}  resolved={len(rows)-unresolved}  unresolved={unresolved}")

    sql = f"""
BEGIN;
CREATE TEMP TABLE z(comps_id text, transaction_type text, registration_date date,
                    unit_raw text, floor_raw text, tower_raw text, reg_date_raw text,
                    wing_letter text, unit_number text, floor_derived int) ON COMMIT DROP;
INSERT INTO z VALUES {",".join(vals)};

INSERT INTO zapkey_transactions
   (comps_id, building_id, building_unit_id, transaction_type, registration_date,
    unit_raw, floor_raw, tower_raw, reg_date_raw, wing_letter, unit_number, floor_derived,
    link_status, resolution_notes, raw_context)
SELECT z.comps_id, '{bid}'::uuid, bu.id, z.transaction_type, z.registration_date,
       z.unit_raw, z.floor_raw, z.tower_raw, z.reg_date_raw,
       z.wing_letter, z.unit_number, z.floor_derived,
       'pending_review',
       CASE WHEN bu.id IS NULL THEN 'wing/flat not resolved from Zapkey unit string' END,
       jsonb_build_object('source','zapkey','phase','zapkey_coverage_2026_07_10',
                          'project',{lit(cfg['name'])},'has_doc_number', false,
                          'is_fake', false, 'external_calls_made', true)
FROM z
LEFT JOIN building_units bu
       ON bu.building_id='{bid}'::uuid
      AND bu.canonical_status='active'
      AND regexp_replace(upper(bu.wing),'.*([A-Z])\\s*$','\\1') = z.wing_letter
      AND regexp_replace(bu.unit_number,'\\D','','g')          = z.unit_number
ON CONFLICT (comps_id) DO UPDATE SET
    building_unit_id = EXCLUDED.building_unit_id,
    transaction_type = EXCLUDED.transaction_type,
    registration_date = EXCLUDED.registration_date,
    wing_letter = EXCLUDED.wing_letter,
    unit_number = EXCLUDED.unit_number,
    floor_derived = EXCLUDED.floor_derived,
    updated_at = now();

SELECT 'total_this_building', count(*) FROM zapkey_transactions WHERE building_id='{bid}'::uuid;
SELECT 'linked_to_unit', count(*) FROM zapkey_transactions
   WHERE building_id='{bid}'::uuid AND building_unit_id IS NOT NULL;
SELECT 'unlinked', count(*) FROM zapkey_transactions
   WHERE building_id='{bid}'::uuid AND building_unit_id IS NULL;
SELECT 'flats_covered', count(DISTINCT building_unit_id) FROM zapkey_transactions
   WHERE building_id='{bid}'::uuid AND building_unit_id IS NOT NULL;
SELECT 'flats_with_no_igr_registration', count(*) FROM vw_zapkey_units_without_registrations
   WHERE building_name={lit(cfg['name'])};
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    return code


def to_iso(d: str) -> str | None:
    from datetime import datetime
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(d.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


if __name__ == "__main__":
    raise SystemExit(main())
