-- 062: Zapkey transaction listings (third-party registration index)
--
-- Zapkey publishes, per project, the registration date + transaction type + unit/floor/tower
-- for every registration it has indexed — WITHOUT the IGR document number. That makes it a
-- coverage source, not a substitute for an Index II: we learn that a flat transacted and when,
-- but not the parties, price or doc number.
--
-- Kept in its own table, never merged into unit_registration_records, because those rows are
-- keyed on (doc_number, registration_year, sro) and carry party/price provenance. Zapkey rows
-- have none of that. Once a doc number is bought/resolved for a row, the operator can create
-- the real unit_registration_record and point back here via zapkey_transaction_id.
--
-- Zapkey's own `floor` and `tower` columns are dirty (unit "224" is labelled floor 2, but 224
-- is floor 22 position 4). The unit NUMBER is consistent with Kalpataru's floor*10+position
-- scheme, so it is the field we trust; floor/tower are retained raw for the operator.

CREATE TABLE IF NOT EXISTS zapkey_transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comps_id            TEXT NOT NULL,              -- Zapkey's stable transaction id
    building_id         UUID REFERENCES buildings(id) ON DELETE CASCADE,
    building_unit_id    UUID REFERENCES building_units(id),

    transaction_type    TEXT,                       -- 'sale' | 'rent' | 'mortgage'
    registration_date   DATE,

    -- as published by Zapkey, unmodified
    unit_raw            TEXT,
    floor_raw           TEXT,
    tower_raw           TEXT,
    reg_date_raw        TEXT,

    -- resolved by the loader from unit_raw (+ tower_raw as a wing hint)
    wing_letter         TEXT,
    unit_number         TEXT,
    floor_derived       INT,

    -- review gate: nothing here is canonical until an operator says so
    link_status         TEXT NOT NULL DEFAULT 'pending_review',  -- pending_review|confirmed|rejected
    resolution_notes    TEXT,
    raw_context         JSONB DEFAULT '{}'::jsonb,

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- comps_id is Zapkey's primary key; re-running the loader must update, not duplicate.
CREATE UNIQUE INDEX IF NOT EXISTS zapkey_transactions_comps_id_key
    ON zapkey_transactions (comps_id);
CREATE INDEX IF NOT EXISTS zapkey_transactions_unit_idx
    ON zapkey_transactions (building_unit_id);
CREATE INDEX IF NOT EXISTS zapkey_transactions_building_flat_idx
    ON zapkey_transactions (building_id, wing_letter, unit_number);

-- Operator view: what Zapkey knows about flats our IGR ingest has NO registration for.
CREATE OR REPLACE VIEW vw_zapkey_units_without_registrations AS
SELECT b.name                       AS building_name,
       z.wing_letter,
       z.unit_number,
       count(*)                                                   AS zapkey_transactions,
       count(*) FILTER (WHERE z.transaction_type = 'sale')        AS sales,
       count(*) FILTER (WHERE z.transaction_type = 'rent')        AS rents,
       count(*) FILTER (WHERE z.transaction_type = 'mortgage')    AS mortgages,
       min(z.registration_date)                                   AS first_seen,
       max(z.registration_date)                                   AS last_seen
FROM zapkey_transactions z
JOIN buildings b ON b.id = z.building_id
JOIN building_units bu ON bu.id = z.building_unit_id
WHERE NOT EXISTS (
        SELECT 1 FROM unit_registration_records r
         WHERE r.building_unit_id = z.building_unit_id)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
