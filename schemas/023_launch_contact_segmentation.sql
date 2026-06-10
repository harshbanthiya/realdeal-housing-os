-- Phase 7.2: DLF contact segmentation and permission review.
-- Review-gated contact-to-launch-segment planning only. No sends, no campaign
-- selection, no permission auto-approval, and no raw contact values in views.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. launch_contact_segment_candidates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_segment_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  launch_lead_segment_id uuid REFERENCES launch_lead_segments(id),
  contact_id uuid REFERENCES contacts(id),
  candidate_status text DEFAULT 'candidate',
  segment_reason text,
  priority_score integer DEFAULT 0,
  whatsapp_permission_status text DEFAULT 'unknown',
  email_permission_status text DEFAULT 'unknown',
  suppression_status text DEFAULT 'unknown',
  last_contacted_at timestamptz,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lcsc_candidate_status_check
    CHECK (candidate_status IN ('candidate', 'needs_permission_review', 'approved_for_segment', 'rejected', 'suppressed', 'archived')),
  CONSTRAINT lcsc_segment_reason_check
    CHECK (segment_reason IS NULL OR segment_reason IN ('active_owner_relationship', 'similar_ticket_owner', 'existing_warm_contact', 'investor_candidate', 'nri_candidate', 'referral_network', 'manual_review')),
  CONSTRAINT lcsc_whatsapp_permission_status_check
    CHECK (whatsapp_permission_status IN ('unknown', 'allowed', 'not_allowed', 'needs_review', 'suppressed')),
  CONSTRAINT lcsc_email_permission_status_check
    CHECK (email_permission_status IN ('unknown', 'allowed', 'not_allowed', 'needs_review', 'suppressed')),
  CONSTRAINT lcsc_suppression_status_check
    CHECK (suppression_status IN ('unknown', 'clear', 'suppressed', 'needs_review'))
);

CREATE INDEX IF NOT EXISTS idx_lcsc_launch_project_id ON launch_contact_segment_candidates(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_launch_lead_segment_id ON launch_contact_segment_candidates(launch_lead_segment_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_contact_id ON launch_contact_segment_candidates(contact_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_candidate_status ON launch_contact_segment_candidates(candidate_status);
CREATE INDEX IF NOT EXISTS idx_lcsc_segment_reason ON launch_contact_segment_candidates(segment_reason);
CREATE INDEX IF NOT EXISTS idx_lcsc_whatsapp_permission_status ON launch_contact_segment_candidates(whatsapp_permission_status);
CREATE INDEX IF NOT EXISTS idx_lcsc_email_permission_status ON launch_contact_segment_candidates(email_permission_status);
CREATE INDEX IF NOT EXISTS idx_lcsc_suppression_status ON launch_contact_segment_candidates(suppression_status);
CREATE INDEX IF NOT EXISTS idx_lcsc_priority_score ON launch_contact_segment_candidates(priority_score);
CREATE INDEX IF NOT EXISTS idx_lcsc_created_at ON launch_contact_segment_candidates(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_contact_permission_review_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_permission_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_contact_segment_candidate_id uuid REFERENCES launch_contact_segment_candidates(id) ON DELETE CASCADE,
  launch_project_id uuid REFERENCES launch_projects(id),
  contact_id uuid REFERENCES contacts(id),
  review_type text,
  status text DEFAULT 'pending',
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lcpri_review_type_check
    CHECK (review_type IN ('segment_fit_review', 'whatsapp_permission_review', 'email_permission_review', 'suppression_review', 'priority_review')),
  CONSTRAINT lcpri_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'needs_more_info', 'skipped')),
  CONSTRAINT lcpri_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE INDEX IF NOT EXISTS idx_lcpri_launch_project_id ON launch_contact_permission_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcpri_candidate_id ON launch_contact_permission_review_items(launch_contact_segment_candidate_id);
CREATE INDEX IF NOT EXISTS idx_lcpri_contact_id ON launch_contact_permission_review_items(contact_id);
CREATE INDEX IF NOT EXISTS idx_lcpri_review_type ON launch_contact_permission_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_lcpri_status ON launch_contact_permission_review_items(status);
CREATE INDEX IF NOT EXISTS idx_lcpri_created_at ON launch_contact_permission_review_items(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_contact_segment_audit_log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_segment_audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_contact_segment_candidate_id uuid REFERENCES launch_contact_segment_candidates(id) ON DELETE SET NULL,
  action_type text,
  old_status text,
  new_status text,
  performed_by text,
  action_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lcsal_candidate_id ON launch_contact_segment_audit_log(launch_contact_segment_candidate_id);
CREATE INDEX IF NOT EXISTS idx_lcsal_action_type ON launch_contact_segment_audit_log(action_type);
CREATE INDEX IF NOT EXISTS idx_lcsal_created_at ON launch_contact_segment_audit_log(created_at);

DROP TRIGGER IF EXISTS trg_launch_contact_segment_candidates_updated_at ON launch_contact_segment_candidates;
CREATE TRIGGER trg_launch_contact_segment_candidates_updated_at
BEFORE UPDATE ON launch_contact_segment_candidates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_contact_permission_review_items_updated_at ON launch_contact_permission_review_items;
CREATE TRIGGER trg_launch_contact_permission_review_items_updated_at
BEFORE UPDATE ON launch_contact_permission_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Masked operator dashboards
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_launch_contact_segment_candidate_dashboard AS
SELECT
  csc.id AS candidate_id,
  lp.launch_key,
  lls.segment_name,
  mask_name(c.full_name) AS masked_contact_name,
  c.status AS contact_status,
  csc.candidate_status,
  csc.segment_reason,
  csc.priority_score,
  csc.whatsapp_permission_status,
  csc.email_permission_status,
  csc.suppression_status,
  csc.human_review_required,
  csc.created_at
FROM launch_contact_segment_candidates csc
JOIN launch_projects lp ON lp.id = csc.launch_project_id
JOIN launch_lead_segments lls ON lls.id = csc.launch_lead_segment_id
JOIN contacts c ON c.id = csc.contact_id;

CREATE OR REPLACE VIEW vw_launch_contact_permission_review_queue AS
SELECT
  pri.id AS review_item_id,
  csc.id AS candidate_id,
  lp.launch_key,
  lls.segment_name,
  mask_name(c.full_name) AS masked_contact_name,
  pri.review_type,
  pri.status,
  pri.priority,
  csc.whatsapp_permission_status,
  csc.email_permission_status,
  csc.suppression_status,
  pri.created_at
FROM launch_contact_permission_review_items pri
JOIN launch_contact_segment_candidates csc ON csc.id = pri.launch_contact_segment_candidate_id
JOIN launch_projects lp ON lp.id = pri.launch_project_id
JOIN launch_lead_segments lls ON lls.id = csc.launch_lead_segment_id
JOIN contacts c ON c.id = pri.contact_id;

CREATE OR REPLACE VIEW vw_dlf_contact_segment_readiness AS
WITH base AS (
  SELECT
    lp.id AS launch_project_id,
    lp.launch_key,
    count(csc.id) AS total_candidates,
    count(*) FILTER (WHERE csc.candidate_status = 'approved_for_segment') AS approved_for_segment,
    count(*) FILTER (WHERE csc.candidate_status IN ('candidate', 'needs_permission_review')) AS pending_review,
    count(*) FILTER (WHERE csc.candidate_status = 'needs_permission_review') AS needs_permission_review,
    count(*) FILTER (WHERE csc.candidate_status = 'suppressed') AS suppressed,
    count(*) FILTER (WHERE csc.whatsapp_permission_status = 'allowed') AS whatsapp_allowed,
    count(*) FILTER (WHERE csc.whatsapp_permission_status = 'needs_review') AS whatsapp_needs_review,
    count(*) FILTER (WHERE csc.email_permission_status = 'allowed') AS email_allowed,
    count(*) FILTER (WHERE csc.email_permission_status = 'needs_review') AS email_needs_review,
    count(*) FILTER (WHERE csc.suppression_status = 'needs_review') AS suppression_needs_review,
    count(*) FILTER (WHERE csc.suppression_status = 'suppressed') AS suppressed_permissions
  FROM launch_projects lp
  LEFT JOIN launch_contact_segment_candidates csc ON csc.launch_project_id = lp.id
  WHERE lp.launch_key = 'dlf-westpark-andheri-west'
  GROUP BY lp.id, lp.launch_key
)
SELECT
  launch_key,
  total_candidates,
  approved_for_segment,
  pending_review,
  needs_permission_review,
  suppressed,
  whatsapp_allowed,
  whatsapp_needs_review,
  email_allowed,
  email_needs_review,
  suppression_needs_review,
  (approved_for_segment > 0
   AND needs_permission_review = 0
   AND whatsapp_needs_review = 0
   AND email_needs_review = 0
   AND suppression_needs_review = 0
   AND suppressed_permissions = 0) AS ready_for_campaign_selection,
  CASE
    WHEN total_candidates = 0 THEN 'no segment candidates planned'
    WHEN approved_for_segment = 0 THEN 'no contacts approved for segment'
    WHEN needs_permission_review > 0 THEN 'permission review pending'
    WHEN whatsapp_needs_review > 0 OR email_needs_review > 0 THEN 'channel permission review pending'
    WHEN suppression_needs_review > 0 THEN 'suppression review pending'
    WHEN suppressed_permissions > 0 THEN 'suppressed contacts present'
    ELSE 'ready only after explicit human approval'
  END AS blocked_reason
FROM base;

CREATE OR REPLACE VIEW vw_dlf_owner_audience_summary AS
WITH owner_contacts AS (
  SELECT DISTINCT cpr.contact_id
  FROM contact_property_relationships cpr
  JOIN launch_projects lp ON lp.launch_key = 'dlf-westpark-andheri-west'
  WHERE cpr.relationship_type = 'owner'
    AND cpr.relationship_status = 'active'
),
candidates AS (
  SELECT csc.*
  FROM launch_contact_segment_candidates csc
  JOIN launch_projects lp ON lp.id = csc.launch_project_id
  WHERE lp.launch_key = 'dlf-westpark-andheri-west'
    AND csc.segment_reason IN ('active_owner_relationship', 'similar_ticket_owner', 'referral_network')
)
SELECT
  lp.launch_key,
  (SELECT count(*) FROM owner_contacts) AS active_owner_contacts_total,
  (SELECT count(*) FROM candidates) AS candidate_owner_contacts,
  (SELECT count(*) FROM candidates WHERE candidate_status = 'approved_for_segment') AS approved_owner_contacts,
  (SELECT count(*) FROM candidates WHERE candidate_status = 'needs_permission_review'
     OR whatsapp_permission_status = 'needs_review'
     OR email_permission_status = 'needs_review'
     OR suppression_status = 'needs_review') AS pending_permission_review,
  (SELECT count(*) FROM candidates WHERE candidate_status = 'suppressed'
     OR suppression_status = 'suppressed') AS suppressed_count,
  true AS no_raw_contact_values_exposed
FROM launch_projects lp
WHERE lp.launch_key = 'dlf-westpark-andheri-west';
