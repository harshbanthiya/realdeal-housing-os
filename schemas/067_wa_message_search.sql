-- migration 067: full-text + fuzzy search over ingested WhatsApp messages.
-- 'simple' config (not 'english') because messages are Hinglish — no stemming,
-- every word searchable as typed. pg_trgm covers partial words ("kalp" → Kalpataru).
-- NOTE: consumer_cases/consent_records renumbers again → 068.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE interactions
  ADD COLUMN IF NOT EXISTS search_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', COALESCE(body_text, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_interactions_search_tsv
  ON interactions USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS idx_interactions_body_trgm
  ON interactions USING GIN (body_text gin_trgm_ops);
