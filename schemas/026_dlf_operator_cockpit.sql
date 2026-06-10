-- Phase 7.5: DLF operator cockpit and daily execution dashboard.
--
-- View-only operator cockpit for the DLF launch. No tables are created, no launch
-- activation flags are changed, no contacts/leads/messages/publishing are created,
-- and no personal contact values are exposed.

-- ---------------------------------------------------------------------------
-- 1. One-row cockpit home.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_cockpit_home AS
WITH project AS (
  SELECT *
  FROM launch_projects
  WHERE launch_key = 'dlf-westpark-andheri-west'
),
review_counts AS (
  SELECT
    p.id AS launch_project_id,
    (SELECT count(*) FROM launch_draft_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS draft_reviews_pending,
    (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS permission_reviews_pending,
    (SELECT count(*) FROM launch_inbound_lead_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS inbound_reviews_pending,
    (SELECT count(*) FROM launch_n8n_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS n8n_reviews_pending
  FROM project p
),
safety AS (
  SELECT
    p.id AS launch_project_id,
    (
      (SELECT count(*) FROM launch_channels WHERE launch_project_id = p.id AND send_enabled)
      + (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND send_enabled)
      + (SELECT count(*) FROM launch_message_templates WHERE launch_project_id = p.id AND send_enabled)
    ) AS send_enabled_count,
    (
      (SELECT count(*) FROM launch_channels WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_landing_page_specs WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_lead_capture_forms WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id = p.id AND publish_enabled)
    ) AS publish_enabled_count,
    (SELECT count(*) FROM inbound_leads) AS inbound_leads,
    (SELECT count(*) FROM launch_readiness_checks rc
       WHERE rc.launch_project_id = p.id
         AND rc.severity = 'blocker'
         AND rc.check_status IN ('pending', 'failed', 'needs_review')) AS pending_blockers,
    (SELECT count(*) FROM launch_operator_tasks t
       WHERE t.launch_project_id = p.id
         AND t.priority IN ('blocker', 'high', 'urgent')
         AND t.task_status IN ('pending', 'in_progress', 'blocked')) AS pending_high_priority_tasks
  FROM project p
)
SELECT
  p.launch_key,
  p.project_display_name,
  p.launch_status,
  lp.ready_for_launch_push,
  li.ready_for_live_lead_capture,
  cs.ready_for_campaign_selection,
  n8n.ready_to_build_in_n8n AS ready_to_build_n8n,
  n8n.ready_to_activate AS ready_to_activate_n8n,
  s.send_enabled_count,
  s.publish_enabled_count,
  s.inbound_leads,
  s.pending_blockers,
  s.pending_high_priority_tasks,
  (rc.draft_reviews_pending + rc.permission_reviews_pending + rc.inbound_reviews_pending + rc.n8n_reviews_pending) AS pending_reviews_total,
  CASE
    WHEN s.pending_blockers > 0 THEN 'clear blocker readiness checks'
    WHEN cs.ready_for_campaign_selection = false THEN 'complete contact permission and suppression review'
    WHEN li.ready_for_live_lead_capture = false THEN 'complete lead-intake field/attribution review'
    WHEN n8n.ready_to_build_in_n8n = false THEN 'review n8n workflow blueprint before build'
    WHEN lp.ready_for_launch_push = false THEN 'complete launch content/campaign approvals'
    ELSE 'ready only after explicit send/publish approval'
  END AS next_required_action,
  concat_ws(
    ' | ',
    NULLIF(lp.blocked_reason, 'ready'),
    NULLIF(cs.blocked_reason, 'ready only after explicit human approval'),
    NULLIF(li.blocked_reason, 'ready'),
    NULLIF(n8n.blocked_reason, 'activation intentionally blocked until a later phase')
  ) AS blocked_reason
FROM project p
LEFT JOIN vw_dlf_launch_priority_dashboard lp ON lp.launch_key = p.launch_key
LEFT JOIN vw_dlf_lead_intake_readiness li ON li.launch_key = p.launch_key
LEFT JOIN vw_dlf_contact_segment_readiness cs ON cs.launch_key = p.launch_key
LEFT JOIN vw_dlf_n8n_readiness n8n ON n8n.launch_key = p.launch_key
LEFT JOIN review_counts rc ON rc.launch_project_id = p.id
LEFT JOIN safety s ON s.launch_project_id = p.id;

-- ---------------------------------------------------------------------------
-- 2. Daily operator task queue.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_today_tasks AS
SELECT
  p.launch_key,
  'operator_task' AS item_type,
  t.id::text AS item_id,
  t.task_type AS task_type_or_review_type,
  t.task_status AS status,
  t.priority,
  t.due_date,
  t.safe_summary,
  CASE
    WHEN t.task_status = 'blocked' THEN 'unblock or document blocker'
    WHEN t.priority IN ('blocker', 'urgent') THEN 'handle before launch work continues'
    WHEN t.due_date IS NOT NULL AND t.due_date <= CURRENT_DATE THEN 'complete today'
    ELSE 'schedule operator follow-up'
  END AS recommended_action
FROM launch_operator_tasks t
JOIN launch_projects p ON p.id = t.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND t.task_status IN ('pending', 'in_progress', 'blocked')

UNION ALL

SELECT
  p.launch_key,
  'readiness_check' AS item_type,
  rc.id::text AS item_id,
  rc.check_type AS task_type_or_review_type,
  rc.check_status AS status,
  rc.severity AS priority,
  NULL::date AS due_date,
  rc.safe_summary,
  'resolve readiness gate before any send/publish' AS recommended_action
FROM launch_readiness_checks rc
JOIN launch_projects p ON p.id = rc.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND rc.check_status IN ('pending', 'failed', 'needs_review')
  AND rc.severity IN ('blocker', 'high')

UNION ALL

SELECT
  p.launch_key,
  'draft_review' AS item_type,
  ri.id::text AS item_id,
  ri.review_type AS task_type_or_review_type,
  ri.status,
  ri.priority,
  NULL::date AS due_date,
  'Draft asset requires review; dashboards expose metadata only.' AS safe_summary,
  'review draft metadata and approve/reject in a later explicit phase' AS recommended_action
FROM launch_draft_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND ri.status = 'pending'
  AND ri.priority IN ('high', 'urgent')

UNION ALL

SELECT
  p.launch_key,
  'permission_review' AS item_type,
  ri.id::text AS item_id,
  ri.review_type AS task_type_or_review_type,
  ri.status,
  ri.priority,
  NULL::date AS due_date,
  'Contact permission/suppression item requires review; no raw contact values exposed.' AS safe_summary,
  'complete permission and suppression review before campaign selection' AS recommended_action
FROM launch_contact_permission_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND ri.status = 'pending'

UNION ALL

SELECT
  p.launch_key,
  'n8n_review' AS item_type,
  ri.id::text AS item_id,
  ri.review_type AS task_type_or_review_type,
  ri.status,
  ri.priority,
  NULL::date AS due_date,
  'n8n blueprint/review gate requires human approval; no workflow is live.' AS safe_summary,
  'review blueprint before any n8n build or activation'
FROM launch_n8n_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND ri.status = 'pending'
  AND ri.priority IN ('high', 'urgent');

-- ---------------------------------------------------------------------------
-- 3. Combined review backlog.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_review_backlog AS
SELECT
  p.launch_key,
  'draft_reviews' AS source_queue,
  ri.id AS review_item_id,
  ri.review_type,
  ri.status,
  ri.priority,
  CASE
    WHEN ri.landing_page_spec_id IS NOT NULL THEN 'landing_page'
    WHEN ri.lead_capture_form_id IS NOT NULL THEN 'lead_form'
    WHEN ri.social_content_draft_id IS NOT NULL THEN 'social'
    WHEN ri.message_template_id IS NOT NULL THEN 'copy'
    WHEN ri.utm_campaign_spec_id IS NOT NULL THEN 'attribution'
    ELSE 'copy'
  END AS linked_area,
  'review asset metadata; full copy is not exposed in cockpit' AS recommended_action,
  ri.created_at
FROM launch_draft_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'

UNION ALL

SELECT
  p.launch_key,
  'permission_reviews' AS source_queue,
  ri.id AS review_item_id,
  ri.review_type,
  ri.status,
  ri.priority,
  CASE
    WHEN ri.review_type LIKE '%suppression%' THEN 'suppression'
    WHEN ri.review_type LIKE '%permission%' THEN 'consent'
    ELSE 'contacts'
  END AS linked_area,
  'review permission/suppression status without exposing contact values' AS recommended_action,
  ri.created_at
FROM launch_contact_permission_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'

UNION ALL

SELECT
  p.launch_key,
  'inbound_lead_reviews' AS source_queue,
  ri.id AS review_item_id,
  ri.review_type,
  ri.status,
  ri.priority,
  'lead_intake' AS linked_area,
  'review inbound lead before contact conversion or follow-up' AS recommended_action,
  ri.created_at
FROM launch_inbound_lead_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'

UNION ALL

SELECT
  p.launch_key,
  'n8n_reviews' AS source_queue,
  ri.id AS review_item_id,
  ri.review_type,
  ri.status,
  ri.priority,
  'n8n' AS linked_area,
  'review n8n blueprint gate before build or activation' AS recommended_action,
  ri.created_at
FROM launch_n8n_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west';

-- ---------------------------------------------------------------------------
-- 4. Next 14 days campaign calendar.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_campaign_calendar_next_14_days AS
SELECT
  p.launch_key,
  cc.planned_date,
  cc.channel,
  cc.campaign_type,
  cc.title,
  cc.status,
  cc.send_enabled,
  cc.publish_enabled,
  CASE
    WHEN cc.send_enabled OR cc.publish_enabled THEN 'unexpected enablement; verify immediately'
    WHEN cc.status IN ('sent', 'published') THEN 'unexpected sent/published status; verify immediately'
    ELSE 'blocked: send/publish intentionally disabled pending review'
  END AS blocker_reason
FROM launch_campaign_calendar cc
JOIN launch_projects p ON p.id = cc.launch_project_id
WHERE p.launch_key = 'dlf-westpark-andheri-west'
  AND cc.planned_date >= CURRENT_DATE
  AND cc.planned_date < CURRENT_DATE + INTERVAL '14 days'
ORDER BY cc.planned_date, cc.channel, cc.campaign_type;

-- ---------------------------------------------------------------------------
-- 5. Audience readiness.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_audience_readiness AS
SELECT
  launch_key,
  total_candidates,
  approved_for_segment,
  (needs_permission_review + whatsapp_needs_review + email_needs_review + suppression_needs_review) AS pending_permission_review,
  whatsapp_allowed,
  email_allowed,
  suppressed,
  ready_for_campaign_selection,
  blocked_reason
FROM vw_dlf_contact_segment_readiness;

-- ---------------------------------------------------------------------------
-- 6. Lead-intake readiness.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_lead_intake_readiness AS
SELECT
  launch_key,
  endpoints_planned,
  endpoints_active,
  field_mappings,
  approved_field_mappings,
  attribution_rules,
  approved_attribution_rules,
  inbound_leads,
  external_call_allowed_count,
  ready_for_live_lead_capture,
  blocked_reason
FROM vw_dlf_lead_intake_readiness;

-- ---------------------------------------------------------------------------
-- 7. n8n readiness.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_n8n_readiness AS
SELECT
  launch_key,
  workflow_blueprints,
  workflows_approved_for_build,
  workflows_built,
  active_workflows,
  pending_reviews,
  external_call_allowed_count,
  ready_to_build_in_n8n,
  ready_to_activate,
  blocked_reason
FROM vw_dlf_n8n_readiness;

-- ---------------------------------------------------------------------------
-- 8. Content readiness.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_content_readiness AS
SELECT
  launch_key,
  landing_pages,
  lead_forms,
  message_templates,
  social_drafts,
  content_pillars,
  pending_reviews AS draft_reviews_pending,
  approved_reviews,
  send_enabled_count,
  publish_enabled_count,
  ready_for_launch_push AS ready_for_content_push,
  blocked_reason
FROM vw_dlf_launch_funnel_readiness;

-- ---------------------------------------------------------------------------
-- 9. Safety posture.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_operator_safety_posture AS
WITH project AS (
  SELECT *
  FROM launch_projects
  WHERE launch_key = 'dlf-westpark-andheri-west'
),
counts AS (
  SELECT
    p.launch_key,
    (
      (SELECT count(*) FROM launch_channels WHERE launch_project_id = p.id AND send_enabled)
      + (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND send_enabled)
      + (SELECT count(*) FROM launch_message_templates WHERE launch_project_id = p.id AND send_enabled)
    ) AS send_enabled_count,
    (
      (SELECT count(*) FROM launch_channels WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_landing_page_specs WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_lead_capture_forms WHERE launch_project_id = p.id AND publish_enabled)
      + (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id = p.id AND publish_enabled)
    ) AS publish_enabled_count,
    (
      (SELECT count(*) FROM launch_lead_intake_endpoints WHERE launch_project_id = p.id AND external_call_allowed)
      + (SELECT count(*) FROM launch_n8n_workflow_blueprints WHERE launch_project_id = p.id AND external_call_allowed)
      + (SELECT count(*) FROM launch_n8n_test_cases t
           JOIN launch_n8n_workflow_blueprints b ON b.id = t.workflow_blueprint_id
          WHERE b.launch_project_id = p.id AND t.external_call_allowed)
    ) AS external_call_allowed_count,
    (SELECT count(*) FROM launch_n8n_workflow_blueprints
      WHERE launch_project_id = p.id AND (workflow_status = 'active' OR activation_status = 'active')) AS active_n8n_workflows,
    COALESCE((SELECT ready_for_live_lead_capture FROM vw_dlf_lead_intake_readiness WHERE launch_key = p.launch_key), false) AS live_lead_capture_ready,
    (SELECT count(*) FROM launch_contact_segment_candidates WHERE launch_project_id = p.id AND candidate_status = 'approved_for_segment') AS contacts_approved_for_campaign,
    (
      (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_message_templates WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_contact_segment_candidates WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_contact_permission_review_items WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_lead_intake_endpoints WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
      + (SELECT count(*) FROM launch_n8n_workflow_blueprints WHERE launch_project_id = p.id AND raw_context->>'communication_sent' = 'true')
    ) AS communication_sent,
    (
      (SELECT count(*) FROM launch_campaign_calendar WHERE launch_project_id = p.id AND (status = 'published' OR publish_enabled))
      + (SELECT count(*) FROM launch_landing_page_specs WHERE launch_project_id = p.id AND (page_status = 'published' OR publish_enabled))
      + (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id = p.id AND (draft_status = 'published' OR publish_enabled))
    ) AS published_count
  FROM project p
)
SELECT
  launch_key,
  send_enabled_count,
  publish_enabled_count,
  external_call_allowed_count,
  active_n8n_workflows,
  live_lead_capture_ready,
  contacts_approved_for_campaign,
  communication_sent,
  published_count,
  CASE
    WHEN send_enabled_count = 0
      AND publish_enabled_count = 0
      AND external_call_allowed_count = 0
      AND active_n8n_workflows = 0
      AND live_lead_capture_ready = false
      AND contacts_approved_for_campaign = 0
      AND communication_sent = 0
      AND published_count = 0
      THEN 'safe_blocked'
    ELSE 'blocked_not_ready'
  END AS safety_status,
  CASE
    WHEN send_enabled_count > 0 OR publish_enabled_count > 0 THEN 'send/publish flag enabled unexpectedly'
    WHEN external_call_allowed_count > 0 OR active_n8n_workflows > 0 THEN 'external automation enabled unexpectedly'
    WHEN communication_sent > 0 OR published_count > 0 THEN 'communication or publishing activity detected'
    ELSE 'all launch activation paths remain blocked'
  END AS safety_notes
FROM counts;
