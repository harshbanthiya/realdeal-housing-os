-- Phase 7.6: DLF launch blocker triage + project-identity status (views only).
--
-- Read-only triage layer over the existing launch command center. It does NOT add tables,
-- does NOT change any send/publish/external/activation flag, and does NOT expose personal
-- contact data. Every view is counts/status/safe-summary only.
--
-- Three views:
--   1. vw_dlf_launch_blocker_triage     — one row per OPEN blocker (readiness checks + operator
--                                          tasks), grouped into operator-facing blocker areas.
--   2. vw_dlf_project_identity_status   — the project-name confirmation state (internal alias vs
--                                          possible public name), never assumed/confirmed here.
--   3. vw_dlf_launch_activation_guardrail — the hard activation guardrail: every send/publish/
--                                          external/launch flag and the hard-stop reason.
--
-- ready_for_launch_push and safety_status are READ from existing real gates; this migration
-- cannot make them true. Idempotent: CREATE OR REPLACE VIEW throughout; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. vw_dlf_launch_blocker_triage — open blockers grouped by operator area.
-- ---------------------------------------------------------------------------
-- Open = readiness checks in (pending, failed, needs_review) and operator tasks in
-- (pending, in_progress, blocked). Each row carries a safe_summary, a recommended action,
-- and two booleans the operator can use to decide what they can close themselves vs. what
-- needs an external system stood up (lead capture, n8n, publishing, sending).
CREATE OR REPLACE VIEW vw_dlf_launch_blocker_triage AS
WITH readiness AS (
  SELECT
    p.launch_key,
    CASE r.check_type
      WHEN 'project_name_confirmed'   THEN 'project_identity'
      WHEN 'rera_checked'             THEN 'project_identity'
      WHEN 'consent_ready'            THEN 'consent'
      WHEN 'lead_privacy_reviewed'    THEN 'consent'
      WHEN 'suppression_checked'      THEN 'suppression'
      WHEN 'whatsapp_template_approved' THEN 'copy_review'
      WHEN 'email_template_approved'  THEN 'copy_review'
      WHEN 'seo_briefs_ready'         THEN 'copy_review'
      WHEN 'social_calendar_ready'    THEN 'copy_review'
      WHEN 'wix_landing_page_ready'   THEN 'lead_capture'
      WHEN 'lead_capture_form_ready'  THEN 'lead_capture'
      WHEN 'wix_form_fields_reviewed' THEN 'lead_capture'
      WHEN 'lead_duplicate_review_ready' THEN 'lead_capture'
      WHEN 'attribution_rules_reviewed'  THEN 'lead_capture'
      WHEN 'lead_scoring_reviewed'    THEN 'lead_capture'
      WHEN 'utm_tracking_ready'       THEN 'lead_capture'
      WHEN 'n8n_webhook_planned'      THEN 'n8n'
      WHEN 'n8n_workflow_ready'       THEN 'n8n'
      ELSE 'other'
    END AS blocker_area,
    r.check_type AS blocker_type,
    'launch_readiness_checks'::text AS source_table,
    r.id AS source_id,
    r.check_status AS status,
    r.severity,
    COALESCE(r.safe_summary, r.check_type) AS safe_summary
  FROM launch_readiness_checks r
  JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE r.check_status IN ('pending', 'failed', 'needs_review')
),
tasks AS (
  SELECT
    p.launch_key,
    CASE t.task_type
      WHEN 'verify_project_name'   THEN 'project_identity'
      WHEN 'confirm_rera'          THEN 'project_identity'
      WHEN 'check_permissions'     THEN 'consent'
      WHEN 'approve_whatsapp_copy' THEN 'copy_review'
      WHEN 'approve_email_copy'    THEN 'copy_review'
      WHEN 'draft_blog'            THEN 'copy_review'
      WHEN 'draft_reel'            THEN 'copy_review'
      WHEN 'upload_creatives'      THEN 'copy_review'
      WHEN 'build_wix_page'        THEN 'lead_capture'
      WHEN 'review_leads'          THEN 'lead_capture'
      WHEN 'follow_up_hot_leads'   THEN 'sending'
      ELSE 'other'
    END AS blocker_area,
    t.task_type AS blocker_type,
    'launch_operator_tasks'::text AS source_table,
    t.id AS source_id,
    t.task_status AS status,
    t.priority AS severity,
    COALESCE(t.safe_summary, t.task_type) AS safe_summary
  FROM launch_operator_tasks t
  JOIN launch_projects p ON p.id = t.launch_project_id
  WHERE t.task_status IN ('pending', 'in_progress', 'blocked')
),
unioned AS (
  SELECT * FROM readiness
  UNION ALL
  SELECT * FROM tasks
)
SELECT
  launch_key,
  blocker_area,
  blocker_type,
  source_table,
  source_id,
  status,
  severity,
  safe_summary,
  CASE blocker_area
    WHEN 'project_identity' THEN 'Operator confirms public project name (or RERA identity); use confirm_dlf_project_identity.py'
    WHEN 'consent'          THEN 'Operator reviews consent/permission readiness before any audience use'
    WHEN 'suppression'      THEN 'Operator runs suppression review before any audience selection'
    WHEN 'copy_review'      THEN 'Operator reviews/approves draft copy (no send/publish enabled by this)'
    WHEN 'lead_capture'     THEN 'Build + review lead capture (Wix/form/n8n) before going live'
    WHEN 'n8n'              THEN 'Build/review n8n workflow blueprint; do not activate this phase'
    WHEN 'publishing'       THEN 'Publishing stays disabled until copy/assets approved'
    WHEN 'sending'          THEN 'Sending stays disabled until consent + suppression + copy approved'
    ELSE 'Operator review required'
  END AS recommended_action,
  -- Operator can close identity/consent/suppression/copy purely by review.
  (blocker_area IN ('project_identity', 'consent', 'suppression', 'copy_review')) AS can_be_closed_by_operator,
  -- Lead capture / n8n / publishing / sending require an external system to be stood up.
  (blocker_area IN ('lead_capture', 'n8n', 'publishing', 'sending')) AS requires_external_action
FROM unioned;

-- ---------------------------------------------------------------------------
-- 2. vw_dlf_project_identity_status — name confirmation state (never assumed here).
-- ---------------------------------------------------------------------------
-- project_name_confirmed_status is READ from the launch_readiness_checks gate and the
-- raw_context flag; this view never sets it. public_name_ready_for_copy is true ONLY when an
-- operator has explicitly confirmed the name (raw_context.project_name_confirmed = 'true' AND
-- the readiness check passed). Until then it is false and the name must not be used in copy.
CREATE OR REPLACE VIEW vw_dlf_project_identity_status AS
SELECT
  p.launch_key,
  p.project_display_name AS current_project_display_name,
  p.internal_alias,
  p.raw_context->>'possible_public_name' AS possible_public_name,
  COALESCE(
    (SELECT r.check_status FROM launch_readiness_checks r
       WHERE r.launch_project_id = p.id AND r.check_type = 'project_name_confirmed'
       ORDER BY r.created_at LIMIT 1),
    'pending'
  ) AS project_name_confirmed_status,
  p.rera_verification_status,
  (
    COALESCE(p.raw_context->>'project_name_confirmed', 'false') = 'true'
    AND COALESCE(
      (SELECT r.check_status FROM launch_readiness_checks r
         WHERE r.launch_project_id = p.id AND r.check_type = 'project_name_confirmed'
         ORDER BY r.created_at LIMIT 1),
      'pending') = 'passed'
  ) AS public_name_ready_for_copy,
  CASE
    WHEN COALESCE(p.raw_context->>'project_name_confirmed', 'false') = 'true'
      THEN 'confirmed by operator'
    ELSE 'project name NOT confirmed — operator must confirm public name (internal alias vs possible public name); do not assume or web-verify'
  END AS blocked_reason
FROM launch_projects p;

-- ---------------------------------------------------------------------------
-- 3. vw_dlf_launch_activation_guardrail — the hard activation guardrail.
-- ---------------------------------------------------------------------------
-- Reads the existing real gates (safety posture + priority dashboard). It cannot make
-- ready_for_launch_push true; it only surfaces the hard-stop reason. safety_status stays
-- safe_blocked while every flag is off.
CREATE OR REPLACE VIEW vw_dlf_launch_activation_guardrail AS
SELECT
  sp.launch_key,
  sp.send_enabled_count,
  sp.publish_enabled_count,
  sp.external_call_allowed_count,
  sp.active_n8n_workflows,
  sp.live_lead_capture_ready,
  sp.contacts_approved_for_campaign,
  pr.ready_for_launch_push,
  sp.safety_status,
  CASE
    WHEN sp.send_enabled_count > 0 OR sp.publish_enabled_count > 0
      THEN 'HARD STOP: send/publish flag enabled unexpectedly'
    WHEN sp.external_call_allowed_count > 0 OR sp.active_n8n_workflows > 0
      THEN 'HARD STOP: external automation enabled unexpectedly'
    WHEN sp.communication_sent > 0 OR sp.published_count > 0
      THEN 'HARD STOP: communication or publishing activity detected'
    WHEN NOT pr.ready_for_launch_push
      THEN pr.blocked_reason
    ELSE 'no hard stop'
  END AS hard_stop_reason
FROM vw_dlf_operator_safety_posture sp
JOIN vw_dlf_launch_priority_dashboard pr ON pr.launch_key = sp.launch_key;
