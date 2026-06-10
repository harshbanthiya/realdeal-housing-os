-- Phase 6.8: MahaRERA verification foundation (schema + fake workflow only).
--
-- Database foundation for FUTURE official RERA (MahaRERA) building verification: official
-- project profiles, internal-building <-> RERA-project match candidates, official carpet-area
-- records, compliance/status/risk checks, area-mismatch candidates, and a human review queue.
--
-- This phase is schema + fake workflow ONLY. NOTHING here scrapes MahaRERA, calls any
-- external/Wix API, browses the web, merges/auto-corrects building data, resolves source
-- gaps, marks content ready, publishes, or sends outreach. Read-only views never expose
-- personal CONTACT data (no phones/emails of people); official public project fields
-- (project name, promoter/company name, RERA registration number) are official records.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. rera_project_profiles — official RERA project-level profile.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_project_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  building_web_profile_id uuid REFERENCES building_web_profiles(id),
  rera_authority text DEFAULT 'MahaRERA',
  rera_registration_number text,
  official_project_name text,
  promoter_name text,
  project_type text,
  project_status text,
  registration_status text,
  registration_date date,
  registration_valid_until date,
  completion_date date,
  district text,
  taluka text,
  locality text,
  pincode text,
  official_project_url text,
  certificate_url text,
  last_verified_at timestamptz,
  verification_status text DEFAULT 'unverified',  -- unverified, search_needed, candidate_found, verified, mismatch_found, needs_human_review, archived
  confidence_score numeric,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rpp_building_id ON rera_project_profiles(building_id);
CREATE INDEX IF NOT EXISTS idx_rpp_building_web_profile_id ON rera_project_profiles(building_web_profile_id);
CREATE INDEX IF NOT EXISTS idx_rpp_registration_number ON rera_project_profiles(rera_registration_number);
CREATE INDEX IF NOT EXISTS idx_rpp_official_project_name ON rera_project_profiles(official_project_name);
CREATE INDEX IF NOT EXISTS idx_rpp_promoter_name ON rera_project_profiles(promoter_name);
CREATE INDEX IF NOT EXISTS idx_rpp_verification_status ON rera_project_profiles(verification_status);
CREATE INDEX IF NOT EXISTS idx_rpp_created_at ON rera_project_profiles(created_at);

-- ---------------------------------------------------------------------------
-- 2. rera_building_match_candidates — internal anchor <-> RERA project matches.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_building_match_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  match_status text DEFAULT 'candidate',          -- candidate, accepted, rejected, needs_more_info
  match_strength text DEFAULT 'candidate',        -- strong, medium, weak, candidate
  match_reason text,
  name_similarity_score numeric,
  location_similarity_score numeric,
  pincode_match boolean,
  developer_match boolean,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rbmc_building_id ON rera_building_match_candidates(building_id);
CREATE INDEX IF NOT EXISTS idx_rbmc_project_profile_id ON rera_building_match_candidates(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rbmc_match_status ON rera_building_match_candidates(match_status);
CREATE INDEX IF NOT EXISTS idx_rbmc_match_strength ON rera_building_match_candidates(match_strength);
CREATE INDEX IF NOT EXISTS idx_rbmc_created_at ON rera_building_match_candidates(created_at);

-- ---------------------------------------------------------------------------
-- 3. rera_carpet_area_records — official apartment/carpet-area records.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_carpet_area_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  building_name text,
  wing text,
  apartment_type text,
  carpet_area_sqm numeric,
  carpet_area_sqft numeric,
  apartment_count integer,
  booked_count integer,
  source_label text,
  verification_status text DEFAULT 'unverified',  -- unverified, verified, needs_human_review, mismatch_found
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rcar_project_profile_id ON rera_carpet_area_records(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rcar_verification_status ON rera_carpet_area_records(verification_status);
CREATE INDEX IF NOT EXISTS idx_rcar_created_at ON rera_carpet_area_records(created_at);

-- ---------------------------------------------------------------------------
-- 4. rera_project_status_checks — compliance/status/risk flags.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_project_status_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  check_type text,                                -- registered_project, lapsed_project, revoked_project, abeyance, deregistered, nclt, complaint_present, extension_present, document_available
  check_status text DEFAULT 'unknown',            -- unknown, clear, present, not_found, needs_review
  severity text DEFAULT 'info',                   -- info, warning, blocker
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  checked_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rpsc_project_profile_id ON rera_project_status_checks(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rpsc_check_type ON rera_project_status_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_rpsc_check_status ON rera_project_status_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_rpsc_created_at ON rera_project_status_checks(created_at);

-- ---------------------------------------------------------------------------
-- 5. rera_area_mismatch_candidates — internal area claim vs RERA carpet area.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_area_mismatch_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  rera_carpet_area_record_id uuid REFERENCES rera_carpet_area_records(id),
  internal_source_table text,
  internal_source_id uuid,
  internal_area_value numeric,
  internal_area_unit text,
  rera_area_sqft numeric,
  mismatch_percent numeric,
  mismatch_status text DEFAULT 'candidate',       -- candidate, accepted_mismatch, rejected, needs_more_info, corrected
  suspected_reason text,                          -- carpet_vs_builtup, carpet_vs_saleable, typo, unit_mismatch, unknown
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ramc_building_id ON rera_area_mismatch_candidates(building_id);
CREATE INDEX IF NOT EXISTS idx_ramc_carpet_area_record_id ON rera_area_mismatch_candidates(rera_carpet_area_record_id);
CREATE INDEX IF NOT EXISTS idx_ramc_mismatch_status ON rera_area_mismatch_candidates(mismatch_status);
CREATE INDEX IF NOT EXISTS idx_ramc_created_at ON rera_area_mismatch_candidates(created_at);

-- ---------------------------------------------------------------------------
-- 6. rera_verification_review_items — human review queue.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rera_verification_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  rera_building_match_candidate_id uuid REFERENCES rera_building_match_candidates(id),
  rera_area_mismatch_candidate_id uuid REFERENCES rera_area_mismatch_candidates(id),
  review_type text,                               -- rera_project_match_review, rera_fact_review, rera_area_mismatch_review, rera_status_risk_review
  status text DEFAULT 'pending',                  -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rvri_project_profile_id ON rera_verification_review_items(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_rvri_match_candidate_id ON rera_verification_review_items(rera_building_match_candidate_id);
CREATE INDEX IF NOT EXISTS idx_rvri_area_mismatch_candidate_id ON rera_verification_review_items(rera_area_mismatch_candidate_id);
CREATE INDEX IF NOT EXISTS idx_rvri_review_type ON rera_verification_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_rvri_status ON rera_verification_review_items(status);
CREATE INDEX IF NOT EXISTS idx_rvri_created_at ON rera_verification_review_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (reuse project-wide set_updated_at()).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_rera_project_profiles_updated_at ON rera_project_profiles;
CREATE TRIGGER trg_rera_project_profiles_updated_at
BEFORE UPDATE ON rera_project_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_building_match_candidates_updated_at ON rera_building_match_candidates;
CREATE TRIGGER trg_rera_building_match_candidates_updated_at
BEFORE UPDATE ON rera_building_match_candidates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_carpet_area_records_updated_at ON rera_carpet_area_records;
CREATE TRIGGER trg_rera_carpet_area_records_updated_at
BEFORE UPDATE ON rera_carpet_area_records FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_project_status_checks_updated_at ON rera_project_status_checks;
CREATE TRIGGER trg_rera_project_status_checks_updated_at
BEFORE UPDATE ON rera_project_status_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_area_mismatch_candidates_updated_at ON rera_area_mismatch_candidates;
CREATE TRIGGER trg_rera_area_mismatch_candidates_updated_at
BEFORE UPDATE ON rera_area_mismatch_candidates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_rera_verification_review_items_updated_at ON rera_verification_review_items;
CREATE TRIGGER trg_rera_verification_review_items_updated_at
BEFORE UPDATE ON rera_verification_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task D — read-only dashboard views. No personal CONTACT data.
-- ===========================================================================

DROP VIEW IF EXISTS vw_rera_project_verification_dashboard;
DROP VIEW IF EXISTS vw_rera_building_match_dashboard;
DROP VIEW IF EXISTS vw_rera_area_mismatch_dashboard;
DROP VIEW IF EXISTS vw_rera_status_risk_dashboard;
DROP VIEW IF EXISTS vw_rera_verification_review_queue;
DROP VIEW IF EXISTS vw_imperial_heights_rera_readiness;

-- 1. RERA project verification dashboard (one row per RERA project profile).
CREATE VIEW vw_rera_project_verification_dashboard AS
SELECT
  pp.id AS rera_project_profile_id,
  pp.building_id,
  b.name AS building_name,
  pp.building_web_profile_id,
  pp.rera_authority,
  pp.rera_registration_number,
  pp.official_project_name,
  pp.promoter_name,
  pp.project_type,
  pp.project_status,
  pp.registration_status,
  pp.verification_status,
  pp.confidence_score,
  pp.district,
  pp.locality,
  pp.pincode,
  pp.last_verified_at,
  (SELECT count(*) FROM rera_building_match_candidates m WHERE m.rera_project_profile_id = pp.id) AS match_candidate_count,
  (SELECT count(*) FROM rera_building_match_candidates m WHERE m.rera_project_profile_id = pp.id AND m.match_status = 'accepted') AS accepted_match_count,
  (SELECT count(*) FROM rera_carpet_area_records c WHERE c.rera_project_profile_id = pp.id) AS carpet_area_record_count,
  (SELECT count(*) FROM rera_project_status_checks s WHERE s.rera_project_profile_id = pp.id) AS status_check_count,
  (SELECT count(*) FROM rera_project_status_checks s WHERE s.rera_project_profile_id = pp.id AND s.severity = 'blocker' AND s.check_status = 'present') AS blocker_risk_count,
  pp.created_at
FROM rera_project_profiles pp
LEFT JOIN buildings b ON b.id = pp.building_id;

-- 2. RERA building-match dashboard.
CREATE VIEW vw_rera_building_match_dashboard AS
SELECT
  m.id AS match_candidate_id,
  m.building_id,
  b.name AS building_name,
  m.rera_project_profile_id,
  pp.official_project_name,
  pp.rera_registration_number,
  m.match_status,
  m.match_strength,
  m.match_reason,
  m.name_similarity_score,
  m.location_similarity_score,
  m.pincode_match,
  m.developer_match,
  (SELECT r.status FROM rera_verification_review_items r WHERE r.rera_building_match_candidate_id = m.id ORDER BY r.created_at LIMIT 1) AS review_status,
  m.created_at
FROM rera_building_match_candidates m
LEFT JOIN buildings b ON b.id = m.building_id
LEFT JOIN rera_project_profiles pp ON pp.id = m.rera_project_profile_id;

-- 3. RERA area-mismatch dashboard.
CREATE VIEW vw_rera_area_mismatch_dashboard AS
SELECT
  am.id AS area_mismatch_candidate_id,
  am.building_id,
  b.name AS building_name,
  am.rera_carpet_area_record_id,
  ca.apartment_type,
  ca.wing,
  am.internal_source_table,
  am.internal_area_value,
  am.internal_area_unit,
  am.rera_area_sqft,
  am.mismatch_percent,
  am.mismatch_status,
  am.suspected_reason,
  (SELECT r.status FROM rera_verification_review_items r WHERE r.rera_area_mismatch_candidate_id = am.id ORDER BY r.created_at LIMIT 1) AS review_status,
  am.created_at
FROM rera_area_mismatch_candidates am
LEFT JOIN buildings b ON b.id = am.building_id
LEFT JOIN rera_carpet_area_records ca ON ca.id = am.rera_carpet_area_record_id;

-- 4. RERA status/risk dashboard.
CREATE VIEW vw_rera_status_risk_dashboard AS
SELECT
  s.id AS status_check_id,
  s.rera_project_profile_id,
  pp.official_project_name,
  pp.rera_registration_number,
  s.check_type,
  s.check_status,
  s.severity,
  s.safe_summary,
  s.checked_at,
  s.created_at
FROM rera_project_status_checks s
LEFT JOIN rera_project_profiles pp ON pp.id = s.rera_project_profile_id;

-- 5. RERA verification review queue.
CREATE VIEW vw_rera_verification_review_queue AS
SELECT
  r.id AS review_item_id,
  r.rera_project_profile_id,
  pp.official_project_name,
  r.rera_building_match_candidate_id,
  r.rera_area_mismatch_candidate_id,
  r.review_type,
  r.status,
  r.priority,
  r.assigned_to,
  r.reviewed_by,
  r.reviewed_at,
  r.created_at
FROM rera_verification_review_items r
LEFT JOIN rera_project_profiles pp ON pp.id = r.rera_project_profile_id;

-- 6. Imperial Heights RERA readiness rollup (one row per Imperial-Heights-like web profile).
--    ready_for_building_dedupe: true only if an ACCEPTED RERA match exists for the building.
--    ready_for_content_fact_use: true only if a VERIFIED RERA profile exists AND no blocker risk.
CREATE VIEW vw_imperial_heights_rera_readiness AS
SELECT
  p.profile_slug,
  p.building_id,
  b.name AS building_name,
  (SELECT count(*) FROM rera_project_profiles pp WHERE pp.building_id = p.building_id OR pp.building_web_profile_id = p.id) AS rera_project_profile_count,
  (SELECT count(*) FROM rera_project_profiles pp WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id) AND pp.verification_status = 'verified') AS verified_profile_count,
  (SELECT count(*) FROM rera_building_match_candidates m WHERE m.building_id = p.building_id AND m.match_status = 'accepted') AS accepted_match_count,
  (SELECT count(*) FROM rera_project_status_checks s
     JOIN rera_project_profiles pp ON pp.id = s.rera_project_profile_id
    WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id)
      AND s.severity = 'blocker' AND s.check_status = 'present') AS blocker_risk_count,
  (SELECT count(*) FROM rera_area_mismatch_candidates am
    WHERE am.building_id = p.building_id AND am.mismatch_status IN ('candidate', 'needs_more_info', 'accepted_mismatch')) AS open_area_mismatch_count,
  (
    (SELECT count(*) FROM rera_building_match_candidates m WHERE m.building_id = p.building_id AND m.match_status = 'accepted') > 0
  ) AS ready_for_building_dedupe,
  (
    (SELECT count(*) FROM rera_project_profiles pp WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id) AND pp.verification_status = 'verified') > 0
    AND (SELECT count(*) FROM rera_project_status_checks s
           JOIN rera_project_profiles pp ON pp.id = s.rera_project_profile_id
          WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id)
            AND s.severity = 'blocker' AND s.check_status = 'present') = 0
  ) AS ready_for_content_fact_use,
  CASE
    WHEN (SELECT count(*) FROM rera_project_profiles pp WHERE pp.building_id = p.building_id OR pp.building_web_profile_id = p.id) = 0 THEN 'no_rera_profile_yet'
    WHEN (SELECT count(*) FROM rera_building_match_candidates m WHERE m.building_id = p.building_id AND m.match_status = 'accepted') = 0 THEN 'rera_match_not_accepted'
    WHEN (SELECT count(*) FROM rera_project_profiles pp WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id) AND pp.verification_status = 'verified') = 0 THEN 'rera_profile_not_verified'
    WHEN (SELECT count(*) FROM rera_project_status_checks s
            JOIN rera_project_profiles pp ON pp.id = s.rera_project_profile_id
           WHERE (pp.building_id = p.building_id OR pp.building_web_profile_id = p.id)
             AND s.severity = 'blocker' AND s.check_status = 'present') > 0 THEN 'blocker_risk_present'
    ELSE 'rera_verified_no_blocker'
  END AS blocked_reason
FROM building_web_profiles p
LEFT JOIN buildings b ON b.id = p.building_id
WHERE lower(COALESCE(b.name, p.building_name)) LIKE '%imperial heights%';
