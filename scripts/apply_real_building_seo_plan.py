#!/usr/bin/env python3
"""Phase 6.1 guarded REAL building SEO/content plan. Dry-run by default.

Creates the first real, review-gated SEO/content planning set for one building:
one building_web_profile, a small low-competition keyword set, three content briefs,
three DRAFT publishing-queue rows, and five QUEUED ai_agent_tasks. It creates NOTHING
else — no contacts, no owner relationships, no inbound leads, no enabled campaigns,
and no published rows. No external API/web calls are made.

Every row is tagged raw_context with phase='6.1', source='real_building_seo_plan',
building_name=<name>, external_calls_made=false, published=false,
communication_sent=false, is_real=true. Writing requires --real-ok AND --apply.
Counts only; no raw personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.1"
SOURCE = "real_building_seo_plan"

# Low-competition-first keyword set: (keyword, keyword_type, priority, intent).
KEYWORDS = [
    ("Imperial Heights Goregaon", "location", "high", "research"),
    ("Imperial Heights Goregaon West", "location", "high", "research"),
    ("Imperial Heights flats for rent", "rent", "high", "rent"),
    ("Imperial Heights resale", "sale", "high", "buy"),
    ("Imperial Heights 3 BHK rent", "configuration", "normal", "rent"),
    ("Imperial Heights 4 BHK rent", "configuration", "normal", "rent"),
    ("Imperial Heights owner contact", "broker", "normal", "availability"),
    ("Imperial Heights broker", "broker", "normal", "broker"),
    ("Imperial Heights property dealer", "broker", "normal", "broker"),
    ("Imperial Heights Mumbai", "building_name", "normal", "research"),
]

# Content briefs: (content_type, title, slug, target_keyword, search_intent).
BRIEFS = [
    ("building_page",
     "Imperial Heights Goregaon West: Flats, Rent, Resale and Owner Listings",
     "imperial-heights-goregaon-west-building-page",
     "Imperial Heights Goregaon West", "research"),
    ("blog",
     "Flats for Rent in Imperial Heights Goregaon West",
     "imperial-heights-flats-for-rent",
     "Imperial Heights flats for rent", "rent"),
    ("blog",
     "Imperial Heights Goregaon West Resale Guide",
     "imperial-heights-resale-guide",
     "Imperial Heights resale", "buy"),
]
def tag_expr(building_name: str) -> str:
    """jsonb tag written to every row's raw_context."""
    return (
        "jsonb_build_object("
        f"'phase', '{PHASE}', "
        f"'source', '{SOURCE}', "
        f"'building_name', {sql_literal(building_name)}, "
        "'external_calls_made', false, "
        "'published', false, "
        "'communication_sent', false, "
        "'is_real', true)"
    )

# (table, jsonb column) for counting/this phase's rows.
PHASE_TABLES = [
    ("building_web_profiles", "raw_context"),
    ("seo_keywords", "raw_context"),
    ("content_briefs", "raw_context"),
    ("content_publishing_queue", "raw_context"),
    ("ai_agent_tasks", "raw_input"),
]

def counts_sql(building_name: str) -> str:
    bn = sql_literal(building_name)
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}' "
        f"AND {col}->>'building_name' = {bn}"
        for t, col in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"

def exists_sql(building_id: str) -> str:
    return f"SELECT count(*) FROM buildings WHERE id = {sql_literal(building_id)}::uuid;"

def existing_profile_sql(building_id: str, slug: str) -> str:
    return (
        "SELECT count(*) FROM building_web_profiles "
        f"WHERE building_id = {sql_literal(building_id)}::uuid "
        f"OR profile_slug = {sql_literal(slug)};"
    )

def insert_sql(building_id: str, name: str, area: str, city: str,
               developer: str, slug: str) -> str:
    tag = tag_expr(name)
    bid = sql_literal(building_id) + "::uuid"
    n, a, c = sql_literal(name), sql_literal(area), sql_literal(city)
    dev = sql_literal(developer) if developer else "NULL"
    s = sql_literal(slug)
    meta_title = sql_literal(f"{name} {area}: Flats, Rent, Resale & Owner Listings".strip())
    meta_desc = sql_literal(
        f"Overview of {name} in {area}, {city}: flats for rent, resale, configurations and owner listings.".strip()
    )
    h1 = sql_literal(f"{name} {area}".strip())

    kw_values = ",\n      ".join(
        f"({sql_literal(k)}, {sql_literal(kt)}, {sql_literal(pr)}, {sql_literal(it)})"
        for (k, kt, pr, it) in KEYWORDS
    )
    brief_values = ",\n      ".join(
        f"({sql_literal(ct)}, {sql_literal(ti)}, {sql_literal(sl)}, {sql_literal(tk)}, {sql_literal(si)})"
        for (ct, ti, sl, tk, si) in BRIEFS
    )
    rent_kw = sql_literal("Imperial Heights flats for rent")
    resale_kw = sql_literal("Imperial Heights resale")

    return f"""
BEGIN;
WITH prof AS (
  INSERT INTO building_web_profiles
    (building_id, profile_slug, building_name, area, city, developer, seo_status, page_type,
     target_audience, meta_title, meta_description, h1, notes, raw_context)
  VALUES ({bid}, {s}, {n}, {a}, {c}, {dev}, 'draft', 'building_page', 'renters_buyers_owners',
          {meta_title}, {meta_desc}, {h1}, 'Real building SEO profile (Phase 6.1, review-gated).', {tag})
  RETURNING id, building_id
),
kw AS (
  INSERT INTO seo_keywords
    (building_id, building_web_profile_id, keyword, keyword_type, target_city, target_area,
     priority, difficulty_estimate, intent, status, source, notes, raw_context)
  SELECT prof.building_id, prof.id, v.keyword, v.ktype, {c}, {a}, v.priority, 'low', v.intent,
         'planned', '{SOURCE}', 'Phase 6.1 low-competition keyword.', {tag}
  FROM prof, (VALUES
      {kw_values}
  ) AS v(keyword, ktype, priority, intent)
  RETURNING id, keyword
),
cb AS (
  INSERT INTO content_briefs
    (building_id, building_web_profile_id, primary_keyword_id, content_type, title, slug,
     target_keyword, search_intent, outline, research_status, approval_status, assigned_to, notes, raw_context)
  SELECT prof.building_id, prof.id,
         (SELECT id FROM kw WHERE kw.keyword = v.target_keyword LIMIT 1),
         v.ctype, v.title, v.slug, v.target_keyword, v.intent, '{{}}'::jsonb,
         'pending', 'draft', 'unassigned', 'Phase 6.1 content brief (review-gated).', {tag}
  FROM prof, (VALUES
      {brief_values}
  ) AS v(ctype, title, slug, target_keyword, intent)
  RETURNING id, content_type, target_keyword
),
pq AS (
  INSERT INTO content_publishing_queue (content_brief_id, channel, publish_status, raw_context)
  SELECT cb.id,
         CASE WHEN cb.content_type = 'building_page' THEN 'wix_page' ELSE 'wix_blog' END,
         'draft', {tag}
  FROM cb
  RETURNING id
)
INSERT INTO ai_agent_tasks
  (task_type, entity_type, entity_id, status, priority, prompt_summary, result_summary,
   human_review_required, raw_input, raw_output)
SELECT 'building_research', 'building', (SELECT building_id FROM prof), 'queued', 'normal',
       'Research Imperial Heights building facts, amenities, and location for SEO. No external calls yet.',
       NULL::text, true, {tag}, '{{}}'::jsonb
UNION ALL SELECT 'keyword_research', 'building', (SELECT building_id FROM prof), 'queued', 'normal',
       'Expand the low-competition keyword set for Imperial Heights.', NULL::text, true, {tag}, '{{}}'::jsonb
UNION ALL SELECT 'blog_brief', 'content_brief',
       (SELECT id FROM cb WHERE target_keyword = {rent_kw} LIMIT 1), 'queued', 'normal',
       'Draft the rent-guide content brief for Imperial Heights.', NULL::text, true, {tag}, '{{}}'::jsonb
UNION ALL SELECT 'blog_brief', 'content_brief',
       (SELECT id FROM cb WHERE target_keyword = {resale_kw} LIMIT 1), 'queued', 'normal',
       'Draft the resale-guide content brief for Imperial Heights.', NULL::text, true, {tag}, '{{}}'::jsonb
UNION ALL SELECT 'seo_monitoring', 'building', (SELECT building_id FROM prof), 'queued', 'normal',
       'Placeholder: monitor search rankings for Imperial Heights keywords (future).', NULL::text, true, {tag}, '{{}}'::jsonb;
COMMIT;
{counts_sql(name)}
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a REAL building SEO/content plan. Dry-run by default.")
    parser.add_argument("--building-id", required=True)
    parser.add_argument("--building-name", required=True)
    parser.add_argument("--area", default="")
    parser.add_argument("--city", default="")
    parser.add_argument("--developer", default="")
    parser.add_argument("--profile-slug", default="")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()

    slug = args.profile_slug or (
        args.building_name.strip().lower().replace(" ", "-") + "-seo-profile"
    )

    print(f"Real building SEO plan. phase={PHASE}; source={SOURCE}; building_name={args.building_name}. "
          "Counts only; no external calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real building data.")
        return 1

    code, out = run_psql(exists_sql(args.building_id))
    if code != 0:
        print(out)
        return code
    if out.strip() != "1":
        print(f"Refusing: building_id {args.building_id} does not exist (found {out}).")
        return 1

    code, existing = run_psql(existing_profile_sql(args.building_id, slug))
    if code != 0:
        print(existing)
        return code
    profile_exists = existing.strip() != "0"

    code, current = run_psql(counts_sql(args.building_name))
    if code != 0:
        print(current)
        return code

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"profile_slug: {slug}")
        print(f"building_web_profiles planned: 1")
        print(f"seo_keywords planned: {len(KEYWORDS)}")
        print(f"content_briefs planned: {len(BRIEFS)}")
        print(f"publishing_queue planned: {len(BRIEFS)} (all publish_status='draft')")
        print(f"ai_agent_tasks planned: 5 (all status='queued', human_review_required=true)")
        print("external_calls_made=false  published=false  communication_sent=false")
        if profile_exists:
            print("NOTE: a building_web_profile already exists for this building/slug; "
                  "applying requires --allow-existing.")
        print("current phase-6.1 rows for this building:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if profile_exists and not args.allow_existing:
        print("Refusing: a building_web_profile already exists for this building/slug. "
              "Pass --allow-existing to add another plan, or run the cleanup script first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(
        args.building_id, args.building_name, args.area, args.city, args.developer, slug,
    ))
    print("Real SEO plan rows created (counts):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
