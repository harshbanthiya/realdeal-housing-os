-- Phase 6.2: Wix CMS field mapping + content review + publishing readiness.
--
-- Foundation for FUTURE Wix publishing. NOTHING here publishes to Wix or calls any
-- Wix/external API; these tables only describe how Real Deal OS content WOULD map to
-- Wix CMS collections, queue content briefs for human review, and record pre-publish
-- checklist results. Read-only dashboard views never expose personal data
-- (names/phones/emails/addresses). Building/unit/content fields are business data.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. wix_cms_collections — Wix CMS collections we expect to publish into later.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wix_cms_collections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  collection_key text NOT NULL,
  collection_name text,
  purpose text,
  status text DEFAULT 'planned',             -- planned, mapped, ready_for_test, active, paused, archived
  wix_collection_id text,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wix_coll_collection_key ON wix_cms_collections(collection_key);
CREATE INDEX IF NOT EXISTS idx_wix_coll_status ON wix_cms_collections(status);
CREATE INDEX IF NOT EXISTS idx_wix_coll_created_at ON wix_cms_collections(created_at);

-- ---------------------------------------------------------------------------
-- 2. wix_cms_field_mappings — map Real Deal OS fields to Wix CMS fields.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wix_cms_field_mappings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  wix_cms_collection_id uuid REFERENCES wix_cms_collections(id),
  source_table text,
  source_field text,
  wix_field_key text,
  wix_field_type text,
  required boolean DEFAULT false,
  transform_rule text,
  status text DEFAULT 'draft',               -- draft, reviewed, approved, deprecated
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wix_map_collection_id ON wix_cms_field_mappings(wix_cms_collection_id);
CREATE INDEX IF NOT EXISTS idx_wix_map_status ON wix_cms_field_mappings(status);
CREATE INDEX IF NOT EXISTS idx_wix_map_wix_field_key ON wix_cms_field_mappings(wix_field_key);
CREATE INDEX IF NOT EXISTS idx_wix_map_created_at ON wix_cms_field_mappings(created_at);

-- ---------------------------------------------------------------------------
-- 3. content_review_items — human review queue for content briefs.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  building_web_profile_id uuid REFERENCES building_web_profiles(id),
  review_type text,                          -- brief_review, seo_review, legal_review, publishing_readiness, ai_output_review
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
CREATE INDEX IF NOT EXISTS idx_cri_content_brief_id ON content_review_items(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_cri_profile_id ON content_review_items(building_web_profile_id);
CREATE INDEX IF NOT EXISTS idx_cri_review_type ON content_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_cri_status ON content_review_items(status);
CREATE INDEX IF NOT EXISTS idx_cri_priority ON content_review_items(priority);
CREATE INDEX IF NOT EXISTS idx_cri_created_at ON content_review_items(created_at);

-- ---------------------------------------------------------------------------
-- 4. publishing_readiness_checks — checklist before FUTURE Wix publishing.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS publishing_readiness_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  content_publishing_queue_id uuid REFERENCES content_publishing_queue(id),
  check_type text,                           -- cms_mapping, title_present, slug_present, meta_present, human_approved, no_external_call_required, no_outreach, wix_ready
  status text DEFAULT 'pending',             -- pending, passed, failed, waived
  details text,
  checked_at timestamptz,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prc_content_brief_id ON publishing_readiness_checks(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_prc_pubqueue_id ON publishing_readiness_checks(content_publishing_queue_id);
CREATE INDEX IF NOT EXISTS idx_prc_check_type ON publishing_readiness_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_prc_status ON publishing_readiness_checks(status);
CREATE INDEX IF NOT EXISTS idx_prc_created_at ON publishing_readiness_checks(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers.
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_wix_cms_collections_updated_at ON wix_cms_collections;
CREATE TRIGGER trg_wix_cms_collections_updated_at
BEFORE UPDATE ON wix_cms_collections
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_wix_cms_field_mappings_updated_at ON wix_cms_field_mappings;
CREATE TRIGGER trg_wix_cms_field_mappings_updated_at
BEFORE UPDATE ON wix_cms_field_mappings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_review_items_updated_at ON content_review_items;
CREATE TRIGGER trg_content_review_items_updated_at
BEFORE UPDATE ON content_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_publishing_readiness_checks_updated_at ON publishing_readiness_checks;
CREATE TRIGGER trg_publishing_readiness_checks_updated_at
BEFORE UPDATE ON publishing_readiness_checks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task E — read-only dashboard views. Counts/metadata only; no personal data.
-- ===========================================================================

DROP VIEW IF EXISTS vw_wix_cms_mapping_dashboard;
DROP VIEW IF EXISTS vw_content_review_dashboard;
DROP VIEW IF EXISTS vw_publishing_readiness_dashboard;
DROP VIEW IF EXISTS vw_imperial_heights_content_plan;

-- 1. Wix CMS mapping coverage per collection.
CREATE VIEW vw_wix_cms_mapping_dashboard AS
SELECT
  c.collection_key,
  c.collection_name,
  c.status AS collection_status,
  count(m.id) AS mapped_field_count,
  count(m.id) FILTER (WHERE m.required) AS required_field_count,
  count(m.id) FILTER (WHERE m.status = 'approved') AS approved_mapping_count,
  count(m.id) FILTER (WHERE m.status = 'draft') AS draft_mapping_count,
  CASE
    WHEN count(m.id) = 0 THEN 'no_mappings'
    WHEN count(m.id) FILTER (WHERE m.status = 'draft') > 0 THEN 'mappings_in_draft'
    WHEN count(m.id) FILTER (WHERE m.status = 'approved') = count(m.id) THEN 'all_mappings_approved'
    ELSE 'mappings_in_review'
  END AS readiness_status
FROM wix_cms_collections c
LEFT JOIN wix_cms_field_mappings m ON m.wix_cms_collection_id = c.id
GROUP BY c.id, c.collection_key, c.collection_name, c.status;

-- 2. Content review queue (no personal data).
CREATE VIEW vw_content_review_dashboard AS
SELECT
  cri.id AS content_review_item_id,
  cri.content_brief_id,
  COALESCE(b.name, p.building_name) AS building_name,
  p.profile_slug,
  cb.content_type,
  cb.title,
  cb.target_keyword,
  cri.review_type,
  cri.status AS review_status,
  cri.priority,
  cri.assigned_to,
  cri.reviewed_by,
  cri.reviewed_at,
  cri.created_at
FROM content_review_items cri
LEFT JOIN content_briefs cb ON cb.id = cri.content_brief_id
LEFT JOIN building_web_profiles p ON p.id = COALESCE(cri.building_web_profile_id, cb.building_web_profile_id)
LEFT JOIN buildings b ON b.id = p.building_id;

-- 3. Publishing readiness per publishing-queue row. ready_for_publish is true ONLY
--    when there is at least one check, no check is failed/pending, and the queue row
--    is approved/ready_for_review. (Nothing here publishes.)
CREATE VIEW vw_publishing_readiness_dashboard AS
SELECT
  cb.id AS content_brief_id,
  q.id AS publishing_queue_id,
  COALESCE(b.name, p.building_name) AS building_name,
  p.profile_slug,
  cb.title,
  q.channel,
  q.publish_status,
  count(prc.id) AS check_count,
  count(prc.id) FILTER (WHERE prc.status = 'passed') AS passed_count,
  count(prc.id) FILTER (WHERE prc.status = 'failed') AS failed_count,
  count(prc.id) FILTER (WHERE prc.status = 'pending') AS pending_count,
  (
    count(prc.id) > 0
    AND count(prc.id) FILTER (WHERE prc.status = 'failed') = 0
    AND count(prc.id) FILTER (WHERE prc.status = 'pending') = 0
    AND q.publish_status IN ('approved', 'ready_for_review')
  ) AS ready_for_publish,
  CASE
    WHEN count(prc.id) = 0 THEN 'no_readiness_checks'
    WHEN count(prc.id) FILTER (WHERE prc.status = 'failed') > 0 THEN 'checks_failed'
    WHEN count(prc.id) FILTER (WHERE prc.status = 'pending') > 0 THEN 'checks_pending'
    WHEN q.publish_status NOT IN ('approved', 'ready_for_review') THEN 'publish_status_not_approved'
    ELSE NULL
  END AS blocked_reason
FROM content_publishing_queue q
LEFT JOIN content_briefs cb ON cb.id = q.content_brief_id
LEFT JOIN building_web_profiles p ON p.id = cb.building_web_profile_id
LEFT JOIN buildings b ON b.id = p.building_id
LEFT JOIN publishing_readiness_checks prc ON prc.content_publishing_queue_id = q.id
GROUP BY cb.id, q.id, b.name, p.building_name, p.profile_slug, cb.title, q.channel, q.publish_status;

-- 4. Human-friendly Imperial Heights plan rollup (one row per web profile).
CREATE VIEW vw_imperial_heights_content_plan AS
SELECT
  COALESCE(b.name, p.building_name) AS building_name,
  p.profile_slug,
  p.seo_status,
  (SELECT count(*) FROM seo_keywords k WHERE k.building_web_profile_id = p.id) AS keyword_count,
  (SELECT count(*) FROM content_briefs cb WHERE cb.building_web_profile_id = p.id) AS content_brief_count,
  (SELECT count(*) FROM content_publishing_queue q
     JOIN content_briefs cb ON cb.id = q.content_brief_id
    WHERE cb.building_web_profile_id = p.id AND q.publish_status = 'draft') AS publishing_draft_count,
  (SELECT count(*) FROM ai_agent_tasks t
    WHERE t.raw_input->>'building_name' = COALESCE(b.name, p.building_name)
      AND t.raw_input->>'phase' = '6.1') AS ai_task_count,
  (SELECT count(*) FROM content_review_items cri
     JOIN content_briefs cb ON cb.id = cri.content_brief_id
    WHERE cb.building_web_profile_id = p.id AND cri.status = 'pending') AS content_review_pending_count,
  (SELECT count(*) FROM publishing_readiness_checks prc
     JOIN content_publishing_queue q ON q.id = prc.content_publishing_queue_id
     JOIN content_briefs cb ON cb.id = q.content_brief_id
    WHERE cb.building_web_profile_id = p.id AND prc.status = 'pending') AS readiness_pending_count,
  (SELECT count(*) FROM content_publishing_queue q
     JOIN content_briefs cb ON cb.id = q.content_brief_id
    WHERE cb.building_web_profile_id = p.id AND q.publish_status = 'published') AS published_count,
  0::bigint AS communications_sent_count
FROM building_web_profiles p
LEFT JOIN buildings b ON b.id = p.building_id;
