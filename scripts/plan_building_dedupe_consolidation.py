#!/usr/bin/env python3
"""Phase 6.7 building consolidation planning. DRY-RUN ONLY (no writes, ever).

Given a building_duplicate_candidate_id, reports — as COUNTS only — what would need to
move from the duplicate building anchor onto the canonical anchor if the merge were
approved in a later phase:
  * building_aliases
  * building_units
  * contact_property_relationships
  * building_web_profiles
  * seo_keywords (via the duplicate's web profiles)
  * content_briefs (by building_id and via the duplicate's web profiles)

This script NEVER updates, merges, or deletes anything. It has no --apply flag. No
personal values are printed (only counts, building names/codes, statuses, UUIDs).
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
def report_sql(candidate_id: str) -> str:
    cid = sql_literal(candidate_id)
    canon = f"(SELECT canonical_building_id FROM building_duplicate_candidates WHERE id = {cid})"
    dup = f"(SELECT duplicate_building_id FROM building_duplicate_candidates WHERE id = {cid})"
    return f"""
SELECT 'candidate_found' k, count(*)::text v FROM building_duplicate_candidates WHERE id = {cid}
UNION ALL SELECT 'candidate_status', COALESCE((SELECT status FROM building_duplicate_candidates WHERE id = {cid}), '(none)')
UNION ALL SELECT 'aliases_to_move', count(*)::text FROM building_aliases WHERE building_id = {dup}
UNION ALL SELECT 'units_to_move', count(*)::text FROM building_units WHERE building_id = {dup}
UNION ALL SELECT 'relationships_to_move', count(*)::text FROM contact_property_relationships WHERE building_id = {dup}
UNION ALL SELECT 'active_relationships_to_move', count(*)::text FROM contact_property_relationships WHERE building_id = {dup} AND relationship_status = 'active'
UNION ALL SELECT 'web_profiles_to_move', count(*)::text FROM building_web_profiles WHERE building_id = {dup}
UNION ALL SELECT 'seo_keywords_via_dup_profiles', count(*)::text FROM seo_keywords k
   WHERE k.building_web_profile_id IN (SELECT id FROM building_web_profiles WHERE building_id = {dup})
UNION ALL SELECT 'content_briefs_by_building_id', count(*)::text FROM content_briefs WHERE building_id = {dup}
UNION ALL SELECT 'content_briefs_via_dup_profiles', count(*)::text FROM content_briefs cb
   WHERE cb.building_web_profile_id IN (SELECT id FROM building_web_profiles WHERE building_id = {dup})
UNION ALL SELECT 'canonical_building', COALESCE(substr({canon}::text, 1, 8), '(none)')
UNION ALL SELECT 'duplicate_building', COALESCE(substr({dup}::text, 1, 8), '(none)')
ORDER BY k;"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Report what a building merge would move. DRY-RUN ONLY.")
    parser.add_argument("--candidate-id", required=True, help="building_duplicate_candidate_id (UUID)")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    args = parser.parse_args()

    if not UUID_RE.match(args.candidate_id):
        print(f"Refusing: '{args.candidate_id}' is not a valid UUID.")
        return 1

    print(f"Building consolidation plan (DRY-RUN ONLY). candidate_id={args.candidate_id}. "
          "Counts only; nothing is moved, merged, or deleted; no --apply exists.")

    code, output = run_psql(report_sql(args.candidate_id))
    if code != 0:
        print(output)
        return code
    rows = dict(line.split("|", 1) for line in output.splitlines() if "|" in line)
    if rows.get("candidate_found", "0") != "1":
        print(f"Refusing: no building_duplicate_candidate with id {args.candidate_id}.")
        return 1

    print("What WOULD move from the duplicate anchor onto the canonical anchor (counts only):")
    print(output)
    print("No writes were made. Actual consolidation is a separate, future, explicitly-approved phase.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
