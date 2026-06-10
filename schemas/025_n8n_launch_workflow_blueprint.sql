-- Phase 7.4: DLF n8n launch workflow blueprint.
--
-- Review-gated n8n automation architecture only. This migration stores planned
-- workflow blueprints, node/step definitions, payload schemas, fake-only test
-- cases, and review gates without creating n8n workflows, live webhooks, inbound
-- leads, contacts, or outbound communications.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. launch_n8n_workflow_blueprints
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_n8n_workflow_blueprints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  workflow_key text,
  workflow_name text,
  workflow_type text,
  workflow_status text DEFAULT 'planned',
  n8n_workflow_id text,
  activation_status text DEFAULT 'not_created',
  external_call_required boolean DEFAULT false,
  external_call_allowed boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lnwb_workflow_status_check
    CHECK (workflow_status IN ('planned', 'needs_review', 'approved_for_build', 'built_in_n8n', 'active', 'paused', 'archived')),
  CONSTRAINT lnwb_activation_status_check
    CHECK (activation_status IN ('not_created', 'created_inactive', 'active', 'paused'))
);

CREATE INDEX IF NOT EXISTS idx_lnwb_launch_project_id ON launch_n8n_workflow_blueprints(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lnwb_workflow_key ON launch_n8n_workflow_blueprints(workflow_key);
CREATE INDEX IF NOT EXISTS idx_lnwb_workflow_status ON launch_n8n_workflow_blueprints(workflow_status);
CREATE INDEX IF NOT EXISTS idx_lnwb_activation_status ON launch_n8n_workflow_blueprints(activation_status);
CREATE INDEX IF NOT EXISTS idx_lnwb_workflow_type ON launch_n8n_workflow_blueprints(workflow_type);
CREATE INDEX IF NOT EXISTS idx_lnwb_created_at ON launch_n8n_workflow_blueprints(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_n8n_workflow_nodes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_n8n_workflow_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id) ON DELETE CASCADE,
  node_key text,
  node_type text,
  node_order integer,
  node_status text DEFAULT 'planned',
  input_summary text,
  output_summary text,
  failure_behavior text,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lnwn_node_status_check
    CHECK (node_status IN ('planned', 'needs_review', 'approved', 'built', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_lnwn_workflow_blueprint_id ON launch_n8n_workflow_nodes(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_lnwn_node_key ON launch_n8n_workflow_nodes(node_key);
CREATE INDEX IF NOT EXISTS idx_lnwn_node_type ON launch_n8n_workflow_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_lnwn_node_status ON launch_n8n_workflow_nodes(node_status);
CREATE INDEX IF NOT EXISTS idx_lnwn_created_at ON launch_n8n_workflow_nodes(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_n8n_payload_schemas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_n8n_payload_schemas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id) ON DELETE CASCADE,
  schema_key text,
  schema_status text DEFAULT 'draft',
  required_fields jsonb DEFAULT '[]'::jsonb,
  optional_fields jsonb DEFAULT '[]'::jsonb,
  pii_fields jsonb DEFAULT '[]'::jsonb,
  consent_fields jsonb DEFAULT '[]'::jsonb,
  utm_fields jsonb DEFAULT '[]'::jsonb,
  validation_rules jsonb DEFAULT '[]'::jsonb,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lnps_schema_status_check
    CHECK (schema_status IN ('draft', 'needs_review', 'approved', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_lnps_workflow_blueprint_id ON launch_n8n_payload_schemas(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_lnps_schema_key ON launch_n8n_payload_schemas(schema_key);
CREATE INDEX IF NOT EXISTS idx_lnps_schema_status ON launch_n8n_payload_schemas(schema_status);
CREATE INDEX IF NOT EXISTS idx_lnps_created_at ON launch_n8n_payload_schemas(created_at);

-- ---------------------------------------------------------------------------
-- 4. launch_n8n_test_cases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_n8n_test_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id) ON DELETE CASCADE,
  test_key text,
  test_status text DEFAULT 'draft',
  fake_payload_summary text,
  expected_result text,
  uses_fake_data boolean DEFAULT true,
  creates_real_lead boolean DEFAULT false,
  external_call_allowed boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT lntc_test_status_check
    CHECK (test_status IN ('draft', 'needs_review', 'approved', 'executed', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_lntc_workflow_blueprint_id ON launch_n8n_test_cases(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_lntc_test_key ON launch_n8n_test_cases(test_key);
CREATE INDEX IF NOT EXISTS idx_lntc_test_status ON launch_n8n_test_cases(test_status);
CREATE INDEX IF NOT EXISTS idx_lntc_created_at ON launch_n8n_test_cases(created_at);

-- ---------------------------------------------------------------------------
-- 5. launch_n8n_review_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_n8n_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id) ON DELETE CASCADE,
  workflow_node_id uuid REFERENCES launch_n8n_workflow_nodes(id) ON DELETE CASCADE,
  payload_schema_id uuid REFERENCES launch_n8n_payload_schemas(id) ON DELETE CASCADE,
  test_case_id uuid REFERENCES launch_n8n_test_cases(id) ON DELETE CASCADE,
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
  CONSTRAINT lnri_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'needs_more_info', 'skipped')),
  CONSTRAINT lnri_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE INDEX IF NOT EXISTS idx_lnri_launch_project_id ON launch_n8n_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lnri_workflow_blueprint_id ON launch_n8n_review_items(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_lnri_workflow_node_id ON launch_n8n_review_items(workflow_node_id);
CREATE INDEX IF NOT EXISTS idx_lnri_payload_schema_id ON launch_n8n_review_items(payload_schema_id);
CREATE INDEX IF NOT EXISTS idx_lnri_test_case_id ON launch_n8n_review_items(test_case_id);
CREATE INDEX IF NOT EXISTS idx_lnri_review_type ON launch_n8n_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_lnri_status ON launch_n8n_review_items(status);
CREATE INDEX IF NOT EXISTS idx_lnri_created_at ON launch_n8n_review_items(created_at);

DROP TRIGGER IF EXISTS trg_launch_n8n_workflow_blueprints_updated_at ON launch_n8n_workflow_blueprints;
CREATE TRIGGER trg_launch_n8n_workflow_blueprints_updated_at
BEFORE UPDATE ON launch_n8n_workflow_blueprints
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_workflow_nodes_updated_at ON launch_n8n_workflow_nodes;
CREATE TRIGGER trg_launch_n8n_workflow_nodes_updated_at
BEFORE UPDATE ON launch_n8n_workflow_nodes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_payload_schemas_updated_at ON launch_n8n_payload_schemas;
CREATE TRIGGER trg_launch_n8n_payload_schemas_updated_at
BEFORE UPDATE ON launch_n8n_payload_schemas
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_test_cases_updated_at ON launch_n8n_test_cases;
CREATE TRIGGER trg_launch_n8n_test_cases_updated_at
BEFORE UPDATE ON launch_n8n_test_cases
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_review_items_updated_at ON launch_n8n_review_items;
CREATE TRIGGER trg_launch_n8n_review_items_updated_at
BEFORE UPDATE ON launch_n8n_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Read-only dashboards. No raw payload values, secrets, or live webhook data.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_launch_n8n_workflow_blueprint_dashboard AS
SELECT
  p.launch_key,
  b.workflow_key,
  b.workflow_name,
  b.workflow_type,
  b.workflow_status,
  b.activation_status,
  b.external_call_required,
  b.external_call_allowed,
  b.human_review_required,
  (SELECT count(*) FROM launch_n8n_workflow_nodes n WHERE n.workflow_blueprint_id = b.id) AS node_count,
  (SELECT count(*) FROM launch_n8n_review_items ri WHERE ri.workflow_blueprint_id = b.id AND ri.status = 'pending') AS pending_reviews
FROM launch_n8n_workflow_blueprints b
JOIN launch_projects p ON p.id = b.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_n8n_node_dashboard AS
SELECT
  p.launch_key,
  b.workflow_key,
  n.node_key,
  n.node_type,
  n.node_order,
  n.node_status,
  n.failure_behavior,
  n.human_review_required
FROM launch_n8n_workflow_nodes n
JOIN launch_n8n_workflow_blueprints b ON b.id = n.workflow_blueprint_id
JOIN launch_projects p ON p.id = b.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_n8n_payload_schema_dashboard AS
SELECT
  p.launch_key,
  b.workflow_key,
  s.schema_key,
  s.schema_status,
  jsonb_array_length(s.required_fields) AS required_field_count,
  jsonb_array_length(s.optional_fields) AS optional_field_count,
  jsonb_array_length(s.pii_fields) AS pii_field_count,
  jsonb_array_length(s.consent_fields) AS consent_field_count,
  jsonb_array_length(s.utm_fields) AS utm_field_count
FROM launch_n8n_payload_schemas s
JOIN launch_n8n_workflow_blueprints b ON b.id = s.workflow_blueprint_id
JOIN launch_projects p ON p.id = b.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_n8n_test_case_dashboard AS
SELECT
  p.launch_key,
  b.workflow_key,
  t.test_key,
  t.test_status,
  t.uses_fake_data,
  t.creates_real_lead,
  t.external_call_allowed
FROM launch_n8n_test_cases t
JOIN launch_n8n_workflow_blueprints b ON b.id = t.workflow_blueprint_id
JOIN launch_projects p ON p.id = b.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_n8n_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  b.workflow_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM launch_n8n_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN launch_n8n_workflow_blueprints b ON b.id = ri.workflow_blueprint_id;

CREATE OR REPLACE VIEW vw_dlf_n8n_readiness AS
WITH agg AS (
  SELECT
    p.id,
    p.launch_key,
    (SELECT count(*) FROM launch_n8n_workflow_blueprints b WHERE b.launch_project_id = p.id) AS workflow_blueprints,
    (SELECT count(*) FROM launch_n8n_workflow_blueprints b WHERE b.launch_project_id = p.id AND b.workflow_status = 'approved_for_build') AS workflows_approved_for_build,
    (SELECT count(*) FROM launch_n8n_workflow_blueprints b WHERE b.launch_project_id = p.id AND b.workflow_status = 'built_in_n8n') AS workflows_built,
    (SELECT count(*) FROM launch_n8n_workflow_blueprints b WHERE b.launch_project_id = p.id AND (b.workflow_status = 'active' OR b.activation_status = 'active')) AS active_workflows,
    (SELECT count(*) FROM launch_n8n_payload_schemas s JOIN launch_n8n_workflow_blueprints b ON b.id = s.workflow_blueprint_id WHERE b.launch_project_id = p.id) AS payload_schemas,
    (SELECT count(*) FROM launch_n8n_test_cases t JOIN launch_n8n_workflow_blueprints b ON b.id = t.workflow_blueprint_id WHERE b.launch_project_id = p.id) AS test_cases,
    (SELECT count(*) FROM launch_n8n_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS pending_reviews,
    (
      (SELECT count(*) FROM launch_n8n_workflow_blueprints b WHERE b.launch_project_id = p.id AND b.external_call_allowed)
      + (SELECT count(*) FROM launch_n8n_test_cases t JOIN launch_n8n_workflow_blueprints b ON b.id = t.workflow_blueprint_id WHERE b.launch_project_id = p.id AND t.external_call_allowed)
    ) AS external_call_allowed_count
  FROM launch_projects p
  WHERE p.launch_key = 'dlf-westpark-andheri-west'
)
SELECT
  launch_key,
  workflow_blueprints,
  workflows_approved_for_build,
  workflows_built,
  active_workflows,
  payload_schemas,
  test_cases,
  pending_reviews,
  external_call_allowed_count,
  (workflow_blueprints > 0 AND workflows_approved_for_build = workflow_blueprints
   AND pending_reviews = 0 AND external_call_allowed_count = 0) AS ready_to_build_in_n8n,
  false AS ready_to_activate,
  CASE
    WHEN active_workflows > 0 THEN 'active workflow detected; Phase 7.4 must remain blueprint-only'
    WHEN external_call_allowed_count > 0 THEN 'external calls are allowed; Phase 7.4 requires all external calls disabled'
    WHEN workflow_blueprints = 0 THEN 'no workflow blueprints planned'
    WHEN pending_reviews > 0 THEN 'n8n blueprint review items are pending'
    WHEN workflows_approved_for_build < workflow_blueprints THEN 'workflow blueprints are not approved for build'
    ELSE 'activation intentionally blocked until a later phase'
  END AS blocked_reason
FROM agg;
