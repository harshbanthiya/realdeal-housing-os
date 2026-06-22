#!/usr/bin/env python3
"""Owner/building/unit dashboard summary. Read-only; counts only; no DB writes.

Optional filters: --building-name, --relationship-status, --relationship-type,
--contact-id. Prints totals plus row counts for the Phase 5.10 dashboard views and a
revert-ready count. Never prints person names, phones, emails, websites, or
addresses (building/unit/property names are business data and may appear).
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def rel_filter(building_name, relationship_status, relationship_type, contact_id, alias="cpr") -> str:
    conds = []
    if relationship_status:
        conds.append(f"{alias}.relationship_status = {sql_literal(relationship_status)}")
    if relationship_type:
        conds.append(f"{alias}.relationship_type = {sql_literal(relationship_type)}")
    if contact_id:
        conds.append(f"{alias}.contact_id = {sql_literal(contact_id)}")
    if building_name:
        lit = sql_literal(f"%{building_name}%")
        conds.append(
            f"(EXISTS (SELECT 1 FROM buildings b WHERE b.id = {alias}.building_id AND b.name ILIKE {lit})"
            f" OR EXISTS (SELECT 1 FROM building_units bu WHERE bu.id = {alias}.building_unit_id AND bu.building_name ILIKE {lit}))"
        )
    return (" AND " + " AND ".join(conds)) if conds else ""

def summary_sql(building_name, relationship_status, relationship_type, contact_id) -> str:
    rf = rel_filter(building_name, relationship_status, relationship_type, contact_id)
    bn = sql_literal(f"%{building_name}%") if building_name else None
    bfilter = f"WHERE COALESCE(b.name, bu.building_name) ILIKE {bn}" if bn else ""
    return f"""
SELECT 'total_buildings' AS item, count(*)::text AS val FROM buildings
UNION ALL SELECT 'total_units', count(*)::text FROM building_units bu LEFT JOIN buildings b ON b.id = bu.building_id {bfilter}
UNION ALL SELECT 'active_owner_relationships', count(*)::text FROM contact_property_relationships cpr
  WHERE cpr.relationship_type = 'owner' AND cpr.relationship_status = 'active' {rf}
UNION ALL SELECT 'pending_relationships', count(*)::text FROM contact_property_relationships cpr
  WHERE cpr.relationship_status IN ('pending_review', 'needs_more_info') {rf}
UNION ALL SELECT 'approved_review_items', count(*)::text FROM property_relationship_review_items WHERE status = 'approved'
UNION ALL SELECT 'relationship_action_log', count(*)::text FROM property_relationship_action_log
UNION ALL SELECT 'view_owner_dashboard_rows', count(*)::text FROM vw_owner_relationship_dashboard
UNION ALL SELECT 'view_building_unit_summary_rows', count(*)::text FROM vw_building_unit_owner_summary
UNION ALL SELECT 'view_contact_property_trace_full_rows', count(*)::text FROM vw_contact_property_trace_full
UNION ALL SELECT 'view_revert_readiness_rows', count(*)::text FROM vw_property_relationship_revert_readiness
UNION ALL SELECT 'revert_ready_count', count(*)::text FROM vw_property_relationship_revert_readiness WHERE revert_allowed = true
ORDER BY item;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Owner/building/unit dashboard summary. Counts only; no DB writes.")
    parser.add_argument("--building-name")
    parser.add_argument("--relationship-status")
    parser.add_argument("--relationship-type")
    parser.add_argument("--contact-id")
    args = parser.parse_args()

    print("Owner/building/unit dashboard summary. Counts only; no raw personal values are printed.")
    for label, val in (("building_name", args.building_name), ("relationship_status", args.relationship_status),
                       ("relationship_type", args.relationship_type), ("contact_id", args.contact_id)):
        if val:
            print(f"filter {label}: {val}")

    code, output = run_psql(summary_sql(args.building_name, args.relationship_status, args.relationship_type, args.contact_id))
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
