#!/usr/bin/env python3
"""Milestone 2B checkpoint summary. Read-only; counts only; no DB writes.

Prints the system summary, owner/unit batch quality, active/revert-ready relationship
counts, the pending candidate-queue count, the duplicate-risk count, and a recommended
next phase. Never prints person names, phones, emails, websites, or addresses
(building/unit/property names are business data and may appear).
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH = "REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001"
def summary_sql(batch_label: str) -> str:
    b = sql_literal(batch_label)
    return f"""
SELECT 'system_summary' AS section, key AS item, val::text AS count FROM (
  SELECT 'canonical_contacts_total' AS key, canonical_contacts_total AS val FROM vw_milestone_2b_summary
  UNION ALL SELECT 'active_canonical_contacts', active_canonical_contacts FROM vw_milestone_2b_summary
  UNION ALL SELECT 'active_owner_relationships', active_owner_relationships FROM vw_milestone_2b_summary
  UNION ALL SELECT 'approved_owner_relationship_reviews', approved_owner_relationship_reviews FROM vw_milestone_2b_summary
  UNION ALL SELECT 'buildings_total', buildings_total FROM vw_milestone_2b_summary
  UNION ALL SELECT 'building_units_total', building_units_total FROM vw_milestone_2b_summary
  UNION ALL SELECT 'source_batches_total', source_batches_total FROM vw_milestone_2b_summary
  UNION ALL SELECT 'owner_unit_batch_rows', owner_unit_batch_rows FROM vw_milestone_2b_summary
  UNION ALL SELECT 'owner_unit_rows_linked_to_canonical', owner_unit_rows_linked_to_canonical FROM vw_milestone_2b_summary
  UNION ALL SELECT 'owner_unit_rows_not_linked_to_canonical', owner_unit_rows_not_linked_to_canonical FROM vw_milestone_2b_summary
  UNION ALL SELECT 'owner_unit_duplicate_candidates', owner_unit_duplicate_candidates FROM vw_milestone_2b_summary
  UNION ALL SELECT 'communication_sent_count', communication_sent_count FROM vw_milestone_2b_summary
) s
UNION ALL
SELECT 'batch_quality', key, val::text FROM (
  SELECT 'contact_import_rows' AS key, contact_import_rows AS val FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'rows_with_contact_methods', rows_with_contact_methods FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'rows_in_duplicate_candidates', rows_in_duplicate_candidates FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'rows_linked_to_canonical_contacts', rows_linked_to_canonical_contacts FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'rows_pending_review', rows_pending_review FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'safe_candidate_estimate', safe_candidate_estimate FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
  UNION ALL SELECT 'risky_duplicate_estimate', risky_duplicate_estimate FROM vw_owner_unit_batch_quality WHERE batch_label = {b}
) q
UNION ALL
SELECT 'rollup', key, val::text FROM (
  SELECT 'active_owner_relationships' AS key, (SELECT count(*) FROM vw_owner_relationship_revert_dashboard) AS val
  UNION ALL SELECT 'revert_ready_active_owner_relationships', (SELECT count(*) FROM vw_owner_relationship_revert_dashboard WHERE revert_allowed = true)
  UNION ALL SELECT 'pending_candidate_queue', (SELECT count(*) FROM vw_owner_unit_candidate_queue)
  UNION ALL SELECT 'safe_candidate_queue', (SELECT count(*) FROM vw_owner_unit_candidate_queue WHERE NOT duplicate_involved AND has_contact_method)
  UNION ALL SELECT 'duplicate_risk_total', (SELECT count(*) FROM vw_duplicate_risk_dashboard)
  UNION ALL SELECT 'duplicate_risk_for_batch', (SELECT count(*) FROM vw_duplicate_risk_dashboard WHERE batch_label = {b})
) r
ORDER BY section, item;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Milestone 2B checkpoint summary. Counts only; no DB writes.")
    parser.add_argument("--batch-label", default=DEFAULT_BATCH)
    args = parser.parse_args()

    print("Milestone 2B checkpoint summary. Counts only; no raw personal values are printed.")
    print(f"owner/unit batch: {args.batch_label}")
    code, output = run_psql(summary_sql(args.batch_label))
    print(output)

    # Recommended next phase, derived from counts only.
    code2, rollup = run_psql(
        "SELECT (SELECT count(*) FROM vw_owner_unit_candidate_queue WHERE NOT duplicate_involved AND has_contact_method),"
        " (SELECT count(*) FROM vw_owner_unit_candidate_queue WHERE duplicate_involved),"
        " (SELECT count(*) FROM buildings),"
        " (SELECT count(*) FROM vw_owner_relationship_revert_dashboard)"
    )
    safe = dup = bld = active = 0
    if code2 == 0 and "|" in rollup:
        parts = rollup.split("|")
        safe, dup, bld, active = (int(parts[0] or 0), int(parts[1] or 0), int(parts[2] or 0), int(parts[3] or 0))
    print("recommended_next_phase:")
    if dup > 0:
        print(f"  Phase 5.14 Option A — merge 2 more safe owner/unit candidates ({safe} safe in queue), "
              f"then candidates only; handle {dup} duplicate-involved rows via a later duplicate-review workflow.")
    else:
        print("  Phase 5.14 Option A — continue safe owner/unit canonical merges (no duplicate risk detected).")
    if bld > 1:
        print(f"  Note: {bld} building anchors exist (possible duplicate 'Imperial Heights'); building dedupe/alias "
              "consolidation (Option C) is a candidate follow-up.")
    return code or code2

if __name__ == "__main__":
    raise SystemExit(main())
