CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE import_review_items
  DROP CONSTRAINT IF EXISTS import_review_items_status_check;

ALTER TABLE import_review_items
  ADD CONSTRAINT import_review_items_status_check
  CHECK (status IN ('pending', 'approved', 'rejected', 'merged', 'merged_later', 'skipped', 'needs_more_info'));

ALTER TABLE contact_duplicate_candidates
  DROP CONSTRAINT IF EXISTS contact_duplicate_candidates_status_check;

ALTER TABLE contact_duplicate_candidates
  ADD CONSTRAINT contact_duplicate_candidates_status_check
  CHECK (status IN ('pending_review', 'approved_merge', 'rejected', 'ignored', 'not_duplicate', 'duplicate_confirmed', 'needs_more_info', 'skipped'));

CREATE TABLE IF NOT EXISTS review_action_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_review_item_id uuid REFERENCES import_review_items(id) ON DELETE SET NULL,
  duplicate_candidate_id uuid REFERENCES contact_duplicate_candidates(id) ON DELETE SET NULL,
  old_status text,
  new_status text,
  action_type text,
  reviewed_by text,
  decision_notes text,
  raw_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_review_action_log_import_review_item_id ON review_action_log(import_review_item_id);
CREATE INDEX IF NOT EXISTS idx_review_action_log_duplicate_candidate_id ON review_action_log(duplicate_candidate_id);
CREATE INDEX IF NOT EXISTS idx_review_action_log_action_type ON review_action_log(action_type);
CREATE INDEX IF NOT EXISTS idx_review_action_log_reviewed_by ON review_action_log(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_review_action_log_created_at ON review_action_log(created_at);

DROP VIEW IF EXISTS vw_review_dashboard_summary;
DROP VIEW IF EXISTS vw_review_duplicate_candidates;
DROP VIEW IF EXISTS vw_review_queue;

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
  count(DISTINCT ral.id) AS action_history_count,
  ib.created_at
FROM import_batches ib
LEFT JOIN source_files sf ON sf.import_batch_id = ib.id
LEFT JOIN contact_import_rows cir ON cir.import_batch_id = ib.id
LEFT JOIN contact_methods cm ON cm.contact_import_row_id = cir.id
LEFT JOIN lead_requirements lr ON lr.contact_import_row_id = cir.id
LEFT JOIN contact_duplicate_candidates cdc ON cdc.import_batch_id = ib.id
LEFT JOIN import_review_items iri ON iri.import_batch_id = ib.id
LEFT JOIN review_action_log ral
  ON ral.import_review_item_id = iri.id
  OR ral.duplicate_candidate_id = cdc.id
GROUP BY ib.id, ib.metadata, ib.created_at;

CREATE OR REPLACE VIEW vw_review_duplicate_candidates AS
SELECT
  cdc.import_batch_id,
  ib.metadata->>'batch_label' AS batch_label,
  cdc.id AS duplicate_candidate_id,
  cdc.duplicate_strength,
  cdc.candidate_type,
  cdc.reason,
  cdc.status,
  count(ral.id) AS action_history_count,
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
LEFT JOIN contact_import_rows right_row ON right_row.id = cdc.contact_import_row_id_2
LEFT JOIN review_action_log ral ON ral.duplicate_candidate_id = cdc.id
GROUP BY
  cdc.id,
  cdc.import_batch_id,
  ib.metadata,
  left_row.source_file,
  left_row.source_row_number,
  right_row.source_file,
  right_row.source_row_number,
  left_row.cleaned_display_name,
  right_row.cleaned_display_name,
  left_row.phone_normalized,
  right_row.phone_normalized,
  left_row.email_normalized,
  right_row.email_normalized;

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
  iri.decision_notes,
  count(ral.id) AS action_history_count,
  iri.created_at
FROM import_review_items iri
JOIN import_batches ib ON ib.id = iri.import_batch_id
LEFT JOIN review_action_log ral ON ral.import_review_item_id = iri.id
GROUP BY iri.id, ib.metadata;
