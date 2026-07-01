-- MIS Phase C: brochure page extractor additions
-- Adds brochure_page column + location_map to asset_type enum

ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS brochure_page integer;

ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS media_assets_asset_type_check;
ALTER TABLE media_assets ADD CONSTRAINT media_assets_asset_type_check
  CHECK (asset_type IS NULL OR asset_type = ANY (ARRAY[
    'floor_plan','exterior','interior','amenity',
    'master_layout','location_map',
    'video','brochure','virtual_stage','other'
  ]));
