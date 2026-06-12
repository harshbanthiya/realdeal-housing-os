-- Phase 7.24: DLF Westpark Wix AI implementation route review.
--
-- Reviews the Phase 7.23 generated Wix AI build artifacts and records the least-manual
-- implementation route. This schema performs NO Wix API call, stores NO Wix API key, creates
-- NO live form/webhook/tracking, publishes nothing, and never changes inbound leads, contacts,
-- sends, or launch-readiness flags.

CREATE TABLE IF NOT EXISTS wix_ai_implementation_route_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  selected_route text,
  route_decision_status text DEFAULT 'pending',
  reason_summary text,
  operator_setup_required boolean DEFAULT true,
  ai_execution_possible boolean DEFAULT true,
  code_artifacts_ready boolean DEFAULT false,
  requires_wix_api_key boolean DEFAULT false,
  requires_publish_permission boolean DEFAULT false,
  requires_live_webhook boolean DEFAULT false,
  requires_tracking boolean DEFAULT false,
  requires_domain_connection boolean DEFAULT false,
  manual_drag_drop_required boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waird_launch_project_id ON wix_ai_implementation_route_decisions(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waird_execution_plan_id ON wix_ai_implementation_route_decisions(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_waird_selected_route ON wix_ai_implementation_route_decisions(selected_route);
CREATE INDEX IF NOT EXISTS idx_waird_route_decision_status ON wix_ai_implementation_route_decisions(route_decision_status);
CREATE INDEX IF NOT EXISTS idx_waird_created_at ON wix_ai_implementation_route_decisions(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_artifact_review_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  execution_plan_id uuid REFERENCES wix_ai_build_execution_plans(id),
  artifact_id uuid REFERENCES wix_ai_build_artifacts(id),
  artifact_key text,
  artifact_type text,
  file_present boolean DEFAULT false,
  review_status text DEFAULT 'pending',
  no_secret_detected boolean DEFAULT false,
  no_api_key_detected boolean DEFAULT false,
  no_webhook_detected boolean DEFAULT false,
  placeholders_preserved boolean DEFAULT false,
  seo_text_in_dom boolean DEFAULT false,
  suitable_for_ai_execution boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wiarr_route_decision_id ON wix_ai_artifact_review_results(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_wiarr_execution_plan_id ON wix_ai_artifact_review_results(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_wiarr_artifact_id ON wix_ai_artifact_review_results(artifact_id);
CREATE INDEX IF NOT EXISTS idx_wiarr_artifact_key ON wix_ai_artifact_review_results(artifact_key);
CREATE INDEX IF NOT EXISTS idx_wiarr_artifact_type ON wix_ai_artifact_review_results(artifact_type);
CREATE INDEX IF NOT EXISTS idx_wiarr_review_status ON wix_ai_artifact_review_results(review_status);
CREATE INDEX IF NOT EXISTS idx_wiarr_created_at ON wix_ai_artifact_review_results(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_operator_setup_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  launch_project_id uuid REFERENCES launch_projects(id),
  task_key text,
  task_order integer,
  task_status text DEFAULT 'pending',
  task_owner text DEFAULT 'operator',
  task_type text,
  instruction text,
  safety_note text,
  minimum_manual_action boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waiost_route_decision_id ON wix_ai_operator_setup_tasks(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_waiost_launch_project_id ON wix_ai_operator_setup_tasks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waiost_task_key ON wix_ai_operator_setup_tasks(task_key);
CREATE INDEX IF NOT EXISTS idx_waiost_task_status ON wix_ai_operator_setup_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_waiost_task_type ON wix_ai_operator_setup_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_waiost_created_at ON wix_ai_operator_setup_tasks(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_execution_package_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  launch_project_id uuid REFERENCES launch_projects(id),
  step_key text,
  step_order integer,
  step_status text DEFAULT 'planned',
  agent_owner text,
  step_type text,
  safe_summary text,
  agent_instruction text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waieps_route_decision_id ON wix_ai_execution_package_steps(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_waieps_launch_project_id ON wix_ai_execution_package_steps(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_waieps_step_key ON wix_ai_execution_package_steps(step_key);
CREATE INDEX IF NOT EXISTS idx_waieps_step_status ON wix_ai_execution_package_steps(step_status);
CREATE INDEX IF NOT EXISTS idx_waieps_step_type ON wix_ai_execution_package_steps(step_type);
CREATE INDEX IF NOT EXISTS idx_waieps_created_at ON wix_ai_execution_package_steps(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_implementation_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  artifact_review_id uuid REFERENCES wix_ai_artifact_review_results(id),
  operator_task_id uuid REFERENCES wix_ai_operator_setup_tasks(id),
  execution_step_id uuid REFERENCES wix_ai_execution_package_steps(id),
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

CREATE INDEX IF NOT EXISTS idx_wairi_launch_project_id ON wix_ai_implementation_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wairi_route_decision_id ON wix_ai_implementation_review_items(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_wairi_artifact_review_id ON wix_ai_implementation_review_items(artifact_review_id);
CREATE INDEX IF NOT EXISTS idx_wairi_operator_task_id ON wix_ai_implementation_review_items(operator_task_id);
CREATE INDEX IF NOT EXISTS idx_wairi_execution_step_id ON wix_ai_implementation_review_items(execution_step_id);
CREATE INDEX IF NOT EXISTS idx_wairi_review_type ON wix_ai_implementation_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_wairi_status ON wix_ai_implementation_review_items(status);
CREATE INDEX IF NOT EXISTS idx_wairi_created_at ON wix_ai_implementation_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_ai_implementation_route_decisions_updated_at ON wix_ai_implementation_route_decisions;
CREATE TRIGGER trg_wix_ai_implementation_route_decisions_updated_at
BEFORE UPDATE ON wix_ai_implementation_route_decisions FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_artifact_review_results_updated_at ON wix_ai_artifact_review_results;
CREATE TRIGGER trg_wix_ai_artifact_review_results_updated_at
BEFORE UPDATE ON wix_ai_artifact_review_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_operator_setup_tasks_updated_at ON wix_ai_operator_setup_tasks;
CREATE TRIGGER trg_wix_ai_operator_setup_tasks_updated_at
BEFORE UPDATE ON wix_ai_operator_setup_tasks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_execution_package_steps_updated_at ON wix_ai_execution_package_steps;
CREATE TRIGGER trg_wix_ai_execution_package_steps_updated_at
BEFORE UPDATE ON wix_ai_execution_package_steps FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_implementation_review_items_updated_at ON wix_ai_implementation_review_items;
CREATE TRIGGER trg_wix_ai_implementation_review_items_updated_at
BEFORE UPDATE ON wix_ai_implementation_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_ai_implementation_route_decision_dashboard AS
SELECT
  p.launch_key,
  e.execution_key,
  rd.selected_route,
  rd.route_decision_status,
  rd.operator_setup_required,
  rd.ai_execution_possible,
  rd.code_artifacts_ready,
  rd.requires_wix_api_key,
  rd.requires_publish_permission,
  rd.requires_live_webhook,
  rd.requires_tracking,
  rd.requires_domain_connection,
  rd.manual_drag_drop_required,
  rd.safe_summary,
  rd.created_at
FROM wix_ai_implementation_route_decisions rd
JOIN launch_projects p ON p.id = rd.launch_project_id
JOIN wix_ai_build_execution_plans e ON e.id = rd.execution_plan_id;

CREATE OR REPLACE VIEW vw_wix_ai_artifact_review_dashboard AS
SELECT
  p.launch_key,
  rd.selected_route,
  ar.artifact_key,
  ar.artifact_type,
  ar.file_present,
  ar.review_status,
  ar.no_secret_detected,
  ar.no_api_key_detected,
  ar.no_webhook_detected,
  ar.placeholders_preserved,
  ar.seo_text_in_dom,
  ar.suitable_for_ai_execution,
  ar.safe_summary
FROM wix_ai_artifact_review_results ar
JOIN wix_ai_implementation_route_decisions rd ON rd.id = ar.route_decision_id
JOIN launch_projects p ON p.id = rd.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_operator_setup_task_dashboard AS
SELECT
  p.launch_key,
  rd.selected_route,
  t.task_key,
  t.task_order,
  t.task_status,
  t.task_owner,
  t.task_type,
  t.minimum_manual_action,
  t.safety_note
FROM wix_ai_operator_setup_tasks t
JOIN wix_ai_implementation_route_decisions rd ON rd.id = t.route_decision_id
JOIN launch_projects p ON p.id = t.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_execution_package_step_dashboard AS
SELECT
  p.launch_key,
  rd.selected_route,
  s.step_key,
  s.step_order,
  s.step_status,
  s.agent_owner,
  s.step_type,
  s.safe_summary
FROM wix_ai_execution_package_steps s
JOIN wix_ai_implementation_route_decisions rd ON rd.id = s.route_decision_id
JOIN launch_projects p ON p.id = s.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_ai_implementation_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  rd.selected_route,
  ar.artifact_key,
  t.task_key,
  s.step_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM wix_ai_implementation_review_items ri
JOIN wix_ai_implementation_route_decisions rd ON rd.id = ri.route_decision_id
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN wix_ai_artifact_review_results ar ON ar.id = ri.artifact_review_id
LEFT JOIN wix_ai_operator_setup_tasks t ON t.id = ri.operator_task_id
LEFT JOIN wix_ai_execution_package_steps s ON s.id = ri.execution_step_id;

CREATE OR REPLACE VIEW vw_dlf_wix_ai_implementation_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key FROM launch_projects
),
decision_pick AS (
  SELECT DISTINCT ON (launch_project_id)
    *
  FROM wix_ai_implementation_route_decisions
  ORDER BY launch_project_id, created_at DESC
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    d.selected_route,
    d.route_decision_status,
    count(DISTINCT ar.id) AS artifact_reviews,
    count(DISTINCT ar.id) FILTER (WHERE ar.review_status = 'passed') AS artifact_reviews_passed,
    count(DISTINCT ar.id) FILTER (WHERE ar.review_status = 'needs_more_info') AS artifact_reviews_needs_more_info,
    count(DISTINCT t.id) AS operator_tasks,
    count(DISTINCT t.id) FILTER (WHERE t.task_status = 'pending') AS operator_tasks_pending,
    count(DISTINCT s.id) AS ai_execution_steps,
    count(DISTINCT s.id) FILTER (WHERE s.step_status = 'ready_for_ai') AS ai_execution_steps_ready,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS implementation_reviews_pending,
    count(DISTINCT d.id) FILTER (WHERE d.code_artifacts_ready) AS code_artifacts_ready_count,
    count(DISTINCT d.id) FILTER (WHERE d.ai_execution_possible) AS ai_execution_possible_count,
    count(DISTINCT d.id) FILTER (WHERE d.manual_drag_drop_required) AS manual_drag_drop_required_count,
    count(DISTINCT d.id) FILTER (WHERE d.requires_wix_api_key) AS requires_wix_api_key_count,
    count(DISTINCT d.id) FILTER (WHERE d.requires_publish_permission) AS requires_publish_permission_count,
    count(DISTINCT d.id) FILTER (WHERE d.requires_live_webhook) AS requires_live_webhook_count
  FROM launch_scope p
  LEFT JOIN decision_pick d ON d.launch_project_id = p.id
  LEFT JOIN wix_ai_artifact_review_results ar ON ar.route_decision_id = d.id
  LEFT JOIN wix_ai_operator_setup_tasks t ON t.route_decision_id = d.id
  LEFT JOIN wix_ai_execution_package_steps s ON s.route_decision_id = d.id
  LEFT JOIN wix_ai_implementation_review_items ri ON ri.route_decision_id = d.id
  GROUP BY p.id, p.launch_key, d.selected_route, d.route_decision_status
)
SELECT
  launch_key,
  selected_route,
  route_decision_status,
  artifact_reviews,
  artifact_reviews_passed,
  artifact_reviews_needs_more_info,
  operator_tasks,
  operator_tasks_pending,
  ai_execution_steps,
  ai_execution_steps_ready,
  implementation_reviews_pending,
  code_artifacts_ready_count,
  ai_execution_possible_count,
  manual_drag_drop_required_count,
  requires_wix_api_key_count,
  requires_publish_permission_count,
  requires_live_webhook_count,
  (
    selected_route IS NOT NULL
    AND artifact_reviews > 0
    AND artifact_reviews_needs_more_info = 0
    AND code_artifacts_ready_count > 0
    AND ai_execution_possible_count > 0
    AND manual_drag_drop_required_count = 0
    AND requires_wix_api_key_count = 0
    AND requires_publish_permission_count = 0
    AND requires_live_webhook_count = 0
  ) AS ready_for_operator_setup,
  (
    route_decision_status = 'ready_for_ai_execution_after_setup'
    AND operator_tasks_pending = 0
    AND implementation_reviews_pending = 0
    AND ai_execution_steps_ready > 0
    AND manual_drag_drop_required_count = 0
    AND requires_wix_api_key_count = 0
    AND requires_publish_permission_count = 0
    AND requires_live_webhook_count = 0
  ) AS ready_for_ai_execution_after_setup,
  (
    route_decision_status IN ('ready_for_ai_execution_after_setup', 'approved_for_operator_setup')
    AND implementation_reviews_pending = 0
    AND ai_execution_steps_ready > 0
    AND manual_drag_drop_required_count = 0
    AND requires_wix_api_key_count = 0
    AND requires_publish_permission_count = 0
    AND requires_live_webhook_count = 0
  ) AS ready_for_code_paste_or_sync,
  false AS ready_for_fake_lead_test,
  false AS ready_for_production_publish,
  CASE
    WHEN selected_route IS NULL THEN 'blocked: no implementation route review'
    WHEN requires_wix_api_key_count > 0 THEN 'blocked: route unexpectedly requires Wix API key'
    WHEN requires_publish_permission_count > 0 THEN 'blocked: route unexpectedly requires publish permission'
    WHEN requires_live_webhook_count > 0 THEN 'blocked: route unexpectedly requires live webhook'
    WHEN manual_drag_drop_required_count > 0 THEN 'blocked: route requires manual drag/drop build'
    WHEN artifact_reviews_needs_more_info > 0 THEN 'blocked: generated artifacts need more info'
    WHEN implementation_reviews_pending > 0 THEN 'route and artifacts reviewed; human approval still pending'
    WHEN operator_tasks_pending > 0 THEN 'minimum operator setup remains before AI execution'
    ELSE 'route review cleared for AI-assisted staging implementation; fake lead test and production publish remain blocked'
  END AS blocked_reason
FROM agg;
