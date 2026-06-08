-- Phase 4.1: canonical contact review dashboard + source traceability.
-- Safe, read-only NocoDB views over the first real canonical contact(s).
-- No raw personal values: names are reduced to an initial via mask_name(),
-- phones/emails go through mask_phone()/mask_email(), links become hints.

-- Name masking helper (phone/email maskers already exist in migration 004).
CREATE OR REPLACE FUNCTION mask_name(value text)
RETURNS text AS $$
BEGIN
  IF value IS NULL OR btrim(value) = '' THEN
    RETURN NULL;
  END IF;
  -- Expose only the first initial as a review hint, never the full name.
  RETURN left(btrim(value), 1) || '[MASKED]';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

DROP VIEW IF EXISTS vw_canonical_contacts_review;
DROP VIEW IF EXISTS vw_canonical_contact_methods_review;
DROP VIEW IF EXISTS vw_canonical_source_trace;
DROP VIEW IF EXISTS vw_canonical_lead_requirements_review;
DROP VIEW IF EXISTS vw_canonical_merge_audit;

-- 1. Canonical contacts, one row per canonical contact, counts + provenance.
CREATE VIEW vw_canonical_contacts_review AS
SELECT
  c.id AS contact_id,
  mask_name(c.full_name) AS display_hint,
  c.canonical_status,
  c.is_test,
  c.source_import_batch_id,
  c.source_merge_batch_id,
  c.created_at,
  c.updated_at,
  (SELECT count(*) FROM contact_methods cm WHERE cm.contact_id = c.id) AS method_count,
  (SELECT count(*) FROM lead_requirements lr WHERE lr.contact_id = c.id) AS lead_requirement_count,
  (SELECT count(DISTINCT cml.source_file_id)
     FROM canonical_merge_links cml
    WHERE cml.canonical_contact_id = c.id AND cml.source_file_id IS NOT NULL) AS source_file_count,
  cmb.merge_label,
  cmb.status AS merge_status
FROM contacts c
LEFT JOIN canonical_merge_batches cmb ON cmb.id = c.source_merge_batch_id;

-- 2. Contact methods linked to canonical contacts, masked values only.
CREATE VIEW vw_canonical_contact_methods_review AS
SELECT
  cm.contact_id,
  c.canonical_status,
  cm.method_type,
  CASE
    WHEN cm.method_type IN ('phone', 'mobile', 'landline', 'whatsapp') THEN mask_phone(cm.normalized_value)
    WHEN cm.method_type = 'email' THEN mask_email(cm.normalized_value)
    WHEN cm.method_type IN ('website', 'google_maps', 'social') THEN '[LINK_PRESENT]'
    ELSE '[MASKED]'
  END AS masked_value,
  cm.label,
  cm.is_primary,
  cm.validation_status,
  cm.confidence,
  COALESCE(cm.source_file, cir.source_file) AS source_file,
  cir.source_format,
  COALESCE(cm.source_row_number, cir.source_row_number) AS source_row_number,
  cm.created_at
FROM contact_methods cm
JOIN contacts c ON c.id = cm.contact_id
LEFT JOIN contact_import_rows cir ON cir.id = cm.contact_import_row_id
WHERE cm.contact_id IS NOT NULL;

-- 3. Source trace: canonical contact -> merge link -> source file / import row / review item.
CREATE VIEW vw_canonical_source_trace AS
SELECT
  cml.canonical_contact_id AS contact_id,
  cmb.merge_label,
  cmb.status AS merge_status,
  cml.merge_action,
  cml.import_batch_id,
  cml.source_file_id,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  COALESCE(sf.detected_source_format, cir.source_format) AS source_format,
  cir.source_row_number,
  cml.review_item_id,
  iri.review_type,
  iri.status AS review_status,
  iri.reviewed_by,
  iri.reviewed_at,
  cml.contact_import_row_id,
  cml.created_at
FROM canonical_merge_links cml
JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
LEFT JOIN source_files sf ON sf.id = cml.source_file_id
LEFT JOIN contact_import_rows cir ON cir.id = cml.contact_import_row_id
LEFT JOIN import_review_items iri ON iri.id = cml.review_item_id
WHERE cml.canonical_contact_id IS NOT NULL;

-- 4. Lead requirements linked to canonical contacts (requirement metadata, no raw contact values).
CREATE VIEW vw_canonical_lead_requirements_review AS
SELECT
  lr.contact_id,
  lr.source_format,
  lr.platform,
  lr.campaign_name,
  lr.purpose,
  lr.property_type,
  lr.locality,
  lr.city,
  lr.budget_min,
  lr.budget_max,
  lr.lead_status,
  lr.needs_review,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  cir.source_row_number,
  lr.created_at
FROM lead_requirements lr
JOIN contacts c ON c.id = lr.contact_id
LEFT JOIN contact_import_rows cir ON cir.id = lr.contact_import_row_id
LEFT JOIN source_files sf ON sf.id = lr.source_file_id
WHERE lr.contact_id IS NOT NULL;

-- 5. Merge audit: batch status + rollback readiness + communication flag.
CREATE VIEW vw_canonical_merge_audit AS
SELECT
  cmb.id AS merge_batch_id,
  cmb.merge_label,
  cmb.status,
  cmb.is_test,
  cmb.import_batch_id,
  cmb.canonical_contacts_created,
  cmb.contact_methods_linked,
  cmb.lead_requirements_linked,
  cmb.metadata,
  cmb.created_at,
  cmb.applied_at,
  cmb.rolled_back_at,
  (cmb.status = 'applied'
     AND COALESCE(cmb.metadata->>'communication_sent', 'false') <> 'true') AS rollback_allowed,
  COALESCE((cmb.metadata->>'communication_sent')::boolean, false) AS communication_sent
FROM canonical_merge_batches cmb;
