CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS canonical_merge_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merge_label text UNIQUE NOT NULL,
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  is_test boolean NOT NULL DEFAULT false,
  source_description text,
  status text NOT NULL DEFAULT 'created',
  canonical_contacts_created integer NOT NULL DEFAULT 0,
  contact_methods_linked integer NOT NULL DEFAULT 0,
  aliases_linked integer NOT NULL DEFAULT 0,
  lead_requirements_linked integer NOT NULL DEFAULT 0,
  inventory_hints_linked integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  applied_at timestamptz,
  rolled_back_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT canonical_merge_batches_status_check
    CHECK (status IN ('created', 'applied', 'rolled_back', 'failed'))
);

CREATE TABLE IF NOT EXISTS canonical_merge_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  merge_batch_id uuid REFERENCES canonical_merge_batches(id) ON DELETE CASCADE,
  import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL,
  contact_import_row_id uuid REFERENCES contact_import_rows(id) ON DELETE SET NULL,
  canonical_contact_id uuid REFERENCES contacts(id) ON DELETE SET NULL,
  source_file_id uuid REFERENCES source_files(id) ON DELETE SET NULL,
  merge_action text,
  review_item_id uuid REFERENCES import_review_items(id) ON DELETE SET NULL,
  confidence numeric,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT canonical_merge_links_action_check
    CHECK (merge_action IN ('create_contact', 'link_method', 'link_alias', 'link_lead_requirement', 'skipped'))
);

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_test boolean NOT NULL DEFAULT false;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS source_import_batch_id uuid REFERENCES import_batches(id) ON DELETE SET NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS source_merge_batch_id uuid REFERENCES canonical_merge_batches(id) ON DELETE SET NULL;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS canonical_status text NOT NULL DEFAULT 'active';

ALTER TABLE contacts
  DROP CONSTRAINT IF EXISTS contacts_canonical_status_check;

ALTER TABLE contacts
  ADD CONSTRAINT contacts_canonical_status_check
  CHECK (canonical_status IN ('active', 'test', 'archived', 'merged', 'inactive'));

CREATE INDEX IF NOT EXISTS idx_canonical_merge_batches_merge_label ON canonical_merge_batches(merge_label);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_batches_import_batch_id ON canonical_merge_batches(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_batches_status ON canonical_merge_batches(status);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_batches_is_test ON canonical_merge_batches(is_test);

CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_merge_batch_id ON canonical_merge_links(merge_batch_id);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_import_batch_id ON canonical_merge_links(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_contact_import_row_id ON canonical_merge_links(contact_import_row_id);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_canonical_contact_id ON canonical_merge_links(canonical_contact_id);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_merge_action ON canonical_merge_links(merge_action);
CREATE INDEX IF NOT EXISTS idx_canonical_merge_links_review_item_id ON canonical_merge_links(review_item_id);

CREATE INDEX IF NOT EXISTS idx_contacts_is_test ON contacts(is_test);
CREATE INDEX IF NOT EXISTS idx_contacts_source_import_batch_id ON contacts(source_import_batch_id);
CREATE INDEX IF NOT EXISTS idx_contacts_source_merge_batch_id ON contacts(source_merge_batch_id);
CREATE INDEX IF NOT EXISTS idx_contacts_canonical_status ON contacts(canonical_status);

CREATE OR REPLACE VIEW vw_canonical_merge_batches AS
SELECT
  cmb.id AS merge_batch_id,
  cmb.merge_label,
  cmb.import_batch_id,
  ib.metadata->>'batch_label' AS import_batch_label,
  cmb.is_test,
  cmb.status,
  cmb.canonical_contacts_created,
  cmb.contact_methods_linked,
  cmb.aliases_linked,
  cmb.lead_requirements_linked,
  cmb.inventory_hints_linked,
  cmb.created_at,
  cmb.applied_at,
  cmb.rolled_back_at
FROM canonical_merge_batches cmb
LEFT JOIN import_batches ib ON ib.id = cmb.import_batch_id;

CREATE OR REPLACE VIEW vw_canonical_merge_links AS
SELECT
  cml.id AS merge_link_id,
  cmb.merge_label,
  ib.metadata->>'batch_label' AS import_batch_label,
  cml.merge_action,
  cml.contact_import_row_id,
  cml.canonical_contact_id,
  cml.review_item_id,
  cir.source_file,
  cir.source_row_number,
  cir.source_format,
  CASE WHEN c.id IS NULL THEN NULL ELSE '[CONTACT_CREATED]' END AS canonical_contact_hint,
  cml.confidence,
  cml.created_at
FROM canonical_merge_links cml
JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
LEFT JOIN import_batches ib ON ib.id = cml.import_batch_id
LEFT JOIN contact_import_rows cir ON cir.id = cml.contact_import_row_id
LEFT JOIN contacts c ON c.id = cml.canonical_contact_id;
