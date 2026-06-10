-- Phase 6.5: source-gap resolution workflow (internal, review-gated, no external calls).
--
-- Turns the open content_source_gap_items into actionable, review-gated resolution
-- tasks and records SAFE references to internal evidence that may help close them.
-- NOTHING here resolves a gap automatically, calls an external/Wix API, scrapes the
-- web, executes AI, publishes, or sends outreach. Every resolution task defaults to
-- external_calls_required=false, external_calls_allowed=false, human_review_required=true.
-- Read-only views never expose personal data (no names/phones/emails/addresses) and
-- only surface safe summaries, counts, types, statuses, and system UUIDs.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. source_gap_resolution_tasks — actionable tasks for resolving source gaps.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_gap_resolution_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_source_gap_item_id uuid REFERENCES content_source_gap_items(id),
  content_source_requirement_id uuid REFERENCES content_source_requirements(id),
  content_brief_id uuid REFERENCES content_briefs(id),
  task_type text,                            -- internal_data_check, human_research, web_research_later, owner_data_check, inventory_check, photo_check, legal_disclaimer_review, market_range_estimate
  task_status text DEFAULT 'pending',        -- pending, in_progress, blocked, resolved, waived, cancelled
  priority text DEFAULT 'normal',
  resolution_source text,                    -- internal_db, owner_relationships, inventory, human_input, future_web_research, future_wix_data, manual_note
  external_calls_required boolean DEFAULT false,
  external_calls_allowed boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  safe_task_summary text,
  resolution_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sgrt_gap_item_id ON source_gap_resolution_tasks(content_source_gap_item_id);
CREATE INDEX IF NOT EXISTS idx_sgrt_requirement_id ON source_gap_resolution_tasks(content_source_requirement_id);
CREATE INDEX IF NOT EXISTS idx_sgrt_content_brief_id ON source_gap_resolution_tasks(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_sgrt_task_type ON source_gap_resolution_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_sgrt_task_status ON source_gap_resolution_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_sgrt_priority ON source_gap_resolution_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_sgrt_external_calls_required ON source_gap_resolution_tasks(external_calls_required);
CREATE INDEX IF NOT EXISTS idx_sgrt_external_calls_allowed ON source_gap_resolution_tasks(external_calls_allowed);
CREATE INDEX IF NOT EXISTS idx_sgrt_created_at ON source_gap_resolution_tasks(created_at);

-- ---------------------------------------------------------------------------
-- 2. internal_source_evidence — safe references to internal evidence per gap.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS internal_source_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_source_gap_item_id uuid REFERENCES content_source_gap_items(id),
  source_table text,
  source_entity_id uuid,
  evidence_type text,                        -- active_owner_relationship_count, unit_count, inventory_hint, building_alias, content_brief, seo_keyword, source_batch_count
  evidence_status text DEFAULT 'candidate',  -- candidate, accepted, rejected, needs_review
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ise_gap_item_id ON internal_source_evidence(content_source_gap_item_id);
CREATE INDEX IF NOT EXISTS idx_ise_evidence_type ON internal_source_evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_ise_evidence_status ON internal_source_evidence(evidence_status);
CREATE INDEX IF NOT EXISTS idx_ise_created_at ON internal_source_evidence(created_at);

-- ---------------------------------------------------------------------------
-- 3. source_gap_review_items — human review queue for accept/resolve/waive.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_gap_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_source_gap_item_id uuid REFERENCES content_source_gap_items(id),
  source_gap_resolution_task_id uuid REFERENCES source_gap_resolution_tasks(id),
  review_type text,                          -- gap_classification_review, internal_evidence_review, waive_gap_review, resolution_review
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
CREATE INDEX IF NOT EXISTS idx_sgri_gap_item_id ON source_gap_review_items(content_source_gap_item_id);
CREATE INDEX IF NOT EXISTS idx_sgri_resolution_task_id ON source_gap_review_items(source_gap_resolution_task_id);
CREATE INDEX IF NOT EXISTS idx_sgri_review_type ON source_gap_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_sgri_status ON source_gap_review_items(status);
CREATE INDEX IF NOT EXISTS idx_sgri_created_at ON source_gap_review_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (reuse project-wide set_updated_at()).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_source_gap_resolution_tasks_updated_at ON source_gap_resolution_tasks;
CREATE TRIGGER trg_source_gap_resolution_tasks_updated_at
BEFORE UPDATE ON source_gap_resolution_tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_internal_source_evidence_updated_at ON internal_source_evidence;
CREATE TRIGGER trg_internal_source_evidence_updated_at
BEFORE UPDATE ON internal_source_evidence
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_source_gap_review_items_updated_at ON source_gap_review_items;
CREATE TRIGGER trg_source_gap_review_items_updated_at
BEFORE UPDATE ON source_gap_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task E — read-only dashboard views. No personal data; safe summaries only.
-- ===========================================================================

DROP VIEW IF EXISTS vw_source_gap_resolution_dashboard;
DROP VIEW IF EXISTS vw_internal_source_evidence_dashboard;
DROP VIEW IF EXISTS vw_source_gap_review_queue;
DROP VIEW IF EXISTS vw_imperial_heights_source_gap_status;

-- 1. Per-gap resolution dashboard with task/evidence/review rollups.
CREATE VIEW vw_source_gap_resolution_dashboard AS
SELECT
  g.id AS gap_id,
  g.content_brief_id,
  cb.title AS content_title,
  g.gap_type,
  g.status AS gap_status,
  g.priority AS gap_priority,
  (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id) AS task_count,
  (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id AND t.task_status = 'pending') AS pending_task_count,
  (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id AND t.task_status = 'resolved') AS resolved_task_count,
  (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id AND t.external_calls_required = true) AS external_calls_required_count,
  (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id AND t.external_calls_allowed = true) AS external_calls_allowed_count,
  (SELECT count(*) FROM internal_source_evidence e WHERE e.content_source_gap_item_id = g.id) AS evidence_count,
  (SELECT count(*) FROM source_gap_review_items r WHERE r.content_source_gap_item_id = g.id AND r.status = 'pending') AS review_pending_count,
  CASE
    WHEN g.status = 'resolved' THEN 'none_resolved'
    WHEN g.status = 'waived' THEN 'none_waived'
    WHEN (SELECT count(*) FROM source_gap_review_items r WHERE r.content_source_gap_item_id = g.id AND r.status = 'pending') > 0 THEN 'await_human_review'
    WHEN (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id AND t.external_calls_required = true) > 0 THEN 'queue_future_external_research'
    WHEN (SELECT count(*) FROM internal_source_evidence e WHERE e.content_source_gap_item_id = g.id) > 0 THEN 'review_internal_evidence'
    WHEN (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_source_gap_item_id = g.id) = 0 THEN 'create_resolution_task'
    ELSE 'await_human_review'
  END AS recommended_next_action
FROM content_source_gap_items g
LEFT JOIN content_briefs cb ON cb.id = g.content_brief_id;

-- 2. Internal evidence dashboard (safe summaries only; no personal values).
CREATE VIEW vw_internal_source_evidence_dashboard AS
SELECT
  e.id AS evidence_id,
  e.content_source_gap_item_id AS gap_id,
  cb.title AS content_title,
  g.gap_type,
  e.evidence_type,
  e.evidence_status,
  e.safe_summary,
  e.created_at
FROM internal_source_evidence e
LEFT JOIN content_source_gap_items g ON g.id = e.content_source_gap_item_id
LEFT JOIN content_briefs cb ON cb.id = g.content_brief_id;

-- 3. Source-gap human review queue.
CREATE VIEW vw_source_gap_review_queue AS
SELECT
  r.id AS review_item_id,
  r.content_source_gap_item_id AS gap_id,
  r.source_gap_resolution_task_id AS task_id,
  cb.title AS content_title,
  g.gap_type,
  r.review_type,
  r.status,
  r.priority,
  r.assigned_to,
  r.reviewed_by,
  r.reviewed_at,
  r.created_at
FROM source_gap_review_items r
LEFT JOIN content_source_gap_items g ON g.id = r.content_source_gap_item_id
LEFT JOIN content_briefs cb ON cb.id = g.content_brief_id;

-- 4. Imperial Heights source-gap readiness rollup (one row per brief on profile).
--    ready_for_publish is a hard-coded false: publishing is a separate, future,
--    gated step and never becomes true from this view.
CREATE VIEW vw_imperial_heights_source_gap_status AS
SELECT
  p.profile_slug,
  cb.id AS content_brief_id,
  cb.title AS content_title,
  (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id) AS total_gaps,
  (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') AS open_gaps,
  (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'resolved') AS resolved_gaps,
  (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'waived') AS waived_gaps,
  (SELECT count(DISTINCT t.content_source_gap_item_id) FROM source_gap_resolution_tasks t
     WHERE t.content_brief_id = cb.id
       AND t.task_type IN ('internal_data_check', 'owner_data_check', 'inventory_check')) AS internal_resolvable_gaps,
  (SELECT count(DISTINCT t.content_source_gap_item_id) FROM source_gap_resolution_tasks t
     WHERE t.content_brief_id = cb.id
       AND (t.task_type IN ('web_research_later', 'market_range_estimate') OR t.external_calls_required = true)) AS external_research_needed_gaps,
  (SELECT count(*) FROM source_gap_review_items r
     JOIN content_source_gap_items g ON g.id = r.content_source_gap_item_id
    WHERE g.content_brief_id = cb.id AND r.status = 'pending') AS human_review_pending,
  (
    (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') > 0
    AND (SELECT count(DISTINCT t.content_source_gap_item_id) FROM source_gap_resolution_tasks t WHERE t.content_brief_id = cb.id)
        = (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open')
  ) AS ready_for_source_review,
  ((SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') = 0) AS ready_for_ai_draft,
  false AS ready_for_publish,
  CASE
    WHEN (SELECT count(*) FROM content_source_gap_items g WHERE g.content_brief_id = cb.id AND g.status = 'open') = 0 THEN 'gaps_cleared_pending_ai_draft_gate'
    WHEN (SELECT count(*) FROM source_gap_resolution_tasks t WHERE t.content_brief_id = cb.id) = 0 THEN 'open_source_gaps_unplanned'
    WHEN (SELECT count(DISTINCT t.content_source_gap_item_id) FROM source_gap_resolution_tasks t
            WHERE t.content_brief_id = cb.id
              AND (t.task_type IN ('web_research_later', 'market_range_estimate') OR t.external_calls_required = true)) > 0
      THEN 'awaiting_human_review_and_future_external_research'
    ELSE 'open_source_gaps_pending_human_review'
  END AS blocked_reason
FROM building_web_profiles p
JOIN content_briefs cb ON cb.building_web_profile_id = p.id;
