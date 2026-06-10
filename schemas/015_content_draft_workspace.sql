-- Phase 6.4: local content draft workspace (internal, non-final artifacts).
--
-- Stores INTERNAL draft artifacts (outlines, placeholder notes, source-gap items)
-- for content briefs. These are never public content: every artifact defaults to
-- internal_only=true, public_ready=false, source_verification_required=true,
-- human_review_required=true, external_calls_made=false, published=false,
-- communication_sent=false. NOTHING here executes AI, calls an external/Wix API,
-- generates final public claims, publishes, or sends outreach. Read-only views never
-- expose personal data and never surface the full artifact_body.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. content_draft_artifacts — internal, non-public draft artifacts per brief.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_draft_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  ai_agent_task_id uuid REFERENCES ai_agent_tasks(id),
  ai_task_execution_plan_id uuid REFERENCES ai_task_execution_plans(id),
  artifact_type text,                        -- outline, research_notes_placeholder, section_plan, meta_tag_draft, faq_draft, internal_brief_notes
  artifact_status text DEFAULT 'draft',      -- draft, needs_review, approved_for_internal_use, rejected, archived
  title text,
  target_keyword text,
  artifact_body text,
  source_requirements_summary jsonb DEFAULT '{}'::jsonb,
  quality_flags jsonb DEFAULT '{}'::jsonb,
  internal_only boolean DEFAULT true,
  public_ready boolean DEFAULT false,
  source_verification_required boolean DEFAULT true,
  human_review_required boolean DEFAULT true,
  external_calls_made boolean DEFAULT false,
  published boolean DEFAULT false,
  communication_sent boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cda_content_brief_id ON content_draft_artifacts(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_cda_ai_agent_task_id ON content_draft_artifacts(ai_agent_task_id);
CREATE INDEX IF NOT EXISTS idx_cda_execution_plan_id ON content_draft_artifacts(ai_task_execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_cda_artifact_type ON content_draft_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_cda_artifact_status ON content_draft_artifacts(artifact_status);
CREATE INDEX IF NOT EXISTS idx_cda_created_at ON content_draft_artifacts(created_at);

-- ---------------------------------------------------------------------------
-- 2. content_draft_reviews — human review queue for internal draft artifacts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_draft_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_draft_artifact_id uuid REFERENCES content_draft_artifacts(id),
  content_brief_id uuid REFERENCES content_briefs(id),
  review_type text,                          -- internal_draft_review, factuality_review, source_gap_review, seo_review, compliance_review
  status text DEFAULT 'pending',             -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cdr_artifact_id ON content_draft_reviews(content_draft_artifact_id);
CREATE INDEX IF NOT EXISTS idx_cdr_content_brief_id ON content_draft_reviews(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_cdr_review_type ON content_draft_reviews(review_type);
CREATE INDEX IF NOT EXISTS idx_cdr_status ON content_draft_reviews(status);
CREATE INDEX IF NOT EXISTS idx_cdr_created_at ON content_draft_reviews(created_at);

-- ---------------------------------------------------------------------------
-- 3. content_source_gap_items — specific missing facts/sources before drafting.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_source_gap_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  content_draft_artifact_id uuid REFERENCES content_draft_artifacts(id),
  gap_type text,                             -- rent_range_missing, resale_range_missing, amenities_unverified, developer_unverified, landmarks_unverified, inventory_availability_unverified, legal_disclaimer_needed, photos_needed, owner_listing_permission_needed
  status text DEFAULT 'open',                -- open, resolved, waived, not_applicable
  priority text DEFAULT 'normal',
  safe_summary text,
  resolution_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_csg_content_brief_id ON content_source_gap_items(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_csg_artifact_id ON content_source_gap_items(content_draft_artifact_id);
CREATE INDEX IF NOT EXISTS idx_csg_gap_type ON content_source_gap_items(gap_type);
CREATE INDEX IF NOT EXISTS idx_csg_status ON content_source_gap_items(status);
CREATE INDEX IF NOT EXISTS idx_csg_created_at ON content_source_gap_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers.
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_content_draft_artifacts_updated_at ON content_draft_artifacts;
CREATE TRIGGER trg_content_draft_artifacts_updated_at
BEFORE UPDATE ON content_draft_artifacts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_draft_reviews_updated_at ON content_draft_reviews;
CREATE TRIGGER trg_content_draft_reviews_updated_at
BEFORE UPDATE ON content_draft_reviews
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_source_gap_items_updated_at ON content_source_gap_items;
CREATE TRIGGER trg_content_source_gap_items_updated_at
BEFORE UPDATE ON content_source_gap_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task D — read-only dashboard views. No personal data; no full artifact_body.
-- ===========================================================================

DROP VIEW IF EXISTS vw_content_draft_artifact_dashboard;
DROP VIEW IF EXISTS vw_content_draft_review_queue;
DROP VIEW IF EXISTS vw_content_source_gap_dashboard;
DROP VIEW IF EXISTS vw_imperial_heights_draft_workspace;

-- 1. Draft artifact dashboard (metadata + flags only; no artifact_body).
CREATE VIEW vw_content_draft_artifact_dashboard AS
SELECT
  a.id AS artifact_id,
  a.content_brief_id,
  cb.title AS content_title,
  cb.content_type,
  a.target_keyword,
  a.artifact_type,
  a.artifact_status,
  a.internal_only,
  a.public_ready,
  a.source_verification_required,
  a.human_review_required,
  a.external_calls_made,
  a.published,
  a.created_at
FROM content_draft_artifacts a
LEFT JOIN content_briefs cb ON cb.id = a.content_brief_id;

-- 2. Draft review queue.
CREATE VIEW vw_content_draft_review_queue AS
SELECT
  r.id AS draft_review_id,
  r.content_draft_artifact_id AS artifact_id,
  r.content_brief_id,
  cb.title AS content_title,
  a.artifact_type,
  r.review_type,
  r.status,
  r.priority,
  r.assigned_to,
  r.reviewed_by,
  r.reviewed_at,
  r.created_at
FROM content_draft_reviews r
LEFT JOIN content_draft_artifacts a ON a.id = r.content_draft_artifact_id
LEFT JOIN content_briefs cb ON cb.id = r.content_brief_id;

-- 3. Source gap dashboard.
CREATE VIEW vw_content_source_gap_dashboard AS
SELECT
  g.id AS gap_id,
  g.content_brief_id,
  cb.title AS content_title,
  g.content_draft_artifact_id AS artifact_id,
  g.gap_type,
  g.status,
  g.priority,
  g.safe_summary,
  g.created_at
FROM content_source_gap_items g
LEFT JOIN content_briefs cb ON cb.id = g.content_brief_id;

-- 4. Imperial Heights draft workspace rollup (one row per brief on the profile).
CREATE VIEW vw_imperial_heights_draft_workspace AS
SELECT
  p.profile_slug,
  cb.id AS content_brief_id,
  cb.title AS content_title,
  cb.target_keyword,
  (SELECT count(*) FROM content_draft_artifacts a WHERE a.content_brief_id = cb.id) AS artifact_count,
  (SELECT count(*) FROM content_draft_reviews r WHERE r.content_brief_id = cb.id AND r.status = 'pending') AS pending_draft_reviews,
  (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') AS open_source_gaps,
  (SELECT count(*) FROM content_draft_artifacts a WHERE a.content_brief_id = cb.id AND a.public_ready = true) AS public_ready_count,
  (SELECT count(*) FROM content_draft_artifacts a WHERE a.content_brief_id = cb.id AND a.published = true) AS published_count,
  (SELECT count(*) FROM content_draft_artifacts a WHERE a.content_brief_id = cb.id AND a.external_calls_made = true) AS external_calls_made_count,
  CASE
    WHEN (SELECT count(*) FROM content_draft_artifacts a WHERE a.content_brief_id = cb.id) = 0 THEN 'no_draft_artifacts'
    WHEN (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') > 0 THEN 'open_source_gaps'
    WHEN (SELECT count(*) FROM content_draft_reviews r WHERE r.content_brief_id = cb.id AND r.status = 'pending') > 0 THEN 'pending_draft_reviews'
    ELSE 'internal_draft_only_not_public'
  END AS blocked_reason
FROM building_web_profiles p
JOIN content_briefs cb ON cb.building_web_profile_id = p.id;
