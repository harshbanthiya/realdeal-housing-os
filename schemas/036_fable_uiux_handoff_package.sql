-- Phase 7.16: Fable UI/UX handoff package for DLF Westpark.
--
-- Tracks privacy-safe, designer-facing Fable handoff packages distilled from the
-- approved Phase 7.15 Wix UX/SEO/integration masterplan. This schema only creates
-- tracking/section/validation/review tables and count-safe dashboards. It performs
-- NO Fable call, NO external API call, NO publishing, NO live form/webhook, NO
-- sends, and NO inbound-lead/contact writes. fable_call_made and external_call_made
-- stay false; the readiness view keeps ready_for_fable_use gated on human review.

CREATE TABLE IF NOT EXISTS fable_uiux_handoff_packages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  site_experience_blueprint_id uuid REFERENCES wix_site_experience_blueprints(id),
  package_key text,
  package_status text DEFAULT 'draft',
  concise_prompt_artifact_path text,
  detailed_brief_artifact_path text,
  contains_private_contact_data boolean DEFAULT false,
  contains_secrets boolean DEFAULT false,
  contains_unverified_claims boolean DEFAULT true,
  fable_call_made boolean DEFAULT false,
  external_call_made boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fuhp_launch_project_id ON fable_uiux_handoff_packages(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_fuhp_site_experience_blueprint_id ON fable_uiux_handoff_packages(site_experience_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_fuhp_package_key ON fable_uiux_handoff_packages(package_key);
CREATE INDEX IF NOT EXISTS idx_fuhp_package_status ON fable_uiux_handoff_packages(package_status);
CREATE INDEX IF NOT EXISTS idx_fuhp_created_at ON fable_uiux_handoff_packages(created_at);

CREATE TABLE IF NOT EXISTS fable_uiux_handoff_sections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  handoff_package_id uuid REFERENCES fable_uiux_handoff_packages(id),
  section_key text,
  section_type text,
  section_status text DEFAULT 'draft',
  safe_summary text,
  included_in_concise_prompt boolean DEFAULT false,
  included_in_detailed_brief boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fuhs_handoff_package_id ON fable_uiux_handoff_sections(handoff_package_id);
CREATE INDEX IF NOT EXISTS idx_fuhs_section_key ON fable_uiux_handoff_sections(section_key);
CREATE INDEX IF NOT EXISTS idx_fuhs_section_type ON fable_uiux_handoff_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_fuhs_created_at ON fable_uiux_handoff_sections(created_at);

CREATE TABLE IF NOT EXISTS fable_uiux_handoff_validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  handoff_package_id uuid REFERENCES fable_uiux_handoff_packages(id),
  validation_type text,
  validation_status text DEFAULT 'pending',
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fuhvr_handoff_package_id ON fable_uiux_handoff_validation_results(handoff_package_id);
CREATE INDEX IF NOT EXISTS idx_fuhvr_validation_type ON fable_uiux_handoff_validation_results(validation_type);
CREATE INDEX IF NOT EXISTS idx_fuhvr_validation_status ON fable_uiux_handoff_validation_results(validation_status);
CREATE INDEX IF NOT EXISTS idx_fuhvr_created_at ON fable_uiux_handoff_validation_results(created_at);

CREATE TABLE IF NOT EXISTS fable_uiux_handoff_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  handoff_package_id uuid REFERENCES fable_uiux_handoff_packages(id),
  validation_result_id uuid REFERENCES fable_uiux_handoff_validation_results(id),
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

CREATE INDEX IF NOT EXISTS idx_fuhri_launch_project_id ON fable_uiux_handoff_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_fuhri_handoff_package_id ON fable_uiux_handoff_review_items(handoff_package_id);
CREATE INDEX IF NOT EXISTS idx_fuhri_validation_result_id ON fable_uiux_handoff_review_items(validation_result_id);
CREATE INDEX IF NOT EXISTS idx_fuhri_review_type ON fable_uiux_handoff_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_fuhri_status ON fable_uiux_handoff_review_items(status);
CREATE INDEX IF NOT EXISTS idx_fuhri_created_at ON fable_uiux_handoff_review_items(created_at);

DROP TRIGGER IF EXISTS trg_fable_uiux_handoff_packages_updated_at ON fable_uiux_handoff_packages;
CREATE TRIGGER trg_fable_uiux_handoff_packages_updated_at
BEFORE UPDATE ON fable_uiux_handoff_packages FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fable_uiux_handoff_sections_updated_at ON fable_uiux_handoff_sections;
CREATE TRIGGER trg_fable_uiux_handoff_sections_updated_at
BEFORE UPDATE ON fable_uiux_handoff_sections FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fable_uiux_handoff_validation_results_updated_at ON fable_uiux_handoff_validation_results;
CREATE TRIGGER trg_fable_uiux_handoff_validation_results_updated_at
BEFORE UPDATE ON fable_uiux_handoff_validation_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fable_uiux_handoff_review_items_updated_at ON fable_uiux_handoff_review_items;
CREATE TRIGGER trg_fable_uiux_handoff_review_items_updated_at
BEFORE UPDATE ON fable_uiux_handoff_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_fable_uiux_handoff_package_dashboard AS
SELECT
  p.launch_key,
  hp.package_key,
  hp.package_status,
  hp.contains_private_contact_data,
  hp.contains_secrets,
  hp.contains_unverified_claims,
  hp.fable_call_made,
  hp.external_call_made,
  hp.human_review_required,
  hp.created_at
FROM fable_uiux_handoff_packages hp
JOIN launch_projects p ON p.id = hp.launch_project_id;

CREATE OR REPLACE VIEW vw_fable_uiux_handoff_section_dashboard AS
SELECT
  p.launch_key,
  hp.package_key,
  s.section_key,
  s.section_type,
  s.section_status,
  s.included_in_concise_prompt,
  s.included_in_detailed_brief,
  s.safe_summary
FROM fable_uiux_handoff_sections s
JOIN fable_uiux_handoff_packages hp ON hp.id = s.handoff_package_id
JOIN launch_projects p ON p.id = hp.launch_project_id;

CREATE OR REPLACE VIEW vw_fable_uiux_handoff_validation_dashboard AS
SELECT
  p.launch_key,
  hp.package_key,
  vr.validation_type,
  vr.validation_status,
  vr.safe_summary
FROM fable_uiux_handoff_validation_results vr
JOIN fable_uiux_handoff_packages hp ON hp.id = vr.handoff_package_id
JOIN launch_projects p ON p.id = hp.launch_project_id;

CREATE OR REPLACE VIEW vw_fable_uiux_handoff_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  hp.package_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM fable_uiux_handoff_review_items ri
JOIN fable_uiux_handoff_packages hp ON hp.id = ri.handoff_package_id
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_fable_handoff_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    count(DISTINCT hp.id) AS handoff_packages,
    count(DISTINCT hp.id) FILTER (WHERE hp.package_status IN ('generated', 'needs_review', 'approved_for_fable')) AS packages_generated,
    count(DISTINCT vr.id) FILTER (WHERE vr.validation_status = 'failed') AS validation_failures,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    count(DISTINCT hp.id) FILTER (WHERE hp.package_status = 'approved_for_fable') AS packages_approved_for_fable,
    count(DISTINCT hp.id) FILTER (WHERE hp.fable_call_made IS TRUE) AS fable_call_made_count,
    count(DISTINCT hp.id) FILTER (WHERE hp.external_call_made IS TRUE) AS external_call_made_count,
    count(DISTINCT hp.id) FILTER (
      WHERE hp.contains_private_contact_data IS TRUE
         OR hp.contains_secrets IS TRUE
    ) AS unsafe_package_flags
  FROM launch_scope p
  LEFT JOIN fable_uiux_handoff_packages hp ON hp.launch_project_id = p.id
  LEFT JOIN fable_uiux_handoff_validation_results vr ON vr.handoff_package_id = hp.id
  LEFT JOIN fable_uiux_handoff_review_items ri ON ri.handoff_package_id = hp.id
  GROUP BY p.id, p.launch_key
)
SELECT
  launch_key,
  handoff_packages,
  packages_generated,
  validation_failures,
  pending_reviews,
  packages_approved_for_fable,
  fable_call_made_count,
  external_call_made_count,
  (
    handoff_packages > 0
    AND packages_approved_for_fable > 0
    AND validation_failures = 0
    AND pending_reviews = 0
    AND fable_call_made_count = 0
    AND external_call_made_count = 0
    AND unsafe_package_flags = 0
  ) AS ready_for_fable_use,
  CASE
    WHEN fable_call_made_count > 0 THEN 'blocked: package marked fable_call_made'
    WHEN external_call_made_count > 0 THEN 'blocked: package marked external_call_made'
    WHEN unsafe_package_flags > 0 THEN 'blocked: package flagged with contact data or secrets'
    WHEN validation_failures > 0 THEN 'blocked: validation failures require review'
    WHEN handoff_packages = 0 THEN 'blocked: no Fable handoff package generated'
    WHEN pending_reviews > 0 THEN 'blocked: pending human handoff reviews'
    WHEN packages_approved_for_fable = 0 THEN 'blocked: no package approved for Fable use'
    ELSE 'approved: operator may paste the concise prompt into Fable manually; no automated Fable call'
  END AS blocked_reason
FROM agg;
