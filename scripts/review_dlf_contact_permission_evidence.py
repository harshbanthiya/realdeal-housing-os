#!/usr/bin/env python3
"""Phase 7.9 — DLF contact permission evidence & suppression review. Dry-run by default.

Evidence-based permission review for the launch candidates. Three opt-in actions:
  --create-unknown-permission-evidence
      For each in-scope candidate and channel (whatsapp, email) create a
      launch_contact_permission_evidence row. permission_decision is 'allowed' ONLY when a real
      channel_permissions 'allowed' row backs that (contact, channel); otherwise 'needs_more_info'.
  --run-suppression-check
      For each in-scope candidate create a launch_contact_suppression_checks row: 'suppressed' if the
      contact is on outreach_suppression_list, else 'clear'. It NEVER writes to
      outreach_suppression_list. When clear, the candidate's suppression_status -> clear and its
      suppression_review item -> approved (suppression-list clear only — NOT consent).
  --mark-permissions-needs-more-info
      Records (in the audit log) that the whatsapp/email permission reviews remain needs_more_info.

It never marks a permission allowed without a backing channel_permissions row, never sets a candidate
to approved_for_segment, never passes consent_ready / whatsapp_template_approved, and never enables
send/publish. An in-transaction guard rolls everything back if any of those would happen.

Writing requires BOTH --real-ok and --apply. Counts only; never prints raw contact values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CHANNELS = ("whatsapp", "email")
def channels_values_sql() -> str:
    return ", ".join(f"({sql_literal(c)})" for c in EVIDENCE_CHANNELS)

def probe_sql(launch_key: str, limit: int | None) -> str:
    lk = sql_literal(launch_key)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
cand AS (
  SELECT id, contact_id FROM launch_contact_segment_candidates
  WHERE launch_project_id IN (SELECT id FROM proj)
  ORDER BY created_at {limit_clause}
)
SELECT
  (SELECT count(*) FROM cand),
  (SELECT count(*) FROM channel_permissions WHERE permission_status = 'allowed'),
  (SELECT count(*) FROM outreach_suppression_list),
  (SELECT count(*) FROM cand WHERE NOT EXISTS (SELECT 1 FROM outreach_suppression_list sl WHERE sl.contact_id = cand.contact_id)),
  (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_contact_segment_candidate_id IN (SELECT id FROM cand) AND ri.review_type = 'suppression_review' AND ri.status = 'pending');
"""

def apply_sql(launch_key, reviewed_by, decision_notes, do_evidence, do_suppression, do_permissions, limit):
    lk = sql_literal(launch_key)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    allowed_exists = ("EXISTS (SELECT 1 FROM channel_permissions cp WHERE cp.contact_id = cand.contact_id "
                      "AND cp.channel = ch.channel AND cp.permission_status = 'allowed')")

    blocks = [f"""
BEGIN;
CREATE TEMP TABLE tmp_cand AS
SELECT cand.id, cand.contact_id, cand.launch_project_id, cand.suppression_status
FROM launch_contact_segment_candidates cand
JOIN launch_projects p ON p.id = cand.launch_project_id
WHERE p.launch_key = {lk}
ORDER BY cand.created_at
{limit_clause};
"""]

    if do_evidence:
        blocks.append(f"""
INSERT INTO launch_contact_permission_evidence
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, channel, evidence_type, evidence_status,
   permission_decision, evidence_source_label, safe_summary, reviewed_by, reviewed_at, decision_notes, raw_context)
SELECT cand.launch_project_id, cand.id, cand.contact_id, ch.channel,
  CASE WHEN {allowed_exists} THEN 'explicit_opt_in' ELSE 'unknown' END,
  CASE WHEN {allowed_exists} THEN 'accepted' ELSE 'needs_review' END,
  CASE WHEN {allowed_exists} THEN 'allowed' ELSE 'needs_more_info' END,
  'no explicit opt-in on record',
  'Permission evidence reviewed; explicit opt-in required before contact use.',
  {rb}, now(), {dn},
  jsonb_build_object('phase','7.9','source','phase_7_9_permission_evidence','channel', ch.channel)
FROM tmp_cand cand
CROSS JOIN (VALUES {channels_values_sql()}) AS ch(channel)
WHERE NOT EXISTS (SELECT 1 FROM launch_contact_permission_evidence e
                  WHERE e.launch_contact_segment_candidate_id = cand.id AND e.channel = ch.channel AND e.raw_context->>'phase' = '7.9');

INSERT INTO launch_contact_permission_decision_log
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT e.launch_project_id, e.launch_contact_segment_candidate_id, e.contact_id, 'evidence_created', NULL, e.permission_decision, {rb},
  'Permission evidence row created.', jsonb_build_object('phase','7.9','channel', e.channel)
FROM launch_contact_permission_evidence e
WHERE e.raw_context->>'phase' = '7.9'
  AND e.launch_contact_segment_candidate_id IN (SELECT id FROM tmp_cand)
  AND NOT EXISTS (SELECT 1 FROM launch_contact_permission_decision_log l
                  WHERE l.action_type = 'evidence_created'
                    AND l.launch_contact_segment_candidate_id = e.launch_contact_segment_candidate_id
                    AND l.raw_context->>'channel' = e.channel);
""")

    if do_suppression:
        blocks.append(f"""
INSERT INTO launch_contact_suppression_checks
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, check_status, suppression_source, safe_summary, checked_by, checked_at, raw_context)
SELECT cand.launch_project_id, cand.id, cand.contact_id,
  CASE WHEN EXISTS (SELECT 1 FROM outreach_suppression_list sl WHERE sl.contact_id = cand.contact_id) THEN 'suppressed' ELSE 'clear' END,
  'outreach_suppression_list',
  'Suppression check vs outreach_suppression_list; no list write performed.',
  {rb}, now(),
  jsonb_build_object('phase','7.9','source','phase_7_9_suppression_check')
FROM tmp_cand cand
WHERE NOT EXISTS (SELECT 1 FROM launch_contact_suppression_checks s
                  WHERE s.launch_contact_segment_candidate_id = cand.id AND s.raw_context->>'phase' = '7.9');

INSERT INTO launch_contact_permission_decision_log
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT s.launch_project_id, s.launch_contact_segment_candidate_id, s.contact_id, 'suppression_checked', NULL, s.check_status, {rb},
  'Suppression check recorded (no list write).', jsonb_build_object('phase','7.9')
FROM launch_contact_suppression_checks s
WHERE s.raw_context->>'phase' = '7.9'
  AND s.launch_contact_segment_candidate_id IN (SELECT id FROM tmp_cand)
  AND NOT EXISTS (SELECT 1 FROM launch_contact_permission_decision_log l
                  WHERE l.action_type = 'suppression_checked' AND l.launch_contact_segment_candidate_id = s.launch_contact_segment_candidate_id);

-- When suppression is clear, set candidate suppression_status -> clear (tracked for revert).
UPDATE launch_contact_segment_candidates cand SET
  suppression_status = 'clear',
  raw_context = cand.raw_context || jsonb_build_object('phase_7_9_suppression_prev', cand.suppression_status),
  updated_at = now()
FROM launch_contact_suppression_checks s
WHERE s.launch_contact_segment_candidate_id = cand.id AND s.raw_context->>'phase' = '7.9' AND s.check_status = 'clear'
  AND cand.id IN (SELECT id FROM tmp_cand) AND cand.suppression_status <> 'clear';

INSERT INTO launch_contact_permission_decision_log
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT cand.launch_project_id, cand.id, cand.contact_id, 'candidate_status_updated',
  cand.raw_context->>'phase_7_9_suppression_prev', 'clear', {rb},
  'Candidate suppression_status set clear (suppression-list clear).', jsonb_build_object('phase','7.9')
FROM launch_contact_segment_candidates cand
WHERE cand.id IN (SELECT id FROM tmp_cand) AND cand.suppression_status = 'clear'
  AND cand.raw_context ? 'phase_7_9_suppression_prev'
  AND NOT EXISTS (SELECT 1 FROM launch_contact_permission_decision_log l
                  WHERE l.action_type = 'candidate_status_updated' AND l.launch_contact_segment_candidate_id = cand.id);

-- suppression_review item -> approved ONLY when suppression is clear AND the list is empty.
UPDATE launch_contact_permission_review_items ri SET
  status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = ri.raw_context || jsonb_build_object('phase','7.9','phase_7_9_action','suppression_review_approved','phase_7_9_prev_status', ri.status),
  updated_at = now()
FROM launch_contact_suppression_checks s
WHERE ri.launch_contact_segment_candidate_id = s.launch_contact_segment_candidate_id
  AND s.raw_context->>'phase' = '7.9' AND s.check_status = 'clear'
  AND ri.launch_contact_segment_candidate_id IN (SELECT id FROM tmp_cand)
  AND ri.review_type = 'suppression_review' AND ri.status = 'pending'
  AND (SELECT count(*) FROM outreach_suppression_list) = 0;

INSERT INTO launch_contact_permission_decision_log
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT ri.launch_project_id, ri.launch_contact_segment_candidate_id, ri.contact_id, 'review_item_updated',
  ri.raw_context->>'phase_7_9_prev_status', 'approved', {rb},
  'suppression_review approved (suppression-list clear; not consent).', jsonb_build_object('phase','7.9','review_type','suppression_review')
FROM launch_contact_permission_review_items ri
WHERE ri.review_type = 'suppression_review' AND ri.raw_context->>'phase' = '7.9'
  AND ri.launch_contact_segment_candidate_id IN (SELECT id FROM tmp_cand)
  AND NOT EXISTS (SELECT 1 FROM launch_contact_permission_decision_log l
                  WHERE l.action_type = 'review_item_updated' AND l.launch_contact_segment_candidate_id = ri.launch_contact_segment_candidate_id
                    AND l.raw_context->>'review_type' = 'suppression_review');
""")

    if do_permissions:
        blocks.append(f"""
-- whatsapp/email permission reviews remain needs_more_info; record it in the audit log only.
INSERT INTO launch_contact_permission_decision_log
  (launch_project_id, launch_contact_segment_candidate_id, contact_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT cand.launch_project_id, cand.id, cand.contact_id, 'permission_marked_needs_more_info', 'needs_more_info', 'needs_more_info', {rb},
  'WhatsApp/email permission remains needs_more_info (no explicit opt-in on record).', jsonb_build_object('phase','7.9')
FROM tmp_cand cand
WHERE NOT EXISTS (SELECT 1 FROM launch_contact_permission_decision_log l
                  WHERE l.action_type = 'permission_marked_needs_more_info' AND l.launch_contact_segment_candidate_id = cand.id);
""")

    blocks.append(f"""
-- Hard guardrail.
DO $GUARD$
DECLARE se int; pe int; an int; rf boolean; cpa int; aff int; cr text; wt text; bad_allow int; bad_supp int;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = {lk} AND m.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN launch_projects p ON p.id = f.launch_project_id WHERE p.launch_key = {lk} AND f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN launch_projects p ON p.id = sc.launch_project_id WHERE p.launch_key = {lk} AND sc.publish_enabled)
  INTO pe;
  SELECT count(*) FROM launch_n8n_workflow_blueprints b JOIN launch_projects p ON p.id = b.launch_project_id
    WHERE p.launch_key = {lk} AND (b.workflow_status = 'active' OR b.activation_status = 'active') INTO an;
  SELECT ready_for_launch_push INTO rf FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk};
  SELECT count(*) FROM channel_permissions WHERE permission_status = 'allowed' INTO cpa;
  SELECT count(*) FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id
    WHERE p.launch_key = {lk} AND c.candidate_status = 'approved_for_segment' INTO aff;
  SELECT check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
    WHERE p.launch_key = {lk} AND r.check_type = 'consent_ready' ORDER BY r.created_at LIMIT 1 INTO cr;
  SELECT check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
    WHERE p.launch_key = {lk} AND r.check_type = 'whatsapp_template_approved' ORDER BY r.created_at LIMIT 1 INTO wt;
  -- evidence marked 'allowed' must be backed by a real channel_permissions allowed row.
  SELECT count(*) FROM launch_contact_permission_evidence e
    WHERE e.permission_decision = 'allowed'
      AND NOT EXISTS (SELECT 1 FROM channel_permissions cp WHERE cp.contact_id = e.contact_id AND cp.channel = e.channel AND cp.permission_status = 'allowed') INTO bad_allow;
  -- suppression checks marked 'suppressed' must be backed by a real outreach_suppression_list row.
  SELECT count(*) FROM launch_contact_suppression_checks s
    WHERE s.check_status = 'suppressed'
      AND NOT EXISTS (SELECT 1 FROM outreach_suppression_list sl WHERE sl.contact_id = s.contact_id) INTO bad_supp;
  IF se > 0 OR pe > 0 OR an > 0 THEN RAISE EXCEPTION 'Refusing: send/publish/n8n activation (send=%, publish=%, n8n=%).', se, pe, an; END IF;
  IF rf THEN RAISE EXCEPTION 'Refusing: ready_for_launch_push would be true.'; END IF;
  IF cpa > 0 THEN RAISE EXCEPTION 'Refusing: channel_permissions allowed must remain 0 this phase (got %).', cpa; END IF;
  IF aff > 0 THEN RAISE EXCEPTION 'Refusing: no candidate may be approved_for_segment this phase (got %).', aff; END IF;
  IF cr = 'passed' THEN RAISE EXCEPTION 'Refusing: consent_ready must not be passed.'; END IF;
  IF wt = 'passed' THEN RAISE EXCEPTION 'Refusing: whatsapp_template_approved must not be passed.'; END IF;
  IF bad_allow > 0 THEN RAISE EXCEPTION 'Refusing: % evidence row(s) marked allowed without a backing channel_permissions record.', bad_allow; END IF;
  IF bad_supp > 0 THEN RAISE EXCEPTION 'Refusing: % suppression check(s) marked suppressed without a backing suppression-list row.', bad_supp; END IF;
END $GUARD$;
COMMIT;

SELECT 'evidence_total', count(*)::text FROM launch_contact_permission_evidence e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'evidence_allowed', count(*)::text FROM launch_contact_permission_evidence e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} AND e.permission_decision = 'allowed'
UNION ALL SELECT 'evidence_needs_more_info', count(*)::text FROM launch_contact_permission_evidence e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} AND e.permission_decision = 'needs_more_info'
UNION ALL SELECT 'suppression_checks_clear', count(*)::text FROM launch_contact_suppression_checks s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.check_status = 'clear'
UNION ALL SELECT 'suppression_checks_suppressed', count(*)::text FROM launch_contact_suppression_checks s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.check_status = 'suppressed'
UNION ALL SELECT 'decision_log_rows', count(*)::text FROM launch_contact_permission_decision_log l JOIN launch_projects p ON p.id = l.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'suppression_reviews_approved', count(*)::text FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.review_type = 'suppression_review' AND ri.status = 'approved'
UNION ALL SELECT 'candidates_approved_for_segment', count(*)::text FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.candidate_status = 'approved_for_segment'
UNION ALL SELECT 'channel_permissions_allowed', count(*)::text FROM channel_permissions WHERE permission_status = 'allowed'
UNION ALL SELECT 'ready_for_campaign_selection', ready_for_campaign_selection::text FROM vw_dlf_campaign_selection_guardrail WHERE launch_key = {lk}
UNION ALL SELECT 'consent_ready', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'consent_ready'
UNION ALL SELECT 'send_enabled_count', send_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
""")
    return "\n".join(blocks)

def main() -> int:
    parser = argparse.ArgumentParser(description="DLF contact permission evidence & suppression review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--create-unknown-permission-evidence", action="store_true")
    parser.add_argument("--run-suppression-check", action="store_true")
    parser.add_argument("--mark-permissions-needs-more-info", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: always refused.
    parser.add_argument("--mark-permission-allowed", action="store_true")
    parser.add_argument("--approve-candidates-for-segment", action="store_true")
    parser.add_argument("--pass-consent-ready", action="store_true")
    parser.add_argument("--enable-send", action="store_true")
    parser.add_argument("--enable-publish", action="store_true")
    args = parser.parse_args()

    print(f"DLF contact permission evidence review. launch_key={args.launch_key}. Counts only; no contact values.")

    if args.mark_permission_allowed or args.approve_candidates_for_segment or args.pass_consent_ready or args.enable_send or args.enable_publish:
        print("Refusing: this script never marks a permission allowed, approves candidates for segment, "
              "passes consent_ready, or enables send/publish.")
        return 1

    do_evidence = args.create_unknown_permission_evidence
    do_suppression = args.run_suppression_check
    do_permissions = args.mark_permissions_needs_more_info
    if not (do_evidence or do_suppression or do_permissions):
        print("Nothing to do: pass at least one of --create-unknown-permission-evidence, "
              "--run-suppression-check, --mark-permissions-needs-more-info.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key, args.limit))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 5:
        print("Refusing: probe returned no usable result.")
        return 1
    cand_count, perms_allowed, supp_rows, would_clear, supp_reviews_pending = (int(x or 0) for x in f[:5])

    print("inputs (counts only):")
    print(f"  candidates in scope: {cand_count}   channel_permissions allowed: {perms_allowed}   suppression-list rows: {supp_rows}")
    print("projected actions:")
    if do_evidence:
        print(f"  permission evidence: {cand_count * len(EVIDENCE_CHANNELS)} row(s) (whatsapp+email); allowed only if a real channel_permissions row exists ({perms_allowed})")
    if do_suppression:
        print(f"  suppression checks: {cand_count} row(s); would be clear: {would_clear}; suppression_review -> approved (list clear): {supp_reviews_pending if supp_rows == 0 else 0}")
    if do_permissions:
        print(f"  whatsapp/email permission: remain needs_more_info (audit log only)")
    print("  candidates approved for segment: 0 (never)   permission marked allowed: never without explicit record")
    print("  consent_ready / whatsapp_template_approved / send / publish: untouched")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, args.reviewed_by, args.decision_notes,
                                      do_evidence, do_suppression, do_permissions, args.limit))
    print("Permission evidence review applied:" if code == 0 else "Permission evidence review FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
