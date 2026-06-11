-- Phase 7.15: Wix website UX, SEO, and integration masterplan.
--
-- Planning-only schema. Tracks the full Wix website experience: UX/SEO blueprints,
-- page architecture, integration readiness (Meta/WhatsApp/email/n8n/GA4/GTM/CMS),
-- premium/Three.js design components, and a human review queue. It performs NO
-- external calls, NO publishing, NO live forms/webhooks, NO sends. All external
-- calls and publishing stay hard-disabled; readiness views keep ready_to_publish
-- false and external_call_allowed_count / publish_enabled_count at 0.

CREATE TABLE IF NOT EXISTS wix_site_experience_blueprints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  blueprint_key text,
  blueprint_status text DEFAULT 'draft',
  site_goal text,
  target_audience jsonb DEFAULT '[]'::jsonb,
  primary_conversion_goals jsonb DEFAULT '[]'::jsonb,
  seo_strategy_summary text,
  design_direction text,
  premium_visual_strategy text,
  threejs_component_strategy text,
  mobile_first_required boolean DEFAULT true,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wseb_launch_project_id ON wix_site_experience_blueprints(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wseb_blueprint_key ON wix_site_experience_blueprints(blueprint_key);
CREATE INDEX IF NOT EXISTS idx_wseb_blueprint_status ON wix_site_experience_blueprints(blueprint_status);
CREATE INDEX IF NOT EXISTS idx_wseb_created_at ON wix_site_experience_blueprints(created_at);

CREATE TABLE IF NOT EXISTS wix_page_blueprints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  site_experience_blueprint_id uuid REFERENCES wix_site_experience_blueprints(id),
  page_key text,
  page_type text,
  page_status text DEFAULT 'draft',
  page_goal text,
  seo_intent text,
  target_keyword text,
  suggested_slug text,
  primary_cta text,
  required_sections jsonb DEFAULT '[]'::jsonb,
  integration_requirements jsonb DEFAULT '[]'::jsonb,
  publish_enabled boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wpb_launch_project_id ON wix_page_blueprints(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wpb_site_experience_blueprint_id ON wix_page_blueprints(site_experience_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_wpb_page_key ON wix_page_blueprints(page_key);
CREATE INDEX IF NOT EXISTS idx_wpb_page_type ON wix_page_blueprints(page_type);
CREATE INDEX IF NOT EXISTS idx_wpb_page_status ON wix_page_blueprints(page_status);
CREATE INDEX IF NOT EXISTS idx_wpb_created_at ON wix_page_blueprints(created_at);

CREATE TABLE IF NOT EXISTS wix_integration_readiness_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  integration_key text,
  integration_type text,
  readiness_status text DEFAULT 'planned',
  external_call_required boolean DEFAULT true,
  external_call_allowed boolean DEFAULT false,
  contains_secret_required boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wiri_launch_project_id ON wix_integration_readiness_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wiri_integration_key ON wix_integration_readiness_items(integration_key);
CREATE INDEX IF NOT EXISTS idx_wiri_integration_type ON wix_integration_readiness_items(integration_type);
CREATE INDEX IF NOT EXISTS idx_wiri_readiness_status ON wix_integration_readiness_items(readiness_status);
CREATE INDEX IF NOT EXISTS idx_wiri_created_at ON wix_integration_readiness_items(created_at);

CREATE TABLE IF NOT EXISTS wix_design_component_specs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  page_blueprint_id uuid REFERENCES wix_page_blueprints(id),
  component_key text,
  component_type text,
  component_status text DEFAULT 'draft',
  design_goal text,
  content_requirements jsonb DEFAULT '[]'::jsonb,
  technical_notes text,
  performance_risk text,
  seo_risk text,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wdcs_launch_project_id ON wix_design_component_specs(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wdcs_page_blueprint_id ON wix_design_component_specs(page_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_wdcs_component_key ON wix_design_component_specs(component_key);
CREATE INDEX IF NOT EXISTS idx_wdcs_component_type ON wix_design_component_specs(component_type);
CREATE INDEX IF NOT EXISTS idx_wdcs_component_status ON wix_design_component_specs(component_status);
CREATE INDEX IF NOT EXISTS idx_wdcs_created_at ON wix_design_component_specs(created_at);

CREATE TABLE IF NOT EXISTS wix_ux_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  site_experience_blueprint_id uuid REFERENCES wix_site_experience_blueprints(id),
  page_blueprint_id uuid REFERENCES wix_page_blueprints(id),
  integration_readiness_item_id uuid REFERENCES wix_integration_readiness_items(id),
  design_component_spec_id uuid REFERENCES wix_design_component_specs(id),
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

CREATE INDEX IF NOT EXISTS idx_wuri_launch_project_id ON wix_ux_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wuri_site_experience_blueprint_id ON wix_ux_review_items(site_experience_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_wuri_page_blueprint_id ON wix_ux_review_items(page_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_wuri_integration_readiness_item_id ON wix_ux_review_items(integration_readiness_item_id);
CREATE INDEX IF NOT EXISTS idx_wuri_design_component_spec_id ON wix_ux_review_items(design_component_spec_id);
CREATE INDEX IF NOT EXISTS idx_wuri_review_type ON wix_ux_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_wuri_status ON wix_ux_review_items(status);
CREATE INDEX IF NOT EXISTS idx_wuri_created_at ON wix_ux_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_site_experience_blueprints_updated_at ON wix_site_experience_blueprints;
CREATE TRIGGER trg_wix_site_experience_blueprints_updated_at
BEFORE UPDATE ON wix_site_experience_blueprints FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_page_blueprints_updated_at ON wix_page_blueprints;
CREATE TRIGGER trg_wix_page_blueprints_updated_at
BEFORE UPDATE ON wix_page_blueprints FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_integration_readiness_items_updated_at ON wix_integration_readiness_items;
CREATE TRIGGER trg_wix_integration_readiness_items_updated_at
BEFORE UPDATE ON wix_integration_readiness_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_design_component_specs_updated_at ON wix_design_component_specs;
CREATE TRIGGER trg_wix_design_component_specs_updated_at
BEFORE UPDATE ON wix_design_component_specs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_ux_review_items_updated_at ON wix_ux_review_items;
CREATE TRIGGER trg_wix_ux_review_items_updated_at
BEFORE UPDATE ON wix_ux_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_site_experience_dashboard AS
SELECT
  p.launch_key,
  seb.blueprint_key,
  seb.blueprint_status,
  seb.site_goal,
  seb.mobile_first_required,
  seb.human_review_required,
  seb.created_at
FROM wix_site_experience_blueprints seb
JOIN launch_projects p ON p.id = seb.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_page_blueprint_dashboard AS
SELECT
  p.launch_key,
  pb.page_key,
  pb.page_type,
  pb.page_status,
  pb.page_goal,
  pb.seo_intent,
  pb.target_keyword,
  pb.suggested_slug,
  pb.primary_cta,
  pb.publish_enabled,
  pb.human_review_required,
  pb.created_at
FROM wix_page_blueprints pb
JOIN launch_projects p ON p.id = pb.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_integration_readiness_dashboard AS
SELECT
  p.launch_key,
  iri.integration_key,
  iri.integration_type,
  iri.readiness_status,
  iri.external_call_required,
  iri.external_call_allowed,
  iri.contains_secret_required,
  iri.human_review_required,
  iri.safe_summary,
  iri.created_at
FROM wix_integration_readiness_items iri
JOIN launch_projects p ON p.id = iri.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_design_component_dashboard AS
SELECT
  p.launch_key,
  pb.page_key,
  dcs.component_key,
  dcs.component_type,
  dcs.component_status,
  dcs.design_goal,
  dcs.performance_risk,
  dcs.seo_risk,
  dcs.human_review_required,
  dcs.created_at
FROM wix_design_component_specs dcs
JOIN launch_projects p ON p.id = dcs.launch_project_id
LEFT JOIN wix_page_blueprints pb ON pb.id = dcs.page_blueprint_id;

CREATE OR REPLACE VIEW vw_wix_ux_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  ri.review_type,
  ri.status,
  ri.priority,
  CASE
    WHEN ri.page_blueprint_id IS NOT NULL THEN 'page'
    WHEN ri.integration_readiness_item_id IS NOT NULL THEN 'integration'
    WHEN ri.design_component_spec_id IS NOT NULL THEN 'design_component'
    WHEN ri.site_experience_blueprint_id IS NOT NULL THEN 'site_experience'
    ELSE 'general'
  END AS linked_area,
  ri.created_at
FROM wix_ux_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_wix_unified_experience_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    (SELECT count(*) FROM wix_site_experience_blueprints seb WHERE seb.launch_project_id = p.id) AS blueprints,
    (SELECT count(*) FROM wix_page_blueprints pb WHERE pb.launch_project_id = p.id) AS pages_planned,
    (SELECT count(*) FROM wix_integration_readiness_items iri WHERE iri.launch_project_id = p.id) AS integrations_planned,
    (SELECT count(*) FROM wix_integration_readiness_items iri WHERE iri.launch_project_id = p.id
        AND iri.readiness_status IN ('active', 'connected_manually')) AS integrations_active,
    (SELECT count(*) FROM wix_design_component_specs dcs WHERE dcs.launch_project_id = p.id) AS design_components,
    (SELECT count(*) FROM wix_ux_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS pending_reviews,
    (SELECT count(*) FROM wix_integration_readiness_items iri WHERE iri.launch_project_id = p.id
        AND iri.external_call_allowed IS TRUE) AS external_call_allowed_count,
    (SELECT count(*) FROM wix_page_blueprints pb WHERE pb.launch_project_id = p.id
        AND pb.publish_enabled IS TRUE) AS publish_enabled_count,
    (SELECT count(*) FROM wix_integration_readiness_items iri WHERE iri.launch_project_id = p.id
        AND iri.integration_type IN ('meta_pixel_capi', 'google_search_console', 'ga4', 'google_tag_manager')
        AND iri.readiness_status = 'approved') AS tracking_integrations_approved,
    (SELECT count(*) FROM launch_wix_build_packages bp WHERE bp.launch_project_id = p.id
        AND bp.package_status = 'approved_for_manual_build') AS wix_packages_approved_for_manual_build
  FROM launch_scope p
)
SELECT
  launch_key,
  blueprints,
  pages_planned,
  integrations_planned,
  integrations_active,
  design_components,
  pending_reviews,
  external_call_allowed_count,
  publish_enabled_count,
  (
    blueprints > 0
    AND pages_planned > 0
    AND pending_reviews = 0
    AND wix_packages_approved_for_manual_build > 0
  ) AS ready_for_manual_wix_build,
  (
    tracking_integrations_approved > 0
    AND pending_reviews = 0
  ) AS ready_for_tracking_connection,
  false AS ready_to_publish,
  CASE
    WHEN publish_enabled_count > 0 THEN 'blocked: a page is marked publish_enabled'
    WHEN external_call_allowed_count > 0 THEN 'blocked: an integration is marked external_call_allowed'
    WHEN integrations_active > 0 THEN 'blocked: an integration is marked active/connected before review sign-off'
    WHEN blueprints = 0 THEN 'blocked: no site experience blueprint planned'
    WHEN pending_reviews > 0 THEN 'planning stage: pending human UX/SEO/integration reviews'
    WHEN wix_packages_approved_for_manual_build = 0 THEN 'planning stage: no Wix build package approved for manual build yet'
    ELSE 'plan approved; manual Wix build may proceed only after explicit operator approval; publishing remains blocked'
  END AS blocked_reason
FROM agg;
