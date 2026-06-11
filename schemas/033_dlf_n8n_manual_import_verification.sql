-- Phase 7.13: DLF n8n manual inactive import verification.
--
-- Records human/operator verification of a manual n8n import without calling
-- n8n, creating workflows, activating workflows, creating live webhooks, or
-- changing lead/contact/send/publish state.

CREATE TABLE IF NOT EXISTS launch_n8n_manual_import_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  build_package_id uuid REFERENCES launch_n8n_build_packages(id),
  workflow_blueprint_id uuid REFERENCES launch_n8n_workflow_blueprints(id),
  check_status text DEFAULT 'pending',
  operator_reported_n8n_workflow_id text,
  operator_reported_workflow_name text,
  verified_inactive boolean DEFAULT false,
  verified_no_credentials boolean DEFAULT false,
  verified_no_live_webhook boolean DEFAULT false,
  verified_not_active boolean DEFAULT false,
  activation_requested boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  checked_by text,
  checked_at timestamptz,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ln8nmic_launch_project_id ON launch_n8n_manual_import_checks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_build_package_id ON launch_n8n_manual_import_checks(build_package_id);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_workflow_blueprint_id ON launch_n8n_manual_import_checks(workflow_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_check_status ON launch_n8n_manual_import_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_verified_inactive ON launch_n8n_manual_import_checks(verified_inactive);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_activation_requested ON launch_n8n_manual_import_checks(activation_requested);
CREATE INDEX IF NOT EXISTS idx_ln8nmic_created_at ON launch_n8n_manual_import_checks(created_at);

DROP TRIGGER IF EXISTS trg_launch_n8n_manual_import_checks_updated_at ON launch_n8n_manual_import_checks;
CREATE TRIGGER trg_launch_n8n_manual_import_checks_updated_at
BEFORE UPDATE ON launch_n8n_manual_import_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_dlf_n8n_manual_import_check_dashboard AS
SELECT
  p.launch_key,
  mic.check_status,
  mic.operator_reported_workflow_name,
  mic.verified_inactive,
  mic.verified_no_credentials,
  mic.verified_no_live_webhook,
  mic.verified_not_active,
  mic.activation_requested,
  mic.external_call_made,
  mic.checked_at
FROM launch_n8n_manual_import_checks mic
JOIN launch_projects p ON p.id = mic.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_n8n_manual_import_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    (
      SELECT count(*)
      FROM launch_n8n_build_packages bp
      WHERE bp.launch_project_id = p.id
        AND bp.package_status = 'approved_for_manual_import'
    ) AS build_packages_approved_for_manual_import,
    (
      SELECT count(*)
      FROM launch_n8n_manual_import_checks mic
      WHERE mic.launch_project_id = p.id
    ) AS manual_import_checks,
    (
      SELECT count(*)
      FROM launch_n8n_manual_import_checks mic
      WHERE mic.launch_project_id = p.id
        AND mic.check_status = 'imported_inactive_verified'
        AND mic.verified_inactive
        AND mic.verified_no_credentials
        AND mic.verified_no_live_webhook
        AND mic.verified_not_active
    ) AS imported_inactive_verified_count,
    (
      SELECT count(*)
      FROM launch_n8n_manual_import_checks mic
      WHERE mic.launch_project_id = p.id
        AND mic.activation_requested
    ) AS activation_requested_count,
    (
      SELECT count(*)
      FROM launch_n8n_manual_import_checks mic
      WHERE mic.launch_project_id = p.id
        AND mic.external_call_made
    ) AS external_call_made_count,
    (
      SELECT count(*)
      FROM launch_n8n_workflow_blueprints wb
      WHERE wb.launch_project_id = p.id
        AND wb.activation_status = 'active'
    ) AS active_workflows
  FROM launch_scope p
)
SELECT
  launch_key,
  build_packages_approved_for_manual_import,
  manual_import_checks,
  imported_inactive_verified_count,
  activation_requested_count,
  external_call_made_count,
  (
    build_packages_approved_for_manual_import > 0
    AND activation_requested_count = 0
    AND external_call_made_count = 0
    AND active_workflows = 0
  ) AS ready_for_inactive_manual_import,
  false AS ready_to_activate,
  CASE
    WHEN active_workflows > 0 THEN 'blocked: active n8n workflow exists'
    WHEN activation_requested_count > 0 THEN 'blocked: activation requested during manual import verification'
    WHEN external_call_made_count > 0 THEN 'blocked: external call made during manual import verification'
    WHEN build_packages_approved_for_manual_import = 0 THEN 'blocked: no package approved for manual import'
    WHEN imported_inactive_verified_count = 0 THEN 'manual import not yet verified; package may be imported manually as inactive only'
    ELSE 'inactive manual import verified; activation remains blocked'
  END AS blocked_reason
FROM agg;
