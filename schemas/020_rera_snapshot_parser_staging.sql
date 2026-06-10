-- Phase 6.13: review-gated MahaRERA snapshot parser staging.
--
-- Staging tables + safe dashboards for parsing a post-CAPTCHA MahaRERA snapshot (captured by
-- scripts/fetch_rera_page_playwright.py under the git-ignored exports/rera_snapshots/) into
-- REVIEW-GATED candidate facts, and comparing them against the Phase 6.9 manual RERA rows.
--
-- This phase is staging + parser ONLY. NOTHING here verifies a RERA profile, accepts a match,
-- merges buildings, resolves source gaps, marks content ready, publishes, or sends outreach.
-- Parsed facts are UNTRUSTED candidates (trusted_for_db=false, human_review_required=true) and
-- never touch the canonical rera_project_profiles / rera_building_match_candidates /
-- rera_carpet_area_records / rera_project_status_checks rows.
--
-- PRIVACY: complaint / litigation / appeal / non-compliance / promoter-landowner sections are
-- stored as COUNTS / STATUS FLAGS only. Personal names (complainant / director / allottee /
-- respondent / advocate / petitioner) are NEVER stored here, and the views below never expose
-- raw page text. Official public project fields (project name, promoter/company name, RERA
-- registration number, status, dates) are official records, not personal contact data.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. rera_snapshot_captures — one row per captured snapshot folder (no raw page contents).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_snapshot_captures (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url text NOT NULL,
  output_label text,
  snapshot_folder text,
  capture_method text DEFAULT 'playwright_human_captcha',
  captcha_solved_by_human boolean DEFAULT false,
  external_call_made boolean DEFAULT true,
  trusted_for_db boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  captured_at timestamptz,
  metadata_summary jsonb DEFAULT '{}'::jsonb,  -- counts/booleans only, never raw page text
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rsc_created_at ON rera_snapshot_captures(created_at);
CREATE INDEX IF NOT EXISTS idx_rsc_output_label ON rera_snapshot_captures(output_label);

-- ---------------------------------------------------------------------------
-- 2. rera_parsed_fact_candidates — review-gated facts parsed from a snapshot.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_parsed_fact_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_snapshot_capture_id uuid REFERENCES rera_snapshot_captures(id),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  fact_group text,        -- project_profile, promoter, wing_building, carpet_area, status_check, document_check, legal_risk_count
  fact_key text,
  fact_value_text text,   -- NEVER a personal name; legal-risk groups store counts in fact_value_numeric
  fact_value_numeric numeric,
  fact_value_date date,
  unit text,
  confidence_score numeric,
  parse_status text DEFAULT 'candidate',  -- candidate, matched_manual, mismatch_manual, needs_human_review, rejected
  safe_for_public_use boolean DEFAULT false,
  personal_data_excluded boolean DEFAULT true,
  source_location_hint text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rpfc_capture_id ON rera_parsed_fact_candidates(rera_snapshot_capture_id);
CREATE INDEX IF NOT EXISTS idx_rpfc_profile_id ON rera_parsed_fact_candidates(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rpfc_fact_group ON rera_parsed_fact_candidates(fact_group);
CREATE INDEX IF NOT EXISTS idx_rpfc_fact_key ON rera_parsed_fact_candidates(fact_key);
CREATE INDEX IF NOT EXISTS idx_rpfc_parse_status ON rera_parsed_fact_candidates(parse_status);
CREATE INDEX IF NOT EXISTS idx_rpfc_created_at ON rera_parsed_fact_candidates(created_at);

-- ---------------------------------------------------------------------------
-- 3. rera_snapshot_compare_results — parsed snapshot facts vs Phase 6.9 manual rows.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_snapshot_compare_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_snapshot_capture_id uuid REFERENCES rera_snapshot_captures(id),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  compare_type text,   -- project_profile_compare, carpet_count_compare, apartment_total_compare, status_check_compare, risk_count_compare
  compare_status text DEFAULT 'pending_review',  -- matched, mismatch, missing_in_snapshot, missing_in_manual, pending_review
  parsed_value text,   -- safe scalar/count summary only, never personal names
  manual_value text,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rscr_capture_id ON rera_snapshot_compare_results(rera_snapshot_capture_id);
CREATE INDEX IF NOT EXISTS idx_rscr_profile_id ON rera_snapshot_compare_results(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rscr_compare_type ON rera_snapshot_compare_results(compare_type);
CREATE INDEX IF NOT EXISTS idx_rscr_compare_status ON rera_snapshot_compare_results(compare_status);
CREATE INDEX IF NOT EXISTS idx_rscr_created_at ON rera_snapshot_compare_results(created_at);

-- ---------------------------------------------------------------------------
-- 4. rera_snapshot_review_items — human review queue for parsed snapshot facts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_snapshot_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_snapshot_capture_id uuid REFERENCES rera_snapshot_captures(id),
  rera_parsed_fact_candidate_id uuid REFERENCES rera_parsed_fact_candidates(id),
  rera_snapshot_compare_result_id uuid REFERENCES rera_snapshot_compare_results(id),
  review_type text,  -- parsed_fact_review, parser_manual_match_review, parser_manual_mismatch_review, privacy_safety_review
  status text DEFAULT 'pending',  -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rsri_capture_id ON rera_snapshot_review_items(rera_snapshot_capture_id);
CREATE INDEX IF NOT EXISTS idx_rsri_parsed_fact_id ON rera_snapshot_review_items(rera_parsed_fact_candidate_id);
CREATE INDEX IF NOT EXISTS idx_rsri_compare_id ON rera_snapshot_review_items(rera_snapshot_compare_result_id);
CREATE INDEX IF NOT EXISTS idx_rsri_review_type ON rera_snapshot_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_rsri_status ON rera_snapshot_review_items(status);
CREATE INDEX IF NOT EXISTS idx_rsri_created_at ON rera_snapshot_review_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (project pattern: set_updated_at() from 001_initial_schema.sql).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_rera_snapshot_captures_updated_at ON rera_snapshot_captures;
CREATE TRIGGER trg_rera_snapshot_captures_updated_at
BEFORE UPDATE ON rera_snapshot_captures FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_parsed_fact_candidates_updated_at ON rera_parsed_fact_candidates;
CREATE TRIGGER trg_rera_parsed_fact_candidates_updated_at
BEFORE UPDATE ON rera_parsed_fact_candidates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_snapshot_compare_results_updated_at ON rera_snapshot_compare_results;
CREATE TRIGGER trg_rera_snapshot_compare_results_updated_at
BEFORE UPDATE ON rera_snapshot_compare_results FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_snapshot_review_items_updated_at ON rera_snapshot_review_items;
CREATE TRIGGER trg_rera_snapshot_review_items_updated_at
BEFORE UPDATE ON rera_snapshot_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 5. Safe read-only dashboards (counts/scalars only; never raw page text or personal names).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_rera_snapshot_capture_dashboard AS
SELECT
  c.id                       AS snapshot_capture_id,
  c.source_url,
  c.output_label,
  c.capture_method,
  c.captcha_solved_by_human,
  c.trusted_for_db,
  c.human_review_required,
  c.captured_at,
  (SELECT count(*) FROM rera_parsed_fact_candidates f WHERE f.rera_snapshot_capture_id = c.id) AS parsed_fact_count,
  (SELECT count(*) FROM rera_snapshot_compare_results r WHERE r.rera_snapshot_capture_id = c.id) AS compare_result_count,
  (SELECT count(*) FROM rera_snapshot_review_items i WHERE i.rera_snapshot_capture_id = c.id AND i.status = 'pending') AS review_pending_count
FROM rera_snapshot_captures c;

-- Parsed-fact dashboard. fact_value_text is project/building/status text only (the parser
-- never writes personal names here); legal-risk groups carry counts in fact_value_numeric.
CREATE OR REPLACE VIEW vw_rera_parsed_fact_candidate_dashboard AS
SELECT
  f.id                       AS parsed_fact_id,
  f.rera_snapshot_capture_id AS snapshot_capture_id,
  f.fact_group,
  f.fact_key,
  f.fact_value_text,
  f.fact_value_numeric,
  f.fact_value_date,
  f.unit,
  f.confidence_score,
  f.parse_status,
  f.safe_for_public_use,
  f.personal_data_excluded,
  f.source_location_hint
FROM rera_parsed_fact_candidates f;

CREATE OR REPLACE VIEW vw_rera_snapshot_compare_dashboard AS
SELECT
  r.id                       AS compare_result_id,
  r.rera_snapshot_capture_id AS snapshot_capture_id,
  r.compare_type,
  r.compare_status,
  r.parsed_value,
  r.manual_value,
  r.safe_summary
FROM rera_snapshot_compare_results r;

CREATE OR REPLACE VIEW vw_rera_snapshot_review_queue AS
SELECT
  i.id                       AS review_item_id,
  i.rera_snapshot_capture_id AS snapshot_capture_id,
  i.review_type,
  i.status,
  i.priority,
  f.fact_group,
  f.fact_key,
  r.compare_type,
  r.compare_status,
  i.created_at
FROM rera_snapshot_review_items i
LEFT JOIN rera_parsed_fact_candidates f ON f.id = i.rera_parsed_fact_candidate_id
LEFT JOIN rera_snapshot_compare_results r ON r.id = i.rera_snapshot_compare_result_id;

-- Parser readiness for Imperial Heights. ready_* are HARD false: parser output is untrusted
-- and must be human-reviewed; nothing here may flip canonical/profile/content readiness.
CREATE OR REPLACE VIEW vw_imperial_heights_rera_parser_readiness AS
WITH prof AS (
  SELECT p.id AS profile_id, wp.profile_slug
  FROM rera_project_profiles p
  JOIN building_web_profiles wp ON wp.id = p.building_web_profile_id
  WHERE wp.profile_slug = 'imperial-heights-goregaon-west'
)
SELECT
  prof.profile_slug,
  (SELECT count(*) FROM rera_snapshot_captures c
     WHERE c.id IN (SELECT rera_snapshot_capture_id FROM rera_parsed_fact_candidates
                     WHERE rera_project_profile_id = prof.profile_id)) AS snapshot_capture_count,
  (SELECT count(*) FROM rera_parsed_fact_candidates f WHERE f.rera_project_profile_id = prof.profile_id) AS parsed_fact_count,
  (SELECT count(*) FROM rera_snapshot_compare_results r WHERE r.rera_project_profile_id = prof.profile_id AND r.compare_status = 'matched') AS matched_manual_count,
  (SELECT count(*) FROM rera_snapshot_compare_results r WHERE r.rera_project_profile_id = prof.profile_id AND r.compare_status = 'mismatch') AS mismatch_manual_count,
  (SELECT count(*) FROM rera_snapshot_review_items i
     JOIN rera_parsed_fact_candidates f ON f.id = i.rera_parsed_fact_candidate_id
     WHERE f.rera_project_profile_id = prof.profile_id AND i.status = 'pending') AS review_pending_count,
  (SELECT count(*) FROM rera_snapshot_review_items i
     JOIN rera_parsed_fact_candidates f ON f.id = i.rera_parsed_fact_candidate_id
     WHERE f.rera_project_profile_id = prof.profile_id AND i.review_type = 'privacy_safety_review' AND i.status = 'pending') AS privacy_safety_pending_count,
  false AS ready_to_update_rera_profile,
  false AS ready_for_content_fact_use,
  'parser output is untrusted; human review of parsed candidates required before any RERA profile update or content fact use' AS blocked_reason
FROM prof;
