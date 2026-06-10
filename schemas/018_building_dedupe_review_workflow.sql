-- Phase 6.7: building-anchor dedupe review workflow (planning only, no merge).
--
-- Tracks possible DUPLICATE building anchors (e.g. two "Imperial Heights" rows), a human
-- review queue before any consolidation, and a future audit log for merge actions.
-- NOTHING here merges or deletes buildings, moves units/relationships, touches
-- building_web_profiles / SEO / content rows, calls an external/Wix API, publishes, or
-- sends outreach. Read-only views never expose personal data (no names/phones/emails of
-- contacts); only building (property) names, codes, counts, statuses, and system UUIDs.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. building_duplicate_candidates — possible duplicate building anchors.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_duplicate_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_group_key text,
  canonical_building_id uuid REFERENCES buildings(id),
  duplicate_building_id uuid REFERENCES buildings(id),
  duplicate_strength text DEFAULT 'candidate',   -- strong, medium, weak, candidate
  status text DEFAULT 'pending_review',          -- pending_review, approved_for_merge, rejected, needs_more_info, merged, archived
  reason text,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bdc_canonical_building_id ON building_duplicate_candidates(canonical_building_id);
CREATE INDEX IF NOT EXISTS idx_bdc_duplicate_building_id ON building_duplicate_candidates(duplicate_building_id);
CREATE INDEX IF NOT EXISTS idx_bdc_candidate_group_key ON building_duplicate_candidates(candidate_group_key);
CREATE INDEX IF NOT EXISTS idx_bdc_duplicate_strength ON building_duplicate_candidates(duplicate_strength);
CREATE INDEX IF NOT EXISTS idx_bdc_status ON building_duplicate_candidates(status);
CREATE INDEX IF NOT EXISTS idx_bdc_created_at ON building_duplicate_candidates(created_at);

-- ---------------------------------------------------------------------------
-- 2. building_dedupe_review_items — human review queue before consolidation.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_dedupe_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_duplicate_candidate_id uuid REFERENCES building_duplicate_candidates(id),
  review_type text,                              -- duplicate_building_review, canonical_anchor_review, merge_plan_review
  status text DEFAULT 'pending',                 -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bdri_candidate_id ON building_dedupe_review_items(building_duplicate_candidate_id);
CREATE INDEX IF NOT EXISTS idx_bdri_review_type ON building_dedupe_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_bdri_status ON building_dedupe_review_items(status);
CREATE INDEX IF NOT EXISTS idx_bdri_created_at ON building_dedupe_review_items(created_at);

-- ---------------------------------------------------------------------------
-- 3. building_dedupe_action_log — future audit log for merge/consolidation.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_dedupe_action_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_duplicate_candidate_id uuid REFERENCES building_duplicate_candidates(id),
  action_type text,
  old_status text,
  new_status text,
  performed_by text,
  action_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bdal_candidate_id ON building_dedupe_action_log(building_duplicate_candidate_id);
CREATE INDEX IF NOT EXISTS idx_bdal_action_type ON building_dedupe_action_log(action_type);
CREATE INDEX IF NOT EXISTS idx_bdal_created_at ON building_dedupe_action_log(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (reuse project-wide set_updated_at()).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_building_duplicate_candidates_updated_at ON building_duplicate_candidates;
CREATE TRIGGER trg_building_duplicate_candidates_updated_at
BEFORE UPDATE ON building_duplicate_candidates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_building_dedupe_review_items_updated_at ON building_dedupe_review_items;
CREATE TRIGGER trg_building_dedupe_review_items_updated_at
BEFORE UPDATE ON building_dedupe_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task E — read-only dashboard views. Property/business fields only; no personal data.
-- ===========================================================================

DROP VIEW IF EXISTS vw_building_dedupe_dashboard;
DROP VIEW IF EXISTS vw_imperial_heights_building_anchor_summary;
DROP VIEW IF EXISTS vw_building_dedupe_review_queue;

-- 1. Per-candidate dedupe dashboard with side-by-side anchor counts.
CREATE VIEW vw_building_dedupe_dashboard AS
SELECT
  c.id AS candidate_id,
  c.candidate_group_key,
  c.canonical_building_id,
  bc.name AS canonical_building_name,
  c.duplicate_building_id,
  bd.name AS duplicate_building_name,
  c.duplicate_strength,
  c.status,
  c.reason,
  c.safe_summary,
  (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = c.canonical_building_id AND r.relationship_status = 'active') AS canonical_active_owner_relationships,
  (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = c.duplicate_building_id AND r.relationship_status = 'active') AS duplicate_active_owner_relationships,
  (SELECT count(*) FROM building_units u WHERE u.building_id = c.canonical_building_id) AS canonical_unit_count,
  (SELECT count(*) FROM building_units u WHERE u.building_id = c.duplicate_building_id) AS duplicate_unit_count,
  (SELECT count(*) FROM building_web_profiles p WHERE p.building_id = c.canonical_building_id) AS canonical_profile_count,
  (SELECT count(*) FROM building_web_profiles p WHERE p.building_id = c.duplicate_building_id) AS duplicate_profile_count,
  (SELECT r.status FROM building_dedupe_review_items r WHERE r.building_duplicate_candidate_id = c.id ORDER BY r.created_at LIMIT 1) AS review_status
FROM building_duplicate_candidates c
LEFT JOIN buildings bc ON bc.id = c.canonical_building_id
LEFT JOIN buildings bd ON bd.id = c.duplicate_building_id;

-- 2. Imperial Heights building-anchor summary (one row per Imperial-Heights-like building).
CREATE VIEW vw_imperial_heights_building_anchor_summary AS
SELECT
  b.id AS building_id,
  b.name AS building_name,
  (SELECT u.building_code FROM building_units u WHERE u.building_id = b.id AND u.building_code IS NOT NULL ORDER BY u.created_at LIMIT 1) AS building_code,
  (SELECT count(*) FROM building_aliases a WHERE a.building_id = b.id) AS alias_count,
  (SELECT count(*) FROM building_units u WHERE u.building_id = b.id AND u.canonical_status = 'active') AS active_unit_count,
  (SELECT count(*) FROM building_units u WHERE u.building_id = b.id AND u.canonical_status = 'needs_review') AS needs_review_unit_count,
  (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = b.id AND r.relationship_status = 'active') AS active_owner_relationship_count,
  (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = b.id AND r.relationship_status = 'pending') AS pending_relationship_count,
  (SELECT count(*) FROM building_web_profiles p WHERE p.building_id = b.id) AS seo_profile_count,
  (SELECT count(*) FROM content_briefs cb WHERE cb.building_id = b.id) AS content_brief_count,
  (SELECT count(DISTINCT s.sf) FROM (
      SELECT u.source_file_id AS sf FROM building_units u WHERE u.building_id = b.id AND u.source_file_id IS NOT NULL
      UNION
      SELECT a.source_file_id FROM building_aliases a WHERE a.building_id = b.id AND a.source_file_id IS NOT NULL
   ) s) AS source_trace_count,
  CASE
    WHEN (SELECT count(*) FROM building_web_profiles p WHERE p.building_id = b.id) > 0 THEN 'proposed_canonical_anchor'
    WHEN (SELECT count(*) FROM building_web_profiles p2
            JOIN buildings b2 ON b2.id = p2.building_id
           WHERE lower(b2.name) = lower(b.name)) > 0 THEN 'merge_into_canonical'
    ELSE 'needs_human_review'
  END AS recommended_role
FROM buildings b
WHERE lower(b.name) LIKE '%imperial heights%';

-- 3. Building dedupe human review queue.
CREATE VIEW vw_building_dedupe_review_queue AS
SELECT
  r.id AS review_item_id,
  r.building_duplicate_candidate_id AS candidate_id,
  bc.name AS canonical_building_name,
  bd.name AS duplicate_building_name,
  r.review_type,
  r.status,
  r.priority,
  c.safe_summary,
  r.created_at
FROM building_dedupe_review_items r
LEFT JOIN building_duplicate_candidates c ON c.id = r.building_duplicate_candidate_id
LEFT JOIN buildings bc ON bc.id = c.canonical_building_id
LEFT JOIN buildings bd ON bd.id = c.duplicate_building_id;
