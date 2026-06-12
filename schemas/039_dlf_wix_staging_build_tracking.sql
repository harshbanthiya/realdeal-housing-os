-- Phase 7.20: DLF Westpark manual Wix staging build tracking.
--
-- Adds an append-only audit log for the HUMAN/manual Wix staging build process and a
-- build-progress dashboard. It records whether an operator manually created a staging site,
-- moves selected setup/safety checklist and QA items forward, and explicitly logs that Wix API
-- permission/key usage is DEFERRED to a later capability-map phase. This schema performs NO Wix
-- API call, NO Wix API key read, NO n8n call, NO external API call, NO publishing, NO live
-- form/webhook, NO sends, and NO inbound-lead/contact writes. The progress view keeps
-- ready_for_fake_lead_test hard-gated and never implies Wix API readiness.

CREATE TABLE IF NOT EXISTS wix_staging_build_action_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  wix_staging_site_id uuid REFERENCES wix_staging_sites(id),
  checklist_item_id uuid REFERENCES wix_staging_build_checklist_items(id),
  qa_check_id uuid REFERENCES wix_staging_qa_checks(id),
  action_type text,
  old_status text,
  new_status text,
  performed_by text,
  action_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wsbal_launch_project_id ON wix_staging_build_action_log(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wsbal_staging_site_id ON wix_staging_build_action_log(wix_staging_site_id);
CREATE INDEX IF NOT EXISTS idx_wsbal_checklist_item_id ON wix_staging_build_action_log(checklist_item_id);
CREATE INDEX IF NOT EXISTS idx_wsbal_qa_check_id ON wix_staging_build_action_log(qa_check_id);
CREATE INDEX IF NOT EXISTS idx_wsbal_action_type ON wix_staging_build_action_log(action_type);
CREATE INDEX IF NOT EXISTS idx_wsbal_created_at ON wix_staging_build_action_log(created_at);

CREATE OR REPLACE VIEW vw_wix_staging_build_action_log_dashboard AS
SELECT
  p.launch_key,
  s.staging_key,
  l.action_type,
  l.old_status,
  l.new_status,
  l.performed_by,
  l.created_at
FROM wix_staging_build_action_log l
JOIN launch_projects p ON p.id = l.launch_project_id
LEFT JOIN wix_staging_sites s ON s.id = l.wix_staging_site_id;

CREATE OR REPLACE VIEW vw_dlf_wix_staging_build_progress AS
WITH launch_scope AS (
  SELECT id, launch_key FROM launch_projects
),
site_pick AS (
  SELECT DISTINCT ON (launch_project_id)
    launch_project_id, staging_status,
    real_domain_connected, public_indexing_enabled, page_created, page_published,
    live_form_created, live_webhook_created, external_tracking_enabled, wix_api_call_made
  FROM wix_staging_sites
  ORDER BY launch_project_id, created_at
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    sp.staging_status,
    count(DISTINCT c.id) AS checklist_items,
    count(DISTINCT c.id) FILTER (WHERE c.checklist_status = 'in_progress') AS checklist_started,
    count(DISTINCT c.id) FILTER (WHERE c.checklist_status = 'passed') AS checklist_passed,
    count(DISTINCT q.id) AS qa_checks,
    count(DISTINCT q.id) FILTER (WHERE q.qa_status = 'passed') AS qa_passed,
    count(DISTINCT q.id) FILTER (WHERE q.blocker AND q.qa_status = 'failed') AS qa_blockers_failed,
    count(DISTINCT l.id) FILTER (WHERE l.action_type = 'api_permission_review_deferred') AS api_permission_review_deferred_count,
    COALESCE(bool_or(sp.real_domain_connected), false) AS any_real_domain,
    COALESCE(bool_or(sp.public_indexing_enabled), false) AS any_indexing,
    COALESCE(bool_or(sp.page_published), false) AS any_published,
    COALESCE(bool_or(sp.live_form_created), false) AS any_live_form,
    COALESCE(bool_or(sp.live_webhook_created), false) AS any_live_webhook,
    COALESCE(bool_or(sp.external_tracking_enabled), false) AS any_tracking,
    COALESCE(bool_or(sp.wix_api_call_made), false) AS any_api_call,
    count(DISTINCT s.id) AS staging_sites,
    count(DISTINCT s.id) FILTER (WHERE s.staging_status IN ('created_manually', 'build_in_progress', 'ready_for_qa', 'qa_passed')) AS staging_created_manually
  FROM launch_scope p
  LEFT JOIN site_pick sp ON sp.launch_project_id = p.id
  LEFT JOIN wix_staging_sites s ON s.launch_project_id = p.id
  LEFT JOIN wix_staging_build_checklist_items c ON c.launch_project_id = p.id
  LEFT JOIN wix_staging_qa_checks q ON q.launch_project_id = p.id
  LEFT JOIN wix_staging_build_action_log l ON l.launch_project_id = p.id
  GROUP BY p.id, p.launch_key, sp.staging_status
)
SELECT
  launch_key,
  staging_status,
  checklist_items,
  checklist_started,
  checklist_passed,
  qa_checks,
  qa_passed,
  api_permission_review_deferred_count,
  (
    NOT any_real_domain
    AND NOT any_indexing
    AND NOT any_published
    AND NOT any_live_form
    AND NOT any_live_webhook
    AND NOT any_tracking
  ) AS safety_flags_clean,
  (
    staging_created_manually > 0
    AND NOT any_real_domain
    AND NOT any_indexing
    AND NOT any_published
    AND NOT any_live_form
    AND NOT any_live_webhook
    AND NOT any_tracking
    AND NOT any_api_call
  ) AS ready_for_staging_qa,
  (
    staging_status = 'qa_passed'
    AND qa_checks > 0
    AND qa_passed = qa_checks
    AND qa_blockers_failed = 0
    AND NOT any_real_domain
    AND NOT any_indexing
    AND NOT any_published
    AND NOT any_live_form
    AND NOT any_live_webhook
    AND NOT any_tracking
  ) AS ready_for_fake_lead_test,
  CASE
    WHEN any_real_domain THEN 'blocked: staging site reports real_domain_connected'
    WHEN any_indexing THEN 'blocked: staging site reports public_indexing_enabled'
    WHEN any_published THEN 'blocked: staging site reports page_published'
    WHEN any_live_form THEN 'blocked: staging site reports live_form_created'
    WHEN any_live_webhook THEN 'blocked: staging site reports live_webhook_created'
    WHEN any_tracking THEN 'blocked: staging site reports external_tracking_enabled'
    WHEN any_api_call THEN 'blocked: staging site reports wix_api_call_made'
    WHEN staging_sites = 0 THEN 'blocked: no staging site planned'
    WHEN staging_created_manually = 0 THEN 'build tracking initialized; awaiting operator-confirmed manual staging site'
    WHEN staging_status <> 'qa_passed' THEN 'manual staging build in progress; staging QA not yet complete'
    ELSE 'staging build + QA complete; fake staging lead test is the next gated phase (Wix API capability mapping stays deferred)'
  END AS blocked_reason
FROM agg;
