-- Phase 6.21: full registration party detail + comprehensive per-registration view.
--
-- The IGR registrations are the core business asset (qualify tenants, track lease expiries,
-- spot owners who've seen appreciation, and — via PAN — enrich business profiles later). This
-- migration makes the parties first-class and complete: English (romanized) name as the primary
-- display, original Devanagari kept alongside, plus PAN / age / address. A single rich view
-- surfaces EVERY extracted field per registration with its parties as JSON.
--
-- Idempotent: ALTER ADD COLUMN IF NOT EXISTS + CREATE OR REPLACE.

ALTER TABLE unit_registration_parties
  ADD COLUMN IF NOT EXISTS party_name_english text,
  ADD COLUMN IF NOT EXISTS party_name_devanagari text,
  ADD COLUMN IF NOT EXISTS party_pan text,
  ADD COLUMN IF NOT EXISTS party_age integer,
  ADD COLUMN IF NOT EXISTS party_address text;

ALTER TABLE unit_registration_records
  ADD COLUMN IF NOT EXISTS registration_fee numeric;

CREATE INDEX IF NOT EXISTS idx_urp_party_pan ON unit_registration_parties(party_pan);

-- Comprehensive per-registration view (OPERATOR — exposes public-register party PII).
CREATE OR REPLACE VIEW vw_unit_registration_full_operator AS
SELECT
  r.id AS record_id,
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  COALESCE(u.wing, r.wing_text) AS wing,
  COALESCE(u.unit_number, r.unit_text) AS unit_number,
  r.wing_text,
  r.unit_text,
  r.floor_text,
  r.registration_date,
  r.registration_year,
  r.document_type,
  COALESCE(r.transaction_category, registration_category(r.document_type)) AS category,
  r.doc_number,
  COALESCE(r.sro_office, r.raw_context->>'sro_raw') AS sro_office,
  r.consideration_amount,
  r.market_value,
  r.stamp_duty,
  COALESCE(r.registration_fee, (r.raw_context->>'reg_fee')::numeric) AS registration_fee,
  r.area_text,
  r.tenancy_start_date,
  r.tenancy_end_date,
  r.tenancy_monthly_rent,
  r.tenancy_deposit,
  r.verification_status,
  r.source_label,
  r.property_description_raw,
  (SELECT count(*) FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS party_count,
  (SELECT count(*) FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id AND p.party_pan IS NOT NULL) AS party_pan_count,
  (SELECT jsonb_agg(jsonb_build_object(
      'role', p.party_role,
      'english', COALESCE(p.party_name_english, p.party_name_normalized),
      'devanagari', COALESCE(p.party_name_devanagari, p.party_name_raw),
      'pan', p.party_pan, 'age', p.party_age, 'address', p.party_address,
      'type', p.party_type) ORDER BY p.display_order)
   FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS parties
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id;
