-- Phase 6.18: generalize registration readiness to ALL buildings (not just Imperial Heights).
--
-- vw_imperial_heights_registration_readiness (migration 047) is hardcoded to Imperial Heights.
-- This adds vw_building_registration_readiness with the SAME gates for every building, so any
-- building we work (e.g. Kalpataru Radiance A) shows ready_for_igr_search / ready_for_party_matching
-- / ready_for_relationship_creation. SAFE: counts + booleans only, no personal names.
--
-- Idempotent: CREATE OR REPLACE.

CREATE OR REPLACE VIEW vw_building_registration_readiness AS
SELECT
  b.id AS building_id,
  b.name AS building_name,
  (SELECT count(*) FROM building_tower_structure ts WHERE ts.building_id = b.id) AS tower_structure_count,
  (SELECT count(*) FROM building_property_identifiers pi WHERE pi.building_id = b.id) AS identifier_count,
  (SELECT count(*) FROM building_property_identifiers pi
     WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) AS verified_search_key_count,
  (SELECT count(*) FROM igr_registration_search_jobs j WHERE j.building_id = b.id) AS search_job_count,
  (SELECT count(*) FROM igr_registration_search_jobs j WHERE j.building_id = b.id AND j.external_call_made) AS external_call_count,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id) AS registration_record_count,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') AS verified_record_count,
  (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') AS accepted_match_count,
  (
    (SELECT count(*) FROM building_property_identifiers pi
       WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) > 0
  ) AS ready_for_igr_search,
  (
    (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') > 0
  ) AS ready_for_party_matching,
  (
    (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') > 0
  ) AS ready_for_relationship_creation,
  CASE
    WHEN (SELECT count(*) FROM building_property_identifiers pi
            WHERE pi.building_id = b.id AND pi.verification_status = 'verified' AND pi.is_igr_search_key) = 0
      THEN 'no_verified_search_key_yet'
    WHEN (SELECT count(*) FROM unit_registration_records r WHERE r.building_id = b.id AND r.verification_status = 'verified') = 0
      THEN 'no_verified_registration_record_yet'
    WHEN (SELECT count(*) FROM registration_party_contact_matches m WHERE m.building_id = b.id AND m.match_status = 'accepted') = 0
      THEN 'no_accepted_party_contact_match_yet'
    ELSE 'ready_for_relationship_creation'
  END AS blocked_reason
FROM buildings b
WHERE EXISTS (SELECT 1 FROM building_tower_structure ts WHERE ts.building_id = b.id)
   OR EXISTS (SELECT 1 FROM building_property_identifiers pi WHERE pi.building_id = b.id)
   OR EXISTS (SELECT 1 FROM unit_registration_records r WHERE r.building_id = b.id);
