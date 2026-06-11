-- Phase 7.14: DLF Wix landing page and lead form build package tracking.
--
-- Tracks local/operator build packages for a human-buildable Wix landing page
-- and lead form. This schema only creates tracking/validation/review tables and
-- count-safe dashboards. It does NOT call Wix, create or publish a Wix page,
-- create a live form/webhook, send messages, or create inbound leads/contacts.
-- ready_to_publish, wix_pages_published, and live_forms_created stay hard-false/0.

CREATE TABLE IF NOT EXISTS launch_wix_build_packages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  landing_page_spec_id uuid REFERENCES launch_landing_page_specs(id),
  lead_capture_form_id uuid REFERENCES launch_lead_capture_forms(id),
  package_key text,
  package_status text DEFAULT 'draft',
  artifact_path text,
  artifact_type text DEFAULT 'wix_landing_page_build_markdown',
  contains_secrets boolean DEFAULT false,
  contains_contact_data boolean DEFAULT false,
  contains_unverified_claims boolean DEFAULT true,
  external_call_made boolean DEFAULT false,
  wix_page_created boolean DEFAULT false,
  wix_page_published boolean DEFAULT false,
  live_form_created boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lwbp_launch_project_id ON launch_wix_build_packages(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lwbp_landing_page_spec_id ON launch_wix_build_packages(landing_page_spec_id);
CREATE INDEX IF NOT EXISTS idx_lwbp_lead_capture_form_id ON launch_wix_build_packages(lead_capture_form_id);
CREATE INDEX IF NOT EXISTS idx_lwbp_package_key ON launch_wix_build_packages(package_key);
CREATE INDEX IF NOT EXISTS idx_lwbp_package_status ON launch_wix_build_packages(package_status);
CREATE INDEX IF NOT EXISTS idx_lwbp_created_at ON launch_wix_build_packages(created_at);

CREATE TABLE IF NOT EXISTS launch_wix_build_validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  build_package_id uuid REFERENCES launch_wix_build_packages(id),
  validation_type text,
  validation_status text DEFAULT 'pending',
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lwbvr_build_package_id ON launch_wix_build_validation_results(build_package_id);
CREATE INDEX IF NOT EXISTS idx_lwbvr_validation_type ON launch_wix_build_validation_results(validation_type);
CREATE INDEX IF NOT EXISTS idx_lwbvr_validation_status ON launch_wix_build_validation_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_lwbvr_created_at ON launch_wix_build_validation_results(created_at);

CREATE TABLE IF NOT EXISTS launch_wix_build_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  build_package_id uuid REFERENCES launch_wix_build_packages(id),
  validation_result_id uuid REFERENCES launch_wix_build_validation_results(id),
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

CREATE INDEX IF NOT EXISTS idx_lwbri_launch_project_id ON launch_wix_build_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lwbri_build_package_id ON launch_wix_build_review_items(build_package_id);
CREATE INDEX IF NOT EXISTS idx_lwbri_validation_result_id ON launch_wix_build_review_items(validation_result_id);
CREATE INDEX IF NOT EXISTS idx_lwbri_review_type ON launch_wix_build_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_lwbri_status ON launch_wix_build_review_items(status);
CREATE INDEX IF NOT EXISTS idx_lwbri_created_at ON launch_wix_build_review_items(created_at);

DROP TRIGGER IF EXISTS trg_launch_wix_build_packages_updated_at ON launch_wix_build_packages;
CREATE TRIGGER trg_launch_wix_build_packages_updated_at
BEFORE UPDATE ON launch_wix_build_packages FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_wix_build_validation_results_updated_at ON launch_wix_build_validation_results;
CREATE TRIGGER trg_launch_wix_build_validation_results_updated_at
BEFORE UPDATE ON launch_wix_build_validation_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_wix_build_review_items_updated_at ON launch_wix_build_review_items;
CREATE TRIGGER trg_launch_wix_build_review_items_updated_at
BEFORE UPDATE ON launch_wix_build_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_dlf_wix_build_package_dashboard AS
SELECT
  p.launch_key,
  bp.package_key,
  bp.package_status,
  bp.artifact_type,
  bp.contains_secrets,
  bp.contains_contact_data,
  bp.contains_unverified_claims,
  bp.external_call_made,
  bp.wix_page_created,
  bp.wix_page_published,
  bp.live_form_created,
  bp.human_review_required
FROM launch_wix_build_packages bp
JOIN launch_projects p ON p.id = bp.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_wix_build_validation_dashboard AS
SELECT
  p.launch_key,
  bp.package_key,
  vr.validation_type,
  vr.validation_status,
  vr.safe_summary
FROM launch_wix_build_validation_results vr
JOIN launch_wix_build_packages bp ON bp.id = vr.build_package_id
JOIN launch_projects p ON p.id = bp.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_wix_build_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  bp.package_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM launch_wix_build_review_items ri
JOIN launch_wix_build_packages bp ON bp.id = ri.build_package_id
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_wix_build_readiness AS
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
    count(DISTINCT bp.id) FILTER (WHERE bp.package_status = 'approved_for_manual_build') AS packages_approved_for_manual_build,
    count(DISTINCT bp.id) FILTER (WHERE bp.wix_page_created IS TRUE) AS wix_pages_created,
    count(DISTINCT bp.id) FILTER (WHERE bp.wix_page_published IS TRUE) AS wix_pages_published,
    count(DISTINCT bp.id) FILTER (WHERE bp.live_form_created IS TRUE) AS live_forms_created,
    count(DISTINCT bp.id) FILTER (
      WHERE bp.contains_secrets IS TRUE
         OR bp.contains_contact_data IS TRUE
         OR bp.external_call_made IS TRUE
    ) AS unsafe_package_flags
  FROM launch_scope p
  LEFT JOIN launch_wix_build_packages bp ON bp.launch_project_id = p.id
  LEFT JOIN launch_wix_build_validation_results vr ON vr.build_package_id = bp.id
  LEFT JOIN launch_wix_build_review_items ri ON ri.build_package_id = bp.id
  GROUP BY p.id, p.launch_key
)
SELECT
  launch_key,
  build_packages,
  packages_validated,
  validation_failures,
  pending_reviews,
  packages_approved_for_manual_build AS approved_for_manual_build,
  wix_pages_created,
  wix_pages_published,
  live_forms_created,
  (
    build_packages > 0
    AND packages_approved_for_manual_build > 0
    AND validation_failures = 0
    AND pending_reviews = 0
    AND wix_pages_created = 0
    AND wix_pages_published = 0
    AND live_forms_created = 0
    AND unsafe_package_flags = 0
  ) AS ready_for_manual_wix_build,
  false AS ready_to_publish,
  CASE
    WHEN wix_pages_published > 0 THEN 'blocked: wix page already marked published'
    WHEN live_forms_created > 0 THEN 'blocked: live form already marked created'
    WHEN wix_pages_created > 0 THEN 'blocked: wix page already marked created'
    WHEN unsafe_package_flags > 0 THEN 'blocked: unsafe package flag present (secrets/contact data/external call)'
    WHEN validation_failures > 0 THEN 'blocked: validation failures require review'
    WHEN pending_reviews > 0 THEN 'blocked: pending human build-package reviews'
    WHEN packages_approved_for_manual_build = 0 THEN 'blocked: no package approved for manual build'
    ELSE 'manual Wix build can be considered only after explicit operator approval; publishing remains blocked'
  END AS blocked_reason
FROM agg;
