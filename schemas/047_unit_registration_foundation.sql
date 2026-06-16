-- Phase 6.15: Building structure + IGR registration foundation (schema + fake workflow only).
--
-- Extends the MahaRERA verification layer (Phases 6.8-6.14) with the layer needed to build a
-- per-UNIT ownership/rental picture for the <10 buildings we actively work:
--
--   1. building tower/wing STRUCTURE (towers -> floors -> units-per-floor),
--   2. property IDENTIFIERS (CTS / survey / plot / milkat / gat / village / SRO) — the bridge
--      MahaRERA filings + property cards give us that IGR eSearch needs,
--   3. IGR eSearch SEARCH JOBS (year x district x village x property-no; human-CAPTCHA only),
--   4. per-unit REGISTRATION RECORDS (Index II transactions: doc#, date, SRO, document type,
--      consideration, raw flat/wing text),
--   5. registration PARTIES (buyer/seller/lessor/lessee names per record),
--   6. PARTY -> CONTACT match candidates (so we can later tie a registered party to a contact),
--   7. a human REVIEW queue for every step.
--
-- This phase is schema + fake workflow ONLY. NOTHING here scrapes IGR/MahaRERA, calls any
-- external API, browses the web, solves a CAPTCHA, auto-creates contact relationships, merges
-- buildings/units, or publishes anything. The actual IGR Index II source is property-number
-- (CTS/survey) first, NOT building-name first, and is behind a CAPTCHA — collection is a
-- separate, deliberate, human-in-the-loop phase (mirrors the MahaRERA capture in 6.10-6.12).
--
-- Privacy posture: IGR Index II party names are from a PUBLIC register, but they are still
-- personal data. The DEFAULT dashboards are counts-only and never expose party names. Views
-- that DO expose names are explicitly suffixed `_operator` and are for internal operator use.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. building_tower_structure — towers/wings -> floors -> units-per-floor.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_tower_structure (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  tower_label text,                               -- e.g. 'Wing C', 'Tower 1', 'A'
  tower_type text,                                -- residential, commercial, mixed, podium
  floors_above_ground integer,
  floors_below_ground integer,
  units_per_typical_floor integer,
  total_units integer,
  sanctioned_floors integer,
  source_label text,
  source_type text DEFAULT 'manual',              -- rera_filing, property_card, developer, manual, derived
  confidence_score numeric,
  verification_status text DEFAULT 'unverified',  -- unverified, candidate, verified, needs_human_review, mismatch_found
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bts_building_id ON building_tower_structure(building_id);
CREATE INDEX IF NOT EXISTS idx_bts_project_profile_id ON building_tower_structure(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_bts_verification_status ON building_tower_structure(verification_status);
CREATE INDEX IF NOT EXISTS idx_bts_created_at ON building_tower_structure(created_at);

-- ---------------------------------------------------------------------------
-- 2. building_property_identifiers — CTS/survey/etc. bridge keys for IGR.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_property_identifiers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  identifier_type text,                           -- cts_number, survey_number, plot_number, milkat_number, gat_number, village, sro_office, district, pincode, khasra
  identifier_value text,
  district text,
  village text,
  sro_office text,
  is_igr_search_key boolean DEFAULT false,        -- true => usable as the IGR property-number search key
  source_label text,
  source_type text DEFAULT 'manual',              -- rera_filing, property_card, mahabhumi, bmc, developer, manual
  source_url text,
  confidence_score numeric,
  verification_status text DEFAULT 'unverified',  -- unverified, candidate, verified, needs_human_review, rejected
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bpi_building_id ON building_property_identifiers(building_id);
CREATE INDEX IF NOT EXISTS idx_bpi_project_profile_id ON building_property_identifiers(rera_project_profile_id);
CREATE INDEX IF NOT EXISTS idx_bpi_identifier_type ON building_property_identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_bpi_verification_status ON building_property_identifiers(verification_status);
CREATE INDEX IF NOT EXISTS idx_bpi_is_search_key ON building_property_identifiers(is_igr_search_key);
CREATE INDEX IF NOT EXISTS idx_bpi_created_at ON building_property_identifiers(created_at);

-- ---------------------------------------------------------------------------
-- 3. igr_registration_search_jobs — planned IGR eSearch queries (no calls here).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS igr_registration_search_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  building_property_identifier_id uuid REFERENCES building_property_identifiers(id),
  search_year integer,
  district text,
  village text,
  property_number text,
  job_status text DEFAULT 'planned',              -- planned, queued, operator_assigned, captcha_required, captured, parsed, no_results, blocked, error
  captcha_required boolean DEFAULT true,          -- IGR eSearch is CAPTCHA-gated; assume true until proven otherwise
  external_call_made boolean DEFAULT false,       -- stays false until a deliberate operator-assisted capture phase
  operator_assigned text,
  snapshot_path text,                             -- git-ignored exports/ path of a future raw capture
  result_record_count integer DEFAULT 0,
  attempted_at timestamptz,
  completed_at timestamptz,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_irsj_building_id ON igr_registration_search_jobs(building_id);
CREATE INDEX IF NOT EXISTS idx_irsj_identifier_id ON igr_registration_search_jobs(building_property_identifier_id);
CREATE INDEX IF NOT EXISTS idx_irsj_job_status ON igr_registration_search_jobs(job_status);
CREATE INDEX IF NOT EXISTS idx_irsj_search_year ON igr_registration_search_jobs(search_year);
CREATE INDEX IF NOT EXISTS idx_irsj_created_at ON igr_registration_search_jobs(created_at);

-- ---------------------------------------------------------------------------
-- 4. unit_registration_records — Index II transactions (per unit, review-gated).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit_registration_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  building_unit_id uuid REFERENCES building_units(id) ON DELETE SET NULL,  -- set only after a unit_link_review
  rera_project_profile_id uuid REFERENCES rera_project_profiles(id),
  igr_registration_search_job_id uuid REFERENCES igr_registration_search_jobs(id),
  doc_number text,
  registration_year integer,
  registration_date date,
  sro_office text,
  document_type text,                             -- sale_deed, agreement_to_sell, lease, leave_and_license, gift_deed, mortgage, release_deed, power_of_attorney, other
  property_description_raw text,                  -- raw flat/wing/CTS text as printed on Index II
  wing_text text,
  unit_text text,
  floor_text text,
  area_text text,
  consideration_amount numeric,
  market_value numeric,
  stamp_duty numeric,
  index2_file_path text,                          -- git-ignored exports/ path of the raw Index II
  parse_confidence numeric,
  verification_status text DEFAULT 'unparsed',    -- unparsed, parsed_candidate, verified, needs_human_review, rejected, duplicate
  source_label text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_urr_building_id ON unit_registration_records(building_id);
CREATE INDEX IF NOT EXISTS idx_urr_building_unit_id ON unit_registration_records(building_unit_id);
CREATE INDEX IF NOT EXISTS idx_urr_search_job_id ON unit_registration_records(igr_registration_search_job_id);
CREATE INDEX IF NOT EXISTS idx_urr_document_type ON unit_registration_records(document_type);
CREATE INDEX IF NOT EXISTS idx_urr_registration_year ON unit_registration_records(registration_year);
CREATE INDEX IF NOT EXISTS idx_urr_verification_status ON unit_registration_records(verification_status);
CREATE INDEX IF NOT EXISTS idx_urr_created_at ON unit_registration_records(created_at);

-- ---------------------------------------------------------------------------
-- 5. unit_registration_parties — party names per registration (personal data).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit_registration_parties (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_registration_record_id uuid REFERENCES unit_registration_records(id) ON DELETE CASCADE,
  party_role text,                                -- purchaser, buyer, seller, vendor, lessor, lessee, landlord, tenant, mortgagor, mortgagee, confirming_party, power_of_attorney_holder, other
  party_name_raw text,
  party_name_normalized text,
  party_type text DEFAULT 'unknown',              -- individual, company, huf, trust, government, unknown
  display_order integer DEFAULT 0,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_urp_record_id ON unit_registration_parties(unit_registration_record_id);
CREATE INDEX IF NOT EXISTS idx_urp_party_role ON unit_registration_parties(party_role);
CREATE INDEX IF NOT EXISTS idx_urp_name_normalized ON unit_registration_parties(party_name_normalized);
CREATE INDEX IF NOT EXISTS idx_urp_created_at ON unit_registration_parties(created_at);

-- ---------------------------------------------------------------------------
-- 6. registration_party_contact_matches — party -> contact match candidates.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS registration_party_contact_matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_registration_party_id uuid REFERENCES unit_registration_parties(id) ON DELETE CASCADE,
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  building_unit_id uuid REFERENCES building_units(id) ON DELETE SET NULL,
  match_status text DEFAULT 'candidate',          -- candidate, accepted, rejected, needs_more_info
  match_strength text DEFAULT 'candidate',        -- strong, medium, weak, candidate
  name_similarity_score numeric,
  match_reason text,
  creates_relationship boolean DEFAULT false,     -- whether ACCEPT should propose a contact_property_relationship
  resulting_relationship_id uuid REFERENCES contact_property_relationships(id),
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rpcm_party_id ON registration_party_contact_matches(unit_registration_party_id);
CREATE INDEX IF NOT EXISTS idx_rpcm_contact_id ON registration_party_contact_matches(contact_id);
CREATE INDEX IF NOT EXISTS idx_rpcm_building_id ON registration_party_contact_matches(building_id);
CREATE INDEX IF NOT EXISTS idx_rpcm_match_status ON registration_party_contact_matches(match_status);
CREATE INDEX IF NOT EXISTS idx_rpcm_created_at ON registration_party_contact_matches(created_at);

-- ---------------------------------------------------------------------------
-- 7. unit_registration_review_items — human review queue for every step.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit_registration_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  building_tower_structure_id uuid REFERENCES building_tower_structure(id),
  building_property_identifier_id uuid REFERENCES building_property_identifiers(id),
  igr_registration_search_job_id uuid REFERENCES igr_registration_search_jobs(id),
  unit_registration_record_id uuid REFERENCES unit_registration_records(id),
  registration_party_contact_match_id uuid REFERENCES registration_party_contact_matches(id),
  review_type text,                               -- structure_review, identifier_review, search_job_review, registration_record_review, party_contact_match_review, unit_link_review
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
CREATE INDEX IF NOT EXISTS idx_urri_building_id ON unit_registration_review_items(building_id);
CREATE INDEX IF NOT EXISTS idx_urri_record_id ON unit_registration_review_items(unit_registration_record_id);
CREATE INDEX IF NOT EXISTS idx_urri_match_id ON unit_registration_review_items(registration_party_contact_match_id);
CREATE INDEX IF NOT EXISTS idx_urri_review_type ON unit_registration_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_urri_status ON unit_registration_review_items(status);
CREATE INDEX IF NOT EXISTS idx_urri_created_at ON unit_registration_review_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (reuse project-wide set_updated_at()).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_building_tower_structure_updated_at ON building_tower_structure;
CREATE TRIGGER trg_building_tower_structure_updated_at
BEFORE UPDATE ON building_tower_structure FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_building_property_identifiers_updated_at ON building_property_identifiers;
CREATE TRIGGER trg_building_property_identifiers_updated_at
BEFORE UPDATE ON building_property_identifiers FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_igr_registration_search_jobs_updated_at ON igr_registration_search_jobs;
CREATE TRIGGER trg_igr_registration_search_jobs_updated_at
BEFORE UPDATE ON igr_registration_search_jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_unit_registration_records_updated_at ON unit_registration_records;
CREATE TRIGGER trg_unit_registration_records_updated_at
BEFORE UPDATE ON unit_registration_records FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_unit_registration_parties_updated_at ON unit_registration_parties;
CREATE TRIGGER trg_unit_registration_parties_updated_at
BEFORE UPDATE ON unit_registration_parties FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_registration_party_contact_matches_updated_at ON registration_party_contact_matches;
CREATE TRIGGER trg_registration_party_contact_matches_updated_at
BEFORE UPDATE ON registration_party_contact_matches FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_unit_registration_review_items_updated_at ON unit_registration_review_items;
CREATE TRIGGER trg_unit_registration_review_items_updated_at
BEFORE UPDATE ON unit_registration_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Read-only dashboards.
--   SAFE views (default): never expose party names — counts only.
--   *_operator views: expose public-register party names for internal operator use.
-- ===========================================================================

DROP VIEW IF EXISTS vw_building_structure_dashboard;
DROP VIEW IF EXISTS vw_building_property_identifier_dashboard;
DROP VIEW IF EXISTS vw_igr_search_job_queue;
DROP VIEW IF EXISTS vw_unit_registration_dashboard;
DROP VIEW IF EXISTS vw_unit_registration_parties_operator;
DROP VIEW IF EXISTS vw_unit_ownership_timeline_operator;
DROP VIEW IF EXISTS vw_registration_party_contact_match_queue_operator;
DROP VIEW IF EXISTS vw_unit_registration_review_queue;
DROP VIEW IF EXISTS vw_imperial_heights_registration_readiness;

-- 1. SAFE — building tower/floor/unit structure (no personal data).
CREATE VIEW vw_building_structure_dashboard AS
SELECT
  ts.id AS tower_structure_id,
  ts.building_id,
  b.name AS building_name,
  ts.tower_label,
  ts.tower_type,
  ts.floors_above_ground,
  ts.floors_below_ground,
  ts.units_per_typical_floor,
  ts.total_units,
  ts.sanctioned_floors,
  ts.source_type,
  ts.confidence_score,
  ts.verification_status,
  ts.created_at
FROM building_tower_structure ts
LEFT JOIN buildings b ON b.id = ts.building_id;

-- 2. SAFE — property identifiers (CTS/survey/etc.; no personal data).
CREATE VIEW vw_building_property_identifier_dashboard AS
SELECT
  pi.id AS property_identifier_id,
  pi.building_id,
  b.name AS building_name,
  pi.identifier_type,
  pi.identifier_value,
  pi.district,
  pi.village,
  pi.sro_office,
  pi.is_igr_search_key,
  pi.source_type,
  pi.confidence_score,
  pi.verification_status,
  pi.created_at
FROM building_property_identifiers pi
LEFT JOIN buildings b ON b.id = pi.building_id;

-- 3. SAFE — IGR search job queue (no personal data; exposes the no-call posture).
CREATE VIEW vw_igr_search_job_queue AS
SELECT
  j.id AS search_job_id,
  j.building_id,
  b.name AS building_name,
  j.building_property_identifier_id,
  j.search_year,
  j.district,
  j.village,
  j.property_number,
  j.job_status,
  j.captcha_required,
  j.external_call_made,
  j.operator_assigned,
  j.result_record_count,
  j.attempted_at,
  j.completed_at,
  j.created_at
FROM igr_registration_search_jobs j
LEFT JOIN buildings b ON b.id = j.building_id;

-- 4. SAFE — per-registration-record dashboard (COUNTS of parties, NO names).
CREATE VIEW vw_unit_registration_dashboard AS
SELECT
  r.id AS unit_registration_record_id,
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  u.unit_number,
  u.wing AS unit_wing,
  r.doc_number,
  r.registration_year,
  r.registration_date,
  r.sro_office,
  r.document_type,
  r.wing_text,
  r.unit_text,
  r.floor_text,
  r.consideration_amount,
  r.market_value,
  r.verification_status,
  (SELECT count(*) FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS party_count,
  (SELECT count(*) FROM unit_registration_parties p
     JOIN registration_party_contact_matches m ON m.unit_registration_party_id = p.id
    WHERE p.unit_registration_record_id = r.id AND m.match_status = 'accepted') AS matched_party_count,
  r.created_at
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id;

-- 5. OPERATOR — registration parties WITH names (public-register, internal use).
CREATE VIEW vw_unit_registration_parties_operator AS
SELECT
  p.id AS party_id,
  p.unit_registration_record_id,
  r.building_id,
  b.name AS building_name,
  r.doc_number,
  r.registration_year,
  r.document_type,
  r.wing_text,
  r.unit_text,
  p.party_role,
  p.party_name_raw,
  p.party_type,
  p.display_order,
  (SELECT count(*) FROM registration_party_contact_matches m WHERE m.unit_registration_party_id = p.id) AS contact_match_count,
  p.created_at
FROM unit_registration_parties p
LEFT JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
LEFT JOIN buildings b ON b.id = r.building_id;

-- 6. OPERATOR — per-unit ownership/rental timeline (the "complete dashboard").
CREATE VIEW vw_unit_ownership_timeline_operator AS
SELECT
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  u.unit_number,
  u.wing AS unit_wing,
  r.registration_date,
  r.registration_year,
  r.document_type,
  r.doc_number,
  r.sro_office,
  r.consideration_amount,
  r.verification_status,
  (SELECT string_agg(p.party_name_raw || ' (' || COALESCE(p.party_role, '?') || ')', '; ' ORDER BY p.display_order)
     FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS parties,
  r.id AS unit_registration_record_id
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id;

-- 7. OPERATOR — party -> contact match review queue (shows both names + score).
CREATE VIEW vw_registration_party_contact_match_queue_operator AS
SELECT
  m.id AS match_id,
  m.unit_registration_party_id,
  p.party_name_raw,
  p.party_role,
  m.contact_id,
  c.full_name AS contact_name,
  m.building_id,
  b.name AS building_name,
  m.building_unit_id,
  m.match_status,
  m.match_strength,
  m.name_similarity_score,
  m.match_reason,
  m.creates_relationship,
  m.resulting_relationship_id,
  m.created_at
FROM registration_party_contact_matches m
LEFT JOIN unit_registration_parties p ON p.id = m.unit_registration_party_id
LEFT JOIN contacts c ON c.id = m.contact_id
LEFT JOIN buildings b ON b.id = m.building_id;

-- 8. SAFE — review queue (references only, no names).
CREATE VIEW vw_unit_registration_review_queue AS
SELECT
  ri.id AS review_item_id,
  ri.building_id,
  b.name AS building_name,
  ri.review_type,
  ri.status,
  ri.priority,
  ri.building_tower_structure_id,
  ri.building_property_identifier_id,
  ri.igr_registration_search_job_id,
  ri.unit_registration_record_id,
  ri.registration_party_contact_match_id,
  ri.assigned_to,
  ri.reviewed_by,
  ri.reviewed_at,
  ri.created_at
FROM unit_registration_review_items ri
LEFT JOIN buildings b ON b.id = ri.building_id;

-- 9. SAFE — Imperial Heights registration readiness (real gates; all hard-false initially).
--    ready_for_igr_search: a VERIFIED, search-key property identifier exists for the building.
--    ready_for_party_matching: at least one VERIFIED registration record exists.
--    ready_for_relationship_creation: at least one ACCEPTED party->contact match exists.
CREATE VIEW vw_imperial_heights_registration_readiness AS
SELECT
  b.id AS building_id,
  b.name AS building_name,
  (SELECT count(*) FROM building_tower_structure ts WHERE ts.building_id = b.id) AS tower_structure_count,
  (SELECT count(*) FROM building_property_identifiers pi WHERE pi.building_id = b.id) AS identifier_count,
  (SELECT count(*) FROM building_property_identifiers pi
     WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) AS verified_search_key_count,
  (SELECT count(*) FROM igr_registration_search_jobs j WHERE j.building_id = b.id) AS search_job_count,
  (SELECT count(*) FROM igr_registration_search_jobs j WHERE j.building_id = b.id AND j.external_call_made) AS external_call_count,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id) AS registration_record_count,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') AS verified_record_count,
  (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') AS accepted_match_count,
  (
    (SELECT count(*) FROM building_property_identifiers pi
       WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) > 0
  ) AS ready_for_igr_search,
  (
    (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') > 0
  ) AS ready_for_party_matching,
  (
    (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') > 0
  ) AS ready_for_relationship_creation,
  CASE
    WHEN (SELECT count(*) FROM building_property_identifiers pi
            WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) = 0
      THEN 'no_verified_search_key_yet'
    WHEN (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') = 0
      THEN 'no_verified_registration_record_yet'
    WHEN (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') = 0
      THEN 'no_accepted_party_contact_match_yet'
    ELSE 'ready_for_relationship_creation'
  END AS blocked_reason
FROM buildings b
WHERE lower(b.name) LIKE '%imperial heights%';
