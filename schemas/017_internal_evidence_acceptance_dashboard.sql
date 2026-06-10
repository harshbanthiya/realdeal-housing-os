-- Phase 6.6: internal-evidence acceptance dashboards (read-only, no personal data).
--
-- Two read-only views over the Phase 6.5 internal_source_evidence / source_gap_review_items
-- tables, surfacing which internal evidence has been accepted for future content drafting.
-- No personal values (names/phones/emails/addresses): only counts, types, statuses, safe
-- summaries, content titles, and system UUIDs. `ready_for_publish` is hard-coded false.
--
-- Idempotent: DROP VIEW IF EXISTS + CREATE; safe to re-run via apply_schema.sh.

DROP VIEW IF EXISTS vw_internal_evidence_acceptance_dashboard;
DROP VIEW IF EXISTS vw_imperial_heights_evidence_readiness;

-- 1. Per-evidence acceptance dashboard (one row per internal_source_evidence).
CREATE VIEW vw_internal_evidence_acceptance_dashboard AS
SELECT
  p.profile_slug,
  e.id AS evidence_id,
  e.content_source_gap_item_id AS gap_id,
  cb.title AS content_title,
  g.gap_type,
  e.evidence_type,
  e.evidence_status,
  e.safe_summary,
  (SELECT r.status FROM source_gap_review_items r
     WHERE r.review_type = 'internal_evidence_review'
       AND r.content_source_gap_item_id = e.content_source_gap_item_id
     ORDER BY r.created_at LIMIT 1) AS review_status,
  CASE
    WHEN e.evidence_status = 'accepted' THEN 'accepted'
    WHEN e.evidence_status = 'rejected' THEN 'rejected'
    WHEN e.evidence_status = 'needs_review' THEN 'needs_human_review'
    WHEN e.evidence_type = 'inventory_hint' THEN 'needs_human_review'
    WHEN e.evidence_type = 'active_owner_relationship_count' THEN 'defer_until_building_dedupe'
    WHEN e.evidence_type IN ('source_batch_count', 'unit_count', 'building_alias') THEN 'accept_internal_evidence'
    ELSE 'needs_human_review'
  END AS recommended_next_action
FROM internal_source_evidence e
JOIN content_source_gap_items g ON g.id = e.content_source_gap_item_id
JOIN content_briefs cb ON cb.id = g.content_brief_id
JOIN building_web_profiles p ON p.id = cb.building_web_profile_id;

-- 2. Imperial Heights evidence-readiness rollup (one row per profile).
CREATE VIEW vw_imperial_heights_evidence_readiness AS
WITH ev AS (
  SELECT p.profile_slug, e.evidence_status
  FROM internal_source_evidence e
  JOIN content_source_gap_items g ON g.id = e.content_source_gap_item_id
  JOIN content_briefs cb ON cb.id = g.content_brief_id
  JOIN building_web_profiles p ON p.id = cb.building_web_profile_id
),
gaps AS (
  SELECT p.profile_slug,
         count(*) FILTER (WHERE g.status = 'open') AS gaps_open,
         count(*) FILTER (WHERE g.status <> 'open') AS gaps_resolved
  FROM content_source_gap_items g
  JOIN content_briefs cb ON cb.id = g.content_brief_id
  JOIN building_web_profiles p ON p.id = cb.building_web_profile_id
  GROUP BY p.profile_slug
)
SELECT
  p.profile_slug,
  (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug) AS total_evidence,
  (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug AND ev.evidence_status = 'candidate') AS candidate_evidence,
  (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug AND ev.evidence_status = 'accepted') AS accepted_evidence,
  (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug AND ev.evidence_status = 'needs_review') AS needs_review_evidence,
  (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug AND ev.evidence_status = 'rejected') AS rejected_evidence,
  COALESCE(gaps.gaps_open, 0) AS gaps_open,
  COALESCE(gaps.gaps_resolved, 0) AS gaps_resolved,
  (COALESCE(gaps.gaps_open, 0) = 0 AND COALESCE(gaps.gaps_resolved, 0) > 0) AS ready_for_ai_draft,
  false AS ready_for_publish,
  CASE
    WHEN COALESCE(gaps.gaps_open, 0) > 0 THEN 'open_source_gaps'
    WHEN (SELECT count(*) FROM ev WHERE ev.profile_slug = p.profile_slug AND ev.evidence_status = 'candidate') > 0
      THEN 'evidence_candidates_pending_review'
    ELSE 'evidence_reviewed_gaps_cleared'
  END AS blocked_reason
FROM building_web_profiles p
LEFT JOIN gaps ON gaps.profile_slug = p.profile_slug
WHERE EXISTS (
  SELECT 1 FROM content_source_gap_items g
  JOIN content_briefs cb ON cb.id = g.content_brief_id
  WHERE cb.building_web_profile_id = p.id
);
