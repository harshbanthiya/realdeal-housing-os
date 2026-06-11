-- Phase 7.9: DLF contact permission evidence & suppression review (3 tables + 4 views).
--
-- An evidence-based layer for deciding whether a launch candidate has an EXPLICIT channel
-- permission. It records evidence and suppression-check results and audits decisions — it never
-- grants a permission, never approves a contact for campaign, never writes to
-- outreach_suppression_list, and never enables send/publish. A permission_decision of 'allowed'
-- is only ever derived from a real channel_permissions 'allowed' row (there are 0 today).
--
-- All views mask person names via mask_name() and expose NO phone/email/address/website values.
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. launch_contact_permission_evidence
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_permission_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  launch_contact_segment_candidate_id uuid REFERENCES launch_contact_segment_candidates(id),
  contact_id uuid REFERENCES contacts(id),
  channel text,                                    -- whatsapp, email, phone_call
  evidence_type text,                              -- explicit_opt_in, prior_business_relationship, referral_permission, manual_note, unknown, unavailable
  evidence_status text DEFAULT 'needs_review',     -- needs_review, accepted, rejected, insufficient, archived
  permission_decision text DEFAULT 'unknown',      -- unknown, allowed, not_allowed, needs_more_info, suppressed
  evidence_source_label text,
  safe_summary text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcpe_launch_project_id ON launch_contact_permission_evidence(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcpe_candidate_id ON launch_contact_permission_evidence(launch_contact_segment_candidate_id);
CREATE INDEX IF NOT EXISTS idx_lcpe_contact_id ON launch_contact_permission_evidence(contact_id);
CREATE INDEX IF NOT EXISTS idx_lcpe_channel ON launch_contact_permission_evidence(channel);
CREATE INDEX IF NOT EXISTS idx_lcpe_evidence_type ON launch_contact_permission_evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_lcpe_evidence_status ON launch_contact_permission_evidence(evidence_status);
CREATE INDEX IF NOT EXISTS idx_lcpe_permission_decision ON launch_contact_permission_evidence(permission_decision);
CREATE INDEX IF NOT EXISTS idx_lcpe_created_at ON launch_contact_permission_evidence(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_contact_suppression_checks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_suppression_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  launch_contact_segment_candidate_id uuid REFERENCES launch_contact_segment_candidates(id),
  contact_id uuid REFERENCES contacts(id),
  check_status text DEFAULT 'pending',             -- pending, clear, suppressed, needs_review
  suppression_source text,                         -- outreach_suppression_list, manual_review, unknown
  safe_summary text,
  checked_by text,
  checked_at timestamptz,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcsc_launch_project_id ON launch_contact_suppression_checks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_candidate_id ON launch_contact_suppression_checks(launch_contact_segment_candidate_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_contact_id ON launch_contact_suppression_checks(contact_id);
CREATE INDEX IF NOT EXISTS idx_lcsc_check_status ON launch_contact_suppression_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_lcsc_created_at ON launch_contact_suppression_checks(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_contact_permission_decision_log (append-only audit; no updated_at)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_contact_permission_decision_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  launch_contact_segment_candidate_id uuid REFERENCES launch_contact_segment_candidates(id),
  contact_id uuid REFERENCES contacts(id),
  action_type text,                                -- evidence_created, permission_marked_needs_more_info, suppression_checked, review_item_updated, candidate_status_updated
  old_status text,
  new_status text,
  performed_by text,
  action_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcpdl_launch_project_id ON launch_contact_permission_decision_log(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcpdl_candidate_id ON launch_contact_permission_decision_log(launch_contact_segment_candidate_id);
CREATE INDEX IF NOT EXISTS idx_lcpdl_contact_id ON launch_contact_permission_decision_log(contact_id);
CREATE INDEX IF NOT EXISTS idx_lcpdl_action_type ON launch_contact_permission_decision_log(action_type);
CREATE INDEX IF NOT EXISTS idx_lcpdl_created_at ON launch_contact_permission_decision_log(created_at);

-- updated_at triggers (tables 1 & 2 only; table 3 is append-only).
DROP TRIGGER IF EXISTS trg_launch_contact_permission_evidence_updated_at ON launch_contact_permission_evidence;
CREATE TRIGGER trg_launch_contact_permission_evidence_updated_at
BEFORE UPDATE ON launch_contact_permission_evidence FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_contact_suppression_checks_updated_at ON launch_contact_suppression_checks;
CREATE TRIGGER trg_launch_contact_suppression_checks_updated_at
BEFORE UPDATE ON launch_contact_suppression_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 4. vw_dlf_contact_permission_evidence_dashboard (masked names; no phone/email).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_contact_permission_evidence_dashboard AS
SELECT
  p.launch_key,
  e.launch_contact_segment_candidate_id AS candidate_id,
  mask_name(c.full_name) AS masked_contact_name,
  e.channel,
  e.evidence_type,
  e.evidence_status,
  e.permission_decision,
  e.safe_summary,
  e.reviewed_at
FROM launch_contact_permission_evidence e
JOIN launch_projects p ON p.id = e.launch_project_id
LEFT JOIN contacts c ON c.id = e.contact_id;

-- ---------------------------------------------------------------------------
-- 5. vw_dlf_contact_suppression_check_dashboard (masked names; no phone/email).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_contact_suppression_check_dashboard AS
SELECT
  p.launch_key,
  s.launch_contact_segment_candidate_id AS candidate_id,
  mask_name(c.full_name) AS masked_contact_name,
  s.check_status,
  s.suppression_source,
  s.safe_summary,
  s.checked_at
FROM launch_contact_suppression_checks s
JOIN launch_projects p ON p.id = s.launch_project_id
LEFT JOIN contacts c ON c.id = s.contact_id;

-- ---------------------------------------------------------------------------
-- 6. vw_dlf_contact_permission_decision_dashboard (per-candidate posture; masked names).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_contact_permission_decision_dashboard AS
SELECT
  p.launch_key,
  cand.id AS candidate_id,
  mask_name(c.full_name) AS masked_contact_name,
  cand.candidate_status,
  cand.whatsapp_permission_status,
  cand.email_permission_status,
  cand.suppression_status,
  (SELECT count(*) FROM launch_contact_permission_evidence e WHERE e.launch_contact_segment_candidate_id = cand.id) AS evidence_count,
  (SELECT count(*) FROM launch_contact_suppression_checks s WHERE s.launch_contact_segment_candidate_id = cand.id) AS suppression_check_count,
  CASE
    WHEN (SELECT count(*) FROM launch_contact_permission_evidence e WHERE e.launch_contact_segment_candidate_id = cand.id AND e.permission_decision = 'allowed') = 0
      THEN 'collect explicit opt-in evidence before any contact use'
    WHEN cand.suppression_status <> 'clear'
      THEN 'run/confirm suppression check before any contact use'
    ELSE 'permission + suppression present — still requires human campaign approval'
  END AS recommended_action,
  CASE
    WHEN (SELECT count(*) FROM channel_permissions cp WHERE cp.contact_id = cand.contact_id AND cp.permission_status = 'allowed') = 0
      THEN 'no explicit channel_permissions allowed record for this contact'
    WHEN cand.candidate_status <> 'approved_for_segment'
      THEN 'candidate not approved for segment'
    ELSE 'eligible pending human approval'
  END AS blocked_reason
FROM launch_contact_segment_candidates cand
JOIN launch_projects p ON p.id = cand.launch_project_id
LEFT JOIN contacts c ON c.id = cand.contact_id;

-- ---------------------------------------------------------------------------
-- 7. vw_dlf_campaign_selection_guardrail (real gate; stays false until explicit allow + approval).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_campaign_selection_guardrail AS
WITH agg AS (
  SELECT
    p.id, p.launch_key,
    (SELECT count(*) FROM launch_contact_segment_candidates WHERE launch_project_id = p.id) AS total_candidates,
    (SELECT count(*) FROM launch_contact_permission_evidence e WHERE e.launch_project_id = p.id AND e.channel = 'whatsapp' AND e.permission_decision = 'allowed') AS explicit_whatsapp_allowed,
    (SELECT count(*) FROM launch_contact_permission_evidence e WHERE e.launch_project_id = p.id AND e.channel = 'email' AND e.permission_decision = 'allowed') AS explicit_email_allowed,
    (SELECT count(*) FROM launch_contact_suppression_checks s WHERE s.launch_project_id = p.id AND s.check_status = 'clear') AS suppression_clear,
    (SELECT count(*) FROM launch_contact_segment_candidates WHERE launch_project_id = p.id AND candidate_status = 'approved_for_segment') AS approved_for_segment,
    (SELECT count(DISTINCT e.launch_contact_segment_candidate_id) FROM launch_contact_permission_evidence e
       JOIN launch_contact_suppression_checks s ON s.launch_contact_segment_candidate_id = e.launch_contact_segment_candidate_id AND s.check_status = 'clear'
      WHERE e.launch_project_id = p.id AND e.channel = 'whatsapp' AND e.permission_decision = 'allowed') AS contacts_ready_for_whatsapp,
    (SELECT count(DISTINCT e.launch_contact_segment_candidate_id) FROM launch_contact_permission_evidence e
       JOIN launch_contact_suppression_checks s ON s.launch_contact_segment_candidate_id = e.launch_contact_segment_candidate_id AND s.check_status = 'clear'
      WHERE e.launch_project_id = p.id AND e.channel = 'email' AND e.permission_decision = 'allowed') AS contacts_ready_for_email
  FROM launch_projects p
)
SELECT
  launch_key, total_candidates, explicit_whatsapp_allowed, explicit_email_allowed,
  suppression_clear, approved_for_segment, contacts_ready_for_whatsapp, contacts_ready_for_email,
  (approved_for_segment > 0
     AND (explicit_whatsapp_allowed > 0 OR explicit_email_allowed > 0)
     AND (contacts_ready_for_whatsapp + contacts_ready_for_email) > 0) AS ready_for_campaign_selection,
  CASE
    WHEN explicit_whatsapp_allowed = 0 AND explicit_email_allowed = 0
      THEN 'no explicit channel permission on record — opt-in evidence required before any contact use'
    WHEN approved_for_segment = 0
      THEN 'no candidate approved for segment (human approval required)'
    ELSE 'ready'
  END AS hard_stop_reason
FROM agg;
