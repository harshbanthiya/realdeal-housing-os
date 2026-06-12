-- Phase 7.25: DLF Westpark Wix Git/CLI availability and setup path check.
--
-- Records operator-reported Wix setup capability status and the selected implementation path.
-- This schema performs NO Wix API call, stores NO Wix API key, creates NO live form/webhook/
-- tracking, publishes nothing, and never changes inbound leads, contacts, sends, or launch flags.

CREATE TABLE IF NOT EXISTS wix_ai_setup_availability_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  check_key text,
  check_status text DEFAULT 'pending',
  capability_type text,
  operator_reported boolean DEFAULT true,
  requires_api_key boolean DEFAULT false,
  requires_publish boolean DEFAULT false,
  requires_live_webhook boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wasac_launch_project_id ON wix_ai_setup_availability_checks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wasac_route_decision_id ON wix_ai_setup_availability_checks(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_wasac_check_key ON wix_ai_setup_availability_checks(check_key);
CREATE INDEX IF NOT EXISTS idx_wasac_check_status ON wix_ai_setup_availability_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_wasac_capability_type ON wix_ai_setup_availability_checks(capability_type);
CREATE INDEX IF NOT EXISTS idx_wasac_created_at ON wix_ai_setup_availability_checks(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_selected_execution_paths (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  route_decision_id uuid REFERENCES wix_ai_implementation_route_decisions(id),
  selected_path text,
  path_status text DEFAULT 'pending',
  selection_reason text,
  requires_operator_setup boolean DEFAULT true,
  requires_api_key boolean DEFAULT false,
  requires_publish boolean DEFAULT false,
  requires_live_webhook boolean DEFAULT false,
  requires_tracking boolean DEFAULT false,
  manual_drag_drop_required boolean DEFAULT false,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wasep_launch_project_id ON wix_ai_selected_execution_paths(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wasep_route_decision_id ON wix_ai_selected_execution_paths(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_wasep_selected_path ON wix_ai_selected_execution_paths(selected_path);
CREATE INDEX IF NOT EXISTS idx_wasep_path_status ON wix_ai_selected_execution_paths(path_status);
CREATE INDEX IF NOT EXISTS idx_wasep_created_at ON wix_ai_selected_execution_paths(created_at);

CREATE TABLE IF NOT EXISTS wix_ai_setup_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  availability_check_id uuid REFERENCES wix_ai_setup_availability_checks(id),
  selected_path_id uuid REFERENCES wix_ai_selected_execution_paths(id),
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

CREATE INDEX IF NOT EXISTS idx_wasri_launch_project_id ON wix_ai_setup_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wasri_availability_check_id ON wix_ai_setup_review_items(availability_check_id);
CREATE INDEX IF NOT EXISTS idx_wasri_selected_path_id ON wix_ai_setup_review_items(selected_path_id);
CREATE INDEX IF NOT EXISTS idx_wasri_review_type ON wix_ai_setup_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_wasri_status ON wix_ai_setup_review_items(status);
CREATE INDEX IF NOT EXISTS idx_wasri_created_at ON wix_ai_setup_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_ai_setup_availability_checks_updated_at ON wix_ai_setup_availability_checks;
CREATE TRIGGER trg_wix_ai_setup_availability_checks_updated_at
BEFORE UPDATE ON wix_ai_setup_availability_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_selected_execution_paths_updated_at ON wix_ai_selected_execution_paths;
CREATE TRIGGER trg_wix_ai_selected_execution_paths_updated_at
BEFORE UPDATE ON wix_ai_selected_execution_paths FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ai_setup_review_items_updated_at ON wix_ai_setup_review_items;
CREATE TRIGGER trg_wix_ai_setup_review_items_updated_at
BEFORE UPDATE ON wix_ai_setup_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_ai_setup_availability_dashboard AS
SELECT
  p.launch_key,
  rd.selected_route,
  c.check_key,
  c.capability_type,
  c.check_status,
  c.operator_reported,
  c.requires_api_key,
  c.requires_publish,
  c.requires_live_webhook,
  c.safe_summary,
  c.created_at
FROM wix_ai_setup_availability_checks c
JOIN launch_projects p ON p.id = c.launch_project_id
JOIN wix_ai_implementation_route_decisions rd ON rd.id = c.route_decision_id;

CREATE OR REPLACE VIEW vw_wix_ai_selected_execution_path_dashboard AS
SELECT
  p.launch_key,
  rd.selected_route AS reviewed_route,
  sp.selected_path,
  sp.path_status,
  sp.requires_operator_setup,
  sp.requires_api_key,
  sp.requires_publish,
  sp.requires_live_webhook,
  sp.requires_tracking,
  sp.manual_drag_drop_required,
  sp.safe_summary,
  sp.created_at
FROM wix_ai_selected_execution_paths sp
JOIN launch_projects p ON p.id = sp.launch_project_id
JOIN wix_ai_implementation_route_decisions rd ON rd.id = sp.route_decision_id;

CREATE OR REPLACE VIEW vw_wix_ai_setup_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  c.check_key,
  c.capability_type,
  sp.selected_path,
  sp.path_status,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM wix_ai_setup_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
LEFT JOIN wix_ai_setup_availability_checks c ON c.id = ri.availability_check_id
LEFT JOIN wix_ai_selected_execution_paths sp ON sp.id = ri.selected_path_id;

CREATE OR REPLACE VIEW vw_dlf_wix_ai_setup_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key FROM launch_projects
),
path_pick AS (
  SELECT DISTINCT ON (launch_project_id)
    *
  FROM wix_ai_selected_execution_paths
  ORDER BY launch_project_id, created_at DESC
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    pp.selected_path,
    pp.path_status,
    count(DISTINCT c.id) FILTER (WHERE c.capability_type = 'wix_git_integration' AND c.check_status = 'available') > 0 AS git_integration_available,
    count(DISTINCT c.id) FILTER (WHERE c.capability_type = 'wix_cli_for_sites' AND c.check_status = 'available') > 0 AS wix_cli_available,
    count(DISTINCT c.id) FILTER (WHERE c.capability_type = 'velo_dev_mode' AND c.check_status = 'available') > 0 AS velo_available,
    count(DISTINCT c.id) FILTER (WHERE c.capability_type = 'custom_element' AND c.check_status = 'available') > 0 AS custom_element_available,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    (
      count(DISTINCT c.id) FILTER (WHERE c.requires_api_key)
      + count(DISTINCT pp.id) FILTER (WHERE pp.requires_api_key)
    ) AS requires_api_key_count,
    (
      count(DISTINCT c.id) FILTER (WHERE c.requires_publish)
      + count(DISTINCT pp.id) FILTER (WHERE pp.requires_publish)
    ) AS requires_publish_count,
    (
      count(DISTINCT c.id) FILTER (WHERE c.requires_live_webhook)
      + count(DISTINCT pp.id) FILTER (WHERE pp.requires_live_webhook)
    ) AS requires_live_webhook_count,
    count(DISTINCT pp.id) FILTER (WHERE pp.manual_drag_drop_required) AS manual_drag_drop_required_count
  FROM launch_scope p
  LEFT JOIN path_pick pp ON pp.launch_project_id = p.id
  LEFT JOIN wix_ai_setup_availability_checks c ON c.launch_project_id = p.id
  LEFT JOIN wix_ai_setup_review_items ri ON ri.launch_project_id = p.id
  GROUP BY p.id, p.launch_key, pp.selected_path, pp.path_status
)
SELECT
  launch_key,
  git_integration_available,
  wix_cli_available,
  velo_available,
  custom_element_available,
  selected_path,
  path_status,
  pending_reviews,
  requires_api_key_count,
  requires_publish_count,
  requires_live_webhook_count,
  manual_drag_drop_required_count,
  (
    selected_path IS NOT NULL
    AND path_status IN ('needs_operator_setup', 'needs_more_info')
    AND requires_api_key_count = 0
    AND requires_publish_count = 0
    AND requires_live_webhook_count = 0
    AND manual_drag_drop_required_count = 0
  ) AS ready_for_operator_setup,
  (
    selected_path IS NOT NULL
    AND path_status = 'ready_for_ai_code_execution'
    AND pending_reviews = 0
    AND requires_api_key_count = 0
    AND requires_publish_count = 0
    AND requires_live_webhook_count = 0
    AND manual_drag_drop_required_count = 0
  ) AS ready_for_ai_code_execution,
  false AS ready_for_fake_lead_test,
  false AS ready_for_production_publish,
  CASE
    WHEN selected_path IS NULL THEN 'blocked: no setup availability check recorded'
    WHEN requires_api_key_count > 0 THEN 'blocked: setup path unexpectedly requires Wix API key'
    WHEN requires_publish_count > 0 THEN 'blocked: setup path unexpectedly requires publish'
    WHEN requires_live_webhook_count > 0 THEN 'blocked: setup path unexpectedly requires live webhook'
    WHEN manual_drag_drop_required_count > 0 THEN 'blocked: all AI implementation paths failed'
    WHEN path_status = 'needs_more_info' THEN 'operator must check Wix Studio capability before selecting setup path'
    WHEN pending_reviews > 0 THEN 'setup path recorded; review still pending before AI code execution'
    WHEN path_status = 'needs_operator_setup' THEN 'minimum operator setup remains before AI code execution'
    WHEN path_status = 'ready_for_ai_code_execution' THEN 'ready for AI-assisted code execution in staging only'
    ELSE 'setup path recorded but not ready'
  END AS blocked_reason
FROM agg;
