-- 054: IDfy PAN enrichment results
-- Stores per-PAN IDfy API results and name match scores.
-- Source of truth stays in unit_registration_parties.party_pan.

CREATE TABLE IF NOT EXISTS idfy_pan_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_pan           TEXT NOT NULL,
    idfy_status         TEXT,           -- 'id_found' | 'id_not_found' | 'error'
    idfy_name           TEXT,           -- official name from NSDL via IDfy
    idfy_name_on_card   TEXT,
    idfy_pan_type       TEXT,           -- 'P'=individual, 'C'=company, etc.
    idfy_pan_status     TEXT,           -- 'E'=existing/valid, others=issues
    idfy_raw_response   JSONB,
    credits_used        INT DEFAULT 3,
    error_message       TEXT,
    fetched_at          TIMESTAMPTZ DEFAULT now(),
    phase               TEXT DEFAULT '6.26',
    UNIQUE (party_pan)
);

CREATE TABLE IF NOT EXISTS idfy_name_match_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_registration_party_id UUID REFERENCES unit_registration_parties(id),
    party_pan           TEXT,
    igr_name            TEXT,           -- party_name_english from IGR
    idfy_name           TEXT,           -- name from IDfy PAN verify
    match_score         NUMERIC(5,4),   -- 0.0–1.0
    match_verdict       TEXT,           -- 'match' | 'close' | 'mismatch'
    idfy_raw_response   JSONB,
    credits_used        INT DEFAULT 1,
    fetched_at          TIMESTAMPTZ DEFAULT now(),
    phase               TEXT DEFAULT '6.26'
);

-- Quick access views
CREATE OR REPLACE VIEW vw_idfy_pan_enrichment_summary AS
SELECT
    COUNT(*)                                            AS total_fetched,
    COUNT(*) FILTER (WHERE idfy_status = 'id_found')   AS found,
    COUNT(*) FILTER (WHERE idfy_status = 'id_not_found') AS not_found,
    COUNT(*) FILTER (WHERE idfy_status = 'error')      AS errors,
    SUM(credits_used)                                   AS credits_spent
FROM idfy_pan_results;

CREATE OR REPLACE VIEW vw_idfy_name_match_summary AS
SELECT
    COUNT(*)                                                AS total_compared,
    COUNT(*) FILTER (WHERE match_verdict = 'match')        AS matched,
    COUNT(*) FILTER (WHERE match_verdict = 'close')        AS close,
    COUNT(*) FILTER (WHERE match_verdict = 'mismatch')     AS mismatched,
    ROUND(AVG(match_score)::NUMERIC, 3)                    AS avg_score
FROM idfy_name_match_results;

-- Enrichment queue: unique PANs not yet fetched OR with retryable source_down status
CREATE OR REPLACE VIEW vw_idfy_pan_queue AS
SELECT DISTINCT ON (p.party_pan)
    p.id                    AS party_id,
    p.party_pan,
    p.party_name_english    AS igr_name,
    p.party_type,
    p.party_role
FROM unit_registration_parties p
LEFT JOIN idfy_pan_results r ON r.party_pan = p.party_pan
WHERE p.party_pan IS NOT NULL
  AND p.party_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
  AND (r.id IS NULL OR r.idfy_status IN ('source_down', 'error'))
ORDER BY p.party_pan, p.created_at;
