#!/usr/bin/env python3
"""Summarise the property-relationship pipeline as counts only. Read-only.

Optional filters: --contact-id, --building-name, --relationship-status.
Reports building_aliases / building_units / contact_property_relationships /
property_relationship_review_items totals, relationships by type and status, and
units by building. Never prints person names, phones, emails, websites, or
addresses (building/property names are business data and may appear).
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def rel_where(contact_id: str | None, building_name: str | None, relationship_status: str | None) -> str:
    conds = []
    if contact_id:
        conds.append(f"cpr.contact_id = {sql_literal(contact_id)}")
    if building_name:
        lit = sql_literal(f"%{building_name}%")
        conds.append(f"(b.name ILIKE {lit} OR bu.building_name ILIKE {lit})")
    if relationship_status:
        conds.append(f"cpr.relationship_status = {sql_literal(relationship_status)}")
    return ("WHERE " + " AND ".join(conds)) if conds else ""

def summary_sql(contact_id, building_name, relationship_status) -> str:
    rw = rel_where(contact_id, building_name, relationship_status)
    bname = f"%{building_name}%" if building_name else None
    alias_unit_filter = f"AND b.name ILIKE {sql_literal(bname)}" if bname else ""
    return f"""
WITH scoped_rel AS (
  SELECT cpr.id, cpr.relationship_type, cpr.relationship_status
  FROM contact_property_relationships cpr
  LEFT JOIN buildings b ON b.id = cpr.building_id
  LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
  {rw}
)
SELECT 'building_aliases' AS item, count(*)::text AS val
  FROM building_aliases ba LEFT JOIN buildings b ON b.id = ba.building_id
  WHERE true {alias_unit_filter}
UNION ALL SELECT 'building_units', count(*)::text
  FROM building_units bu LEFT JOIN buildings b ON b.id = bu.building_id
  WHERE true {alias_unit_filter}
UNION ALL SELECT 'contact_property_relationships', count(*)::text FROM scoped_rel
UNION ALL SELECT 'property_relationship_review_items', count(*)::text
  FROM property_relationship_review_items
  WHERE contact_property_relationship_id IN (SELECT id FROM scoped_rel)
UNION ALL SELECT 'rel_type:' || relationship_type, count(*)::text FROM scoped_rel GROUP BY relationship_type
UNION ALL SELECT 'rel_status:' || relationship_status, count(*)::text FROM scoped_rel GROUP BY relationship_status
ORDER BY item;
"""

def units_by_building_sql(building_name) -> str:
    bname = f"%{building_name}%" if building_name else None
    flt = f"WHERE COALESCE(b.name, bu.building_name) ILIKE {sql_literal(bname)}" if bname else ""
    return f"""
SELECT 'units_in:' || COALESCE(b.name, bu.building_name, '(unknown)') AS item, count(*)::text
FROM building_units bu LEFT JOIN buildings b ON b.id = bu.building_id
{flt}
GROUP BY COALESCE(b.name, bu.building_name, '(unknown)')
ORDER BY item;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Property relationship summary. Counts only; no DB writes.")
    parser.add_argument("--contact-id")
    parser.add_argument("--building-name")
    parser.add_argument("--relationship-status")
    args = parser.parse_args()

    print("Property relationship summary. Counts only; no raw personal values are printed.")
    if args.contact_id:
        print(f"contact_id: {args.contact_id}")
    if args.building_name:
        print(f"building_name filter: {args.building_name}")
    if args.relationship_status:
        print(f"relationship_status filter: {args.relationship_status}")

    code, output = run_psql(summary_sql(args.contact_id, args.building_name, args.relationship_status))
    print(output)
    code2, output2 = run_psql(units_by_building_sql(args.building_name))
    print(output2)
    return code or code2

if __name__ == "__main__":
    raise SystemExit(main())
