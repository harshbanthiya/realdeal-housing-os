CREATE OR REPLACE FUNCTION mask_phone(value text)
RETURNS text AS $$
DECLARE
  digits text;
BEGIN
  IF value IS NULL OR btrim(value) = '' THEN
    RETURN NULL;
  END IF;
  digits := regexp_replace(value, '\D', '', 'g');
  IF length(digits) <= 4 THEN
    RETURN '[MASKED]';
  END IF;
  RETURN '[MASKED]' || right(digits, 4);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION mask_email(value text)
RETURNS text AS $$
DECLARE
  email text;
  domain text;
BEGIN
  IF value IS NULL OR btrim(value) = '' THEN
    RETURN NULL;
  END IF;
  email := lower(btrim(value));
  IF position('@' in email) = 0 THEN
    RETURN '[MASKED]';
  END IF;
  domain := split_part(email, '@', 2);
  IF domain = '' THEN
    RETURN '[MASKED]';
  END IF;
  RETURN left(email, 1) || '[MASKED]@' || domain;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE VIEW vw_review_dashboard_summary AS
SELECT
  ib.id AS import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  COALESCE((ib.metadata->>'is_real_import')::boolean, false) AS is_real_import,
  COALESCE((ib.metadata->>'source_aware_only')::boolean, false) AS source_aware_only,
  COALESCE((ib.metadata->>'canonical_merge_done')::boolean, false) AS canonical_merge_done,
  count(DISTINCT sf.id) AS source_files_count,
  count(DISTINCT cir.id) AS contact_import_rows_count,
  count(DISTINCT cm.id) AS contact_methods_count,
  count(DISTINCT lr.id) AS lead_requirements_count,
  count(DISTINCT cdc.id) AS duplicate_candidates_count,
  count(DISTINCT iri.id) FILTER (WHERE iri.status = 'pending') AS pending_review_items_count,
  count(DISTINCT iri.id) FILTER (WHERE iri.status = 'approved') AS approved_review_items_count,
  count(DISTINCT iri.id) FILTER (WHERE iri.status = 'rejected') AS rejected_review_items_count,
  ib.created_at
FROM import_batches ib
LEFT JOIN source_files sf ON sf.import_batch_id = ib.id
LEFT JOIN contact_import_rows cir ON cir.import_batch_id = ib.id
LEFT JOIN contact_methods cm ON cm.contact_import_row_id = cir.id
LEFT JOIN lead_requirements lr ON lr.contact_import_row_id = cir.id
LEFT JOIN contact_duplicate_candidates cdc ON cdc.import_batch_id = ib.id
LEFT JOIN import_review_items iri ON iri.import_batch_id = ib.id
GROUP BY ib.id, ib.metadata, ib.created_at;

CREATE OR REPLACE VIEW vw_review_contact_methods AS
SELECT
  cir.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  cir.source_file,
  cir.source_format,
  cir.source_row_number,
  cir.cleaned_display_name,
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
  review_status.status AS review_status
FROM contact_methods cm
JOIN contact_import_rows cir ON cir.id = cm.contact_import_row_id
JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN (
  SELECT
    contact_import_row_id,
    CASE
      WHEN bool_or(status = 'pending') THEN 'pending'
      WHEN bool_or(status = 'needs_more_info') THEN 'needs_more_info'
      WHEN bool_or(status = 'approved') THEN 'approved'
      WHEN bool_or(status = 'rejected') THEN 'rejected'
      WHEN bool_or(status = 'skipped') THEN 'skipped'
      WHEN bool_or(status = 'merged') THEN 'merged'
      ELSE NULL
    END AS status
  FROM import_review_items
  WHERE review_type IN ('invalid_phone', 'invalid_email', 'merge_candidate', 'lead_requirement_review', 'property_hint_review')
  GROUP BY contact_import_row_id
) review_status ON review_status.contact_import_row_id = cir.id;

CREATE OR REPLACE VIEW vw_review_business_leads AS
SELECT
  cir.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  cir.source_file,
  cir.source_row_number,
  cir.cleaned_display_name,
  cir.source_format,
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
  iri.status AS review_item_status
FROM lead_requirements lr
JOIN contact_import_rows cir ON cir.id = lr.contact_import_row_id
JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN import_review_items iri
  ON iri.contact_import_row_id = cir.id
 AND iri.review_type = 'lead_requirement_review';

CREATE OR REPLACE VIEW vw_review_duplicate_candidates AS
SELECT
  cdc.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  cdc.duplicate_strength,
  cdc.candidate_type,
  cdc.reason,
  cdc.status,
  left_row.source_file AS left_source_file,
  left_row.source_row_number AS left_source_row_number,
  right_row.source_file AS right_source_file,
  right_row.source_row_number AS right_source_row_number,
  left_row.cleaned_display_name AS left_display_hint,
  right_row.cleaned_display_name AS right_display_hint,
  COALESCE(mask_phone(left_row.phone_normalized), mask_phone(right_row.phone_normalized)) AS masked_phone_hint,
  COALESCE(mask_email(left_row.email_normalized), mask_email(right_row.email_normalized)) AS masked_email_hint
FROM contact_duplicate_candidates cdc
JOIN import_batches ib ON ib.id = cdc.import_batch_id
LEFT JOIN contact_import_rows left_row ON left_row.id = cdc.contact_import_row_id_1
LEFT JOIN contact_import_rows right_row ON right_row.id = cdc.contact_import_row_id_2;

CREATE OR REPLACE VIEW vw_review_queue AS
SELECT
  iri.id AS review_item_id,
  iri.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  iri.review_type,
  iri.priority,
  iri.status,
  iri.title,
  iri.summary,
  iri.recommended_action,
  iri.assigned_to,
  iri.reviewed_by,
  iri.reviewed_at,
  iri.created_at
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id;

CREATE OR REPLACE VIEW vw_review_batch_sources AS
SELECT
  sf.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  sf.id AS source_file_id,
  sf.original_file_name,
  sf.detected_source_format,
  sf.row_count,
  sf.processing_status,
  sf.processing_notes,
  sf.created_at
FROM source_files sf
JOIN import_batches ib ON ib.id = sf.import_batch_id;
