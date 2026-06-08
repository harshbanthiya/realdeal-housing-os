-- Phase 5.1: building / unit / contact relationship pipeline (schema + views).
-- Foundation for linking canonical contacts to buildings/units with a reviewed
-- relationship type (owner / tenant / broker / buyer / lead ...). No real owner
-- or property sheets are imported in this phase. Fake/test rows carry a
-- raw_context/metadata marker so they can be cleaned up precisely.

-- 1. building_aliases: messy import names/codes -> canonical buildings.
CREATE TABLE IF NOT EXISTS building_aliases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  alias_text text NOT NULL,
  alias_type text NOT NULL DEFAULT 'import_alias',
  normalized_alias text,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  source_format text,
  confidence numeric(4,3),
  status text NOT NULL DEFAULT 'pending_review',
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT building_aliases_status_check
    CHECK (status IN ('pending_review', 'approved', 'rejected', 'merged', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_building_aliases_building_id ON building_aliases(building_id);
CREATE INDEX IF NOT EXISTS idx_building_aliases_normalized_alias ON building_aliases(normalized_alias);
CREATE INDEX IF NOT EXISTS idx_building_aliases_alias_text ON building_aliases(alias_text);
CREATE INDEX IF NOT EXISTS idx_building_aliases_status ON building_aliases(status);

-- 2. building_units: canonical / semi-canonical units in buildings.
CREATE TABLE IF NOT EXISTS building_units (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id) ON DELETE CASCADE,
  building_name text,
  building_code text,
  wing text,
  unit_number text,
  floor text,
  typology text,
  bhk text,
  area_carpet numeric,
  area_salable numeric,
  area_unit text,
  canonical_status text NOT NULL DEFAULT 'active',
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  source_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE SET NULL,
  confidence numeric(4,3),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT building_units_canonical_status_check
    CHECK (canonical_status IN ('active', 'inactive', 'duplicate', 'needs_review'))
);

CREATE INDEX IF NOT EXISTS idx_building_units_building_id ON building_units(building_id);
CREATE INDEX IF NOT EXISTS idx_building_units_building_name ON building_units(building_name);
CREATE INDEX IF NOT EXISTS idx_building_units_building_code ON building_units(building_code);
CREATE INDEX IF NOT EXISTS idx_building_units_wing ON building_units(wing);
CREATE INDEX IF NOT EXISTS idx_building_units_unit_number ON building_units(unit_number);
CREATE INDEX IF NOT EXISTS idx_building_units_canonical_status ON building_units(canonical_status);
-- Non-unique on purpose: imported unit data may be messy / duplicated.
CREATE INDEX IF NOT EXISTS idx_building_units_bld_wing_unit ON building_units(building_id, wing, unit_number);

-- 3. contact_property_relationships: canonical contact <-> building/unit link.
CREATE TABLE IF NOT EXISTS contact_property_relationships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  building_unit_id uuid REFERENCES building_units(id) ON DELETE SET NULL,
  source_contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE SET NULL,
  source_property_hint_id uuid REFERENCES contact_property_hints(id) ON DELETE SET NULL,
  source_inventory_import_row_id uuid REFERENCES inventory_import_rows(id) ON DELETE SET NULL,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  relationship_type text NOT NULL,
  relationship_status text NOT NULL DEFAULT 'pending_review',
  confidence numeric(4,3),
  start_date date,
  end_date date,
  notes text,
  raw_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT contact_property_relationships_type_check
    CHECK (relationship_type IN (
      'owner', 'tenant', 'broker', 'agent', 'buyer', 'seller', 'landlord',
      'business_lead', 'interested_buyer', 'interested_tenant', 'unknown')),
  CONSTRAINT contact_property_relationships_status_check
    CHECK (relationship_status IN (
      'pending_review', 'approved', 'rejected', 'active', 'inactive',
      'superseded', 'needs_more_info'))
);

CREATE INDEX IF NOT EXISTS idx_cpr_contact_id ON contact_property_relationships(contact_id);
CREATE INDEX IF NOT EXISTS idx_cpr_building_id ON contact_property_relationships(building_id);
CREATE INDEX IF NOT EXISTS idx_cpr_building_unit_id ON contact_property_relationships(building_unit_id);
CREATE INDEX IF NOT EXISTS idx_cpr_relationship_type ON contact_property_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_cpr_relationship_status ON contact_property_relationships(relationship_status);
CREATE INDEX IF NOT EXISTS idx_cpr_source_file_id ON contact_property_relationships(source_file_id);

-- 4. property_relationship_review_items: dedicated review queue.
CREATE TABLE IF NOT EXISTS property_relationship_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_property_relationship_id uuid REFERENCES contact_property_relationships(id) ON DELETE CASCADE,
  contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  building_id uuid REFERENCES buildings(id) ON DELETE SET NULL,
  building_unit_id uuid REFERENCES building_units(id) ON DELETE SET NULL,
  review_type text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  priority text NOT NULL DEFAULT 'normal',
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
  CONSTRAINT prri_review_type_check
    CHECK (review_type IN (
      'building_alias_review', 'unit_match_review', 'owner_tenant_review',
      'broker_relationship_review', 'lead_interest_review')),
  CONSTRAINT prri_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'skipped', 'needs_more_info')),
  CONSTRAINT prri_priority_check
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE INDEX IF NOT EXISTS idx_prri_contact_id ON property_relationship_review_items(contact_id);
CREATE INDEX IF NOT EXISTS idx_prri_building_id ON property_relationship_review_items(building_id);
CREATE INDEX IF NOT EXISTS idx_prri_building_unit_id ON property_relationship_review_items(building_unit_id);
CREATE INDEX IF NOT EXISTS idx_prri_review_type ON property_relationship_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_prri_status ON property_relationship_review_items(status);
CREATE INDEX IF NOT EXISTS idx_prri_priority ON property_relationship_review_items(priority);

-- 5. property_relationship_action_log: audit of relationship review decisions
--    (separate from review_action_log, which logs import_review_items).
CREATE TABLE IF NOT EXISTS property_relationship_action_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_relationship_review_item_id uuid REFERENCES property_relationship_review_items(id) ON DELETE SET NULL,
  contact_property_relationship_id uuid REFERENCES contact_property_relationships(id) ON DELETE SET NULL,
  old_status text,
  new_status text,
  action_type text,
  reviewed_by text,
  decision_notes text,
  raw_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pral_review_item_id ON property_relationship_action_log(property_relationship_review_item_id);
CREATE INDEX IF NOT EXISTS idx_pral_relationship_id ON property_relationship_action_log(contact_property_relationship_id);
CREATE INDEX IF NOT EXISTS idx_pral_action_type ON property_relationship_action_log(action_type);

-- ---------------------------------------------------------------------------
-- Safe NocoDB views. Person names are masked via mask_name() (migration 007);
-- building/property names are business data and shown as-is.
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS vw_building_alias_review;
DROP VIEW IF EXISTS vw_building_units_review;
DROP VIEW IF EXISTS vw_contact_property_relationship_review;
DROP VIEW IF EXISTS vw_property_relationship_review_queue;
DROP VIEW IF EXISTS vw_contact_building_unit_trace;

CREATE VIEW vw_building_alias_review AS
SELECT
  ba.id AS alias_id,
  ba.alias_text,
  ba.normalized_alias,
  ba.alias_type,
  ba.building_id,
  b.name AS building_name,
  ba.source_format,
  ba.confidence,
  ba.status,
  ba.created_at
FROM building_aliases ba
LEFT JOIN buildings b ON b.id = ba.building_id;

CREATE VIEW vw_building_units_review AS
SELECT
  bu.id AS building_unit_id,
  bu.building_id,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.building_code,
  bu.wing,
  bu.unit_number,
  bu.typology,
  bu.bhk,
  bu.canonical_status,
  bu.confidence,
  bu.source_file_id,
  bu.created_at
FROM building_units bu
LEFT JOIN buildings b ON b.id = bu.building_id;

CREATE VIEW vw_contact_property_relationship_review AS
SELECT
  cpr.id AS relationship_id,
  cpr.contact_id,
  mask_name(c.full_name) AS contact_display_hint,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.building_code,
  bu.wing,
  bu.unit_number,
  cpr.relationship_type,
  cpr.relationship_status,
  cpr.confidence,
  cpr.source_file_id,
  COALESCE(sf.detected_source_format, bu.metadata->>'source_format') AS source_format,
  cpr.created_at
FROM contact_property_relationships cpr
LEFT JOIN contacts c ON c.id = cpr.contact_id
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN source_files sf ON sf.id = cpr.source_file_id;

CREATE VIEW vw_property_relationship_review_queue AS
SELECT
  pr.id AS review_item_id,
  pr.contact_property_relationship_id AS relationship_id,
  pr.review_type,
  pr.status,
  pr.priority,
  pr.title,
  pr.summary,
  pr.recommended_action,
  pr.assigned_to,
  pr.reviewed_by,
  pr.reviewed_at,
  pr.created_at
FROM property_relationship_review_items pr;

CREATE VIEW vw_contact_building_unit_trace AS
SELECT
  cpr.contact_id,
  cpr.id AS relationship_id,
  cpr.relationship_type,
  cpr.relationship_status,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.wing,
  bu.unit_number,
  cpr.source_file_id,
  sf.original_file_name AS source_file,
  COALESCE(sf.detected_source_format, cir.source_format) AS source_format,
  cpr.source_contact_import_row_id AS source_row_reference,
  cpr.created_at
FROM contact_property_relationships cpr
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN source_files sf ON sf.id = cpr.source_file_id
LEFT JOIN contact_import_rows cir ON cir.id = cpr.source_contact_import_row_id;
