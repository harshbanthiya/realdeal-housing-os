-- Phase 6.25: PAN-based KYC-style enrichment (MVP) — safe, format-only, NO external calls.
--
-- PAN is sensitive personal data (DPDP: lawful, purpose-limited, minimised). This migration adds
-- the *safest first* enrichment — the entity-type signal that lives in the PAN itself (its 4th
-- character: P=individual, C=company, F=firm/LLP, H=HUF, T=trust, …) — plus a format-valid flag
-- and an enrichment timestamp on each party. No GST / Income-Tax / MCA lookups happen here; those
-- are a later, separately-gated step.
--
-- Sensitive-data handling for the MVP:
--   * Raw PAN stays only in unit_registration_parties.party_pan (it is public-register data, already
--     captured from Index II). Full-PAN exposure is limited to the existing *_operator views.
--   * A MASKED view (vw_party_pan_enrichment_operator) surfaces only first-5+last-1 of the PAN plus
--     the entity type / lead signal — this is what analysis & marketing-adjacent flows should read.
--   * pan_access_log is an append-only audit of every enrichment run (actor, purpose, scope) so PAN
--     access is logged, not silent. Encryption-at-rest of party_pan is a tracked follow-up.
--
-- Idempotent: ALTER ADD COLUMN IF NOT EXISTS + CREATE OR REPLACE + CREATE TABLE IF NOT EXISTS.

ALTER TABLE unit_registration_parties
  ADD COLUMN IF NOT EXISTS pan_entity_type text,
  ADD COLUMN IF NOT EXISTS pan_format_valid boolean,
  ADD COLUMN IF NOT EXISTS pan_enriched_at timestamptz;

-- Entity type from the PAN 4th character (pure format, no external lookup).
CREATE OR REPLACE FUNCTION pan_entity_type(pan text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN pan IS NULL OR pan !~ '^[A-Z]{5}[0-9]{4}[A-Z]$' THEN NULL
    ELSE CASE upper(substr(pan, 4, 1))
      WHEN 'P' THEN 'individual'
      WHEN 'C' THEN 'company'
      WHEN 'H' THEN 'huf'
      WHEN 'F' THEN 'firm_llp'
      WHEN 'A' THEN 'aop'
      WHEN 'T' THEN 'trust'
      WHEN 'B' THEN 'body_of_individuals'
      WHEN 'L' THEN 'local_authority'
      WHEN 'J' THEN 'artificial_juridical'
      WHEN 'G' THEN 'government'
      ELSE 'other'
    END
  END;
$$;

-- Masked PAN: first 5 + **** + check char. Never returns the full number.
CREATE OR REPLACE FUNCTION pan_mask(pan text) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE WHEN pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'
              THEN substr(pan, 1, 5) || '****' || substr(pan, 10, 1)
              ELSE NULL END;
$$;

-- Append-only audit of PAN-enrichment access (purpose-limitation evidence).
CREATE TABLE IF NOT EXISTS pan_access_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  accessed_at    timestamptz NOT NULL DEFAULT now(),
  actor          text NOT NULL,
  purpose        text NOT NULL,
  source_script  text,
  doc_numbers    text[],
  parties_touched integer,
  pan_count      integer,
  raw_context    jsonb
);

-- MASKED operator view — entity type + lead signal + masked PAN. NEVER the raw PAN.
CREATE OR REPLACE VIEW vw_party_pan_enrichment_operator AS
SELECT
  p.id AS party_id,
  b.name AS building_name,
  COALESCE(u.wing, r.wing_text) AS wing,
  COALESCE(u.unit_number, r.unit_text) AS unit_number,
  r.doc_number,
  r.registration_year,
  COALESCE(r.transaction_category, registration_category(r.document_type)) AS category,
  p.party_role,
  COALESCE(p.party_name_english, p.party_name_normalized) AS party_name,
  pan_mask(p.party_pan) AS pan_masked,
  COALESCE(p.pan_entity_type, pan_entity_type(p.party_pan)) AS pan_entity_type,
  (p.party_pan IS NOT NULL AND p.party_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$') AS pan_format_valid,
  CASE COALESCE(p.pan_entity_type, pan_entity_type(p.party_pan))
    WHEN 'company' THEN 'business_entity'
    WHEN 'firm_llp' THEN 'business_entity'
    WHEN 'trust'   THEN 'business_entity'
    WHEN 'huf'     THEN 'family_structure'
    WHEN 'individual' THEN 'individual'
    WHEN NULL THEN 'no_pan'
    ELSE 'review'
  END AS lead_signal,
  p.pan_enriched_at
FROM unit_registration_parties p
JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id
WHERE p.party_pan IS NOT NULL;

-- Coverage + entity-type breakdown per building.
CREATE OR REPLACE VIEW vw_pan_enrichment_summary AS
SELECT
  b.name AS building_name,
  count(*) AS parties_total,
  count(p.party_pan) AS parties_with_pan,
  count(*) FILTER (WHERE pan_entity_type(p.party_pan) = 'individual') AS individuals,
  count(*) FILTER (WHERE pan_entity_type(p.party_pan) = 'company')    AS companies,
  count(*) FILTER (WHERE pan_entity_type(p.party_pan) = 'firm_llp')   AS firms_llp,
  count(*) FILTER (WHERE pan_entity_type(p.party_pan) IN
    ('trust','huf','aop','body_of_individuals','local_authority','artificial_juridical','government','other')) AS other_entities,
  count(*) FILTER (WHERE p.party_pan IS NOT NULL AND p.party_pan !~ '^[A-Z]{5}[0-9]{4}[A-Z]$') AS invalid_format
FROM unit_registration_parties p
JOIN unit_registration_records r ON r.id = p.unit_registration_record_id
JOIN buildings b ON b.id = r.building_id
GROUP BY b.name;
