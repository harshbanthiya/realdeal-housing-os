#!/usr/bin/env python3
"""Cleanup Phase 7.2 DLF contact segment planning rows.

Dry-run by default. Deletes only rows tagged with phase=7.2 and
source=dlf_contact_segment_planning. It never deletes contacts, contact methods,
relationships, launch projects, templates, campaign drafts, or source data.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.2"
SOURCE = "dlf_contact_segment_planning"
def target_cte(launch_key: str) -> str:
    return f"""
WITH launch AS (
  SELECT id FROM launch_projects WHERE launch_key = {sql_literal(launch_key)}
),
target_candidates AS (
  SELECT csc.id
  FROM launch_contact_segment_candidates csc
  WHERE csc.launch_project_id IN (SELECT id FROM launch)
    AND csc.raw_context->>'phase' = {sql_literal(PHASE)}
    AND csc.raw_context->>'source' = {sql_literal(SOURCE)}
),
target_reviews AS (
  SELECT pri.id
  FROM launch_contact_permission_review_items pri
  WHERE pri.launch_project_id IN (SELECT id FROM launch)
    AND pri.raw_context->>'phase' = {sql_literal(PHASE)}
    AND pri.raw_context->>'source' = {sql_literal(SOURCE)}
),
target_audit AS (
  SELECT log.id
  FROM launch_contact_segment_audit_log log
  WHERE log.launch_contact_segment_candidate_id IN (SELECT id FROM target_candidates)
     OR (
       log.raw_context->>'phase' = {sql_literal(PHASE)}
       AND log.raw_context->>'source' = {sql_literal(SOURCE)}
     )
)
"""

def dry_run_sql(launch_key: str) -> str:
    return (
        target_cte(launch_key)
        + """
SELECT 'candidate_rows_to_delete' AS item, count(*)::text FROM target_candidates
UNION ALL SELECT 'review_rows_to_delete', count(*)::text FROM target_reviews
UNION ALL SELECT 'audit_rows_to_delete', count(*)::text FROM target_audit
UNION ALL SELECT 'approved_for_segment_guard', count(*)::text
FROM launch_contact_segment_candidates
WHERE id IN (SELECT id FROM target_candidates)
  AND candidate_status = 'approved_for_segment'
UNION ALL SELECT 'communication_sent_guard', (
  (SELECT count(*) FROM launch_contact_segment_candidates WHERE id IN (SELECT id FROM target_candidates) AND raw_context->>'communication_sent' = 'true')
  + (SELECT count(*) FROM launch_contact_permission_review_items WHERE id IN (SELECT id FROM target_reviews) AND raw_context->>'communication_sent' = 'true')
  + (SELECT count(*) FROM launch_contact_segment_audit_log WHERE id IN (SELECT id FROM target_audit) AND raw_context->>'communication_sent' = 'true')
)::text
UNION ALL SELECT 'campaign_send_audit_guard', count(*)::text
FROM launch_contact_segment_audit_log
WHERE id IN (SELECT id FROM target_audit)
  AND (action_type IN ('campaign_send', 'message_sent', 'added_to_live_campaign')
       OR raw_context->>'campaign_send' = 'true')
ORDER BY item;
"""
    )

def guard_sql(launch_key: str) -> str:
    return (
        target_cte(launch_key)
        + """
SELECT
  (SELECT count(*) FROM launch_projects WHERE launch_key = {launch_key})::text,
  (SELECT count(*) FROM launch_contact_segment_candidates WHERE id IN (SELECT id FROM target_candidates) AND candidate_status = 'approved_for_segment')::text,
  (
    (SELECT count(*) FROM launch_contact_segment_candidates WHERE id IN (SELECT id FROM target_candidates) AND raw_context->>'communication_sent' = 'true')
    + (SELECT count(*) FROM launch_contact_permission_review_items WHERE id IN (SELECT id FROM target_reviews) AND raw_context->>'communication_sent' = 'true')
    + (SELECT count(*) FROM launch_contact_segment_audit_log WHERE id IN (SELECT id FROM target_audit) AND raw_context->>'communication_sent' = 'true')
  )::text,
  (SELECT count(*) FROM launch_contact_segment_audit_log
   WHERE id IN (SELECT id FROM target_audit)
     AND (action_type IN ('campaign_send', 'message_sent', 'added_to_live_campaign')
          OR raw_context->>'campaign_send' = 'true'))::text;
""".format(launch_key=sql_literal(launch_key))
    )

def cleanup_sql(launch_key: str) -> str:
    return (
        "BEGIN;\n"
        + target_cte(launch_key)
        + """
, deleted_reviews AS (
  DELETE FROM launch_contact_permission_review_items
  WHERE id IN (SELECT id FROM target_reviews)
  RETURNING id
),
deleted_audit AS (
  DELETE FROM launch_contact_segment_audit_log
  WHERE id IN (SELECT id FROM target_audit)
  RETURNING id
),
deleted_candidates AS (
  DELETE FROM launch_contact_segment_candidates
  WHERE id IN (SELECT id FROM target_candidates)
  RETURNING id
)
SELECT 'candidate_rows_deleted' AS item, count(*)::text FROM deleted_candidates
UNION ALL SELECT 'review_rows_deleted', count(*)::text FROM deleted_reviews
UNION ALL SELECT 'audit_rows_deleted', count(*)::text FROM deleted_audit
ORDER BY item;

COMMIT;
"""
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup DLF contact segment planning rows. Dry-run by default.")
    parser.add_argument("--launch-key", required=True)
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.real_ok:
        print("Refusing cleanup: --real-ok is required.")
        return 1

    code, output = run_psql(dry_run_sql(args.launch_key), tuples_only=True)
    if code != 0:
        print(output)
        return code
    print("DLF contact segment cleanup plan. Counts only; no raw contact values are printed.")
    print(output)

    if not args.apply:
        print("Dry run only. No database rows were deleted.")
        return 0

    code, guard = run_psql(guard_sql(args.launch_key), tuples_only=True)
    if code != 0:
        print(guard)
        return code
    fields = guard.split("|") if guard else []
    if len(fields) < 4 or fields[0] != "1":
        print("Refusing cleanup: expected exactly one launch project.")
        return 1
    if int(fields[1] or 0) > 0:
        print("Refusing cleanup: approved_for_segment rows exist.")
        return 1
    if int(fields[2] or 0) > 0:
        print("Refusing cleanup: communication_sent=true detected.")
        return 1
    if int(fields[3] or 0) > 0:
        print("Refusing cleanup: campaign-send audit detected.")
        return 1

    code, output = run_psql(cleanup_sql(args.launch_key), tuples_only=True)
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
