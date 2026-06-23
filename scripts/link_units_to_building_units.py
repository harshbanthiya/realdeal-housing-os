"""Link unit_registration_records to building_units where wing_text+unit_text match.

Extracts wing letter from wing_text (e.g. "Wing A-Ora" → "A", "Wing D-Lumina" → "D"),
then joins on building_id + wing + unit_number. Patra Chawl and other non-matching
wings resolve to NULL and are safely skipped.

Usage:
  python scripts/link_units_to_building_units.py          # dry run — shows count
  python scripts/link_units_to_building_units.py --apply  # write building_unit_id
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql  # noqa: E402

# Extracts wing letter and unit number from unit_registration_records.
# unit_text is preferred; falls back to leading number in property_description_raw
# for English XLS format ("D/215 LUMINA..." or "305 WING A-ORA...").
# ponytail: inline SQL function — upgrade to stored function if reused elsewhere
_UNIT_EXPR = """
  COALESCE(
    NULLIF(urr.unit_text, ''),
    SUBSTRING(urr.property_description_raw FROM '^[A-Z]/([0-9]{3,4})\s'),
    SUBSTRING(urr.property_description_raw FROM '^([0-9]{3,4})\s+(?:KALPATARU|THE MEADOWS|WING|K)')
  )
"""

_WING_EXPR = "SUBSTRING(urr.wing_text FROM 'Wing ([A-Z])')"
# building_units.wing may be "KALPATARU RADIANCE  D" or just "D" — match on last letter
_BU_WING_EXPR = "RIGHT(TRIM(bu.wing), 1)"

_COUNT_SQL = f"""
SELECT COUNT(*) FROM unit_registration_records urr
JOIN building_units bu ON
  bu.building_id = urr.building_id
  AND {_BU_WING_EXPR} = {_WING_EXPR}
  AND bu.unit_number = ({_UNIT_EXPR})
WHERE urr.building_unit_id IS NULL
  AND urr.wing_text IS NOT NULL;
"""

_PREVIEW_SQL = f"""
SELECT urr.doc_number, urr.wing_text, urr.unit_text,
       {_WING_EXPR} AS wing_extracted,
       ({_UNIT_EXPR}) AS unit_resolved,
       bu.unit_number AS bu_unit
FROM unit_registration_records urr
JOIN building_units bu ON
  bu.building_id = urr.building_id
  AND {_BU_WING_EXPR} = {_WING_EXPR}
  AND bu.unit_number = ({_UNIT_EXPR})
WHERE urr.building_unit_id IS NULL
  AND urr.wing_text IS NOT NULL
LIMIT 10;
"""

_UPDATE_SQL = f"""
UPDATE unit_registration_records urr
SET building_unit_id = bu.id, updated_at = now()
FROM building_units bu
WHERE bu.building_id = urr.building_id
  AND {_BU_WING_EXPR} = {_WING_EXPR}
  AND bu.unit_number = ({_UNIT_EXPR})
  AND urr.building_unit_id IS NULL
  AND urr.wing_text IS NOT NULL;
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write building_unit_id (default: dry run)")
    args = ap.parse_args()

    code, out = run_psql(_COUNT_SQL)
    if code != 0:
        print(f"DB error: {out}")
        return 1

    linkable = int(out.strip() or "0")
    print(f"Linkable records (wing+unit match building_units): {linkable}")

    if linkable == 0:
        print("Nothing to link — already done or no matching building_units rows.")
        return 0

    _, preview = run_psql(_PREVIEW_SQL)
    if preview:
        print("\nSample matches:")
        for line in preview.splitlines():
            print(" ", line)

    if not args.apply:
        print(f"\nDry run — {linkable} record(s) would be linked. Re-run with --apply to write.")
        return 0

    code, out = run_psql(_UPDATE_SQL)
    if code != 0:
        print(f"Update failed: {out}")
        return 1

    print(f"\nLinked {linkable} record(s) → building_unit_id populated.")
    print("rows_linked:", linkable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
