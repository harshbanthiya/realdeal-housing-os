-- Phase MIS-B: Brochure Intelligence Pipeline — staging tables
-- Pattern mirrors RERA parser (migrations 019/020): everything lands reviewed=false.
-- Nothing touches buildings/building_units until operator approves via review script.

-- ── brochure source tracking ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brochure_extractions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id       uuid REFERENCES buildings(id) ON DELETE SET NULL,
  source_pdf_path   text NOT NULL,
  rera_number       text,
  developer_name    text,
  project_name      text,
  phase_label       text,
  page_count        integer,
  towers_found      text[],
  extraction_method text NOT NULL DEFAULT 'visual_review', -- visual_review | ocr | api_vision
  extraction_phase  text,
  reviewed          boolean NOT NULL DEFAULT false,
  review_decision   text CHECK (review_decision IN ('approved','needs_more_info','rejected') OR review_decision IS NULL),
  review_notes      text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- ── tower structure staging ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brochure_tower_staging (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  extraction_id            uuid NOT NULL REFERENCES brochure_extractions(id) ON DELETE CASCADE,
  tower_name               text NOT NULL,  -- "Tower-02"
  tower_code               text NOT NULL,  -- "T02"
  floor_count              integer,
  units_per_typical_floor  integer,
  typical_floor_ranges     text,           -- "3-6, 8-12 & 14, 16-21, 23-28, 30-35"
  atypical_floors          jsonb NOT NULL DEFAULT '[]'::jsonb, -- [{floors:"7,15,22,29", type:"refuge"}, ...]
  brochure_page_start      integer,
  reviewed                 boolean NOT NULL DEFAULT false,
  review_gate              text,           -- TOWER_NAME_AMBIGUOUS | FLOOR_COUNT_MISMATCH
  review_decision          text CHECK (review_decision IN ('approved','needs_more_info','rejected') OR review_decision IS NULL),
  review_notes             text,
  created_at               timestamptz NOT NULL DEFAULT now()
);

-- ── unit configuration staging ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brochure_unit_config_staging (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  extraction_id           uuid NOT NULL REFERENCES brochure_extractions(id) ON DELETE CASCADE,
  tower_staging_id        uuid REFERENCES brochure_tower_staging(id) ON DELETE SET NULL,
  tower_code              text NOT NULL,
  unit_position           text NOT NULL,   -- "01", "02", "03", "04"
  configuration_type      text NOT NULL,   -- "T02-3BHK-01" — canonical key for media fallback
  bhk                     integer NOT NULL,
  carpet_area_sqft        numeric(10,2),
  carpet_area_sqm         numeric(10,2),
  balcony_sqft            numeric(10,2),
  total_area_sqft         numeric(10,2),
  typical_floors          text,
  is_penthouse            boolean NOT NULL DEFAULT false,
  is_refuge_variant       boolean NOT NULL DEFAULT false,
  floor_plan_page         integer,         -- brochure page number
  area_source             text NOT NULL DEFAULT 'brochure', -- brochure | rera | manual
  reviewed                boolean NOT NULL DEFAULT false,
  review_gate             text,            -- CARPET_AREA_CONFLICT | UNIT_POSITION_UNCLEAR
  review_decision         text CHECK (review_decision IN ('approved','needs_more_info','rejected') OR review_decision IS NULL),
  review_notes            text,
  created_at              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (extraction_id, tower_code, unit_position, is_penthouse, is_refuge_variant)
);

-- ── views ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_brochure_extraction_status AS
SELECT
  be.id,
  be.project_name,
  be.rera_number,
  be.extraction_method,
  be.reviewed                                                         AS extraction_reviewed,
  be.review_decision                                                  AS extraction_decision,
  COUNT(DISTINCT bts.id)                                              AS towers_staged,
  COUNT(DISTINCT bts.id) FILTER (WHERE bts.reviewed)                 AS towers_reviewed,
  COUNT(DISTINCT buc.id)                                              AS configs_staged,
  COUNT(DISTINCT buc.id) FILTER (WHERE buc.reviewed)                 AS configs_reviewed,
  COUNT(DISTINCT buc.id) FILTER (WHERE buc.review_decision='approved') AS configs_approved,
  -- real readiness gate: extraction approved + all configs approved
  (COALESCE(be.review_decision,'') = 'approved'
    AND COUNT(DISTINCT buc.id) > 0
    AND COUNT(DISTINCT buc.id) FILTER (WHERE COALESCE(buc.review_decision,'') != 'approved') = 0
  )                                                                   AS ready_to_apply
FROM brochure_extractions be
LEFT JOIN brochure_tower_staging bts ON bts.extraction_id = be.id
LEFT JOIN brochure_unit_config_staging buc ON buc.extraction_id = be.id
GROUP BY be.id, be.project_name, be.rera_number, be.extraction_method,
         be.reviewed, be.review_decision;

CREATE OR REPLACE VIEW vw_brochure_config_review_queue AS
SELECT
  buc.id,
  buc.tower_code,
  buc.unit_position,
  buc.configuration_type,
  buc.bhk,
  buc.carpet_area_sqft,
  buc.carpet_area_sqm,
  buc.balcony_sqft,
  buc.total_area_sqft,
  buc.typical_floors,
  buc.is_penthouse,
  buc.is_refuge_variant,
  buc.floor_plan_page,
  buc.area_source,
  buc.review_gate,
  buc.review_decision,
  be.project_name,
  be.rera_number
FROM brochure_unit_config_staging buc
JOIN brochure_extractions be ON be.id = buc.extraction_id
WHERE buc.review_decision IS NULL OR buc.review_decision != 'approved'
ORDER BY buc.tower_code, buc.unit_position;

-- ponytail: ready_to_apply is the only hard gate before apply script runs
CREATE OR REPLACE VIEW vw_brochure_apply_readiness AS
SELECT
  id,
  project_name,
  rera_number,
  ready_to_apply,
  configs_staged,
  configs_approved,
  CASE
    WHEN NOT ready_to_apply THEN
      'BLOCKED: ' || CASE
        WHEN extraction_decision != 'approved' THEN 'extraction not approved'
        WHEN configs_staged = 0 THEN 'no configs staged'
        ELSE (configs_staged - configs_approved)::text || ' config(s) not yet approved'
      END
    ELSE 'CLEAR'
  END AS gate_reason
FROM vw_brochure_extraction_status;
