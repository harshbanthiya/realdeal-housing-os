-- Phase 7.3: DLF lead intake and attribution planning.
--
-- Review-gated Wix/n8n lead-intake foundation only. This migration defines planned
-- endpoints, form-to-lead field mappings, attribution rules, inbound-lead review
-- queues, and daily operator metrics without creating live webhooks or enabling
-- external calls. No contacts or inbound leads are created by this schema.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. launch_lead_intake_endpoints
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_intake_endpoints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  endpoint_key text,
  endpoint_type text,
  endpoint_status text DEFAULT 'planned',
  planned_url text,
  webhook_path text,
  source_channel text,
  form_key text,
  external_call_required boolean DEFAULT false,
  external_call_allowed boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT llie_endpoint_status_check
    CHECK (endpoint_status IN ('planned', 'needs_review', 'approved', 'active', 'paused', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_llie_launch_project_id ON launch_lead_intake_endpoints(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llie_endpoint_key ON launch_lead_intake_endpoints(endpoint_key);
CREATE INDEX IF NOT EXISTS idx_llie_endpoint_status ON launch_lead_intake_endpoints(endpoint_status);
CREATE INDEX IF NOT EXISTS idx_llie_source_channel ON launch_lead_intake_endpoints(source_channel);
CREATE INDEX IF NOT EXISTS idx_llie_created_at ON launch_lead_intake_endpoints(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_lead_field_mappings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_field_mappings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  lead_capture_form_id uuid REFERENCES launch_lead_capture_forms(id),
  field_key text,
  field_label text,
  target_table text,
  target_field text,
  field_type text,
  required boolean DEFAULT false,
  pii_type text,
  validation_rule text,
  mapping_status text DEFAULT 'draft',
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT llfm_mapping_status_check
    CHECK (mapping_status IN ('draft', 'needs_review', 'approved', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_llfm_launch_project_id ON launch_lead_field_mappings(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llfm_lead_capture_form_id ON launch_lead_field_mappings(lead_capture_form_id);
CREATE INDEX IF NOT EXISTS idx_llfm_field_key ON launch_lead_field_mappings(field_key);
CREATE INDEX IF NOT EXISTS idx_llfm_mapping_status ON launch_lead_field_mappings(mapping_status);
CREATE INDEX IF NOT EXISTS idx_llfm_created_at ON launch_lead_field_mappings(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_lead_attribution_rules
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_attribution_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  rule_key text,
  source text,
  medium text,
  campaign_name text,
  content_angle text,
  mapped_channel text,
  mapped_funnel_stage text,
  mapped_segment_key text,
  priority integer DEFAULT 0,
  rule_status text DEFAULT 'draft',
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT llar_rule_status_check
    CHECK (rule_status IN ('draft', 'needs_review', 'approved', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_llar_launch_project_id ON launch_lead_attribution_rules(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llar_rule_key ON launch_lead_attribution_rules(rule_key);
CREATE INDEX IF NOT EXISTS idx_llar_rule_status ON launch_lead_attribution_rules(rule_status);
CREATE INDEX IF NOT EXISTS idx_llar_source ON launch_lead_attribution_rules(source);
CREATE INDEX IF NOT EXISTS idx_llar_created_at ON launch_lead_attribution_rules(created_at);

-- ---------------------------------------------------------------------------
-- 4. launch_inbound_lead_review_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_inbound_lead_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  inbound_lead_id uuid REFERENCES inbound_leads(id),
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
  CONSTRAINT lilri_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'needs_more_info', 'skipped')),
  CONSTRAINT lilri_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE INDEX IF NOT EXISTS idx_lilri_launch_project_id ON launch_inbound_lead_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lilri_inbound_lead_id ON launch_inbound_lead_review_items(inbound_lead_id);
CREATE INDEX IF NOT EXISTS idx_lilri_review_type ON launch_inbound_lead_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_lilri_status ON launch_inbound_lead_review_items(status);
CREATE INDEX IF NOT EXISTS idx_lilri_created_at ON launch_inbound_lead_review_items(created_at);

-- ---------------------------------------------------------------------------
-- 5. launch_operator_daily_metrics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_operator_daily_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  metric_date date,
  leads_new integer DEFAULT 0,
  leads_reviewed integer DEFAULT 0,
  leads_hot integer DEFAULT 0,
  followups_due integer DEFAULT 0,
  site_visits_requested integer DEFAULT 0,
  whatsapp_replies integer DEFAULT 0,
  email_replies integer DEFAULT 0,
  social_inquiries integer DEFAULT 0,
  seo_leads integer DEFAULT 0,
  referral_leads integer DEFAULT 0,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lodm_launch_project_id ON launch_operator_daily_metrics(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lodm_metric_date ON launch_operator_daily_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_lodm_created_at ON launch_operator_daily_metrics(created_at);

DROP TRIGGER IF EXISTS trg_launch_lead_intake_endpoints_updated_at ON launch_lead_intake_endpoints;
CREATE TRIGGER trg_launch_lead_intake_endpoints_updated_at
BEFORE UPDATE ON launch_lead_intake_endpoints
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_lead_field_mappings_updated_at ON launch_lead_field_mappings;
CREATE TRIGGER trg_launch_lead_field_mappings_updated_at
BEFORE UPDATE ON launch_lead_field_mappings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_lead_attribution_rules_updated_at ON launch_lead_attribution_rules;
CREATE TRIGGER trg_launch_lead_attribution_rules_updated_at
BEFORE UPDATE ON launch_lead_attribution_rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_inbound_lead_review_items_updated_at ON launch_inbound_lead_review_items;
CREATE TRIGGER trg_launch_inbound_lead_review_items_updated_at
BEFORE UPDATE ON launch_inbound_lead_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_operator_daily_metrics_updated_at ON launch_operator_daily_metrics;
CREATE TRIGGER trg_launch_operator_daily_metrics_updated_at
BEFORE UPDATE ON launch_operator_daily_metrics
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Read-only dashboards. No raw lead/contact payloads are exposed.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_launch_lead_intake_endpoint_dashboard AS
SELECT
  p.launch_key,
  e.endpoint_key,
  e.endpoint_type,
  e.endpoint_status,
  e.source_channel,
  e.external_call_required,
  e.external_call_allowed,
  e.human_review_required
FROM launch_lead_intake_endpoints e
JOIN launch_projects p ON p.id = e.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_lead_field_mapping_dashboard AS
SELECT
  p.launch_key,
  m.field_key,
  m.field_label,
  m.target_table,
  m.target_field,
  m.field_type,
  m.required,
  m.pii_type,
  m.mapping_status
FROM launch_lead_field_mappings m
JOIN launch_projects p ON p.id = m.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_lead_attribution_rule_dashboard AS
SELECT
  p.launch_key,
  r.rule_key,
  r.source,
  r.medium,
  r.mapped_channel,
  r.mapped_funnel_stage,
  r.mapped_segment_key,
  r.rule_status
FROM launch_lead_attribution_rules r
JOIN launch_projects p ON p.id = r.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_inbound_lead_review_dashboard AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM launch_inbound_lead_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_operator_daily_metrics_dashboard AS
SELECT
  p.launch_key,
  m.metric_date,
  m.leads_new,
  m.leads_reviewed,
  m.leads_hot,
  m.followups_due,
  m.site_visits_requested,
  m.whatsapp_replies,
  m.email_replies,
  m.social_inquiries,
  m.seo_leads,
  m.referral_leads
FROM launch_operator_daily_metrics m
JOIN launch_projects p ON p.id = m.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_lead_intake_readiness AS
WITH agg AS (
  SELECT
    p.id,
    p.launch_key,
    (SELECT count(*) FROM launch_lead_intake_endpoints e WHERE e.launch_project_id = p.id) AS endpoints_planned,
    (SELECT count(*) FROM launch_lead_intake_endpoints e WHERE e.launch_project_id = p.id AND e.endpoint_status = 'active') AS endpoints_active,
    (SELECT count(*) FROM launch_lead_field_mappings m WHERE m.launch_project_id = p.id) AS field_mappings,
    (SELECT count(*) FROM launch_lead_field_mappings m WHERE m.launch_project_id = p.id AND m.mapping_status = 'approved') AS approved_field_mappings,
    (SELECT count(*) FROM launch_lead_attribution_rules r WHERE r.launch_project_id = p.id) AS attribution_rules,
    (SELECT count(*) FROM launch_lead_attribution_rules r WHERE r.launch_project_id = p.id AND r.rule_status = 'approved') AS approved_attribution_rules,
    (SELECT count(*) FROM inbound_leads) AS inbound_leads,
    (SELECT count(*) FROM launch_inbound_lead_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS pending_lead_reviews,
    (SELECT count(*) FROM launch_lead_intake_endpoints e WHERE e.launch_project_id = p.id AND e.external_call_allowed) AS external_call_allowed_count
  FROM launch_projects p
  WHERE p.launch_key = 'dlf-westpark-andheri-west'
)
SELECT
  launch_key,
  endpoints_planned,
  endpoints_active,
  field_mappings,
  approved_field_mappings,
  attribution_rules,
  approved_attribution_rules,
  inbound_leads,
  pending_lead_reviews,
  external_call_allowed_count,
  false AS ready_for_live_lead_capture,
  CASE
    WHEN endpoints_active > 0 THEN 'live endpoint detected; Phase 7.3 must remain planning-only'
    WHEN external_call_allowed_count > 0 THEN 'external calls are allowed; Phase 7.3 requires all external calls disabled'
    WHEN approved_field_mappings = 0 THEN 'field mappings are draft and require human review'
    WHEN approved_attribution_rules = 0 THEN 'attribution rules are draft and require human review'
    WHEN inbound_leads > 0 THEN 'inbound leads exist; live capture still requires separate approval'
    ELSE 'live capture intentionally blocked until a future approval phase'
  END AS blocked_reason
FROM agg;
