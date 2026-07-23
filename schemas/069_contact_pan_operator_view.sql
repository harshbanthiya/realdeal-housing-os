-- 069 — contact ↔ PAN, resolved through registration party matches.
--
-- PAN stays where it already lives (unit_registration_parties, behind pan_access_log and the
-- masked operator views). Contacts do NOT get a pan column: a second copy of the same PII is a
-- second thing to guard and a second thing to go stale. This view joins a contact to the PAN of
-- the registration party it was matched to, masked by the existing pan_mask().
--
-- Only 'matched' rows resolve. 'needs_review' matches are surfaced separately so an operator can
-- see what is pending without the pending guesses polluting the confirmed set.

CREATE OR REPLACE VIEW vw_contact_pan_operator AS
SELECT
    c.id                AS contact_id,
    c.full_name         AS contact_name,
    b.name              AS building_name,
    COALESCE(u.wing, r.wing_text)            AS wing,
    COALESCE(u.unit_number, r.unit_text)     AS unit_number,
    m.match_status,
    m.match_strength,
    m.name_similarity_score,
    p.party_role,
    COALESCE(p.party_name_english, p.party_name_normalized) AS party_name,
    pan_mask(p.party_pan)                                    AS pan_masked,
    COALESCE(p.pan_entity_type, pan_entity_type(p.party_pan)) AS pan_entity_type,
    p.party_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'                  AS pan_format_valid,
    r.doc_number,
    r.registration_year,
    COALESCE(r.transaction_category, registration_category(r.document_type)) AS category,
    p.pan_enriched_at
FROM registration_party_contact_matches m
JOIN contacts c                     ON c.id = m.contact_id
JOIN unit_registration_parties p    ON p.id = m.unit_registration_party_id
JOIN unit_registration_records r    ON r.id = p.unit_registration_record_id
JOIN buildings b                    ON b.id = r.building_id
LEFT JOIN building_units u          ON u.id = r.building_unit_id
WHERE p.party_pan IS NOT NULL
  AND m.match_status = 'matched';

COMMENT ON VIEW vw_contact_pan_operator IS
    'Contact -> masked PAN via confirmed registration-party matches. Masked; PAN is never '
    'copied onto contacts. Pending matches are in vw_contact_pan_review.';

CREATE OR REPLACE VIEW vw_contact_pan_review AS
SELECT
    c.id                AS contact_id,
    c.full_name         AS contact_name,
    b.name              AS building_name,
    COALESCE(u.unit_number, r.unit_text)     AS unit_number,
    m.match_strength,
    m.name_similarity_score,
    COALESCE(p.party_name_english, p.party_name_normalized) AS party_name,
    pan_mask(p.party_pan)                    AS pan_masked,
    m.match_reason,
    m.id                AS match_id
FROM registration_party_contact_matches m
JOIN contacts c                     ON c.id = m.contact_id
JOIN unit_registration_parties p    ON p.id = m.unit_registration_party_id
JOIN unit_registration_records r    ON r.id = p.unit_registration_record_id
JOIN buildings b                    ON b.id = r.building_id
LEFT JOIN building_units u          ON u.id = r.building_unit_id
WHERE p.party_pan IS NOT NULL
  AND m.match_status = 'needs_review';

COMMENT ON VIEW vw_contact_pan_review IS
    'Name matches between a contact and a PAN-bearing registration party that are not confirmed '
    'yet. Approve by setting match_status = ''matched''.';
