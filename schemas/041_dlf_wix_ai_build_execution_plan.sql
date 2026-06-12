-- Phase 7.23: DLF Westpark Wix AI build execution plan.
--
-- Creates a review-gated, AI-executable implementation plan for building the blank Wix Studio
-- staging site from the approved Gallery White direction. This schema performs NO Wix API call,
-- stores NO Wix API key, creates NO live form/webhook/tracking, publishes nothing, and never
-- changes inbound leads, contacts, sends, or production-readiness flags.

CREATE TABLE IF NOT EXISTS wix_ai_build_execution_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  wix_staging_site_id uuid REFERENCES wix_staging_sites(id),
  execution_key text,
  execution_status text DEFAULT 'planned',
  preferred_route text,
  fallback_route text,
  requires_human_setup boolean DEFAULT true,
  requires_wix_api_key boolean DEFAULT false,
  requires_wix_cli boolean DEFAULT false,
  requires_github_connection boolean DEFAULT false,
  requires_custom_element boolean DEFAULT false,
  requires_code_paste boolean DEFAULT false,
  wix_api_call_made boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  publish_enabled boolean DEFAULT false,
  live_webhook_created boolean DEFAULT false,
  permission_analysis_summary text,
  required_permissions_now jsonb DEFAULT '[]'::jsonb,
  required_permissions_later jsonb DEFAULT '[]'::jsonb,
  forbidden_permissions_now jsonb DEFAULT '[]'::jsonb,
  recommended_key_profile_for_route text,
  route_blockers jsonb DEFAULT '[]'::jsonb,
  operator_setup_needed jsonb DEFAULT '[]'::jsonb,
  safe_summary text,
  operator_setup_instructions text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waibep_launch_project_id ON wix_ai_build_execution_plans(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waibep_staging_site_id ON wix_ai_build_execution_plans(wix_staging_site_id);
CREATE INDEX IF NOT EXISTS idx_waibep_execution_key ON wix_ai_build_execution_plans(execution_key);
CREATE INDEX IF NOT EXISTS idx_waibep_execution_status ON wix_ai_build_execution_plans(execution_status);
CREATE INDEX IF NOT EXISTS idx_waibep_preferred_route ON wix_ai_build_execution_plans(preferred_route);
CREATE INDEX IF NOT EXISTS idx_waibep_created_at ON wix_ai_build_execution_plans(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_build_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  launch_project_id uuid REFERENCES launch_projects(id),
  artifact_key text,
  artifact_type text,
  artifact_status text DEFAULT 'generated',
  artifact_path text,
  contains_private_contact_data boolean DEFAULT false,
  contains_secrets boolean DEFAULT false,
  contains_api_key boolean DEFAULT false,
  contains_live_webhook boolean DEFAULT false,
  publish_enabled boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waiba_execution_plan_id ON wix_ai_build_artifacts(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_waiba_launch_project_id ON wix_ai_build_artifacts(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waiba_artifact_key ON wix_ai_build_artifacts(artifact_key);
CREATE INDEX IF NOT EXISTS idx_waiba_artifact_type ON wix_ai_build_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_waiba_artifact_status ON wix_ai_build_artifacts(artifact_status);
CREATE INDEX IF NOT EXISTS idx_waiba_created_at ON wix_ai_build_artifacts(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_build_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  launch_project_id uuid REFERENCES launch_projects(id),
  step_key text,
  step_order integer,
  step_owner text,
  step_status text DEFAULT 'planned',
  step_type text,
  safe_summary text,
  operator_instruction text,
  agent_instruction text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waibs_execution_plan_id ON wix_ai_build_steps(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_waibs_launch_project_id ON wix_ai_build_steps(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waibs_step_key ON wix_ai_build_steps(step_key);
CREATE INDEX IF NOT EXISTS idx_waibs_step_status ON wix_ai_build_steps(step_status);
CREATE INDEX IF NOT EXISTS idx_waibs_step_type ON wix_ai_build_steps(step_type);
CREATE INDEX IF NOT EXISTS idx_waibs_created_at ON wix_ai_build_steps(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_build_validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  artifact_id uuid REFERENCES wix_ai_build_artifacts(id),
  validation_type text,
  validation_status text DEFAULT 'pending',
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waibvr_execution_plan_id ON wix_ai_build_validation_results(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_waibvr_artifact_id ON wix_ai_build_validation_results(artifact_id);
CREATE INDEX IF NOT EXISTS idx_waibvr_validation_type ON wix_ai_build_validation_results(validation_type);
CREATE INDEX IF NOT EXISTS idx_waibvr_validation_status ON wix_ai_build_validation_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_waibvr_created_at ON wix_ai_build_validation_results(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_build_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  artifact_id uuid REFERENCES wix_ai_build_artifacts(id),
  validation_result_id uuid REFERENCES wix_ai_build_validation_results(id),
  build_step_id uuid REFERENCES wix_ai_build_steps(id),
  review_type text,
  status text DEFAULT 'pending',
  priority text DEFAULT 'normal',
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waibri_launch_project_id ON wix_ai_build_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waibri_execution_plan_id ON wix_ai_build_review_items(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_waibri_artifact_id ON wix_ai_build_review_items(artifact_id);
CREATE INDEX IF NOT EXISTS idx_waibri_validation_result_id ON wix_ai_build_review_items(validation_result_id);
CREATE INDEX IF NOT EXISTS idx_waibri_build_step_id ON wix_ai_build_review_items(build_step_id);
CREATE INDEX IF NOT EXISTS idx_waibri_review_type ON wix_ai_build_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_waibri_status ON wix_ai_build_review_items(status);
CREATE INDEX IF NOT EXISTS idx_waibri_created_at ON wix_ai_build_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_ai_build_execution_plans_updated_at ON wix_ai_build_execution_plans;
CREATE TRIGGER trg_wix_ai_build_execution_plans_updated_at
BEFORE UPDATE ON wix_ai_build_execution_plans FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_build_artifacts_updated_at ON wix_ai_build_artifacts;
CREATE TRIGGER trg_wix_ai_build_artifacts_updated_at
BEFORE UPDATE ON wix_ai_build_artifacts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_build_steps_updated_at ON wix_ai_build_steps;
CREATE TRIGGER trg_wix_ai_build_steps_updated_at
BEFORE UPDATE ON wix_ai_build_steps FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_build_validation_results_updated_at ON wix_ai_build_validation_results;
CREATE TRIGGER trg_wix_ai_build_validation_results_updated_at
BEFORE UPDATE ON wix_ai_build_validation_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_build_review_items_updated_at ON wix_ai_build_review_items;
CREATE TRIGGER trg_wix_ai_build_review_items_updated_at
BEFORE UPDATE ON wix_ai_build_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_ai_build_execution_plan_dashboard AS
SELECT
  p.launch_key,
  e.execution_key,
  e.execution_status,
  e.preferred_route,
  e.fallback_route,
  e.requires_human_setup,
  e.requires_wix_api_key,
  e.requires_wix_cli,
  e.requires_github_connection,
  e.requires_custom_element,
  e.requires_code_paste,
  e.wix_api_call_made,
  e.external_call_made,
  e.publish_enabled,
  e.live_webhook_created,
  e.recommended_key_profile_for_route,
  e.safe_summary,
  e.created_at
FROM wix_ai_build_execution_plans e
JOIN launch_projects p ON p.id = e.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_build_artifact_dashboard AS
SELECT
  p.launch_key,
  e.execution_key,
  a.artifact_key,
  a.artifact_type,
  a.artifact_status,
  a.artifact_path,
  a.contains_private_contact_data,
  a.contains_secrets,
  a.contains_api_key,
  a.contains_live_webhook,
  a.publish_enabled,
  a.safe_summary
FROM wix_ai_build_artifacts a
JOIN wix_ai_build_execution_plans e ON e.id = a.execution_plan_id
JOIN launch_projects p ON p.id = a.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_build_step_dashboard AS
SELECT
  p.launch_key,
  e.execution_key,
  s.step_key,
  s.step_order,
  s.step_owner,
  s.step_status,
  s.step_type,
  s.safe_summary
FROM wix_ai_build_steps s
JOIN wix_ai_build_execution_plans e ON e.id = s.execution_plan_id
JOIN launch_projects p ON p.id = s.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_build_validation_dashboard AS
SELECT
  p.launch_key,
  e.execution_key,
  a.artifact_key,
  v.validation_type,
  v.validation_status,
  v.safe_summary
FROM wix_ai_build_validation_results v
JOIN wix_ai_build_execution_plans e ON e.id = v.execution_plan_id
LEFT JOIN wix_ai_build_artifacts a ON a.id = v.artifact_id
JOIN launch_projects p ON p.id = e.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_build_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  e.execution_key,
  a.artifact_key,
  s.step_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM wix_ai_build_review_items ri
JOIN wix_ai_build_execution_plans e ON e.id = ri.execution_plan_id
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN wix_ai_build_artifacts a ON a.id = ri.artifact_id
LEFT JOIN wix_ai_build_steps s ON s.id = ri.build_step_id;

CREATE OR REPLACE VIEW vw_dlf_wix_ai_build_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key FROM launch_projects
),
plan_pick AS (
  SELECT DISTINCT ON (launch_project_id)
    *
  FROM wix_ai_build_execution_plans
  ORDER BY launch_project_id, created_at DESC
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    pp.preferred_route,
    pp.execution_status,
    count(DISTINCT e.id) AS execution_plans,
    count(DISTINCT a.id) AS artifacts,
    count(DISTINCT a.id) FILTER (WHERE a.artifact_status IN ('generated', 'needs_review', 'approved_for_use')) AS generated_artifacts,
    count(DISTINCT s.id) AS build_steps,
    count(DISTINCT s.id) FILTER (WHERE s.step_status = 'ready_for_agent') AS ready_for_agent_steps,
    count(DISTINCT v.id) AS validations,
    count(DISTINCT v.id) FILTER (WHERE v.validation_status = 'failed') AS validation_failures,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    count(DISTINCT e.id) FILTER (WHERE e.wix_api_call_made) AS wix_api_call_made_count,
    count(DISTINCT e.id) FILTER (WHERE e.external_call_made) AS external_call_made_count,
    count(DISTINCT e.id) FILTER (WHERE e.publish_enabled) AS publish_enabled_count,
    count(DISTINCT e.id) FILTER (WHERE e.live_webhook_created) AS live_webhook_created_count
  FROM launch_scope p
  LEFT JOIN plan_pick pp ON pp.launch_project_id = p.id
  LEFT JOIN wix_ai_build_execution_plans e ON e.launch_project_id = p.id
  LEFT JOIN wix_ai_build_artifacts a ON a.launch_project_id = p.id
  LEFT JOIN wix_ai_build_steps s ON s.launch_project_id = p.id
  LEFT JOIN wix_ai_build_validation_results v ON v.execution_plan_id = e.id
  LEFT JOIN wix_ai_build_review_items ri ON ri.launch_project_id = p.id
  GROUP BY p.id, p.launch_key, pp.preferred_route, pp.execution_status
)
SELECT
  launch_key,
  execution_plans,
  preferred_route,
  execution_status,
  artifacts,
  generated_artifacts,
  build_steps,
  ready_for_agent_steps,
  validations,
  validation_failures,
  pending_reviews,
  wix_api_call_made_count,
  external_call_made_count,
  publish_enabled_count,
  live_webhook_created_count,
  (
    execution_plans > 0
    AND generated_artifacts > 0
    AND validations > 0
    AND validation_failures = 0
    AND wix_api_call_made_count = 0
    AND external_call_made_count = 0
    AND publish_enabled_count = 0
    AND live_webhook_created_count = 0
  ) AS ready_for_code_review,
  (
    execution_plans > 0
    AND execution_status IN ('needs_operator_setup', 'ready_for_local_code_build', 'ready_for_custom_element_build', 'ready_for_snippet_paste')
    AND wix_api_call_made_count = 0
    AND external_call_made_count = 0
    AND publish_enabled_count = 0
    AND live_webhook_created_count = 0
  ) AS ready_for_operator_setup,
  (
    generated_artifacts > 0
    AND validations > 0
    AND validation_failures = 0
    AND pending_reviews = 0
    AND wix_api_call_made_count = 0
    AND external_call_made_count = 0
    AND publish_enabled_count = 0
    AND live_webhook_created_count = 0
  ) AS ready_for_wix_implementation,
  false AS ready_for_fake_lead_test,
  CASE
    WHEN wix_api_call_made_count > 0 THEN 'blocked: Wix API call recorded'
    WHEN external_call_made_count > 0 THEN 'blocked: external call recorded'
    WHEN publish_enabled_count > 0 THEN 'blocked: publish enabled'
    WHEN live_webhook_created_count > 0 THEN 'blocked: live webhook created'
    WHEN execution_plans = 0 THEN 'blocked: no AI build execution plan'
    WHEN generated_artifacts = 0 THEN 'AI build route planned; generated artifacts pending'
    WHEN validation_failures > 0 THEN 'generated artifacts have validation failures'
    WHEN pending_reviews > 0 THEN 'generated artifacts ready for human code/route review; Wix implementation waits for approval'
    ELSE 'generated artifacts validated and reviewed; implementation may proceed in staging only; fake lead test remains blocked'
  END AS blocked_reason
FROM agg;
