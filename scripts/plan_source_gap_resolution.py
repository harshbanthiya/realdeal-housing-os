#!/usr/bin/env python3
"""Phase 6.5 source-gap resolution workflow. Dry-run by default.

For one building web profile (default: imperial-heights-goregaon-west) it reads the
open content_source_gap_items (and their content_source_requirements) and creates,
for each open gap:
  * one source_gap_resolution_tasks row, classified by gap_type into an internal /
    human / future-external task_type (external_calls_allowed is NEVER set true here);
  * internal_source_evidence rows for the gaps that have internal evidence (safe
    COUNTS only, scoped to the profile's building — no names/phones/emails);
  * source_gap_review_items so a human can accept / resolve / waive each gap.

It does NOT resolve any gap (gaps stay 'open'), call any AI/external/Wix API, scrape
the web, set external_calls_allowed=true, mark content ready_for_publish/public_ready,
or send any outreach. Writing requires --real-ok AND --apply. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.5"
SOURCE = "source_gap_resolution_workflow"

# gap_type -> (task_type, resolution_source, external_calls_required, requirement_type)
# external_calls_allowed is ALWAYS false in this phase; external_calls_required only
# flags work that *will eventually* need external/web research (queued, not executed).
GAP_CLASSIFICATION = [
    ("inventory_availability_unverified", "internal_data_check", "inventory", False, "internal_inventory"),
    ("owner_listing_permission_needed", "owner_data_check", "owner_relationships", False, "owner_relationships"),
    ("amenities_unverified", "human_research", "human_input", False, "amenities"),
    ("photos_needed", "photo_check", "human_input", False, None),
    ("legal_disclaimer_needed", "legal_disclaimer_review", "human_input", False, "legal_disclaimer"),
    ("developer_unverified", "web_research_later", "future_web_research", True, "developer_info"),
    ("landmarks_unverified", "web_research_later", "future_web_research", True, "location_landmarks"),
    ("rent_range_missing", "market_range_estimate", "future_web_research", True, "rental_range"),
    ("resale_range_missing", "market_range_estimate", "future_web_research", True, "resale_range"),
]

# gap_type -> list of (evidence_type, source_table, count_expr_template, summary_template)
# count_expr_template uses {pb} = the profile's building_id subquery. Summaries embed
# COUNTS only — never any personal value.
EVIDENCE_BY_GAP = {
    "inventory_availability_unverified": [
        ("unit_count", "building_units",
         "(SELECT count(*) FROM building_units u WHERE u.building_id = {pb})",
         "Internal building_units on file for this building: "),
        ("inventory_hint", "building_units",
         "(SELECT count(*) FROM building_units u WHERE u.building_id = {pb})",
         "Internal inventory hint (building_units count; verify live availability before drafting): "),
        ("source_batch_count", "building_units",
         "(SELECT count(DISTINCT u.source_file_id) FROM building_units u WHERE u.building_id = {pb} AND u.source_file_id IS NOT NULL)",
         "Distinct internal source batches behind these units: "),
    ],
    "owner_listing_permission_needed": [
        ("active_owner_relationship_count", "contact_property_relationships",
         "(SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = {pb} AND r.relationship_status = 'active')",
         "Active owner relationships on file for this building (permission still required from a human): "),
        ("building_alias", "building_aliases",
         "(SELECT count(*) FROM building_aliases a WHERE a.building_id = {pb})",
         "Known internal building aliases for matching: "),
    ],
}

PHASE_TABLES = [
    ("source_gap_resolution_tasks", "raw_context"),
    ("internal_source_evidence", "raw_context"),
    ("source_gap_review_items", "raw_context"),
]

# Planned counts for the default Imperial Heights profile (dry-run display).
PLANNED_TASKS = 17
PLANNED_EVIDENCE = 15
PLANNED_REVIEWS = 23
def sql_bool(value: bool) -> str:
    return "true" if value else "false"
TAG = (
    "jsonb_build_object("
    f"'phase', '{PHASE}', 'source', '{SOURCE}', "
    "'external_calls_made', false, 'published', false, "
    "'communication_sent', false, 'internal_only', true, 'is_real', true)"
)

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"
        for t, col in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def profile_exists_sql(slug: str) -> str:
    return f"SELECT count(*) FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)};"

def insert_sql(slug: str) -> str:
    profile = f"(SELECT id FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)})"
    pb = f"(SELECT building_id FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)})"
    brief_filter = f"g.content_brief_id IN (SELECT id FROM content_briefs WHERE building_web_profile_id = {profile})"
    stmts = []

    # 1. One resolution task per open gap, classified by gap_type.
    class_rows = ",\n      ".join(
        "({gt}, {tt}, {rs}, {ext}, {req})".format(
            gt=sql_literal(gap_type),
            tt=sql_literal(task_type),
            rs=sql_literal(resolution_source),
            ext=sql_bool(external_required),
            req="NULL" if requirement_type is None else sql_literal(requirement_type),
        )
        for gap_type, task_type, resolution_source, external_required, requirement_type in GAP_CLASSIFICATION
    )
    stmts.append(f"""
INSERT INTO source_gap_resolution_tasks
  (content_source_gap_item_id, content_source_requirement_id, content_brief_id, task_type, task_status,
   priority, resolution_source, external_calls_required, external_calls_allowed, human_review_required,
   safe_task_summary, raw_context)
SELECT g.id,
       (SELECT r.id FROM content_source_requirements r
         WHERE r.content_brief_id = g.content_brief_id AND r.requirement_type = m.requirement_type
         ORDER BY r.created_at LIMIT 1),
       g.content_brief_id, m.task_type, 'pending', g.priority,
       m.resolution_source, m.external_calls_required, false, true,
       'Gap ' || g.gap_type || ' -> ' || m.task_type || ' (resolution_source=' || m.resolution_source
         || '). external_calls_allowed=false this phase. Human review required.',
       {TAG}
FROM content_source_gap_items g
JOIN (VALUES
      {class_rows}
) AS m(gap_type, task_type, resolution_source, external_calls_required, requirement_type)
  ON m.gap_type = g.gap_type
WHERE g.status = 'open' AND {brief_filter};""")

    # 2. Internal evidence (safe COUNTS only) for internally-resolvable gaps.
    for gap_type, specs in EVIDENCE_BY_GAP.items():
        for evidence_type, source_table, count_template, summary_prefix in specs:
            count_expr = count_template.format(pb=pb)
            stmts.append(f"""
INSERT INTO internal_source_evidence
  (content_source_gap_item_id, source_table, source_entity_id, evidence_type, evidence_status, safe_summary, raw_context)
SELECT g.id, {sql_literal(source_table)}, {pb}, {sql_literal(evidence_type)}, 'candidate',
       {sql_literal(summary_prefix)} || ({count_expr})::text || ' (count only; human review required).',
       {TAG}
FROM content_source_gap_items g
WHERE g.status = 'open' AND g.gap_type = {sql_literal(gap_type)} AND {brief_filter};""")

    # 3a. One gap_classification_review per open gap.
    stmts.append(f"""
INSERT INTO source_gap_review_items
  (content_source_gap_item_id, source_gap_resolution_task_id, review_type, status, priority, raw_context)
SELECT g.id,
       (SELECT t.id FROM source_gap_resolution_tasks t
         WHERE t.content_source_gap_item_id = g.id AND t.raw_context->>'phase' = '{PHASE}'
         ORDER BY t.created_at LIMIT 1),
       'gap_classification_review', 'pending', 'normal', {TAG}
FROM content_source_gap_items g
WHERE g.status = 'open' AND {brief_filter};""")

    # 3b. An internal_evidence_review for each gap that received internal evidence.
    stmts.append(f"""
INSERT INTO source_gap_review_items
  (content_source_gap_item_id, source_gap_resolution_task_id, review_type, status, priority, raw_context)
SELECT DISTINCT g.id,
       (SELECT t.id FROM source_gap_resolution_tasks t
         WHERE t.content_source_gap_item_id = g.id AND t.raw_context->>'phase' = '{PHASE}'
         ORDER BY t.created_at LIMIT 1),
       'internal_evidence_review', 'pending', 'normal', {TAG}
FROM content_source_gap_items g
JOIN internal_source_evidence e
  ON e.content_source_gap_item_id = g.id AND e.raw_context->>'phase' = '{PHASE}'
WHERE g.status = 'open' AND {brief_filter};""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Plan source-gap resolution tasks. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Source-gap resolution workflow. phase={PHASE}; source={SOURCE}; profile_slug={args.profile_slug}. "
          "Counts only; review-gated; no gap auto-resolved; no AI/external/web calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real planning data.")
        return 1

    code, found = run_psql(profile_exists_sql(args.profile_slug))
    if code != 0:
        print(found)
        return code
    if found.strip() != "1":
        print(f"Refusing: profile_slug {args.profile_slug} not found (matched {found}).")
        return 1

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"source_gap_resolution_tasks planned: {PLANNED_TASKS} (one per open gap; "
              "internal_data_check/owner_data_check/human_research/legal_disclaimer_review/web_research_later/market_range_estimate)")
        print(f"internal_source_evidence planned: {PLANNED_EVIDENCE} (safe counts only for inventory/owner gaps)")
        print(f"source_gap_review_items planned: {PLANNED_REVIEWS} (gap_classification_review + internal_evidence_review; all pending)")
        print("gaps resolved: 0  external_calls_allowed: 0  ready_for_publish: false  published: 0  communication_sent: 0")
        print("current phase-6.5 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.5 rows already exist. Run cleanup_source_gap_resolution.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args.profile_slug))
    print("Source-gap resolution rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
