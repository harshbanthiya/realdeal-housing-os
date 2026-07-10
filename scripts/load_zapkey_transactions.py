#!/usr/bin/env python3
"""Load Zapkey transaction listings for Kalpataru Radiance into zapkey_transactions.

Zapkey indexes every registration for a project with its date, type and unit — but NOT the
IGR document number. So this fills coverage ("flat A-105 sold in 2019") for apartments our
IGR ingest has no document for at all; it is not a substitute for an Index II.

Zapkey's floor and tower columns are dirty: unit "224" comes back with floor 2, though 224 is
floor 22 position 4 under Kalpataru's floor*10+position scheme. The unit NUMBER is internally
consistent, so it decides the flat and the floor; tower is used only as a wing hint when the
unit string carries no "A-" prefix. Rows whose wing cannot be established, or whose flat does
not fit the scheme, are loaded UNLINKED and left for review rather than guessed onto a flat.

Everything lands link_status='pending_review'.

    python3 scripts/load_zapkey_transactions.py --dry-run
    python3 scripts/load_zapkey_transactions.py
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

from _db import lit, run_psql
from load_kalpataru_mygate import BUILDING_ID

CSV = Path(__file__).resolve().parents[1] / "imports" / "zapkey" / "kalpataru_transactions.csv"
PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
MAX_FLOOR = 31


def wing_of(unit: str, tower: str) -> str:
    m = re.match(r"\s*([A-D])\s*-", unit or "")
    if m:
        return m.group(1)
    # tower is free text: "B B", "Ellora C", "-, B B", "28, D". Last bare A-D token wins.
    tokens = re.findall(r"\b([A-D])\b", (tower or "").upper())
    return tokens[-1] if tokens else ""


def flat_and_floor(unit: str, wing: str) -> tuple[str, int | None]:
    """Kalpataru: flat = floor*10 + position. The unit digits ARE the flat number."""
    d = re.sub(r"\D", "", unit or "")
    if not d:
        return "", None
    n = int(d)
    floor, pos = n // 10, n % 10
    if 1 <= floor <= MAX_FLOOR and 1 <= pos <= PER_FLOOR.get(wing, 6):
        return d, floor
    return d, None                                  # digits kept, floor unproven


def iso(d: str) -> str | None:
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(d.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def main() -> int:
    dry = "--dry-run" in sys.argv
    if not CSV.exists():
        sys.exit(f"missing {CSV}")

    rows = list(csv.DictReader(CSV.open()))
    vals, unresolved = [], 0
    for r in rows:
        wing = wing_of(r["unit"], r["tower"])
        flat, floor = flat_and_floor(r["unit"], wing) if wing else ("", None)
        if not wing or not flat or floor is None:
            unresolved += 1
        vals.append(
            f"({lit(r['comps_id'])},{lit(r['transaction_type'])},{lit(iso(r['reg_date']))},"
            f"{lit(r['unit'])},{lit(r['floor'])},{lit(r['tower'])},{lit(r['reg_date'])},"
            f"{lit(wing or None)},{lit(flat or None)},"
            f"{('NULL' if floor is None else str(floor))})")

    print(f"rows={len(rows)}  resolvable to a flat={len(rows)-unresolved}  unresolved={unresolved}")

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
SELECT z.comps_id, '{BUILDING_ID}'::uuid, bu.id, z.transaction_type, z.registration_date,
       z.unit_raw, z.floor_raw, z.tower_raw, z.reg_date_raw,
       z.wing_letter, z.unit_number, z.floor_derived,
       'pending_review',
       CASE WHEN bu.id IS NULL THEN 'wing/flat not resolved from Zapkey unit string' END,
       jsonb_build_object('source','zapkey','phase','zapkey_coverage_2026_07_10',
                          'project','Kalpataru Radiance','has_doc_number', false,
                          'is_fake', false, 'external_calls_made', true)
FROM z
LEFT JOIN building_units bu
       ON bu.building_id='{BUILDING_ID}'::uuid
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

SELECT 'total', count(*) FROM zapkey_transactions;
SELECT 'linked_to_unit', count(*) FROM zapkey_transactions WHERE building_unit_id IS NOT NULL;
SELECT 'unlinked', count(*) FROM zapkey_transactions WHERE building_unit_id IS NULL;
SELECT 'flats_covered', count(DISTINCT building_unit_id) FROM zapkey_transactions
   WHERE building_unit_id IS NOT NULL;
SELECT 'flats_with_no_igr_registration', count(*) FROM vw_zapkey_units_without_registrations;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
