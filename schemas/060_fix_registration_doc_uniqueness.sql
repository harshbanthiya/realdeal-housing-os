-- migration 060: fix unit_registration_records uniqueness key
--
-- Found 2026-07-06 during an independent QA audit of Imperial Heights + Kalpataru
-- Radiance: unit_registration_records had UNIQUE (building_id, doc_number) -- with no
-- registration_year. IGR doc numbers reset every year per SRO office, so two genuinely
-- different documents (e.g. doc 7346/2021 at SRO Mumbai-16 = unit A-2205, and doc
-- 7346/2024 at SRO Mumbai-25 = a completely different unit A-03) collide on that key.
-- Every ingest script's "does this doc already exist" check mirrors the same flawed
-- key, so the second document silently overwrites/merges into the first instead of
-- inserting as its own row -- this was blocking ~290 apartments' worth of genuine,
-- never-before-stored registration documents from ever being stored correctly.
--
-- This constraint predates the tracked schema migrations (added ad-hoc, not present
-- in any prior schemas/*.sql file), so there's no earlier migration to reference.
ALTER TABLE unit_registration_records
  DROP CONSTRAINT IF EXISTS unit_registration_records_building_doc_uniq,
  ADD CONSTRAINT unit_registration_records_building_doc_year_sro_uniq
    UNIQUE (building_id, doc_number, registration_year, sro_office);
