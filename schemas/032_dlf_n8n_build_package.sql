-- Phase 7.11: DLF inactive n8n workflow build package tracking.
--
-- Tracks local/importable workflow template artifacts without creating anything
-- in n8n, without live webhooks, and without credentials. This schema only
-- creates tracking/review tables and count-safe dashboards.

CREATE TABLE IF NOT EXISTS launch_n8n_build_packages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id),
  package_key text,
  package_status text DEFAULT 'draft',
  artifact_path text,
  artifact_type text DEFAULT 'n8n_workflow_template_json',
  contains_credentials boolean DEFAULT false,
  contains_webhook_secret boolean DEFAULT false,
  contains_live_webhook_url boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  workflow_created_in_n8n boolean DEFAULT false,
  activation_requested boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ln8nbp_launch_project_id ON launch_n8n_build_packages(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbp_workflow_blueprint_id ON launch_n8n_build_packages(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbp_package_key ON launch_n8n_build_packages(package_key);
CREATE INDEX IF NOT EXISTS idx_ln8nbp_package_status ON launch_n8n_build_packages(package_status);
CREATE INDEX IF NOT EXISTS idx_ln8nbp_created_at ON launch_n8n_build_packages(created_at);

CREATE TABLE IF NOT EXISTS launch_n8n_build_validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  build_package_id uuid REFERENCES launch_n8n_build_packages(id),
  validation_type text,
  validation_status text DEFAULT 'pending',
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ln8nbvr_build_package_id ON launch_n8n_build_validation_results(build_package_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbvr_validation_type ON launch_n8n_build_validation_results(validation_type);
CREATE INDEX IF NOT EXISTS idx_ln8nbvr_validation_status ON launch_n8n_build_validation_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_ln8nbvr_created_at ON launch_n8n_build_validation_results(created_at);

CREATE TABLE IF NOT EXISTS launch_n8n_build_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  build_package_id uuid REFERENCES launch_n8n_build_packages(id),
  validation_result_id uuid REFERENCES launch_n8n_build_validation_results(id),
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

CREATE INDEX IF NOT EXISTS idx_ln8nbri_launch_project_id ON launch_n8n_build_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbri_build_package_id ON launch_n8n_build_review_items(build_package_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbri_validation_result_id ON launch_n8n_build_review_items(validation_result_id);
CREATE INDEX IF NOT EXISTS idx_ln8nbri_review_type ON launch_n8n_build_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_ln8nbri_status ON launch_n8n_build_review_items(status);
CREATE INDEX IF NOT EXISTS idx_ln8nbri_created_at ON launch_n8n_build_review_items(created_at);

DROP TRIGGER IF EXISTS trg_launch_n8n_build_packages_updated_at ON launch_n8n_build_packages;
CREATE TRIGGER trg_launch_n8n_build_packages_updated_at
BEFORE UPDATE ON launch_n8n_build_packages FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_build_validation_results_updated_at ON launch_n8n_build_validation_results;
CREATE TRIGGER trg_launch_n8n_build_validation_results_updated_at
BEFORE UPDATE ON launch_n8n_build_validation_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_n8n_build_review_items_updated_at ON launch_n8n_build_review_items;
CREATE TRIGGER trg_launch_n8n_build_review_items_updated_at
BEFORE UPDATE ON launch_n8n_build_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_dlf_n8n_build_package_dashboard AS
SELECT
  p.launch_key,
  bp.package_key,
  bp.package_status,
  bp.artifact_type,
  bp.contains_credentials,
  bp.contains_webhook_secret,
  bp.contains_live_webhook_url,
  bp.external_call_made,
  bp.workflow_created_in_n8n,
  bp.activation_requested,
  bp.human_review_required
FROM launch_n8n_build_packages bp
JOIN launch_projects p ON p.id = bp.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_n8n_build_validation_dashboard AS
SELECT
  p.launch_key,
  bp.package_key,
  vr.validation_type,
  vr.validation_status,
  vr.safe_summary
FROM launch_n8n_build_validation_results vr
JOIN launch_n8n_build_packages bp ON bp.id = vr.build_package_id
JOIN launch_projects p ON p.id = bp.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_n8n_build_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  bp.package_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM launch_n8n_build_review_items ri
JOIN launch_n8n_build_packages bp ON bp.id = ri.build_package_id
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_n8n_build_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    count(DISTINCT bp.id) AS build_packages,
    count(DISTINCT bp.id) FILTER (WHERE bp.package_status = 'validated') AS packages_validated,
    count(DISTINCT vr.id) FILTER (WHERE vr.validation_status = 'failed') AS validation_failures,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    count(DISTINCT bp.id) FILTER (WHERE bp.package_status = 'approved_for_manual_import') AS packages_approved_for_manual_import,
    count(DISTINCT bp.id) FILTER (WHERE bp.workflow_created_in_n8n IS TRUE) AS workflows_created_in_n8n,
    (
      SELECT count(*)
      FROM launch_n8n_workflow_blueprints wb
      WHERE wb.launch_project_id = p.id
        AND wb.activation_status = 'active'
    ) AS active_workflows,
    count(DISTINCT bp.id) FILTER (
      WHERE bp.contains_credentials IS TRUE
         OR bp.contains_webhook_secret IS TRUE
         OR bp.contains_live_webhook_url IS TRUE
         OR bp.external_call_made IS TRUE
         OR bp.activation_requested IS TRUE
    ) AS unsafe_package_flags
  FROM launch_scope p
  LEFT JOIN launch_n8n_build_packages bp ON bp.launch_project_id = p.id
  LEFT JOIN launch_n8n_build_validation_results vr ON vr.build_package_id = bp.id
  LEFT JOIN launch_n8n_build_review_items ri ON ri.build_package_id = bp.id
  GROUP BY p.id, p.launch_key
)
SELECT
  launch_key,
  build_packages,
  packages_validated,
  validation_failures,
  pending_reviews,
  packages_approved_for_manual_import,
  workflows_created_in_n8n,
  active_workflows,
  (
    build_packages > 0
    AND packages_approved_for_manual_import > 0
    AND validation_failures = 0
    AND pending_reviews = 0
    AND workflows_created_in_n8n = 0
    AND active_workflows = 0
    AND unsafe_package_flags = 0
  ) AS ready_for_manual_import,
  false AS ready_to_activate,
  CASE
    WHEN workflows_created_in_n8n > 0 THEN 'blocked: workflow already marked created in n8n'
    WHEN active_workflows > 0 THEN 'blocked: active n8n workflow exists'
    WHEN unsafe_package_flags > 0 THEN 'blocked: unsafe package flag present'
    WHEN validation_failures > 0 THEN 'blocked: validation failures require review'
    WHEN pending_reviews > 0 THEN 'blocked: pending human build-package reviews'
    WHEN packages_approved_for_manual_import = 0 THEN 'blocked: no package approved for manual import'
    ELSE 'manual import can be considered only after explicit operator approval; activation remains blocked'
  END AS blocked_reason
FROM agg;
