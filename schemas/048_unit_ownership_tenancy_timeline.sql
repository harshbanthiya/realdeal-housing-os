-- Phase 6.16: per-unit accounting from RERA + ownership/tenancy timelines.
--
-- Builds on the Phase 6.15 foundation so that, per building:
--   1. EVERY unit is ACCOUNTED FOR — RERA carpet records give the expected unit inventory,
--      reconciled against enumerated building_units and units that actually have registrations.
--   2. Each unit's timeline cleanly separates the OWNERSHIP chain (sale / gift / release /
--      conveyance -> current owner) from ACTIVE TENANCY (lease / leave-and-license with a live
--      end-date -> current tenant), plus a unified chronological view.
--   3. Every extractable detail from a registration is modelled: party names/roles/types,
--      consideration, market value, dates, SRO, area text, and now tenancy rent/deposit/term.
--
-- Still schema-only with respect to collection: NOTHING here scrapes IGR/MahaRERA, calls an
-- external API, solves a CAPTCHA, or auto-creates a contact relationship. Party names remain
-- behind `_operator`-suffixed views; default dashboards stay counts-only.
--
-- Idempotent: ALTER ... ADD COLUMN IF NOT EXISTS + CREATE OR REPLACE; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. Tenancy detail columns on registration records (extracted from the deed).
--    transaction_category: optional explicit override; otherwise derived from document_type.
--    Allowed transaction_category values: ownership, tenancy, encumbrance, other.
-- ---------------------------------------------------------------------------
ALTER TABLE unit_registration_records
  ADD COLUMN IF NOT EXISTS transaction_category text,
  ADD COLUMN IF NOT EXISTS tenancy_start_date date,
  ADD COLUMN IF NOT EXISTS tenancy_end_date date,
  ADD COLUMN IF NOT EXISTS tenancy_monthly_rent numeric,
  ADD COLUMN IF NOT EXISTS tenancy_deposit numeric;

-- ---------------------------------------------------------------------------
-- 2. Helper: classify a registration document_type into a transaction category.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION registration_category(doc_type text) RETURNS text AS $$
  SELECT CASE
    WHEN doc_type IN ('sale_deed', 'agreement_to_sell', 'gift_deed', 'release_deed',
                      'conveyance', 'deed_of_apartment', 'deed_of_assignment') THEN 'ownership'
    WHEN doc_type IN ('lease', 'leave_and_license') THEN 'tenancy'
    WHEN doc_type IN ('mortgage') THEN 'encumbrance'
    ELSE 'other'
  END;
$$ LANGUAGE sql IMMUTABLE;


-- ===========================================================================
-- Views. SAFE = counts-only/no names; *_operator = public-register names.
-- ===========================================================================

DROP VIEW IF EXISTS vw_unit_ownership_timeline_operator;     -- redefined (ownership-only now)
DROP VIEW IF EXISTS vw_unit_tenancy_timeline_operator;
DROP VIEW IF EXISTS vw_unit_full_timeline_operator;
DROP VIEW IF EXISTS vw_unit_current_status_operator;
DROP VIEW IF EXISTS vw_building_unit_accounting;

-- 1. OPERATOR — OWNERSHIP timeline per unit (ownership-category records only).
CREATE VIEW vw_unit_ownership_timeline_operator AS
SELECT
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  u.unit_number,
  u.wing AS unit_wing,
  r.registration_date,
  r.registration_year,
  r.document_type,
  r.doc_number,
  r.sro_office,
  r.consideration_amount,
  r.market_value,
  r.verification_status,
  (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
     FROM unit_registration_parties p
    WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('seller', 'vendor')) AS sellers,
  (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
     FROM unit_registration_parties p
    WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('purchaser', 'buyer')) AS purchasers,
  r.id AS unit_registration_record_id
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id
WHERE COALESCE(r.transaction_category, registration_category(r.document_type)) = 'ownership'
  AND r.verification_status <> 'rejected';

-- 2. OPERATOR — TENANCY timeline per unit (tenancy-category records only) with active flag.
CREATE VIEW vw_unit_tenancy_timeline_operator AS
SELECT
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  u.unit_number,
  u.wing AS unit_wing,
  r.registration_date,
  r.document_type,
  r.doc_number,
  r.sro_office,
  r.tenancy_start_date,
  r.tenancy_end_date,
  r.tenancy_monthly_rent,
  r.tenancy_deposit,
  (r.tenancy_end_date IS NULL OR r.tenancy_end_date >= current_date) AS is_active,
  (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
     FROM unit_registration_parties p
    WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('lessor', 'landlord')) AS lessors,
  (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
     FROM unit_registration_parties p
    WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('lessee', 'tenant')) AS tenants,
  r.verification_status,
  r.id AS unit_registration_record_id
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id
WHERE COALESCE(r.transaction_category, registration_category(r.document_type)) = 'tenancy'
  AND r.verification_status <> 'rejected';

-- 3. OPERATOR — unified chronological timeline (every event, tagged ownership/tenancy/etc.).
CREATE VIEW vw_unit_full_timeline_operator AS
SELECT
  r.building_id,
  b.name AS building_name,
  r.building_unit_id,
  u.unit_number,
  u.wing AS unit_wing,
  COALESCE(r.transaction_category, registration_category(r.document_type)) AS category,
  r.document_type,
  r.registration_date,
  r.doc_number,
  r.sro_office,
  r.consideration_amount,
  r.tenancy_start_date,
  r.tenancy_end_date,
  r.tenancy_monthly_rent,
  CASE WHEN COALESCE(r.transaction_category, registration_category(r.document_type)) = 'tenancy'
       THEN (r.tenancy_end_date IS NULL OR r.tenancy_end_date >= current_date) END AS tenancy_active,
  (SELECT string_agg(p.party_name_raw || ' (' || COALESCE(p.party_role, '?') || ')', '; ' ORDER BY p.display_order)
     FROM unit_registration_parties p WHERE p.unit_registration_record_id = r.id) AS parties,
  r.verification_status,
  r.id AS unit_registration_record_id
FROM unit_registration_records r
LEFT JOIN buildings b ON b.id = r.building_id
LEFT JOIN building_units u ON u.id = r.building_unit_id
WHERE r.verification_status <> 'rejected';

-- 4. OPERATOR — current status per unit: latest owner + active tenant (the "complete" row).
--    Driven from building_units so EVERY enumerated unit appears (accounted for), even with
--    no registrations yet (current_owner / active_tenant simply NULL).
CREATE VIEW vw_unit_current_status_operator AS
WITH ownership_events AS (
  SELECT
    r.building_unit_id,
    r.registration_date,
    r.doc_number,
    r.consideration_amount,
    (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
       FROM unit_registration_parties p
      WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('purchaser', 'buyer')) AS owner_names
  FROM unit_registration_records r
  WHERE r.building_unit_id IS NOT NULL
    AND COALESCE(r.transaction_category, registration_category(r.document_type)) = 'ownership'
    AND r.verification_status <> 'rejected'
),
latest_owner AS (
  SELECT DISTINCT ON (building_unit_id)
    building_unit_id, owner_names, registration_date, doc_number, consideration_amount
  FROM ownership_events
  ORDER BY building_unit_id, registration_date DESC NULLS LAST
),
tenancy_events AS (
  SELECT
    r.building_unit_id,
    r.registration_date,
    r.tenancy_start_date,
    r.tenancy_end_date,
    r.tenancy_monthly_rent,
    (SELECT string_agg(p.party_name_raw, ', ' ORDER BY p.display_order)
       FROM unit_registration_parties p
      WHERE p.unit_registration_record_id = r.id AND p.party_role IN ('lessee', 'tenant')) AS tenant_names
  FROM unit_registration_records r
  WHERE r.building_unit_id IS NOT NULL
    AND COALESCE(r.transaction_category, registration_category(r.document_type)) = 'tenancy'
    AND r.verification_status <> 'rejected'
    AND (r.tenancy_end_date IS NULL OR r.tenancy_end_date >= current_date)
),
active_tenancy AS (
  SELECT DISTINCT ON (building_unit_id)
    building_unit_id, tenant_names, tenancy_start_date, tenancy_end_date, tenancy_monthly_rent
  FROM tenancy_events
  ORDER BY building_unit_id, tenancy_start_date DESC NULLS LAST, registration_date DESC NULLS LAST
)
SELECT
  u.id AS building_unit_id,
  u.building_id,
  b.name AS building_name,
  u.wing,
  u.unit_number,
  u.floor,
  u.typology,
  lo.owner_names AS current_owner,
  lo.registration_date AS owner_since,
  lo.doc_number AS ownership_doc_number,
  lo.consideration_amount AS last_sale_consideration,
  at.tenant_names AS active_tenant,
  at.tenancy_start_date,
  at.tenancy_end_date,
  at.tenancy_monthly_rent,
  (at.tenant_names IS NOT NULL) AS has_active_tenancy,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_unit_id = u.id
     AND r.verification_status <> 'rejected') AS registration_count,
  (SELECT count(*) FROM unit_registration_records r WHERE r.building_unit_id = u.id
     AND r.verification_status <> 'rejected'
     AND COALESCE(r.transaction_category, registration_category(r.document_type)) = 'ownership') AS ownership_event_count
FROM building_units u
LEFT JOIN buildings b ON b.id = u.building_id
LEFT JOIN latest_owner lo ON lo.building_unit_id = u.id
LEFT JOIN active_tenancy at ON at.building_unit_id = u.id
WHERE u.canonical_status = 'active';

-- 5. SAFE — per-building unit accounting (no names): expected (from RERA) vs. enumerated vs.
--    units-with-registration vs. units-with-known-owner, plus the still-to-account gap.
--    RERA-expected counts only flow from a RERA profile that is LINKED to the building
--    (profile.building_id), so it stays 0 until the RERA match is accepted — review-first.
CREATE VIEW vw_building_unit_accounting AS
SELECT
  b.id AS building_id,
  b.name AS building_name,
  (SELECT COALESCE(sum(c.apartment_count), 0) FROM rera_carpet_area_records c
     JOIN rera_project_profiles pp ON pp.id = c.rera_project_profile_id
    WHERE pp.building_id = b.id) AS rera_expected_units,
  (SELECT count(*) FROM building_units u WHERE u.building_id = b.id AND u.canonical_status = 'active') AS enumerated_units,
  (SELECT count(DISTINCT r.building_unit_id) FROM unit_registration_records r
     WHERE r.building_id = b.id AND r.building_unit_id IS NOT NULL AND r.verification_status <> 'rejected') AS units_with_registration,
  (SELECT count(*) FROM unit_registration_records r
     WHERE r.building_id = b.id AND r.building_unit_id IS NULL AND r.verification_status <> 'rejected') AS unlinked_registration_count,
  GREATEST(
    (SELECT COALESCE(sum(c.apartment_count), 0) FROM rera_carpet_area_records c
       JOIN rera_project_profiles pp ON pp.id = c.rera_project_profile_id
      WHERE pp.building_id = b.id)
    - (SELECT count(*) FROM building_units u WHERE u.building_id = b.id AND u.canonical_status = 'active'),
    0
  ) AS units_not_yet_enumerated
FROM buildings b;
