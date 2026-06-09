-- Phase 5.10: owner/building/unit dashboard views (read-only, masked).
-- Polish over the first active owner relationship so it can be inspected, audited,
-- traced to source, and revert-checked in NocoDB before scaling. Person names are
-- masked via mask_name() (migration 007); no phones/emails/websites/addresses are
-- exposed. Building/unit/property fields are business data and shown as-is.

DROP VIEW IF EXISTS vw_owner_relationship_dashboard;
DROP VIEW IF EXISTS vw_building_unit_owner_summary;
-- CASCADE: Phase 6.0 layered human-dashboard views (migration 011) depend on this
-- view. On a re-apply they are dropped here and recreated by 011 later in the pass.
DROP VIEW IF EXISTS vw_contact_property_trace_full CASCADE;
DROP VIEW IF EXISTS vw_property_relationship_revert_readiness;

-- 1. Active owner/unit relationships, one row each, with review + source context.
CREATE VIEW vw_owner_relationship_dashboard AS
SELECT
  cpr.id AS relationship_id,
  cpr.contact_id,
  mask_name(c.full_name) AS contact_display_hint,
  cpr.relationship_type,
  cpr.relationship_status,
  cpr.building_id,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.building_code,
  bu.wing,
  bu.unit_number,
  bu.canonical_status AS unit_status,
  (SELECT ba.status FROM building_aliases ba
     WHERE ba.building_id = cpr.building_id
       AND ba.metadata->>'rel_label' = cpr.raw_context->>'rel_label'
     ORDER BY ba.created_at LIMIT 1) AS alias_status,
  COALESCE(sf.detected_source_format, cir.source_format) AS source_format,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  cir.source_row_number,
  pr.id AS review_item_id,
  pr.status AS review_status,
  pr.reviewed_by,
  pr.reviewed_at,
  cpr.created_at,
  cpr.updated_at
FROM contact_property_relationships cpr
LEFT JOIN contacts c ON c.id = cpr.contact_id
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN contact_import_rows cir ON cir.id = cpr.source_contact_import_row_id
LEFT JOIN source_files sf ON sf.id = cpr.source_file_id
LEFT JOIN LATERAL (
  SELECT id, status, reviewed_by, reviewed_at
  FROM property_relationship_review_items pri
  WHERE pri.contact_property_relationship_id = cpr.id
  ORDER BY pri.created_at LIMIT 1
) pr ON true
WHERE cpr.relationship_type = 'owner' AND cpr.relationship_status = 'active';

-- 2. Building/unit level owner summary.
CREATE VIEW vw_building_unit_owner_summary AS
SELECT
  bu.building_id,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.building_code,
  bu.wing,
  bu.unit_number,
  bu.canonical_status AS unit_status,
  count(cpr.id) FILTER (WHERE cpr.relationship_type = 'owner') AS owner_relationship_count,
  count(cpr.id) FILTER (WHERE cpr.relationship_type = 'owner' AND cpr.relationship_status = 'active') AS active_owner_count,
  count(cpr.id) FILTER (WHERE cpr.relationship_status IN ('pending_review', 'needs_more_info')) AS pending_relationship_count,
  count(DISTINCT cpr.source_file_id) AS source_file_count,
  max(GREATEST(bu.updated_at, cpr.updated_at)) AS last_updated
FROM building_units bu
LEFT JOIN buildings b ON b.id = bu.building_id
LEFT JOIN contact_property_relationships cpr ON cpr.building_unit_id = bu.id
GROUP BY bu.id, bu.building_id, b.name, bu.building_name, bu.building_code, bu.wing, bu.unit_number, bu.canonical_status;

-- 3. Full trace: contact -> relationship -> building/unit -> source import -> canonical merge.
CREATE VIEW vw_contact_property_trace_full AS
SELECT
  cpr.contact_id,
  mask_name(c.full_name) AS contact_display_hint,
  cpr.id AS relationship_id,
  cpr.relationship_type,
  cpr.relationship_status,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.wing,
  bu.unit_number,
  ib.source_name AS source_batch_label,
  COALESCE(sf.detected_source_format, cir.source_format) AS source_format,
  COALESCE(sf.original_file_name, cir.source_file) AS source_file,
  cir.source_row_number,
  cpr.source_contact_import_row_id AS contact_import_row_id,
  cmb.merge_label AS canonical_merge_label,
  cmb.status AS canonical_merge_status,
  pr.id AS property_review_item_id,
  pr.status AS property_review_status,
  (SELECT count(*) FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id) AS property_action_log_count
FROM contact_property_relationships cpr
LEFT JOIN contacts c ON c.id = cpr.contact_id
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN contact_import_rows cir ON cir.id = cpr.source_contact_import_row_id
LEFT JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN source_files sf ON sf.id = cpr.source_file_id
LEFT JOIN LATERAL (
  SELECT id, status FROM property_relationship_review_items pri
  WHERE pri.contact_property_relationship_id = cpr.id ORDER BY pri.created_at LIMIT 1
) pr ON true
LEFT JOIN LATERAL (
  SELECT cmb.merge_label, cmb.status
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.canonical_contact_id = cpr.contact_id AND cml.merge_action = 'create_contact' AND cmb.status = 'applied'
  ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC LIMIT 1
) cmb ON true;

-- 4. Revert readiness for each relationship.
CREATE VIEW vw_property_relationship_revert_readiness AS
SELECT
  cpr.id AS relationship_id,
  pr.id AS review_item_id,
  cpr.relationship_status,
  pr.status AS review_status,
  COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) AS communication_sent,
  EXISTS (
    SELECT 1 FROM property_relationship_action_log pal
    WHERE pal.contact_property_relationship_id = cpr.id
      AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')
  ) AS has_downstream_activity,
  (SELECT count(*) FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id) AS action_log_count,
  (
    cpr.relationship_status = 'active'
    AND pr.status = 'approved'
    AND COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) = false
    AND NOT EXISTS (
      SELECT 1 FROM property_relationship_action_log pal
      WHERE pal.contact_property_relationship_id = cpr.id
        AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')
    )
  ) AS revert_allowed,
  CASE
    WHEN cpr.relationship_status <> 'active' THEN 'relationship_not_active'
    WHEN pr.status IS DISTINCT FROM 'approved' THEN 'review_not_approved'
    WHEN COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) THEN 'communication_sent'
    WHEN EXISTS (
      SELECT 1 FROM property_relationship_action_log pal
      WHERE pal.contact_property_relationship_id = cpr.id
        AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')
    ) THEN 'downstream_activity'
    ELSE NULL
  END AS reason_if_not_allowed,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.wing,
  bu.unit_number
FROM contact_property_relationships cpr
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN LATERAL (
  SELECT id, status FROM property_relationship_review_items pri
  WHERE pri.contact_property_relationship_id = cpr.id ORDER BY pri.created_at LIMIT 1
) pr ON true;
