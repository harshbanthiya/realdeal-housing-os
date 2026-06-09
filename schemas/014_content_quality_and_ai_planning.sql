-- Phase 6.3: content quality checks + source requirements + AI prompt templates
-- + AI task execution plans.
--
-- Planning/quality only. NOTHING here executes an AI task, calls any external/Wix
-- API, generates final article text, publishes, or sends outreach. AI execution
-- plans default to external_calls_allowed=false and requires_human_review=true.
-- Prompt templates carry explicit safety_rules. Read-only views never expose
-- personal data; long prompt text is not surfaced (title/summary only).
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. content_quality_checks — pre-draft / pre-publish checklist per brief.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_quality_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  check_key text NOT NULL,                   -- target_keyword_present, search_intent_present, outline_present, source_requirements_present, local_market_claims_reviewed, no_unverified_claims, compliance_review_needed, cms_mapping_exists, human_review_required
  check_status text DEFAULT 'pending',       -- pending, passed, failed, waived
  severity text DEFAULT 'normal',            -- low, normal, high, blocker
  details text,
  checked_by text,
  checked_at timestamptz,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cqc_content_brief_id ON content_quality_checks(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_cqc_check_status ON content_quality_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_cqc_check_key ON content_quality_checks(check_key);
CREATE INDEX IF NOT EXISTS idx_cqc_severity ON content_quality_checks(severity);
CREATE INDEX IF NOT EXISTS idx_cqc_created_at ON content_quality_checks(created_at);

-- ---------------------------------------------------------------------------
-- 2. content_source_requirements — research/sources needed before drafting.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_source_requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  requirement_type text,                     -- building_facts, amenities, location_landmarks, rental_range, resale_range, developer_info, faq, internal_inventory, owner_relationships, legal_disclaimer
  status text DEFAULT 'needed',              -- needed, collected, not_available, waived, needs_human_review
  source_notes text,
  source_url_placeholder text,
  verified_by text,
  verified_at timestamptz,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_csr_content_brief_id ON content_source_requirements(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_csr_requirement_type ON content_source_requirements(requirement_type);
CREATE INDEX IF NOT EXISTS idx_csr_status ON content_source_requirements(status);
CREATE INDEX IF NOT EXISTS idx_csr_created_at ON content_source_requirements(created_at);

-- ---------------------------------------------------------------------------
-- 3. ai_prompt_templates — reusable prompt templates for FUTURE AI execution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_prompt_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key text NOT NULL,
  task_type text,
  content_type text,
  title text,
  prompt_template text,
  output_requirements jsonb DEFAULT '{}'::jsonb,
  safety_rules jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'draft',               -- draft, reviewed, approved, archived
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apt_template_key ON ai_prompt_templates(template_key);
CREATE INDEX IF NOT EXISTS idx_apt_task_type ON ai_prompt_templates(task_type);
CREATE INDEX IF NOT EXISTS idx_apt_status ON ai_prompt_templates(status);
CREATE INDEX IF NOT EXISTS idx_apt_created_at ON ai_prompt_templates(created_at);

-- ---------------------------------------------------------------------------
-- 4. ai_task_execution_plans — how queued ai_agent_tasks should run LATER.
--    external_calls_allowed defaults false; requires_human_review defaults true.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_task_execution_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ai_agent_task_id uuid REFERENCES ai_agent_tasks(id),
  content_brief_id uuid REFERENCES content_briefs(id),
  prompt_template_id uuid REFERENCES ai_prompt_templates(id),
  execution_status text DEFAULT 'planned',   -- planned, ready_for_dry_run, dry_run_complete, ready_for_human_review, completed, cancelled
  execution_mode text DEFAULT 'manual',      -- manual, local_model, api_model, n8n_agent
  external_calls_allowed boolean DEFAULT false,
  requires_human_review boolean DEFAULT true,
  planned_prompt_summary text,
  expected_output_type text,                 -- research_notes, content_outline, draft_blog, meta_tags, faq, seo_update_plan
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_atep_ai_agent_task_id ON ai_task_execution_plans(ai_agent_task_id);
CREATE INDEX IF NOT EXISTS idx_atep_content_brief_id ON ai_task_execution_plans(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_atep_prompt_template_id ON ai_task_execution_plans(prompt_template_id);
CREATE INDEX IF NOT EXISTS idx_atep_execution_status ON ai_task_execution_plans(execution_status);
CREATE INDEX IF NOT EXISTS idx_atep_execution_mode ON ai_task_execution_plans(execution_mode);
CREATE INDEX IF NOT EXISTS idx_atep_created_at ON ai_task_execution_plans(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers.
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_content_quality_checks_updated_at ON content_quality_checks;
CREATE TRIGGER trg_content_quality_checks_updated_at
BEFORE UPDATE ON content_quality_checks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_source_requirements_updated_at ON content_source_requirements;
CREATE TRIGGER trg_content_source_requirements_updated_at
BEFORE UPDATE ON content_source_requirements
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ai_prompt_templates_updated_at ON ai_prompt_templates;
CREATE TRIGGER trg_ai_prompt_templates_updated_at
BEFORE UPDATE ON ai_prompt_templates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ai_task_execution_plans_updated_at ON ai_task_execution_plans;
CREATE TRIGGER trg_ai_task_execution_plans_updated_at
BEFORE UPDATE ON ai_task_execution_plans
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task E — read-only dashboard views. Counts/metadata only; no personal data;
-- no full prompt text.
-- ===========================================================================

DROP VIEW IF EXISTS vw_content_quality_dashboard;
DROP VIEW IF EXISTS vw_content_source_requirements_dashboard;
DROP VIEW IF EXISTS vw_ai_prompt_template_dashboard;
DROP VIEW IF EXISTS vw_ai_task_execution_plan_dashboard;
DROP VIEW IF EXISTS vw_imperial_heights_content_readiness;

-- 1. Quality checklist rollup per brief.
CREATE VIEW vw_content_quality_dashboard AS
SELECT
  cb.id AS content_brief_id,
  cb.title,
  cb.content_type,
  cb.target_keyword,
  count(q.id) AS total_checks,
  count(q.id) FILTER (WHERE q.check_status = 'passed') AS passed_checks,
  count(q.id) FILTER (WHERE q.check_status = 'pending') AS pending_checks,
  count(q.id) FILTER (WHERE q.check_status = 'failed') AS failed_checks,
  count(q.id) FILTER (WHERE q.severity = 'blocker' AND q.check_status IN ('pending', 'failed')) AS blocker_checks,
  CASE
    WHEN count(q.id) = 0 THEN 'no_checks'
    WHEN count(q.id) FILTER (WHERE q.severity = 'blocker' AND q.check_status IN ('pending', 'failed')) > 0 THEN 'blocked'
    WHEN count(q.id) FILTER (WHERE q.check_status = 'failed') > 0 THEN 'has_failures'
    WHEN count(q.id) FILTER (WHERE q.check_status = 'pending') > 0 THEN 'checks_pending'
    ELSE 'all_passed'
  END AS quality_status,
  cb.approval_status,
  cb.research_status
FROM content_briefs cb
LEFT JOIN content_quality_checks q ON q.content_brief_id = cb.id
GROUP BY cb.id, cb.title, cb.content_type, cb.target_keyword, cb.approval_status, cb.research_status;

-- 2. Source requirements per brief.
CREATE VIEW vw_content_source_requirements_dashboard AS
SELECT
  r.content_brief_id,
  cb.title,
  r.requirement_type,
  r.status,
  (NULLIF(btrim(COALESCE(r.source_url_placeholder, '')), '') IS NOT NULL) AS has_source_url_placeholder,
  r.verified_by,
  r.verified_at,
  r.created_at
FROM content_source_requirements r
LEFT JOIN content_briefs cb ON cb.id = r.content_brief_id;

-- 3. Prompt template catalogue (no full prompt text).
CREATE VIEW vw_ai_prompt_template_dashboard AS
SELECT
  t.template_key,
  t.task_type,
  t.content_type,
  t.title,
  t.status,
  t.created_at
FROM ai_prompt_templates t;

-- 4. AI task execution plans.
CREATE VIEW vw_ai_task_execution_plan_dashboard AS
SELECT
  p.id AS execution_plan_id,
  p.ai_agent_task_id,
  p.content_brief_id,
  cb.title AS content_title,
  t.task_type,
  p.execution_status,
  p.execution_mode,
  p.external_calls_allowed,
  p.requires_human_review,
  p.expected_output_type,
  p.created_at
FROM ai_task_execution_plans p
LEFT JOIN content_briefs cb ON cb.id = p.content_brief_id
LEFT JOIN ai_agent_tasks t ON t.id = p.ai_agent_task_id;

-- 5. Imperial Heights content readiness (one row per brief on that profile).
--    ready_for_publish stays false here (publishing is a separate, future, gated
--    step). ready_for_ai_draft is true only when there is no outstanding blocker
--    quality check AND no source requirement is still needed/needs_human_review.
CREATE VIEW vw_imperial_heights_content_readiness AS
WITH base AS (
  SELECT
    p.profile_slug,
    cb.id AS content_brief_id,
    cb.title,
    cb.content_type,
    cb.target_keyword,
    (SELECT cri.status FROM content_review_items cri WHERE cri.content_brief_id = cb.id ORDER BY cri.created_at LIMIT 1) AS content_review_status,
    (SELECT q.publish_status FROM content_publishing_queue q WHERE q.content_brief_id = cb.id ORDER BY q.created_at LIMIT 1) AS publishing_status,
    (SELECT count(*) FROM content_quality_checks c WHERE c.content_brief_id = cb.id) AS total_quality_checks,
    (SELECT count(*) FROM content_quality_checks c WHERE c.content_brief_id = cb.id
       AND c.severity = 'blocker' AND c.check_status IN ('pending', 'failed')) AS blocker_quality_checks,
    (SELECT count(*) FROM content_source_requirements r WHERE r.content_brief_id = cb.id AND r.status = 'needed') AS source_requirements_needed,
    (SELECT count(*) FROM content_source_requirements r WHERE r.content_brief_id = cb.id AND r.status = 'collected') AS source_requirements_collected,
    (SELECT count(*) FROM content_source_requirements r WHERE r.content_brief_id = cb.id
       AND r.status IN ('needed', 'needs_human_review')) AS source_requirements_outstanding,
    (SELECT count(*) FROM ai_task_execution_plans ep WHERE ep.content_brief_id = cb.id) AS ai_execution_plans
  FROM building_web_profiles p
  JOIN content_briefs cb ON cb.building_web_profile_id = p.id
)
SELECT
  base.profile_slug,
  base.content_brief_id,
  base.title,
  base.content_type,
  base.target_keyword,
  base.content_review_status,
  base.publishing_status,
  CASE
    WHEN base.total_quality_checks = 0 THEN 'no_checks'
    WHEN base.blocker_quality_checks > 0 THEN 'blocked'
    ELSE 'checks_present'
  END AS quality_status,
  base.source_requirements_needed,
  base.source_requirements_collected,
  base.ai_execution_plans,
  (base.blocker_quality_checks = 0 AND base.total_quality_checks > 0 AND base.source_requirements_outstanding = 0) AS ready_for_ai_draft,
  false AS ready_for_publish,
  CASE
    WHEN base.total_quality_checks = 0 THEN 'no_quality_checks'
    WHEN base.blocker_quality_checks > 0 THEN 'blocker_quality_checks_open'
    WHEN base.source_requirements_outstanding > 0 THEN 'source_requirements_outstanding'
    ELSE 'ready_for_ai_draft_not_publish'
  END AS blocked_reason
FROM base;
