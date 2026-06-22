#!/usr/bin/env python3
"""Plan DLF launch contact segment candidates.

Phase 7.2: creates review-gated contact-to-launch-segment candidates only. It
never sends messages, enables campaigns, creates contacts, merges contacts, or
prints raw contact values. Dry-run by default; writes require --real-ok --apply.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.2"
SOURCE = "dlf_contact_segment_planning"
def project_status_sql(launch_key: str) -> str:
    return f"""
SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(launch_key)};
"""

def candidate_cte_sql(launch_key: str, limit: int) -> str:
    key = sql_literal(launch_key)
    return f"""
WITH launch AS (
  SELECT id FROM launch_projects WHERE launch_key = {key}
),
segments AS (
  SELECT id, segment_key
  FROM launch_lead_segments
  WHERE launch_project_id IN (SELECT id FROM launch)
),
contact_signals AS (
  SELECT DISTINCT
    c.id AS contact_id,
    'owner_network_referrals' AS segment_key,
    'active_owner_relationship' AS segment_reason,
    90 AS priority_score
  FROM contacts c
  JOIN contact_property_relationships cpr ON cpr.contact_id = c.id
  WHERE c.is_test = false
    AND c.status = 'active'
    AND cpr.relationship_type = 'owner'
    AND cpr.relationship_status = 'active'

  UNION

  SELECT DISTINCT
    c.id AS contact_id,
    'old_real_estate_contacts_needs_permission_review' AS segment_key,
    'existing_warm_contact' AS segment_reason,
    50 AS priority_score
  FROM contacts c
  WHERE c.is_test = false
    AND c.status = 'active'
    AND EXISTS (
      SELECT 1
      FROM contact_methods cm
      WHERE cm.contact_id = c.id
        AND cm.validation_status = 'valid'
        AND cm.method_type IN ('phone', 'mobile', 'whatsapp', 'email')
    )
),
limited_signals AS (
  SELECT *
  FROM contact_signals
  ORDER BY priority_score DESC, segment_key, contact_id
  LIMIT {int(limit)}
),
eligible AS (
  SELECT
    gen_random_uuid() AS candidate_id,
    (SELECT id FROM launch) AS launch_project_id,
    s.id AS launch_lead_segment_id,
    ls.contact_id,
    ls.segment_reason,
    ls.priority_score,
    EXISTS (
      SELECT 1 FROM contact_methods cm
      WHERE cm.contact_id = ls.contact_id
        AND cm.method_type IN ('phone', 'mobile', 'whatsapp')
        AND cm.validation_status = 'valid'
    ) AS has_phone_method,
    EXISTS (
      SELECT 1 FROM contact_methods cm
      WHERE cm.contact_id = ls.contact_id
        AND cm.method_type = 'email'
        AND cm.validation_status = 'valid'
    ) AS has_email_method,
    EXISTS (
      SELECT 1 FROM outreach_suppression_list osl
      WHERE osl.contact_id = ls.contact_id
        AND osl.status = 'active'
    ) AS is_suppressed,
    (
      SELECT cp.permission_status
      FROM channel_permissions cp
      WHERE cp.contact_id = ls.contact_id
        AND cp.channel = 'whatsapp'
      ORDER BY cp.created_at DESC
      LIMIT 1
    ) AS whatsapp_permission,
    (
      SELECT cp.permission_status
      FROM channel_permissions cp
      WHERE cp.contact_id = ls.contact_id
        AND cp.channel = 'email'
      ORDER BY cp.created_at DESC
      LIMIT 1
    ) AS email_permission
  FROM limited_signals ls
  JOIN segments s ON s.segment_key = ls.segment_key
  WHERE NOT EXISTS (
    SELECT 1
    FROM launch_contact_segment_candidates existing
    WHERE existing.launch_project_id = (SELECT id FROM launch)
      AND existing.launch_lead_segment_id = s.id
      AND existing.contact_id = ls.contact_id
      AND existing.raw_context->>'phase' = {sql_literal(PHASE)}
      AND existing.raw_context->>'source' = {sql_literal(SOURCE)}
  )
),
planned AS (
  SELECT
    candidate_id,
    launch_project_id,
    launch_lead_segment_id,
    contact_id,
    CASE WHEN is_suppressed THEN 'suppressed' ELSE 'needs_permission_review' END AS candidate_status,
    segment_reason,
    priority_score,
    CASE
      WHEN is_suppressed THEN 'suppressed'
      WHEN whatsapp_permission IN ('allowed', 'opted_in') THEN 'allowed'
      WHEN whatsapp_permission IN ('opted_out', 'do_not_contact', 'invalid') THEN 'not_allowed'
      WHEN has_phone_method THEN 'needs_review'
      ELSE 'unknown'
    END AS whatsapp_permission_status,
    CASE
      WHEN is_suppressed THEN 'suppressed'
      WHEN email_permission IN ('allowed', 'opted_in') THEN 'allowed'
      WHEN email_permission IN ('opted_out', 'do_not_contact', 'invalid') THEN 'not_allowed'
      WHEN has_email_method THEN 'needs_review'
      ELSE 'unknown'
    END AS email_permission_status,
    CASE WHEN is_suppressed THEN 'suppressed' ELSE 'needs_review' END AS suppression_status,
    has_phone_method,
    has_email_method,
    is_suppressed
  FROM eligible
)
"""

def plan_counts_sql(launch_key: str, limit: int) -> str:
    return (
        candidate_cte_sql(launch_key, limit)
        + """
SELECT 'candidate_rows_to_create' AS item, count(*)::text FROM planned
UNION ALL SELECT 'candidate_status_' || candidate_status, count(*)::text FROM planned GROUP BY candidate_status
UNION ALL SELECT 'segment_reason_' || segment_reason, count(*)::text FROM planned GROUP BY segment_reason
UNION ALL SELECT 'whatsapp_permission_' || whatsapp_permission_status, count(*)::text FROM planned GROUP BY whatsapp_permission_status
UNION ALL SELECT 'email_permission_' || email_permission_status, count(*)::text FROM planned GROUP BY email_permission_status
UNION ALL SELECT 'suppression_' || suppression_status, count(*)::text FROM planned GROUP BY suppression_status
UNION ALL SELECT 'review_items_to_create', (
  count(*) FILTER (WHERE true)
  + count(*) FILTER (WHERE has_phone_method)
  + count(*) FILTER (WHERE has_email_method)
  + count(*) FILTER (WHERE true)
)::text FROM planned
UNION ALL SELECT 'segment_fit_review_items', count(*)::text FROM planned
UNION ALL SELECT 'whatsapp_permission_review_items', count(*) FILTER (WHERE has_phone_method)::text FROM planned
UNION ALL SELECT 'email_permission_review_items', count(*) FILTER (WHERE has_email_method)::text FROM planned
UNION ALL SELECT 'suppression_review_items', count(*)::text FROM planned
UNION ALL SELECT 'send_enabled', '0'
UNION ALL SELECT 'communication_sent', '0'
ORDER BY item;
"""
    )

def apply_sql(launch_key: str, limit: int) -> str:
    tag = (
        "jsonb_build_object("
        f"'phase', {sql_literal(PHASE)}, "
        f"'source', {sql_literal(SOURCE)}, "
        "'send_enabled', false, "
        "'communication_sent', false, "
        "'external_calls_made', false)"
    )
    cte = candidate_cte_sql(launch_key, limit)
    return (
        "BEGIN;\n"
        + cte
        + f"""
, inserted_candidates AS (
  INSERT INTO launch_contact_segment_candidates (
    id, launch_project_id, launch_lead_segment_id, contact_id, candidate_status,
    segment_reason, priority_score, whatsapp_permission_status, email_permission_status,
    suppression_status, human_review_required, raw_context
  )
  SELECT
    candidate_id, launch_project_id, launch_lead_segment_id, contact_id, candidate_status,
    segment_reason, priority_score, whatsapp_permission_status, email_permission_status,
    suppression_status, true, {tag}
  FROM planned
  RETURNING id, launch_project_id, contact_id
),
review_plan AS (
  SELECT id, launch_project_id, contact_id, 'segment_fit_review' AS review_type, 'high' AS priority FROM inserted_candidates
  UNION ALL
  SELECT ic.id, ic.launch_project_id, ic.contact_id, 'whatsapp_permission_review', 'high'
  FROM inserted_candidates ic
  JOIN planned p ON p.candidate_id = ic.id
  WHERE p.has_phone_method
  UNION ALL
  SELECT ic.id, ic.launch_project_id, ic.contact_id, 'email_permission_review', 'high'
  FROM inserted_candidates ic
  JOIN planned p ON p.candidate_id = ic.id
  WHERE p.has_email_method
  UNION ALL
  SELECT id, launch_project_id, contact_id, 'suppression_review', 'high' FROM inserted_candidates
),
inserted_reviews AS (
  INSERT INTO launch_contact_permission_review_items (
    launch_contact_segment_candidate_id, launch_project_id, contact_id,
    review_type, status, priority, raw_context
  )
  SELECT id, launch_project_id, contact_id, review_type, 'pending', priority, {tag}
  FROM review_plan
  RETURNING id, review_type
)
SELECT 'candidate_rows_created' AS item, count(*)::text FROM inserted_candidates
UNION ALL SELECT 'review_items_created', count(*)::text FROM inserted_reviews
UNION ALL SELECT 'segment_fit_review_items', count(*) FILTER (WHERE review_type = 'segment_fit_review')::text FROM inserted_reviews
UNION ALL SELECT 'whatsapp_permission_review_items', count(*) FILTER (WHERE review_type = 'whatsapp_permission_review')::text FROM inserted_reviews
UNION ALL SELECT 'email_permission_review_items', count(*) FILTER (WHERE review_type = 'email_permission_review')::text FROM inserted_reviews
UNION ALL SELECT 'suppression_review_items', count(*) FILTER (WHERE review_type = 'suppression_review')::text FROM inserted_reviews
UNION ALL SELECT 'approved_for_segment', '0'
UNION ALL SELECT 'send_enabled', '0'
UNION ALL SELECT 'communication_sent', '0'
ORDER BY item;

COMMIT;
"""
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Plan DLF launch contact segments. Counts only.")
    parser.add_argument("--launch-key", required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required for real contact segment planning.")
        return 1
    if args.limit < 1:
        print("--limit must be positive.")
        return 1

    code, status = run_psql(project_status_sql(args.launch_key), tuples_only=True)
    if code != 0:
        print(status)
        return code
    if status.strip() != "1":
        print("Refusing: expected exactly one launch project for --launch-key.")
        return 1

    print("DLF contact segment plan. Counts only; no raw contact values are printed.")
    print(f"launch_key: {args.launch_key}")
    print(f"limit: {args.limit}")
    if not args.apply:
        code, output = run_psql(plan_counts_sql(args.launch_key, args.limit), tuples_only=True)
        print(output)
        print("Dry run only. No database rows were inserted.")
        print("Writing requires --apply and --real-ok.")
        return code

    code, output = run_psql(apply_sql(args.launch_key, args.limit), tuples_only=True)
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
