-- Phase 7.10: DLF controlled test lead-intake harness (3 tables + 4 views).
--
-- A self-contained, FAKE-ONLY harness to prove the lead-intake validation path without touching the
-- real inbound_leads / contacts tables, without live webhooks/APIs, and without enabling anything.
-- Every test payload is flagged uses_fake_data=true / creates_real_contact=false /
-- creates_real_lead=false / external_call_made=false. Dashboards never expose the fake name / phone /
-- email columns. ready_for_live_lead_capture mirrors the real (false) lead-intake gate — this harness
-- cannot make it true. Idempotent: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW.

-- ---------------------------------------------------------------------------
-- 1. launch_test_lead_payloads — fake lead payloads for controlled validation.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_test_lead_payloads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  test_key text,
  payload_status text DEFAULT 'draft',             -- draft, validated, failed, archived
  payload_type text,                               -- wix_form, instagram_link, whatsapp_click, referral_link, listing_portal
  fake_name text,
  fake_phone text,
  fake_email text,
  fake_payload jsonb DEFAULT '{}'::jsonb,
  uses_fake_data boolean DEFAULT true,
  creates_real_contact boolean DEFAULT false,
  creates_real_lead boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ltlp_launch_project_id ON launch_test_lead_payloads(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ltlp_test_key ON launch_test_lead_payloads(test_key);
CREATE INDEX IF NOT EXISTS idx_ltlp_payload_status ON launch_test_lead_payloads(payload_status);
CREATE INDEX IF NOT EXISTS idx_ltlp_payload_type ON launch_test_lead_payloads(payload_type);
CREATE INDEX IF NOT EXISTS idx_ltlp_created_at ON launch_test_lead_payloads(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_test_lead_validation_results — validation results for fake payloads.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_test_lead_validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  test_payload_id uuid REFERENCES launch_test_lead_payloads(id),
  validation_type text,                            -- required_fields, pii_mapping, consent_fields, utm_mapping, attribution_rule, lead_scoring, duplicate_check, review_item_creation
  validation_status text DEFAULT 'pending',        -- pending, passed, failed, needs_review
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ltlvr_launch_project_id ON launch_test_lead_validation_results(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ltlvr_test_payload_id ON launch_test_lead_validation_results(test_payload_id);
CREATE INDEX IF NOT EXISTS idx_ltlvr_validation_type ON launch_test_lead_validation_results(validation_type);
CREATE INDEX IF NOT EXISTS idx_ltlvr_validation_status ON launch_test_lead_validation_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_ltlvr_created_at ON launch_test_lead_validation_results(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_test_lead_review_items — human review queue for the harness.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_test_lead_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  test_payload_id uuid REFERENCES launch_test_lead_payloads(id),
  validation_result_id uuid REFERENCES launch_test_lead_validation_results(id),
  review_type text,                                -- fake_payload_review, validation_result_review, privacy_review, cleanup_review
  status text DEFAULT 'pending',                   -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ltlri_launch_project_id ON launch_test_lead_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ltlri_test_payload_id ON launch_test_lead_review_items(test_payload_id);
CREATE INDEX IF NOT EXISTS idx_ltlri_review_type ON launch_test_lead_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_ltlri_status ON launch_test_lead_review_items(status);
CREATE INDEX IF NOT EXISTS idx_ltlri_created_at ON launch_test_lead_review_items(created_at);

-- updated_at triggers.
DROP TRIGGER IF EXISTS trg_launch_test_lead_payloads_updated_at ON launch_test_lead_payloads;
CREATE TRIGGER trg_launch_test_lead_payloads_updated_at
BEFORE UPDATE ON launch_test_lead_payloads FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_test_lead_validation_results_updated_at ON launch_test_lead_validation_results;
CREATE TRIGGER trg_launch_test_lead_validation_results_updated_at
BEFORE UPDATE ON launch_test_lead_validation_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_test_lead_review_items_updated_at ON launch_test_lead_review_items;
CREATE TRIGGER trg_launch_test_lead_review_items_updated_at
BEFORE UPDATE ON launch_test_lead_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 4. vw_dlf_test_lead_payload_dashboard (NO fake name/phone/email exposed).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_test_lead_payload_dashboard AS
SELECT
  p.launch_key,
  t.test_key,
  t.payload_status,
  t.payload_type,
  t.uses_fake_data,
  t.creates_real_contact,
  t.creates_real_lead,
  t.external_call_made,
  t.created_at
FROM launch_test_lead_payloads t
JOIN launch_projects p ON p.id = t.launch_project_id;

-- ---------------------------------------------------------------------------
-- 5. vw_dlf_test_lead_validation_dashboard
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_test_lead_validation_dashboard AS
SELECT
  p.launch_key,
  t.test_key,
  v.validation_type,
  v.validation_status,
  v.safe_summary,
  v.created_at
FROM launch_test_lead_validation_results v
JOIN launch_test_lead_payloads t ON t.id = v.test_payload_id
JOIN launch_projects p ON p.id = v.launch_project_id;

-- ---------------------------------------------------------------------------
-- 6. vw_dlf_test_lead_review_queue
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_test_lead_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  t.test_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM launch_test_lead_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN launch_test_lead_payloads t ON t.id = ri.test_payload_id;

-- ---------------------------------------------------------------------------
-- 7. vw_dlf_test_lead_readiness (ready_for_live_lead_capture mirrors the real false gate).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_dlf_test_lead_readiness AS
WITH agg AS (
  SELECT
    p.id, p.launch_key,
    (SELECT count(*) FROM launch_test_lead_payloads t WHERE t.launch_project_id = p.id) AS fake_payloads,
    (SELECT count(*) FROM launch_test_lead_validation_results v WHERE v.launch_project_id = p.id) AS validations_total,
    (SELECT count(*) FROM launch_test_lead_validation_results v WHERE v.launch_project_id = p.id AND v.validation_status = 'passed') AS validations_passed,
    (SELECT count(*) FROM launch_test_lead_validation_results v WHERE v.launch_project_id = p.id AND v.validation_status = 'failed') AS validations_failed,
    (SELECT count(*) FROM launch_test_lead_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS reviews_pending,
    (SELECT count(*) FROM launch_test_lead_payloads t WHERE t.launch_project_id = p.id AND t.creates_real_lead) AS fake_payloads_create_real_lead_count,
    (SELECT count(*) FROM launch_test_lead_payloads t WHERE t.launch_project_id = p.id AND t.creates_real_contact) AS fake_payloads_create_real_contact_count,
    (SELECT count(*) FROM launch_test_lead_payloads t WHERE t.launch_project_id = p.id AND t.external_call_made) AS external_call_made_count,
    COALESCE((SELECT v.ready_for_live_lead_capture FROM vw_dlf_lead_intake_readiness v WHERE v.launch_key = p.launch_key), false) AS real_gate
  FROM launch_projects p
)
SELECT
  launch_key, fake_payloads, validations_total, validations_passed, validations_failed, reviews_pending,
  fake_payloads_create_real_lead_count, fake_payloads_create_real_contact_count, external_call_made_count,
  (real_gate
     AND fake_payloads_create_real_lead_count = 0
     AND fake_payloads_create_real_contact_count = 0
     AND external_call_made_count = 0) AS ready_for_live_lead_capture,
  CASE
    WHEN fake_payloads_create_real_lead_count > 0 OR fake_payloads_create_real_contact_count > 0 OR external_call_made_count > 0
      THEN 'UNSAFE: test residue marked as real-lead/real-contact/external-call — investigate'
    WHEN NOT real_gate
      THEN 'test harness only — live capture requires approved field mappings + active endpoint + operator approval'
    ELSE 'ready'
  END AS blocked_reason
FROM agg;
