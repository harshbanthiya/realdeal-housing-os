CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS contact_import_rows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  source_file text,
  source_sheet text,
  source_row_number integer,
  source_format text,
  raw_name text,
  raw_phone text,
  raw_email text,
  raw_notes text,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  cleaned_display_name text,
  phone_normalized text,
  email_normalized text,
  parsed_building_code text,
  parsed_building_name text,
  parsed_wing text,
  parsed_unit_number text,
  parsed_role text,
  parsed_tags text[] NOT NULL DEFAULT '{}',
  parse_confidence numeric(4,3),
  rejection_reason text,
  needs_review boolean NOT NULL DEFAULT false,
  matched_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contact_aliases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  alias_text text NOT NULL,
  alias_type text NOT NULL DEFAULT 'source_raw_name',
  source_file text,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_aliases_alias_type_check
    CHECK (alias_type IN ('source_raw_name', 'phonebook_raw_name', 'alternate_name', 'company_name', 'business_name', 'other'))
);

CREATE TABLE IF NOT EXISTS contact_property_hints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  building_code text,
  building_name text,
  wing text,
  unit_number text,
  relationship_type text NOT NULL DEFAULT 'unknown',
  confidence numeric(4,3),
  raw_hint text,
  needs_review boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_property_hints_relationship_type_check
    CHECK (relationship_type IN ('owner', 'broker', 'agent', 'tenant', 'buyer', 'seller', 'landlord', 'reference', 'existing_customer', 'business_lead', 'unknown', 'other'))
);

CREATE TABLE IF NOT EXISTS contact_duplicate_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  candidate_type text,
  duplicate_strength text,
  contact_import_row_id_1 uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  contact_import_row_id_2 uuid REFERENCES contact_import_rows(id) ON DELETE CASCADE,
  matched_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  reason text,
  status text NOT NULL DEFAULT 'pending_review',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_duplicate_candidates_strength_check
    CHECK (duplicate_strength IN ('strong', 'medium', 'weak')),
  CONSTRAINT contact_duplicate_candidates_status_check
    CHECK (status IN ('pending_review', 'approved_merge', 'rejected', 'ignored'))
);

ALTER TABLE contact_import_rows ADD COLUMN IF NOT EXISTS source_sheet text;
ALTER TABLE contact_import_rows ADD COLUMN IF NOT EXISTS source_format text;
ALTER TABLE contact_import_rows ADD COLUMN IF NOT EXISTS parsed_building_name text;

ALTER TABLE contact_property_hints ADD COLUMN IF NOT EXISTS building_name text;

ALTER TABLE contact_aliases ALTER COLUMN alias_type SET DEFAULT 'source_raw_name';

CREATE INDEX IF NOT EXISTS idx_contact_import_rows_import_batch_id ON contact_import_rows(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_phone_normalized ON contact_import_rows(phone_normalized);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_email_normalized ON contact_import_rows(email_normalized);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_parsed_building_code ON contact_import_rows(parsed_building_code);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_parsed_building_name ON contact_import_rows(parsed_building_name);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_parsed_wing ON contact_import_rows(parsed_wing);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_parsed_unit_number ON contact_import_rows(parsed_unit_number);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_source_file ON contact_import_rows(source_file);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_source_format ON contact_import_rows(source_format);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_needs_review ON contact_import_rows(needs_review);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_matched_contact_id ON contact_import_rows(matched_contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_import_rows_source_file_row ON contact_import_rows(source_file, source_row_number);

CREATE INDEX IF NOT EXISTS idx_contact_aliases_contact_id ON contact_aliases(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_aliases_alias_text_lower ON contact_aliases(lower(alias_text));
CREATE INDEX IF NOT EXISTS idx_contact_aliases_alias_type ON contact_aliases(alias_type);

CREATE INDEX IF NOT EXISTS idx_contact_property_hints_contact_id ON contact_property_hints(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_import_row_id ON contact_property_hints(contact_import_row_id);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_building_id ON contact_property_hints(building_id);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_building_code ON contact_property_hints(building_code);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_building_name ON contact_property_hints(building_name);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_unit_number ON contact_property_hints(unit_number);
CREATE INDEX IF NOT EXISTS idx_contact_property_hints_needs_review ON contact_property_hints(needs_review);

CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_import_batch_id ON contact_duplicate_candidates(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_strength ON contact_duplicate_candidates(duplicate_strength);
CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_status ON contact_duplicate_candidates(status);
CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_row_1 ON contact_duplicate_candidates(contact_import_row_id_1);
CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_row_2 ON contact_duplicate_candidates(contact_import_row_id_2);
CREATE INDEX IF NOT EXISTS idx_contact_duplicate_candidates_matched_contact_id ON contact_duplicate_candidates(matched_contact_id);

DROP TRIGGER IF EXISTS trg_contact_import_rows_updated_at ON contact_import_rows;
CREATE TRIGGER trg_contact_import_rows_updated_at
BEFORE UPDATE ON contact_import_rows
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_contact_property_hints_updated_at ON contact_property_hints;
CREATE TRIGGER trg_contact_property_hints_updated_at
BEFORE UPDATE ON contact_property_hints
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
