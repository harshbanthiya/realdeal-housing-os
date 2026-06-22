#!/usr/bin/env python3
"""Phase 6.7 building-anchor dedupe planning. Dry-run by default.

Finds duplicate building anchors for a building name (default "Imperial Heights"),
picks a proposed CANONICAL anchor, and records review-gated planning rows only:
building_duplicate_candidates + building_dedupe_review_items. Canonical selection:
  1) the building linked to the given --profile-slug web profile, else
  2) the building with any building_web_profile, else
  3) the building with the most active owner relationships, else
  4) the earliest created_at.

It does NOT merge or delete buildings, move units/relationships, touch
building_web_profiles / SEO / content rows, resolve source gaps, call any
external/Wix API, publish, or send outreach. Every planning row is tagged in
raw_context (phase='6.7', source='building_dedupe_planning', merged=false). Writing
requires --real-ok AND --apply. Counts only; no personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.7"
SOURCE = "building_dedupe_planning"

PHASE_TABLES = [
    ("building_duplicate_candidates", "raw_context"),
    ("building_dedupe_review_items", "raw_context"),
]
TAG = (
    "jsonb_build_object("
    f"'phase', '{PHASE}', 'source', '{SOURCE}', "
    "'merged', false, 'external_calls_made', false, 'published', false, "
    "'communication_sent', false, 'is_real', true)"
)

def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"
        for t, col in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

# Buildings matching the name (case-insensitive substring).
def name_filter(name: str) -> str:
    return f"lower(b.name) LIKE lower('%' || {sql_literal(name)} || '%')"

def building_code_expr(alias: str) -> str:
    return (f"(SELECT u.building_code FROM building_units u "
            f"WHERE u.building_id = {alias}.id AND u.building_code IS NOT NULL ORDER BY u.created_at LIMIT 1)")

# Canonical anchor: profile-slug match > any profile > most active rels > earliest.
def canonical_id_sql(name: str, slug: str) -> str:
    return f"""(
  SELECT b.id FROM buildings b
  WHERE {name_filter(name)}
  ORDER BY
    (EXISTS (SELECT 1 FROM building_web_profiles p WHERE p.building_id = b.id AND p.profile_slug = {sql_literal(slug)})) DESC,
    (SELECT count(*) FROM building_web_profiles p WHERE p.building_id = b.id) DESC,
    (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = b.id AND r.relationship_status = 'active') DESC,
    b.created_at ASC, b.id ASC
  LIMIT 1
)"""

def summary_sql(name: str) -> str:
    """Pre-write summary: building anchors + counts (safe), and chosen canonical."""
    return f"""
SELECT 'matching_anchors' k, count(*)::text v FROM buildings b WHERE {name_filter(name)}
UNION ALL SELECT 'active_rel_total', count(*)::text FROM contact_property_relationships r
  WHERE r.building_id IN (SELECT b.id FROM buildings b WHERE {name_filter(name)}) AND r.relationship_status = 'active'
ORDER BY k;"""

def insert_sql(name: str, slug: str) -> str:
    canonical = canonical_id_sql(name, slug)
    group_key = f"regexp_replace(lower(trim({sql_literal(name)})), '[^a-z0-9]+', '-', 'g')"
    bc = building_code_expr("bcan")
    bdup = building_code_expr("b")
    stmts = []

    # One candidate row per duplicate (every matching building that is not the canonical).
    stmts.append(f"""
INSERT INTO building_duplicate_candidates
  (candidate_group_key, canonical_building_id, duplicate_building_id, duplicate_strength, status,
   reason, safe_summary, raw_context)
SELECT
  {group_key},
  {canonical},
  b.id,
  CASE
    WHEN lower(b.name) = (SELECT lower(bcan.name) FROM buildings bcan WHERE bcan.id = {canonical})
         AND {bdup} IS NOT DISTINCT FROM (SELECT {bc} FROM buildings bcan WHERE bcan.id = {canonical})
      THEN 'strong'
    WHEN lower(b.name) = (SELECT lower(bcan.name) FROM buildings bcan WHERE bcan.id = {canonical}) THEN 'medium'
    ELSE 'candidate'
  END,
  'pending_review',
  'Same building name/code as the canonical anchor; active owner relationships split across anchors.',
  'Duplicate building anchor for ' || b.name || '. Canonical anchor holds the SEO profile/content; this duplicate holds '
    || (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = b.id AND r.relationship_status = 'active')::text
    || ' active owner relationship(s). Planning only; no merge performed.',
  {TAG}
FROM buildings b
WHERE {name_filter(name)} AND b.id <> {canonical};""")

    # One duplicate_building_review per candidate just created in this phase.
    stmts.append(f"""
INSERT INTO building_dedupe_review_items
  (building_duplicate_candidate_id, review_type, status, priority, raw_context)
SELECT c.id, 'duplicate_building_review', 'pending', 'normal', {TAG}
FROM building_duplicate_candidates c
WHERE c.raw_context->>'phase' = '{PHASE}' AND c.raw_context->>'source' = '{SOURCE}';""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Imperial Heights building dedupe. Dry-run by default.")
    parser.add_argument("--building-name", default="Imperial Heights")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Building dedupe planning. phase={PHASE}; source={SOURCE}; building_name={args.building_name!r}; "
          f"profile_slug={args.profile_slug}. Counts only; review-gated; no merge; no relationship/SEO/content "
          "changes; no external calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real building data.")
        return 1

    code, summary = run_psql(summary_sql(args.building_name))
    if code != 0:
        print(summary)
        return code
    s = dict(line.split("|", 1) for line in summary.splitlines() if "|" in line)
    matching = int(s.get("matching_anchors", "0"))
    if matching < 2:
        print(f"Refusing: found {matching} building anchor(s) matching {args.building_name!r}; need >= 2 to plan dedupe.")
        return 1

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"matching building anchors: {matching}; active owner relationships across them: {s.get('active_rel_total','?')}")
        print(f"building_duplicate_candidates planned: {matching - 1} (1 canonical + {matching - 1} duplicate(s); status='pending_review')")
        print(f"building_dedupe_review_items planned: {matching - 1} (review_type='duplicate_building_review', status='pending')")
        print("no building merge; no relationship/SEO/content updates; nothing published or sent.")
        print("current phase-6.7 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.7 planning rows already exist. Run cleanup_building_dedupe_plan.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args.building_name, args.profile_slug))
    print("Building dedupe planning rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
