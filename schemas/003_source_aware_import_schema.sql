CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS source_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  archive_name text,
  archive_member_path text,
  original_file_name text,
  stored_relative_path text,
  file_ext text,
  file_size_bytes bigint,
  file_hash_sha256 text,
  detected_source_format text,
  detected_encoding text,
  detected_delimiter text,
  sheet_name text,
  sheet_count integer,
  row_count integer,
  column_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  profile_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  processing_status text NOT NULL DEFAULT 'profiled',
  processing_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT source_files_processing_status_check
    CHECK (processing_status IN ('profiled', 'normalized', 'cleaned', 'planned', 'reviewing', 'approved', 'rejected', 'error', 'archived'))
);

CREATE TABLE IF NOT EXISTS contact_methods (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  method_type text NOT NULL,
  raw_value text,
  normalized_value text,
  label text,
  is_primary boolean NOT NULL DEFAULT false,
  confidence numeric(4,3),
  validation_status text NOT NULL DEFAULT 'unverified',
  source_file text,
  source_sheet text,
  source_row_number integer,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_methods_method_type_check
    CHECK (method_type IN ('phone', 'mobile', 'landline', 'whatsapp', 'email', 'website', 'google_maps', 'social', 'other')),
  CONSTRAINT contact_methods_validation_status_check
    CHECK (validation_status IN ('valid', 'invalid', 'placeholder', 'duplicate', 'unverified'))
);

CREATE TABLE IF NOT EXISTS lead_requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  source text,
  source_format text,
  campaign_name text,
  platform text,
  lead_status text,
  purpose text,
  property_type text,
  bhk text,
  typology text,
  locality text,
  area text,
  city text,
  budget_min numeric,
  budget_max numeric,
  visit_intent text,
  requirement_text text,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  needs_review boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT lead_requirements_purpose_check
    CHECK (purpose IS NULL OR purpose IN ('buy', 'rent', 'sell', 'lease_out', 'unknown', 'other'))
);

CREATE TABLE IF NOT EXISTS inventory_import_rows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  source_file text,
  source_sheet text,
  source_row_number integer,
  source_format text,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  building_name text,
  building_code text,
  wing text,
  unit_number text,
  floor text,
  typology text,
  bhk text,
  carpet_area numeric,
  salable_area numeric,
  area_unit text,
  rent_price numeric,
  sale_price numeric,
  deposit numeric,
  availability_status text,
  listing_purpose text,
  owner_contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE SET NULL,
  owner_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  broker_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  matched_inventory_id uuid REFERENCES inventory(id) ON DELETE SET NULL,
  match_confidence numeric(4,3),
  needs_review boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT inventory_import_rows_listing_purpose_check
    CHECK (listing_purpose IS NULL OR listing_purpose IN ('rent', 'sale', 'both', 'unknown', 'other'))
);

CREATE TABLE IF NOT EXISTS import_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  inventory_import_row_id uuid REFERENCES inventory_import_rows(id) ON DELETE CASCADE,
  duplicate_candidate_id uuid REFERENCES contact_duplicate_candidates(id) ON DELETE CASCADE,
  review_type text NOT NULL,
  priority text NOT NULL DEFAULT 'normal',
  status text NOT NULL DEFAULT 'pending',
  title text,
  summary text,
  recommended_action text,
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT import_review_items_review_type_check
    CHECK (review_type IN ('duplicate_contact', 'missing_name', 'invalid_phone', 'invalid_email', 'property_hint_review', 'inventory_match_review', 'lead_requirement_review', 'source_format_unknown', 'merge_candidate', 'other')),
  CONSTRAINT import_review_items_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  CONSTRAINT import_review_items_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'merged', 'skipped', 'needs_more_info'))
);

CREATE INDEX IF NOT EXISTS idx_source_files_file_hash_sha256 ON source_files(file_hash_sha256);
CREATE INDEX IF NOT EXISTS idx_source_files_detected_source_format ON source_files(detected_source_format);
CREATE INDEX IF NOT EXISTS idx_source_files_archive_name ON source_files(archive_name);
CREATE INDEX IF NOT EXISTS idx_source_files_original_file_name ON source_files(original_file_name);
CREATE INDEX IF NOT EXISTS idx_source_files_processing_status ON source_files(processing_status);

CREATE INDEX IF NOT EXISTS idx_contact_methods_contact_id ON contact_methods(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_methods_contact_import_row_id ON contact_methods(contact_import_row_id);
CREATE INDEX IF NOT EXISTS idx_contact_methods_source_file_id ON contact_methods(source_file_id);
CREATE INDEX IF NOT EXISTS idx_contact_methods_method_type ON contact_methods(method_type);
CREATE INDEX IF NOT EXISTS idx_contact_methods_normalized_value ON contact_methods(normalized_value);
CREATE INDEX IF NOT EXISTS idx_contact_methods_validation_status ON contact_methods(validation_status);

CREATE INDEX IF NOT EXISTS idx_lead_requirements_contact_id ON lead_requirements(contact_id);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_contact_import_row_id ON lead_requirements(contact_import_row_id);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_source_file_id ON lead_requirements(source_file_id);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_source_format ON lead_requirements(source_format);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_platform ON lead_requirements(platform);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_purpose ON lead_requirements(purpose);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_locality ON lead_requirements(locality);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_city ON lead_requirements(city);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_budget_min ON lead_requirements(budget_min);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_budget_max ON lead_requirements(budget_max);
CREATE INDEX IF NOT EXISTS idx_lead_requirements_needs_review ON lead_requirements(needs_review);

CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_import_batch_id ON inventory_import_rows(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_source_file_id ON inventory_import_rows(source_file_id);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_source_format ON inventory_import_rows(source_format);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_building_name ON inventory_import_rows(building_name);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_building_code ON inventory_import_rows(building_code);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_wing ON inventory_import_rows(wing);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_unit_number ON inventory_import_rows(unit_number);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_listing_purpose ON inventory_import_rows(listing_purpose);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_availability_status ON inventory_import_rows(availability_status);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_needs_review ON inventory_import_rows(needs_review);
CREATE INDEX IF NOT EXISTS idx_inventory_import_rows_matched_inventory_id ON inventory_import_rows(matched_inventory_id);

CREATE INDEX IF NOT EXISTS idx_import_review_items_import_batch_id ON import_review_items(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_import_review_items_source_file_id ON import_review_items(source_file_id);
CREATE INDEX IF NOT EXISTS idx_import_review_items_review_type ON import_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_import_review_items_priority ON import_review_items(priority);
CREATE INDEX IF NOT EXISTS idx_import_review_items_status ON import_review_items(status);
CREATE INDEX IF NOT EXISTS idx_import_review_items_assigned_to ON import_review_items(assigned_to);
CREATE INDEX IF NOT EXISTS idx_import_review_items_created_at ON import_review_items(created_at);

DROP TRIGGER IF EXISTS trg_source_files_updated_at ON source_files;
CREATE TRIGGER trg_source_files_updated_at
BEFORE UPDATE ON source_files
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_contact_methods_updated_at ON contact_methods;
CREATE TRIGGER trg_contact_methods_updated_at
BEFORE UPDATE ON contact_methods
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_lead_requirements_updated_at ON lead_requirements;
CREATE TRIGGER trg_lead_requirements_updated_at
BEFORE UPDATE ON lead_requirements
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_inventory_import_rows_updated_at ON inventory_import_rows;
CREATE TRIGGER trg_inventory_import_rows_updated_at
BEFORE UPDATE ON inventory_import_rows
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_import_review_items_updated_at ON import_review_items;
CREATE TRIGGER trg_import_review_items_updated_at
BEFORE UPDATE ON import_review_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE VIEW vw_import_contact_review AS
SELECT
  cir.id AS contact_import_row_id,
  sf.id AS source_file_id,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  cir.source_sheet,
  cir.source_row_number,
  COALESCE(sf.detected_source_format, cir.source_format) AS source_format,
  cir.cleaned_display_name,
  CASE
    WHEN cir.phone_normalized IS NULL OR cir.phone_normalized = '' THEN NULL
    ELSE concat('[MASKED]', right(cir.phone_normalized, 4))
  END AS phone_masked,
  CASE
    WHEN cir.email_normalized IS NULL OR cir.email_normalized = '' THEN NULL
    WHEN position('@' in cir.email_normalized) > 1 THEN concat(left(cir.email_normalized, 1), '[MASKED]@', split_part(cir.email_normalized, '@', 2))
    ELSE '[MASKED]'
  END AS email_masked,
  cir.parsed_building_code,
  cir.parsed_building_name,
  cir.parsed_wing,
  cir.parsed_unit_number,
  cir.parsed_role,
  cir.needs_review,
  cir.rejection_reason,
  cir.matched_contact_id,
  cir.created_at
FROM contact_import_rows cir
LEFT JOIN source_files sf
  ON sf.import_batch_id = cir.import_batch_id
 AND sf.original_file_name = cir.source_file
 AND (sf.sheet_name IS NULL OR sf.sheet_name = cir.source_sheet);

CREATE OR REPLACE VIEW vw_duplicate_review AS
SELECT
  cdc.id AS duplicate_candidate_id,
  cdc.duplicate_strength,
  cdc.reason,
  cdc.status,
  left_ri.id AS left_contact_import_row_id,
  right_ri.id AS right_contact_import_row_id,
  left_ri.cleaned_display_name AS left_display_name,
  right_ri.cleaned_display_name AS right_display_name,
  concat('[MASKED]', right(COALESCE(left_ri.phone_normalized, right_ri.phone_normalized, ''), 4)) AS phone_masked,
  CASE
    WHEN COALESCE(left_ri.email_normalized, right_ri.email_normalized, '') = '' THEN NULL
    WHEN position('@' in COALESCE(left_ri.email_normalized, right_ri.email_normalized, '')) > 1
      THEN concat(left(COALESCE(left_ri.email_normalized, right_ri.email_normalized), 1), '[MASKED]@', split_part(COALESCE(left_ri.email_normalized, right_ri.email_normalized), '@', 2))
    ELSE '[MASKED]'
  END AS email_masked,
  COALESCE(left_ri.parsed_building_code, right_ri.parsed_building_code) AS parsed_building_code,
  COALESCE(left_ri.parsed_building_name, right_ri.parsed_building_name) AS parsed_building_name,
  COALESCE(left_ri.parsed_unit_number, right_ri.parsed_unit_number) AS parsed_unit_number,
  left_ri.source_file AS left_source_file,
  left_ri.source_row_number AS left_source_row_number,
  right_ri.source_file AS right_source_file,
  right_ri.source_row_number AS right_source_row_number,
  cdc.created_at
FROM contact_duplicate_candidates cdc
LEFT JOIN contact_import_rows left_ri ON left_ri.id = cdc.contact_import_row_id_1
LEFT JOIN contact_import_rows right_ri ON right_ri.id = cdc.contact_import_row_id_2;

CREATE OR REPLACE VIEW vw_inventory_import_review AS
SELECT
  iir.id AS inventory_import_row_id,
  sf.id AS source_file_id,
  COALESCE(sf.original_file_name, iir.source_file) AS source_file,
  iir.source_sheet,
  iir.source_row_number,
  iir.source_format,
  iir.building_name,
  iir.building_code,
  iir.wing,
  iir.unit_number,
  iir.typology,
  iir.bhk,
  iir.rent_price,
  iir.sale_price,
  iir.listing_purpose,
  iir.availability_status,
  iir.needs_review,
  iir.match_confidence,
  iir.matched_inventory_id,
  iir.created_at
FROM inventory_import_rows iir
LEFT JOIN source_files sf ON sf.id = iir.source_file_id;

CREATE OR REPLACE VIEW vw_lead_requirements_review AS
SELECT
  lr.id AS lead_requirement_id,
  sf.id AS source_file_id,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  cir.source_sheet,
  cir.source_row_number,
  lr.source,
  lr.source_format,
  lr.platform,
  lr.campaign_name,
  lr.purpose,
  lr.property_type,
  lr.locality,
  lr.city,
  lr.budget_min,
  lr.budget_max,
  lr.visit_intent,
  lr.needs_review,
  lr.contact_id,
  lr.contact_import_row_id,
  lr.created_at
FROM lead_requirements lr
LEFT JOIN source_files sf ON sf.id = lr.source_file_id
LEFT JOIN contact_import_rows cir ON cir.id = lr.contact_import_row_id;
