-- Phase 5.13: Milestone 2B checkpoint + data-quality dashboard (read-only, masked).
-- A system snapshot before scaling beyond two owner/unit relationships. Person names
-- are masked via mask_name() (migration 007); the duplicate `reason` text describes
-- the match TYPE only ("matching normalized phone/email"), never raw values. No
-- phones/emails/websites/addresses are exposed.

-- CASCADE on views that Phase 6.0 human-dashboard views (migration 011) build on:
-- on a re-apply they are dropped here and recreated by 011 later in the same pass.
DROP VIEW IF EXISTS vw_milestone_2b_summary CASCADE;
DROP VIEW IF EXISTS vw_owner_unit_batch_quality;
DROP VIEW IF EXISTS vw_owner_unit_candidate_queue CASCADE;
DROP VIEW IF EXISTS vw_owner_relationship_revert_dashboard CASCADE;
DROP VIEW IF EXISTS vw_duplicate_risk_dashboard CASCADE;

-- The owner/unit audit batch this milestone is built on.
-- (Inlined as a literal in each view; kept here as documentation.)
-- REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001

-- 1. One-row system summary.
CREATE VIEW vw_milestone_2b_summary AS
WITH oub AS (SELECT id FROM import_batches WHERE source_name = 'REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001'),
linked AS (
  SELECT DISTINCT cml.contact_import_row_id
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.merge_action = 'create_contact' AND cmb.status = 'applied'
    AND cml.import_batch_id IN (SELECT id FROM oub)
)
SELECT
  (SELECT count(*) FROM contacts) AS canonical_contacts_total,
  (SELECT count(*) FROM contacts WHERE canonical_status = 'active') AS active_canonical_contacts,
  (SELECT count(*) FROM contact_property_relationships WHERE relationship_status = 'active' AND relationship_type = 'owner') AS active_owner_relationships,
  (SELECT count(*) FROM property_relationship_review_items WHERE status = 'approved') AS approved_owner_relationship_reviews,
  (SELECT count(*) FROM property_relationship_review_items WHERE status = 'pending') AS pending_owner_relationship_reviews,
  (SELECT count(*) FROM buildings) AS buildings_total,
  (SELECT count(*) FROM building_units) AS building_units_total,
  (SELECT count(*) FROM building_aliases WHERE status = 'approved') AS approved_building_aliases,
  (SELECT count(*) FROM building_aliases WHERE status = 'pending_review') AS pending_building_aliases,
  (SELECT count(*) FROM import_batches) AS source_batches_total,
  (SELECT count(*) FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM oub)) AS owner_unit_batch_rows,
  (SELECT count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM oub) AND status = 'pending') AS owner_unit_batch_pending_reviews,
  (SELECT count(*) FROM import_review_items WHERE import_batch_id IN (SELECT id FROM oub) AND status = 'approved') AS owner_unit_batch_approved_reviews,
  (SELECT count(*) FROM contact_duplicate_candidates WHERE import_batch_id IN (SELECT id FROM oub)) AS owner_unit_duplicate_candidates,
  (SELECT count(*) FROM linked) AS owner_unit_rows_linked_to_canonical,
  ((SELECT count(*) FROM contact_import_rows WHERE import_batch_id IN (SELECT id FROM oub)) - (SELECT count(*) FROM linked)) AS owner_unit_rows_not_linked_to_canonical,
  ((SELECT count(*) FROM contact_property_relationships WHERE raw_context->>'communication_sent' = 'true')
   + (SELECT count(*) FROM canonical_merge_batches WHERE metadata->>'communication_sent' = 'true')) AS communication_sent_count,
  now() AS generated_at;

-- 2. Quality breakdown for the owner/unit audit batch (one row).
CREATE VIEW vw_owner_unit_batch_quality AS
WITH oub AS (SELECT id FROM import_batches WHERE source_name = 'REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001'),
r AS (
  SELECT cir.id,
    EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) AS has_method,
    EXISTS (SELECT 1 FROM contact_property_hints cph WHERE cph.contact_import_row_id = cir.id) AS has_hint,
    EXISTS (SELECT 1 FROM inventory_import_rows iir WHERE iir.owner_contact_import_row_id = cir.id) AS has_inv,
    EXISTS (SELECT 1 FROM contact_duplicate_candidates dc WHERE dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id) AS in_dup,
    EXISTS (SELECT 1 FROM canonical_merge_links cml JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
            WHERE cml.contact_import_row_id = cir.id AND cml.merge_action = 'create_contact' AND cmb.status = 'applied') AS linked,
    EXISTS (SELECT 1 FROM canonical_merge_links cml JOIN contact_property_relationships rel ON rel.contact_id = cml.canonical_contact_id
            WHERE cml.contact_import_row_id = cir.id AND cml.merge_action = 'create_contact'
              AND rel.relationship_status = 'active') AS has_active_rel,
    (SELECT iri.status FROM import_review_items iri WHERE iri.contact_import_row_id = cir.id AND iri.review_type = 'merge_candidate' ORDER BY iri.created_at LIMIT 1) AS review_status
  FROM contact_import_rows cir WHERE cir.import_batch_id IN (SELECT id FROM oub)
)
SELECT
  'REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001' AS batch_label,
  count(*) AS contact_import_rows,
  count(*) FILTER (WHERE has_method) AS rows_with_contact_methods,
  count(*) FILTER (WHERE has_hint) AS rows_with_property_hints,
  count(*) FILTER (WHERE has_inv) AS rows_with_inventory_rows,
  count(*) FILTER (WHERE in_dup) AS rows_in_duplicate_candidates,
  count(*) FILTER (WHERE linked) AS rows_linked_to_canonical_contacts,
  count(*) FILTER (WHERE has_active_rel) AS rows_with_active_relationships,
  count(*) FILTER (WHERE review_status = 'pending') AS rows_pending_review,
  count(*) FILTER (WHERE review_status = 'approved') AS rows_approved_review,
  count(*) FILTER (WHERE has_method AND has_hint AND NOT in_dup AND NOT linked) AS safe_candidate_estimate,
  count(*) FILTER (WHERE in_dup AND NOT linked) AS risky_duplicate_estimate
FROM r;

-- 3. Safe candidate queue for next phases (one row per not-yet-linked owner/unit
--    merge_candidate row).
CREATE VIEW vw_owner_unit_candidate_queue AS
WITH oub AS (SELECT id FROM import_batches WHERE source_name = 'REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001')
SELECT
  cir.id AS contact_import_row_id,
  iri.id AS review_item_id,
  cir.source_row_number,
  cir.source_format,
  EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) AS has_contact_method,
  (SELECT count(*) FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) AS method_count,
  EXISTS (SELECT 1 FROM contact_property_hints cph WHERE cph.contact_import_row_id = cir.id) AS has_property_hint,
  EXISTS (SELECT 1 FROM inventory_import_rows iir2 WHERE iir2.owner_contact_import_row_id = cir.id) AS has_inventory_row,
  EXISTS (SELECT 1 FROM contact_property_hints cph WHERE cph.contact_import_row_id = cir.id
          AND (NULLIF(btrim(cph.building_name), '') IS NOT NULL OR NULLIF(btrim(cph.building_code), '') IS NOT NULL)) AS has_building_hint,
  EXISTS (SELECT 1 FROM contact_property_hints cph WHERE cph.contact_import_row_id = cir.id
          AND NULLIF(btrim(cph.unit_number), '') IS NOT NULL) AS has_unit_hint,
  EXISTS (SELECT 1 FROM contact_duplicate_candidates dc WHERE dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id) AS duplicate_involved,
  false AS already_linked_to_canonical,
  false AS has_active_relationship,
  iri.status AS review_status,
  CASE
    WHEN EXISTS (SELECT 1 FROM contact_duplicate_candidates dc WHERE dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id) THEN 'duplicate_review_first'
    WHEN NOT EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) THEN 'needs_contact_method'
    WHEN iri.status = 'approved' THEN 'ready_to_merge'
    WHEN iri.status = 'pending' THEN 'approve_then_merge'
    ELSE 'needs_more_info'
  END AS recommended_next_action,
  CASE
    WHEN EXISTS (SELECT 1 FROM contact_duplicate_candidates dc WHERE dc.contact_import_row_id_1 = cir.id OR dc.contact_import_row_id_2 = cir.id) THEN 'duplicate_candidate_present'
    WHEN NOT EXISTS (SELECT 1 FROM contact_methods cm WHERE cm.contact_import_row_id = cir.id) THEN 'no_contact_method'
    WHEN EXISTS (SELECT 1 FROM contact_property_hints cph WHERE cph.contact_import_row_id = cir.id) THEN 'safe_owner_unit_candidate'
    ELSE 'incomplete_signals'
  END AS safe_reason
FROM contact_import_rows cir
JOIN import_review_items iri ON iri.contact_import_row_id = cir.id AND iri.review_type = 'merge_candidate'
WHERE cir.import_batch_id IN (SELECT id FROM oub)
  AND NOT EXISTS (
    SELECT 1 FROM canonical_merge_links cml JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
    WHERE cml.contact_import_row_id = cir.id AND cml.merge_action = 'create_contact' AND cmb.status = 'applied'
  );

-- 4. Active owner relationships + revert readiness (masked).
CREATE VIEW vw_owner_relationship_revert_dashboard AS
SELECT
  cpr.id AS relationship_id,
  pr.id AS review_item_id,
  mask_name(c.full_name) AS contact_display_hint,
  COALESCE(b.name, bu.building_name) AS building_name,
  bu.wing,
  bu.unit_number,
  cpr.relationship_type,
  cpr.relationship_status,
  pr.status AS review_status,
  (SELECT count(*) FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id) AS action_log_count,
  COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) AS communication_sent,
  EXISTS (SELECT 1 FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id
          AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')) AS has_downstream_activity,
  (cpr.relationship_status = 'active' AND pr.status = 'approved'
   AND COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) = false
   AND NOT EXISTS (SELECT 1 FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id
                   AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship'))) AS revert_allowed,
  CASE
    WHEN cpr.relationship_status <> 'active' THEN 'relationship_not_active'
    WHEN pr.status IS DISTINCT FROM 'approved' THEN 'review_not_approved'
    WHEN COALESCE((cpr.raw_context->>'communication_sent')::boolean, false) THEN 'communication_sent'
    WHEN EXISTS (SELECT 1 FROM property_relationship_action_log pal WHERE pal.contact_property_relationship_id = cpr.id
                 AND pal.action_type NOT IN ('approve_property_relationship', 'revert_property_relationship')) THEN 'downstream_activity'
    ELSE NULL
  END AS reason_if_not_allowed
FROM contact_property_relationships cpr
LEFT JOIN contacts c ON c.id = cpr.contact_id
LEFT JOIN buildings b ON b.id = cpr.building_id
LEFT JOIN building_units bu ON bu.id = cpr.building_unit_id
LEFT JOIN LATERAL (
  SELECT id, status FROM property_relationship_review_items pri
  WHERE pri.contact_property_relationship_id = cpr.id ORDER BY pri.created_at LIMIT 1
) pr ON true
WHERE cpr.relationship_type = 'owner' AND cpr.relationship_status = 'active';

-- 5. Duplicate-risk groups (no raw contact data; reason text is type-only).
CREATE VIEW vw_duplicate_risk_dashboard AS
SELECT
  ib.source_name AS batch_label,
  dc.id AS duplicate_candidate_id,
  dc.duplicate_strength,
  dc.status,
  dc.reason,
  ((dc.contact_import_row_id_1 IS NOT NULL)::int + (dc.contact_import_row_id_2 IS NOT NULL)::int) AS involved_row_count,
  (SELECT cir.source_format FROM contact_import_rows cir
     WHERE cir.id = COALESCE(dc.contact_import_row_id_1, dc.contact_import_row_id_2) LIMIT 1) AS source_format,
  ('strength=' || COALESCE(dc.duplicate_strength, '?') || ', status=' || dc.status) AS safe_summary,
  CASE
    WHEN dc.status = 'pending_review' THEN 'review_before_merge'
    WHEN dc.status = 'approved_merge' THEN 'merge_then_dedupe'
    WHEN dc.status = 'rejected' THEN 'no_action'
    ELSE 'no_action'
  END AS recommended_action
FROM contact_duplicate_candidates dc
LEFT JOIN import_batches ib ON ib.id = dc.import_batch_id;
