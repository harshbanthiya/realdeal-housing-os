-- Phase 6.23: registration QA dashboard (translation + parse quality).
--
-- The IGR data is parsed/transliterated and review-gated (parsed_candidate). This surfaces the
-- data-quality issues a human QA must work through before the records are trusted: parties missing
-- an English name, names that look concatenated (no spaces — a transliteration artifact), records
-- not yet linked to a unit, ownership rows missing a price, and parties missing PAN.
--
-- Idempotent: CREATE OR REPLACE.

CREATE OR REPLACE VIEW vw_kalpataru_registration_qa AS
SELECT
  r.id AS record_id,
  b.name AS building_name,
  r.wing_text,
  r.unit_text,
  r.doc_number,
  r.registration_year,
  r.document_type,
  COALESCE(r.transaction_category, registration_category(r.document_type)) AS category,
  r.consideration_amount,
  r.verification_status,
  (r.building_unit_id IS NULL) AS needs_unit_link,
  (COALESCE(r.transaction_category, registration_category(r.document_type)) = 'ownership'
     AND r.consideration_amount IS NULL) AS missing_price,
  (SELECT count(*) FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS party_count,
  (SELECT count(*) FROM unit_registration_parties p
     WHERE p.unit_registration_record_id = r.id AND (p.party_name_english IS NULL OR p.party_name_english = '')) AS parties_missing_english,
  (SELECT count(*) FROM unit_registration_parties p
     WHERE p.unit_registration_record_id = r.id AND p.party_pan IS NULL) AS parties_missing_pan,
  COALESCE((SELECT bool_or(p.party_name_english ~ '[A-Za-z]{16,}')
     FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id), false) AS has_concatenated_name
FROM unit_registration_records r
JOIN buildings b ON b.id = r.building_id
WHERE r.raw_context->>'source' LIKE 'igr_%';

CREATE OR REPLACE VIEW vw_kalpataru_registration_qa_summary AS
SELECT
  building_name,
  count(*) AS records,
  count(*) FILTER (WHERE needs_unit_link) AS needs_unit_link,
  count(*) FILTER (WHERE missing_price) AS missing_price,
  count(*) FILTER (WHERE parties_missing_english > 0) AS records_missing_english,
  count(*) FILTER (WHERE has_concatenated_name) AS records_concatenated_name,
  count(*) FILTER (WHERE parties_missing_pan > 0) AS records_missing_pan,
  count(*) FILTER (WHERE verification_status = 'parsed_candidate') AS pending_verification
FROM vw_kalpataru_registration_qa
GROUP BY building_name;
