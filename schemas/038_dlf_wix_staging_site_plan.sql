-- Phase 7.19: DLF Westpark Wix staging / preview-site plan.
--
-- Tracks a manually-created Wix staging/preview site, a Gallery White build checklist, and
-- pre-publish QA checks so the website can be built and tested visually WITHOUT connecting the
-- real domain, publishing production pages, enabling public indexing, wiring live forms/webhooks,
-- enabling external tracking, or creating real leads. This schema only creates
-- tracking/checklist/QA/review tables and count-safe dashboards. It performs NO Wix API call, NO
-- n8n call, NO external API call, NO publishing, NO live form/webhook, NO sends, and NO
-- inbound-lead/contact writes. Every site-level live flag (real_domain_connected,
-- public_indexing_enabled, wix_api_call_made, page_created, page_published, live_form_created,
-- live_webhook_created, external_tracking_enabled) defaults to false, and the readiness view keeps
-- ready_for_production_publish hard-false.

CREATE TABLE IF NOT EXISTS wix_staging_sites (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  staging_key text,
  staging_status text DEFAULT 'planned',
  staging_site_name text,
  staging_site_url text,
  real_domain_connected boolean DEFAULT false,
  public_indexing_enabled boolean DEFAULT false,
  wix_api_call_made boolean DEFAULT false,
  page_created boolean DEFAULT false,
  page_published boolean DEFAULT false,
  live_form_created boolean DEFAULT false,
  live_webhook_created boolean DEFAULT false,
  external_tracking_enabled boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wss_launch_project_id ON wix_staging_sites(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wss_staging_key ON wix_staging_sites(staging_key);
CREATE INDEX IF NOT EXISTS idx_wss_staging_status ON wix_staging_sites(staging_status);
CREATE INDEX IF NOT EXISTS idx_wss_created_at ON wix_staging_sites(created_at);

CREATE TABLE IF NOT EXISTS wix_staging_build_checklist_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  wix_staging_site_id uuid REFERENCES wix_staging_sites(id),
  checklist_key text,
  checklist_category text,
  checklist_status text DEFAULT 'pending',
  priority text DEFAULT 'normal',
  safe_summary text,
  operator_note text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wsbci_launch_project_id ON wix_staging_build_checklist_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wsbci_staging_site_id ON wix_staging_build_checklist_items(wix_staging_site_id);
CREATE INDEX IF NOT EXISTS idx_wsbci_checklist_category ON wix_staging_build_checklist_items(checklist_category);
CREATE INDEX IF NOT EXISTS idx_wsbci_checklist_status ON wix_staging_build_checklist_items(checklist_status);
CREATE INDEX IF NOT EXISTS idx_wsbci_created_at ON wix_staging_build_checklist_items(created_at);

CREATE TABLE IF NOT EXISTS wix_staging_qa_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  wix_staging_site_id uuid REFERENCES wix_staging_sites(id),
  qa_key text,
  qa_type text,
  qa_status text DEFAULT 'pending',
  blocker boolean DEFAULT true,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wsqa_launch_project_id ON wix_staging_qa_checks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wsqa_staging_site_id ON wix_staging_qa_checks(wix_staging_site_id);
CREATE INDEX IF NOT EXISTS idx_wsqa_qa_type ON wix_staging_qa_checks(qa_type);
CREATE INDEX IF NOT EXISTS idx_wsqa_qa_status ON wix_staging_qa_checks(qa_status);
CREATE INDEX IF NOT EXISTS idx_wsqa_created_at ON wix_staging_qa_checks(created_at);

CREATE TABLE IF NOT EXISTS wix_staging_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  wix_staging_site_id uuid REFERENCES wix_staging_sites(id),
  checklist_item_id uuid REFERENCES wix_staging_build_checklist_items(id),
  qa_check_id uuid REFERENCES wix_staging_qa_checks(id),
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

CREATE INDEX IF NOT EXISTS idx_wsri_launch_project_id ON wix_staging_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_wsri_staging_site_id ON wix_staging_review_items(wix_staging_site_id);
CREATE INDEX IF NOT EXISTS idx_wsri_checklist_item_id ON wix_staging_review_items(checklist_item_id);
CREATE INDEX IF NOT EXISTS idx_wsri_qa_check_id ON wix_staging_review_items(qa_check_id);
CREATE INDEX IF NOT EXISTS idx_wsri_review_type ON wix_staging_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_wsri_status ON wix_staging_review_items(status);
CREATE INDEX IF NOT EXISTS idx_wsri_created_at ON wix_staging_review_items(created_at);

DROP TRIGGER IF EXISTS trg_wix_staging_sites_updated_at ON wix_staging_sites;
CREATE TRIGGER trg_wix_staging_sites_updated_at
BEFORE UPDATE ON wix_staging_sites FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_staging_build_checklist_items_updated_at ON wix_staging_build_checklist_items;
CREATE TRIGGER trg_wix_staging_build_checklist_items_updated_at
BEFORE UPDATE ON wix_staging_build_checklist_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_staging_qa_checks_updated_at ON wix_staging_qa_checks;
CREATE TRIGGER trg_wix_staging_qa_checks_updated_at
BEFORE UPDATE ON wix_staging_qa_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_staging_review_items_updated_at ON wix_staging_review_items;
CREATE TRIGGER trg_wix_staging_review_items_updated_at
BEFORE UPDATE ON wix_staging_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_wix_staging_site_dashboard AS
SELECT
  p.launch_key,
  s.staging_key,
  s.staging_status,
  s.staging_site_name,
  s.real_domain_connected,
  s.public_indexing_enabled,
  s.wix_api_call_made,
  s.page_created,
  s.page_published,
  s.live_form_created,
  s.live_webhook_created,
  s.external_tracking_enabled,
  s.human_review_required,
  s.created_at
FROM wix_staging_sites s
JOIN launch_projects p ON p.id = s.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_staging_build_checklist_dashboard AS
SELECT
  p.launch_key,
  s.staging_key,
  c.checklist_key,
  c.checklist_category,
  c.checklist_status,
  c.priority,
  c.safe_summary
FROM wix_staging_build_checklist_items c
JOIN wix_staging_sites s ON s.id = c.wix_staging_site_id
JOIN launch_projects p ON p.id = c.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_staging_qa_dashboard AS
SELECT
  p.launch_key,
  s.staging_key,
  q.qa_key,
  q.qa_type,
  q.qa_status,
  q.blocker,
  q.safe_summary
FROM wix_staging_qa_checks q
JOIN wix_staging_sites s ON s.id = q.wix_staging_site_id
JOIN launch_projects p ON p.id = q.launch_project_id;

CREATE OR REPLACE VIEW vw_wix_staging_review_queue AS
SELECT
  ri.id AS review_item_id,
  p.launch_key,
  s.staging_key,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.created_at
FROM wix_staging_review_items ri
JOIN wix_staging_sites s ON s.id = ri.wix_staging_site_id
JOIN launch_projects p ON p.id = ri.launch_project_id;

CREATE OR REPLACE VIEW vw_dlf_wix_staging_readiness AS
WITH launch_scope AS (
  SELECT id, launch_key
  FROM launch_projects
),
agg AS (
  SELECT
    p.id,
    p.launch_key,
    count(DISTINCT s.id) AS staging_sites,
    count(DISTINCT s.id) FILTER (WHERE s.staging_status IN ('created_manually', 'build_in_progress', 'ready_for_qa', 'qa_passed')) AS staging_created_manually,
    count(DISTINCT c.id) AS checklist_items,
    count(DISTINCT c.id) FILTER (WHERE c.checklist_status = 'passed') AS checklist_passed,
    count(DISTINCT q.id) AS qa_checks,
    count(DISTINCT q.id) FILTER (WHERE q.qa_status = 'passed') AS qa_passed,
    count(DISTINCT q.id) FILTER (WHERE q.blocker AND q.qa_status = 'failed') AS qa_blockers_failed,
    count(DISTINCT ri.id) FILTER (WHERE ri.status = 'pending') AS pending_reviews,
    count(DISTINCT s.id) FILTER (WHERE s.real_domain_connected IS TRUE) AS real_domain_connected_count,
    count(DISTINCT s.id) FILTER (WHERE s.public_indexing_enabled IS TRUE) AS public_indexing_enabled_count,
    count(DISTINCT s.id) FILTER (WHERE s.page_published IS TRUE) AS page_published_count,
    count(DISTINCT s.id) FILTER (WHERE s.live_form_created IS TRUE) AS live_form_created_count,
    count(DISTINCT s.id) FILTER (WHERE s.live_webhook_created IS TRUE) AS live_webhook_created_count,
    count(DISTINCT s.id) FILTER (WHERE s.wix_api_call_made IS TRUE) AS wix_api_call_made_count,
    count(DISTINCT s.id) FILTER (WHERE s.external_tracking_enabled IS TRUE) AS external_tracking_enabled_count
  FROM launch_scope p
  LEFT JOIN wix_staging_sites s ON s.launch_project_id = p.id
  LEFT JOIN wix_staging_build_checklist_items c ON c.launch_project_id = p.id
  LEFT JOIN wix_staging_qa_checks q ON q.launch_project_id = p.id
  LEFT JOIN wix_staging_review_items ri ON ri.launch_project_id = p.id
  GROUP BY p.id, p.launch_key
)
SELECT
  launch_key,
  staging_sites,
  staging_created_manually,
  checklist_items,
  checklist_passed,
  qa_checks,
  qa_passed,
  pending_reviews,
  real_domain_connected_count,
  public_indexing_enabled_count,
  page_published_count,
  live_form_created_count,
  live_webhook_created_count,
  (
    staging_sites > 0
    AND real_domain_connected_count = 0
    AND public_indexing_enabled_count = 0
    AND page_published_count = 0
    AND live_form_created_count = 0
    AND live_webhook_created_count = 0
    AND wix_api_call_made_count = 0
  ) AS ready_for_manual_staging_build,
  (
    staging_created_manually > 0
    AND checklist_items > 0
    AND checklist_passed = checklist_items
    AND qa_blockers_failed = 0
    AND real_domain_connected_count = 0
    AND public_indexing_enabled_count = 0
    AND page_published_count = 0
    AND live_form_created_count = 0
    AND live_webhook_created_count = 0
  ) AS ready_for_staging_qa,
  false AS ready_for_production_publish,
  CASE
    WHEN real_domain_connected_count > 0 THEN 'blocked: staging site reports real_domain_connected'
    WHEN public_indexing_enabled_count > 0 THEN 'blocked: staging site reports public_indexing_enabled'
    WHEN page_published_count > 0 THEN 'blocked: staging site reports page_published'
    WHEN live_form_created_count > 0 THEN 'blocked: staging site reports live_form_created'
    WHEN live_webhook_created_count > 0 THEN 'blocked: staging site reports live_webhook_created'
    WHEN wix_api_call_made_count > 0 THEN 'blocked: staging site reports wix_api_call_made'
    WHEN staging_sites = 0 THEN 'blocked: no staging site planned'
    WHEN staging_created_manually = 0 THEN 'staging plan ready; awaiting manual Wix staging build (next phase)'
    WHEN checklist_passed < checklist_items THEN 'staging build in progress; checklist not fully passed'
    ELSE 'staging build + QA complete in staging; production publish is a separate gated phase and stays blocked'
  END AS blocked_reason
FROM agg;
