-- Phase 5.13A: Human operator dashboard views (read-only, masked).
--
-- These views sit on top of the Milestone 2B dashboard views (migrations 007-010)
-- and re-shape them for a human operating NocoDB. They add NO new data and mutate
-- nothing. Person names are exposed only through the already-masked
-- contact_display_hint columns of the underlying views (mask_name(), migration 007:
-- first initial + "[MASKED]"). No phones/emails/websites/addresses are selected.
-- Building/unit/property names are business data and may appear (same policy as the
-- existing dashboard views).
--
-- Naming: vw_human_* signals "open these first in NocoDB". Each is a thin,
-- friendlier projection of an existing audited view, so correctness stays anchored
-- in the lower layers.

DROP VIEW IF EXISTS vw_human_candidate_review_queue;
DROP VIEW IF EXISTS vw_human_owner_relationships;
DROP VIEW IF EXISTS vw_human_next_actions;
DROP VIEW IF EXISTS vw_human_dashboard_home;

-- 1. One-row "home" overview of the whole system, for the top of the dashboard.
--    Pure counts; no identifiers.
CREATE VIEW vw_human_dashboard_home AS
SELECT
  s.canonical_contacts_total                                            AS canonical_contacts,
  s.active_canonical_contacts                                           AS active_canonical_contacts,
  s.active_owner_relationships                                          AS active_owner_relationships,
  (SELECT count(*) FROM vw_owner_unit_candidate_queue)                  AS pending_candidate_queue,
  (SELECT count(*) FROM vw_owner_unit_candidate_queue
     WHERE NOT duplicate_involved AND has_contact_method)               AS safe_candidate_queue,
  (SELECT count(*) FROM vw_duplicate_risk_dashboard)                    AS duplicate_risk_count,
  (SELECT count(*) FROM vw_owner_relationship_revert_dashboard
     WHERE revert_allowed = true)                                       AS revert_ready_active_relationships,
  s.communication_sent_count                                           AS communications_sent,
  s.buildings_total                                                     AS buildings,
  s.building_units_total                                                AS building_units,
  s.pending_owner_relationship_reviews                                  AS pending_relationship_reviews,
  now()                                                                 AS generated_at
FROM vw_milestone_2b_summary s;

-- 2. Safe action queue: one row per actionable item, lowest "priority" first.
--    Sourced entirely from existing views/tables. No raw contact values; the only
--    person hint is the already-masked display hint where one is meaningful.
CREATE VIEW vw_human_next_actions AS
-- (a) Owner/unit candidates not yet linked to a canonical contact.
SELECT
  CASE WHEN q.duplicate_involved THEN 'resolve_duplicate_then_merge'
       ELSE 'merge_owner_unit_candidate' END                           AS action_type,
  CASE
    WHEN q.duplicate_involved              THEN 4
    WHEN NOT q.has_contact_method          THEN 5
    WHEN q.review_status = 'approved'      THEN 2
    WHEN q.review_status = 'pending'       THEN 3
    ELSE 5
  END                                                                   AS priority,
  'vw_owner_unit_candidate_queue'                                       AS related_view,
  'contact_import_rows'                                                 AS related_table,
  q.contact_import_row_id                                              AS entity_id,
  ('candidate row #' || q.source_row_number::text
     || ' (' || q.source_format || '); ' || q.safe_reason)             AS safe_summary,
  q.recommended_next_action                                            AS recommended_action,
  COALESCE(q.review_status, 'unknown')                                 AS status
FROM vw_owner_unit_candidate_queue q

UNION ALL
-- (b) Duplicate-risk groups that still need a review decision.
SELECT
  'review_duplicate_risk'                                              AS action_type,
  CASE WHEN d.status = 'pending_review' THEN 2 ELSE 6 END              AS priority,
  'vw_duplicate_risk_dashboard'                                        AS related_view,
  'contact_duplicate_candidates'                                       AS related_table,
  d.duplicate_candidate_id                                            AS entity_id,
  d.safe_summary                                                       AS safe_summary,
  d.recommended_action                                                 AS recommended_action,
  d.status                                                             AS status
FROM vw_duplicate_risk_dashboard d

UNION ALL
-- (c) Active owner relationships that are currently revert-ready (a reversible,
--     low-risk inspection target — not an instruction to revert).
SELECT
  'verify_or_revert_relationship'                                      AS action_type,
  7                                                                     AS priority,
  'vw_owner_relationship_revert_dashboard'                             AS related_view,
  'contact_property_relationships'                                     AS related_table,
  r.relationship_id                                                   AS entity_id,
  ('active owner relationship for unit '
     || COALESCE(r.building_name, '?') || ' '
     || COALESCE(r.wing, '') || ' ' || COALESCE(r.unit_number, ''))    AS safe_summary,
  'inspect_source_trace_before_any_change'                            AS recommended_action,
  r.review_status                                                      AS status
FROM vw_owner_relationship_revert_dashboard r
WHERE r.revert_allowed = true;

-- 3. Simplified active owner relationships, masked, with revert readiness and a
--    "source trace present" flag (does the full trace view resolve a source row?).
CREATE VIEW vw_human_owner_relationships AS
SELECT
  r.relationship_id,
  r.contact_display_hint                                              AS owner_hint,
  r.building_name,
  r.wing,
  r.unit_number,
  r.relationship_type,
  r.relationship_status,
  r.review_status,
  r.revert_allowed                                                    AS revert_ready,
  r.reason_if_not_allowed                                             AS revert_blocked_reason,
  EXISTS (
    SELECT 1 FROM vw_contact_property_trace_full t
    WHERE t.relationship_id = r.relationship_id
      AND t.source_row_number IS NOT NULL
  )                                                                    AS source_trace_present,
  r.communication_sent
FROM vw_owner_relationship_revert_dashboard r;

-- 4. Next owner/unit candidate review queue: safe metadata only, ordered so the
--    cleanest candidates surface first. Excludes all raw contact values (none are
--    present in the underlying view either).
CREATE VIEW vw_human_candidate_review_queue AS
SELECT
  q.contact_import_row_id,
  q.review_item_id,
  q.source_row_number,
  q.source_format,
  q.has_contact_method,
  q.method_count,
  q.has_property_hint,
  q.has_building_hint,
  q.has_unit_hint,
  q.duplicate_involved,
  q.review_status,
  q.recommended_next_action                                          AS recommended_action,
  q.safe_reason,
  CASE
    WHEN q.duplicate_involved              THEN 4
    WHEN NOT q.has_contact_method          THEN 5
    WHEN q.review_status = 'approved'      THEN 1
    WHEN q.review_status = 'pending'       THEN 2
    ELSE 3
  END                                                                AS review_priority
FROM vw_owner_unit_candidate_queue q;
