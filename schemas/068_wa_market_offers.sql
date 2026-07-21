-- migration 068: parsed broker offers from ingested WhatsApp group messages.
-- Deterministic regex parse (workers/wa_offer_parser.py) — no LLM. Each offer
-- points back at its interactions row (full text + sender + chat provenance).
-- NOTE: consumer_cases/consent_records renumbers again → 069.

CREATE TABLE IF NOT EXISTS wa_market_offers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interaction_id  UUID NOT NULL UNIQUE REFERENCES interactions(id) ON DELETE CASCADE,
  beeper_chat_id  TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL,
  sender_name     TEXT,
  sender_phone    TEXT,
  transaction     TEXT NOT NULL DEFAULT 'unknown' CHECK (transaction IN
                    ('rent','sale','pg','unknown')),
  bhk             NUMERIC(3,1),                 -- 2, 2.5, 3 … NULL = unstated
  building_id     UUID REFERENCES buildings(id),-- set when OUR building matched
  building_hit    TEXT,                         -- matched alias text, raw
  price_text      TEXT,                         -- "₹1.65 Cr", "55k", raw capture
  area_text       TEXT,                         -- "600 sq ft" raw capture
  furnished       TEXT,                         -- fully|semi|unfurnished, raw-ish
  locality        TEXT,                         -- crude "in <locality>" capture
  status          TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','seen','archived')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wa_offers_matrix
  ON wa_market_offers (transaction, bhk, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_wa_offers_building
  ON wa_market_offers (building_id, occurred_at DESC) WHERE building_id IS NOT NULL;

-- our-buildings box (Ekta Tripolis / Imperial Heights / Kalpataru Radiance …)
CREATE OR REPLACE VIEW vw_wa_offers_our_buildings AS
SELECT o.id, o.occurred_at, o.transaction, o.bhk, o.building_hit, o.price_text,
       o.sender_name, o.sender_phone, o.status, b.name AS building_name,
       w.title AS chat_title, LEFT(COALESCE(i.body_text,''), 600) AS body,
       i.contact_id
FROM wa_market_offers o
JOIN buildings b ON b.id = o.building_id
LEFT JOIN wa_chats w ON w.beeper_chat_id = o.beeper_chat_id
LEFT JOIN interactions i ON i.id = o.interaction_id
WHERE o.status <> 'archived';

-- matrix boxes: transaction × BHK
CREATE OR REPLACE VIEW vw_wa_offers_matrix AS
SELECT o.id, o.occurred_at, o.transaction, o.bhk, o.price_text, o.area_text,
       o.furnished, o.locality, o.sender_name, o.sender_phone, o.status,
       o.building_hit, w.title AS chat_title,
       LEFT(COALESCE(i.body_text,''), 600) AS body, i.contact_id
FROM wa_market_offers o
LEFT JOIN wa_chats w ON w.beeper_chat_id = o.beeper_chat_id
LEFT JOIN interactions i ON i.id = o.interaction_id
WHERE o.status <> 'archived';
