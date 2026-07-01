-- Phase MIS-A: Digital Asset Library (DAM) extensions
-- Extends existing media_assets table with MIS fields.
-- Adds configuration_type to building_units as the unit→stock-media link.
-- All rows land with reviewed=false; nothing touches the website until approved.

-- ─── building_units: add configuration_type ──────────────────────────────────

ALTER TABLE building_units
  ADD COLUMN IF NOT EXISTS configuration_type text;

COMMENT ON COLUMN building_units.configuration_type IS
  'Canonical floor-plan label e.g. 3BHK-A, 2BHK-B. Units sharing a type share stock media.';

-- ─── media_assets: MIS extensions ────────────────────────────────────────────

ALTER TABLE media_assets
  ADD COLUMN IF NOT EXISTS unit_id             uuid REFERENCES building_units(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS configuration_type  text,
  ADD COLUMN IF NOT EXISTS asset_level         text,
  ADD COLUMN IF NOT EXISTS asset_type          text,
  ADD COLUMN IF NOT EXISTS source              text,
  ADD COLUMN IF NOT EXISTS wix_url             text,
  ADD COLUMN IF NOT EXISTS youtube_url         text,
  ADD COLUMN IF NOT EXISTS alt_text            text,
  ADD COLUMN IF NOT EXISTS seo_title           text,
  ADD COLUMN IF NOT EXISTS tags                text[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS reviewed            boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS upload_status       text NOT NULL DEFAULT 'local_only',
  ADD COLUMN IF NOT EXISTS virtual_stage_status text NOT NULL DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS review_notes        text,
  ADD COLUMN IF NOT EXISTS scan_phase          text;

-- constraints (IF NOT EXISTS via DO block to be idempotent)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='media_assets' AND constraint_name='media_assets_asset_level_check'
  ) THEN
    ALTER TABLE media_assets ADD CONSTRAINT media_assets_asset_level_check
      CHECK (asset_level IS NULL OR asset_level IN ('unit','configuration','tower','building','generic'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='media_assets' AND constraint_name='media_assets_asset_type_check'
  ) THEN
    ALTER TABLE media_assets ADD CONSTRAINT media_assets_asset_type_check
      CHECK (asset_type IS NULL OR asset_type IN (
        'floor_plan','exterior','interior','amenity',
        'master_layout','video','brochure','virtual_stage','other'
      ));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='media_assets' AND constraint_name='media_assets_source_check'
  ) THEN
    ALTER TABLE media_assets ADD CONSTRAINT media_assets_source_check
      CHECK (source IS NULL OR source IN ('brochure_extract','disk_scan','youtube','manual'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='media_assets' AND constraint_name='media_assets_upload_status_check'
  ) THEN
    ALTER TABLE media_assets ADD CONSTRAINT media_assets_upload_status_check
      CHECK (upload_status IN ('local_only','wix_uploaded','youtube_uploaded'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name='media_assets' AND constraint_name='media_assets_virtual_stage_check'
  ) THEN
    ALTER TABLE media_assets ADD CONSTRAINT media_assets_virtual_stage_check
      CHECK (virtual_stage_status IN ('none','queued','done'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_media_assets_building_id   ON media_assets(building_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_unit_id       ON media_assets(unit_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_asset_level   ON media_assets(asset_level);
CREATE INDEX IF NOT EXISTS idx_media_assets_reviewed      ON media_assets(reviewed);

-- ─── views ───────────────────────────────────────────────────────────────────

-- Operator review queue: everything not yet reviewed
CREATE OR REPLACE VIEW vw_media_review_queue AS
SELECT
  ma.id,
  ma.file_path,
  ma.asset_level,
  ma.asset_type,
  ma.source,
  ma.configuration_type,
  b.name                                  AS building_name,
  bu.unit_number,
  ma.review_notes,
  ma.scan_phase,
  ma.created_at
FROM media_assets ma
LEFT JOIN buildings b   ON b.id = ma.building_id
LEFT JOIN building_units bu ON bu.id = ma.unit_id
WHERE ma.reviewed = false
ORDER BY ma.asset_level, b.name, ma.created_at;

-- Upload queue: reviewed + alt_text filled + not yet on Wix
CREATE OR REPLACE VIEW vw_media_upload_queue AS
SELECT
  ma.id,
  ma.file_path,
  ma.asset_type,
  ma.asset_level,
  ma.alt_text,
  ma.seo_title,
  b.name AS building_name,
  ma.configuration_type,
  ma.upload_status
FROM media_assets ma
LEFT JOIN buildings b ON b.id = ma.building_id
WHERE ma.reviewed = true
  AND ma.upload_status = 'local_only'
  AND ma.alt_text IS NOT NULL
ORDER BY ma.asset_level, b.name;

-- Per-building summary
CREATE OR REPLACE VIEW vw_media_by_building AS
SELECT
  b.name                                                        AS building_name,
  COUNT(*)                                                      AS total_assets,
  COUNT(*) FILTER (WHERE ma.reviewed = true)                    AS reviewed,
  COUNT(*) FILTER (WHERE ma.reviewed = false)                   AS pending_review,
  COUNT(*) FILTER (WHERE ma.upload_status = 'wix_uploaded')     AS on_wix,
  COUNT(*) FILTER (WHERE ma.alt_text IS NULL AND ma.reviewed)   AS missing_alt_text,
  array_agg(DISTINCT ma.asset_type) FILTER (WHERE ma.asset_type IS NOT NULL) AS asset_types
FROM media_assets ma
LEFT JOIN buildings b ON b.id = ma.building_id
GROUP BY b.name
ORDER BY total_assets DESC;

-- Fallback ladder for a given unit:
-- join unit → building, then rank assets by specificity
CREATE OR REPLACE VIEW vw_media_fallback_ladder AS
SELECT
  bu.id                                   AS unit_id,
  bu.unit_number,
  bu.configuration_type,
  b.id                                    AS building_id,
  b.name                                  AS building_name,
  ma.id                                   AS asset_id,
  ma.file_path,
  ma.asset_type,
  ma.asset_level,
  ma.wix_url,
  ma.reviewed,
  CASE ma.asset_level
    WHEN 'unit'          THEN 1
    WHEN 'configuration' THEN 2
    WHEN 'tower'         THEN 3
    WHEN 'building'      THEN 4
    WHEN 'generic'       THEN 5
    ELSE                      6
  END                                     AS ladder_rank
FROM building_units bu
JOIN buildings b ON b.id = bu.building_id
LEFT JOIN media_assets ma ON
  ma.reviewed = true AND (
    ma.unit_id = bu.id
    OR (ma.configuration_type = bu.configuration_type AND ma.building_id = bu.building_id)
    OR (ma.asset_level IN ('tower','building','generic') AND ma.building_id = bu.building_id)
  )
ORDER BY bu.unit_number, ladder_rank;
