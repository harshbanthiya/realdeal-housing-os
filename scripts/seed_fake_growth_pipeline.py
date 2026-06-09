#!/usr/bin/env python3
"""Phase 6.0 guarded FAKE seed of the growth/SEO/lead pipeline. Dry-run by default.

Creates a single self-contained chain of FAKE/test rows across the Phase 6.0 tables:
  building -> building_web_profile -> seo_keyword -> content_brief ->
  content_publishing_queue (draft) ; inbound_lead_source -> inbound_lead ->
  lead_attribution_event ; channel_permission ; campaign_draft ; ai_agent_task.

Every row is tagged fake_batch='FAKE_PHASE_6_0_GROWTH_PIPELINE', phase='6.0',
is_test=true (in metadata/raw_context/raw_payload/raw_input as appropriate), so
cleanup_fake_growth_pipeline.py can remove exactly these rows. The fake lead is NOT
linked to any real contact. Nothing is published and nothing is sent;
campaign_drafts.send_enabled stays false. Writing requires --apply AND --fake-ok.
Counts only; no raw personal values are printed.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
FAKE_BATCH = "FAKE_PHASE_6_0_GROWTH_PIPELINE"

# JSON tag stored in raw_context / metadata / raw_payload / raw_input columns.
TAG = ("jsonb_build_object('is_test', true, 'phase', '6.0', 'fake_batch', '"
       + FAKE_BATCH + "', 'source', 'fake_growth_pipeline')")


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


# (table, jsonb column holding the tag) — shared with cleanup script semantics.
FAKE_TABLES = [
    ("buildings", "metadata"),
    ("building_web_profiles", "raw_context"),
    ("seo_keywords", "raw_context"),
    ("content_briefs", "raw_context"),
    ("content_publishing_queue", "raw_context"),
    ("inbound_lead_sources", "raw_context"),
    ("inbound_leads", "raw_payload"),
    ("lead_attribution_events", "raw_context"),
    ("channel_permissions", "raw_context"),
    ("outreach_suppression_list", "raw_context"),
    ("campaign_drafts", "raw_context"),
    ("ai_agent_tasks", "raw_input"),
]


def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'fake_batch' = '{FAKE_BATCH}'"
        for t, col in FAKE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def insert_sql() -> str:
    return f"""
BEGIN;
WITH nb AS (
  INSERT INTO buildings (name, city, area, developer, notes, metadata)
  VALUES ('FAKE Skyline Residences (Phase 6.0)', 'Mumbai', 'Andheri West', 'FAKE Developer Co',
          'Fake building for Phase 6.0 growth pipeline test.', {TAG})
  RETURNING id
),
bwp AS (
  INSERT INTO building_web_profiles
    (building_id, profile_slug, building_name, area, city, developer, seo_status, page_type,
     target_audience, meta_title, meta_description, h1, notes, raw_context)
  SELECT nb.id, 'fake-skyline-residences-phase-6-0', 'FAKE Skyline Residences', 'Andheri West', 'Mumbai',
         'FAKE Developer Co', 'draft', 'building_page', 'renters_and_buyers',
         'FAKE Skyline Residences — Price & Reviews', 'Fake meta description for Phase 6.0 test.',
         'FAKE Skyline Residences', 'Fake web profile (Phase 6.0).', {TAG}
  FROM nb
  RETURNING id, building_id
),
kw AS (
  INSERT INTO seo_keywords
    (building_id, building_web_profile_id, keyword, keyword_type, target_city, target_area,
     priority, difficulty_estimate, intent, status, source, notes, raw_context)
  SELECT bwp.building_id, bwp.id, 'fake skyline residences andheri rent', 'rent', 'Mumbai', 'Andheri West',
         'normal', 'medium', 'rent', 'planned', 'phase_6_0_seed', 'Fake keyword (Phase 6.0).', {TAG}
  FROM bwp
  RETURNING id, building_id, building_web_profile_id
),
cb AS (
  INSERT INTO content_briefs
    (building_id, building_web_profile_id, primary_keyword_id, content_type, title, slug,
     target_keyword, search_intent, outline, research_status, approval_status, assigned_to, notes, raw_context)
  SELECT kw.building_id, kw.building_web_profile_id, kw.id, 'building_page', 'FAKE Skyline Residences Guide',
         'fake-skyline-residences-guide', 'fake skyline residences andheri rent', 'rent',
         '{{}}'::jsonb, 'pending', 'draft', 'unassigned', 'Fake content brief (Phase 6.0).', {TAG}
  FROM kw
  RETURNING id, building_id, building_web_profile_id
),
pq AS (
  INSERT INTO content_publishing_queue (content_brief_id, channel, publish_status, raw_context)
  SELECT cb.id, 'wix_page', 'draft', {TAG} FROM cb
  RETURNING id
),
src AS (
  INSERT INTO inbound_lead_sources (source_name, source_type, channel, status, notes, raw_context)
  VALUES ('FAKE Wix Form (Phase 6.0)', 'wix_form', 'wix', 'active', 'Fake lead source (Phase 6.0).', {TAG})
  RETURNING id
),
il AS (
  INSERT INTO inbound_leads
    (source_id, related_building_id, related_building_web_profile_id, lead_name_masked, lead_status,
     lead_intent, property_type, area, city, budget_min, budget_max, preferred_channel, consent_status, raw_payload)
  SELECT src.id, bwp.building_id, bwp.id, 'F[MASKED]', 'new', 'rent', 'apartment', 'Andheri West', 'Mumbai',
         30000, 60000, 'whatsapp', 'unknown', {TAG}
  FROM src, bwp
  RETURNING id, source_id, related_building_web_profile_id
),
lae AS (
  INSERT INTO lead_attribution_events
    (inbound_lead_id, source_id, building_web_profile_id, content_brief_id, event_type, campaign_name,
     utm_source, utm_medium, utm_campaign, landing_page, referrer, raw_context)
  SELECT il.id, il.source_id, il.related_building_web_profile_id, cb.id, 'form_submit', 'FAKE Phase 6.0 Campaign',
         'instagram', 'social', 'fake_phase_6_0', '/fake-skyline-residences', 'https://example.test', {TAG}
  FROM il, cb
  RETURNING id
),
chp AS (
  INSERT INTO channel_permissions (inbound_lead_id, channel, permission_status, consent_source, notes, raw_context)
  SELECT il.id, 'whatsapp', 'unknown', 'fake_phase_6_0_form', 'Fake channel permission (Phase 6.0).', {TAG}
  FROM il
  RETURNING id
),
camp AS (
  INSERT INTO campaign_drafts
    (campaign_name, campaign_type, target_segment, channel, status, content_brief_id, message_template,
     consent_required, send_enabled, notes, raw_context)
  SELECT 'FAKE Phase 6.0 Reactivation', 'owner_reactivation', 'fake_test_segment', 'whatsapp', 'draft', cb.id,
         'FAKE template — do not send.', true, false,
         'Fake campaign draft (Phase 6.0). send_enabled stays false.', {TAG}
  FROM cb
  RETURNING id
)
INSERT INTO ai_agent_tasks
  (task_type, entity_type, entity_id, status, priority, prompt_summary, result_summary,
   human_review_required, raw_input, raw_output)
SELECT 'building_research', 'content_brief', cb.id, 'queued', 'normal',
       'Fake research task for Phase 6.0 content brief.', NULL, true, {TAG}, '{{}}'::jsonb
FROM cb;
COMMIT;
{counts_sql()}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed FAKE Phase 6.0 growth pipeline. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    args = parser.parse_args()

    print(f"Fake growth-pipeline seed. fake_batch={FAKE_BATCH}; phase=6.0. Counts only; nothing published or sent.")

    code, existing = run_psql(counts_sql())
    if code != 0:
        print(existing)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in existing.splitlines() if "|" in line)

    if not (args.apply and args.fake_ok):
        print("Dry run only. No database writes were made.")
        print("planned (would create): buildings|1 building_web_profiles|1 seo_keywords|1 content_briefs|1 "
              "content_publishing_queue|1 inbound_lead_sources|1 inbound_leads|1 lead_attribution_events|1 "
              "channel_permissions|1 campaign_drafts|1 ai_agent_tasks|1")
        print("current fake rows:")
        print(existing)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if already:
        print("Refusing: fake growth-pipeline rows already exist. Run cleanup_fake_growth_pipeline.py first.")
        print(existing)
        return 1

    code, output = run_psql(insert_sql())
    print("Fake growth-pipeline rows created:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
