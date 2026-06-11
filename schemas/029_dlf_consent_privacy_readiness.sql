-- Phase 7.8: DLF consent, suppression & lead-privacy readiness (1 audit table + 4 views).
--
-- This layer reviews the PROCESS-level consent/privacy posture of the DLF launch without ever
-- changing a contact's permission, approving a contact for campaign, or enabling send/publish.
-- It adds one audit table (process-review decisions only) and four read-only dashboards.
--
-- Hard invariants this migration preserves:
--   * It never grants a channel permission and never reads/exposes raw contact values.
--   * consent_ready can only become "ready" when an explicit channel_permissions 'allowed' basis
--     exists (count is 0 here, so it stays blocked).
--   * whatsapp_template_approved is provider-side and out of scope; it is never passed here.
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. launch_consent_privacy_review_log — process-level consent/privacy decisions (audit only).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_consent_privacy_review_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  review_area text,                                -- lead_form_consent, whatsapp_optin, email_optin, suppression_process, privacy_field_mapping, contact_permission_queue
  review_status text DEFAULT 'pending',            -- pending, process_approved, needs_more_info, rejected, waived
  reviewed_by text,
  reviewed_at timestamptz,
  safe_summary text,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcprl_launch_project_id ON launch_consent_privacy_review_log(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcprl_review_area ON launch_consent_privacy_review_log(review_area);
CREATE INDEX IF NOT EXISTS idx_lcprl_review_status ON launch_consent_privacy_review_log(review_status);
CREATE INDEX IF NOT EXISTS idx_lcprl_created_at ON launch_consent_privacy_review_log(created_at);

DROP TRIGGER IF EXISTS trg_launch_consent_privacy_review_log_updated_at ON launch_consent_privacy_review_log;
CREATE TRIGGER trg_launch_consent_privacy_review_log_updated_at
BEFORE UPDATE ON launch_consent_privacy_review_log FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 2. vw_dlf_consent_privacy_readiness — one-row consent/privacy posture (counts only).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_consent_privacy_readiness AS
SELECT
  p.launch_key,
  (SELECT count(*) FROM launch_lead_capture_forms f WHERE f.launch_project_id = p.id) AS lead_form_count,
  (SELECT count(*) FROM launch_lead_field_mappings m WHERE m.launch_project_id = p.id AND m.pii_type = 'consent') AS consent_field_mappings,
  (SELECT count(*) FROM launch_lead_capture_forms f WHERE f.launch_project_id = p.id AND f.whatsapp_optin_required) AS whatsapp_optin_fields,
  (SELECT count(*) FROM launch_lead_capture_forms f WHERE f.launch_project_id = p.id AND f.email_optin_required) AS email_optin_fields,
  (SELECT count(*) FROM launch_lead_field_mappings m WHERE m.launch_project_id = p.id AND m.pii_type IN ('name','email','phone')) AS pii_field_mappings,
  (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS permission_reviews_pending,
  (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id = p.id AND ri.review_type = 'suppression_review' AND ri.status = 'pending') AS suppression_reviews_pending,
  (SELECT count(*) FROM channel_permissions cp WHERE cp.permission_status = 'allowed') AS channel_permissions_allowed,
  (SELECT count(DISTINCT s.contact_id) FROM outreach_suppression_list s) AS suppressed_contacts,
  COALESCE((SELECT r.check_status FROM launch_readiness_checks r WHERE r.launch_project_id = p.id AND r.check_type = 'consent_ready' ORDER BY r.created_at LIMIT 1), 'pending') AS consent_ready_process_status,
  COALESCE((SELECT r.check_status FROM launch_readiness_checks r WHERE r.launch_project_id = p.id AND r.check_type = 'lead_privacy_reviewed' ORDER BY r.created_at LIMIT 1), 'pending') AS lead_privacy_process_status,
  COALESCE((SELECT v.ready_for_campaign_selection FROM vw_dlf_contact_segment_readiness v WHERE v.launch_key = p.launch_key), false) AS ready_for_campaign_selection,
  COALESCE((SELECT v.ready_for_live_lead_capture FROM vw_dlf_lead_intake_readiness v WHERE v.launch_key = p.launch_key), false) AS ready_for_live_lead_capture,
  CASE
    WHEN (SELECT count(*) FROM channel_permissions cp WHERE cp.permission_status = 'allowed') = 0
      THEN 'no explicit channel_permissions allowed record — consent basis required before any contact use'
    WHEN (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') > 0
      THEN 'contact permission reviews still pending'
    ELSE 'consent/privacy process clear (still no send/publish without explicit approval)'
  END AS blocked_reason
FROM launch_projects p;

-- ---------------------------------------------------------------------------
-- 3. vw_dlf_contact_permission_gap_dashboard — who is blocked by unknown consent (counts only).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_contact_permission_gap_dashboard AS
SELECT
  p.launch_key,
  c.candidate_status,
  c.whatsapp_permission_status,
  c.email_permission_status,
  c.suppression_status,
  count(*) AS candidate_count,
  CASE
    WHEN c.whatsapp_permission_status <> 'allowed' AND c.email_permission_status <> 'allowed'
      THEN 'no allowed channel — explicit opt-in / channel_permissions required before any contact use'
    WHEN c.suppression_status <> 'cleared'
      THEN 'run suppression check before any contact use'
    ELSE 'permission present — still requires human campaign approval'
  END AS recommended_action
FROM launch_contact_segment_candidates c
JOIN launch_projects p ON p.id = c.launch_project_id
GROUP BY p.launch_key, c.candidate_status, c.whatsapp_permission_status, c.email_permission_status, c.suppression_status;

-- ---------------------------------------------------------------------------
-- 4. vw_dlf_lead_form_privacy_dashboard — lead-form consent/PII posture (counts only).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_lead_form_privacy_dashboard AS
SELECT
  p.launch_key,
  f.form_key,
  f.form_status,
  f.whatsapp_optin_required,
  f.email_optin_required,
  f.utm_capture_required,
  (SELECT count(*) FROM launch_lead_field_mappings m WHERE m.lead_capture_form_id = f.id AND m.pii_type IN ('name','email','phone')) AS pii_field_count,
  jsonb_array_length(COALESCE(f.consent_fields, '[]'::jsonb)) AS consent_field_count,
  COALESCE((SELECT lg.review_status FROM launch_consent_privacy_review_log lg
              WHERE lg.launch_project_id = p.id AND lg.review_area IN ('lead_form_consent','privacy_field_mapping')
              ORDER BY lg.created_at DESC LIMIT 1), 'pending') AS privacy_review_status,
  CASE
    WHEN f.publish_enabled THEN 'form publish flag set unexpectedly — investigate'
    WHEN f.form_status = 'draft' THEN 'review consent + PII fields; keep form unpublished until consent basis confirmed'
    ELSE 'maintain consent/PII review on any change'
  END AS recommended_action
FROM launch_lead_capture_forms f
JOIN launch_projects p ON p.id = f.launch_project_id;

-- ---------------------------------------------------------------------------
-- 5. vw_dlf_suppression_readiness_dashboard — suppression-process posture (counts only).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_suppression_readiness_dashboard AS
SELECT
  p.launch_key,
  (SELECT count(*) FROM outreach_suppression_list) AS suppression_rows,
  (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id = p.id AND ri.review_type = 'suppression_review' AND ri.status = 'pending') AS suppression_reviews_pending,
  (SELECT count(DISTINCT s.contact_id) FROM outreach_suppression_list s) AS contacts_suppressed,
  COALESCE((SELECT lg.review_status FROM launch_consent_privacy_review_log lg
              WHERE lg.launch_project_id = p.id AND lg.review_area = 'suppression_process'
              ORDER BY lg.created_at DESC LIMIT 1), 'pending') AS suppression_process_status,
  CASE
    WHEN (SELECT count(*) FROM outreach_suppression_list) = 0
      THEN 'no suppression entries yet — a suppression run is required before any send (process may be approved, execution is not)'
    ELSE 'suppression list present — verify coverage before any send'
  END AS blocked_reason
FROM launch_projects p;
