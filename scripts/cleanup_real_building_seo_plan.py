#!/usr/bin/env python3
"""Phase 6.1 cleanup/rollback of a REAL building SEO/content plan. Dry-run by default.

Deletes ONLY the planning rows created by apply_real_building_seo_plan.py — those
tagged raw_context phase='6.1', source='real_building_seo_plan',
building_name='Imperial Heights' — in FK-safe order. It NEVER deletes the building,
contacts, or owner relationships.

It refuses to delete if anything has progressed past planning: any publishing row is
'published', any campaign has send_enabled=true, or any targeted row recorded
external_calls_made=true. Optional --building-id / --profile-slug narrow the target
to one profile. Deleting requires --apply AND --real-ok. Counts only; no raw
personal values are printed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "6.1"
SOURCE = "real_building_seo_plan"
BUILDING_NAME = "Imperial Heights"
def tag_match(col: str) -> str:
    return (f"{col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}' "
            f"AND {col}->>'building_name' = {sql_literal(BUILDING_NAME)}")

def profile_filter(building_id: str, slug: str) -> str:
    """Which building_web_profiles rows are in scope (tag + optional narrowing)."""
    clauses = [tag_match("raw_context")]
    if building_id:
        clauses.append(f"building_id = {sql_literal(building_id)}::uuid")
    if slug:
        clauses.append(f"profile_slug = {sql_literal(slug)}")
    return " AND ".join(clauses)

def target_profiles_sql(building_id: str, slug: str) -> str:
    return f"SELECT id, building_id FROM building_web_profiles WHERE {profile_filter(building_id, slug)}"

def counts_sql(building_id: str, slug: str) -> str:
    tp = target_profiles_sql(building_id, slug)
    return f"""
WITH tp AS ({tp}),
tb AS (SELECT id FROM content_briefs WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tag_match('raw_context')})
SELECT 'building_web_profiles' AS item, count(*)::text FROM tp
UNION ALL SELECT 'seo_keywords', count(*)::text FROM seo_keywords
  WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tag_match('raw_context')}
UNION ALL SELECT 'content_briefs', count(*)::text FROM tb
UNION ALL SELECT 'content_publishing_queue', count(*)::text FROM content_publishing_queue
  WHERE content_brief_id IN (SELECT id FROM tb) AND {tag_match('raw_context')}
UNION ALL SELECT 'ai_agent_tasks', count(*)::text FROM ai_agent_tasks
  WHERE {tag_match('raw_input')}
    AND (entity_id IN (SELECT building_id FROM tp) OR entity_id IN (SELECT id FROM tb))
ORDER BY item;
"""

def guard_sql(building_id: str, slug: str) -> str:
    """published rows | send_enabled campaigns | external_calls_made=true among targets."""
    tp = target_profiles_sql(building_id, slug)
    return f"""
WITH tp AS ({tp}),
tb AS (SELECT id FROM content_briefs WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tag_match('raw_context')})
SELECT
  (SELECT count(*) FROM content_publishing_queue
     WHERE content_brief_id IN (SELECT id FROM tb) AND publish_status = 'published')::text,
  (SELECT count(*) FROM campaign_drafts WHERE send_enabled = true)::text,
  ((SELECT count(*) FROM building_web_profiles WHERE id IN (SELECT id FROM tp) AND raw_context->>'external_calls_made' = 'true')
   + (SELECT count(*) FROM ai_agent_tasks WHERE {tag_match('raw_input')} AND raw_input->>'external_calls_made' = 'true'))::text;
"""

def delete_sql(building_id: str, slug: str) -> str:
    tp = target_profiles_sql(building_id, slug)
    tagc = tag_match("raw_context")
    tagi = tag_match("raw_input")
    return f"""
BEGIN;
WITH tp AS ({tp}),
tb AS (SELECT id FROM content_briefs WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tagc})
DELETE FROM content_publishing_queue
  WHERE content_brief_id IN (SELECT id FROM tb) AND {tagc};
WITH tp AS ({tp})
DELETE FROM content_briefs
  WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tagc};
WITH tp AS ({tp})
DELETE FROM seo_keywords
  WHERE building_web_profile_id IN (SELECT id FROM tp) AND {tagc};
WITH tp AS ({tp})
DELETE FROM ai_agent_tasks
  WHERE {tagi} AND (entity_id IN (SELECT building_id FROM tp) OR entity_type = 'content_brief');
DELETE FROM building_web_profiles WHERE {profile_filter(building_id, slug)};
COMMIT;
{counts_sql(building_id, slug)}
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup a REAL Phase 6.1 building SEO plan. Dry-run by default.")
    parser.add_argument("--building-id", default="")
    parser.add_argument("--profile-slug", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Real building SEO-plan cleanup. phase={PHASE}; source={SOURCE}; building_name={BUILDING_NAME}. "
          "Counts only; only tagged planning rows are deleted; the building is never deleted.")

    code, current = run_psql(counts_sql(args.building_id, args.profile_slug))
    if code != 0:
        print(current)
        return code

    code, guard = run_psql(guard_sql(args.building_id, args.profile_slug))
    if code != 0:
        print(guard)
        return code
    pub, send_en, ext = (guard.split("|") + ["0", "0", "0"])[:3]

    if not args.apply or not args.real_ok:
        print("Dry run only. No database writes were made.")
        print("current phase-6.1 rows (would delete):")
        print(current)
        print(f"guard checks -> published_rows={pub}  send_enabled_campaigns={send_en}  external_calls_made={ext}")
        print("Deleting requires --apply and --real-ok.")
        return 0

    if pub != "0" or send_en != "0" or ext != "0":
        print(f"Refusing: plan has progressed past planning (published={pub}, send_enabled={send_en}, "
              f"external_calls_made={ext}). Not deleting.")
        return 1

    code, output = run_psql(delete_sql(args.building_id, args.profile_slug))
    print("Remaining phase-6.1 rows after cleanup (expect all 0):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
