-- migration 066: Beeper WhatsApp read-only ingest → contact timelines
-- (docs/BEEPER-ASSISTANT-PLAN.md; ROADMAP §10). Send NEVER goes through the
-- API — cockpit renders wa.me deep links only (Lane A).
-- NOTE: consumer_cases/consent_records (old §17 item 7) renumbers to 067.

-- ── chat registry (operator classifies once; personal chats get ingest_enabled=false)
CREATE TABLE IF NOT EXISTS wa_chats (
  beeper_chat_id  TEXT PRIMARY KEY,               -- "!x:beeper.local"
  title           TEXT NOT NULL DEFAULT '',
  chat_type       TEXT NOT NULL DEFAULT 'single' CHECK (chat_type IN ('single','group')),
  kind            TEXT NOT NULL DEFAULT 'unclassified' CHECK (kind IN
                    ('unclassified','client','broker','broker_group',
                     'tenant_group','community_ours','personal','other')),
  ingest_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
  contact_id      UUID REFERENCES contacts(id),   -- 1:1 chat → canonical contact
  building_id     UUID REFERENCES buildings(id),  -- tenant/broker group → building
  member_count    INT,
  last_activity   TIMESTAMPTZ,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── group rosters: the enrichment substrate (LID → phone → contact)
CREATE TABLE IF NOT EXISTS wa_chat_members (
  beeper_chat_id  TEXT NOT NULL REFERENCES wa_chats(beeper_chat_id) ON DELETE CASCADE,
  member_id       TEXT NOT NULL,                  -- "@whatsapp_lid-…" or "@whatsapp_<phone>…"
  phone           TEXT,                           -- +E164 when Beeper resolves it
  display_name    TEXT,                           -- her saved name or raw number
  is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
  contact_id      UUID REFERENCES contacts(id),   -- resolved canonical match
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (beeper_chat_id, member_id)
);
CREATE INDEX IF NOT EXISTS idx_wa_chat_members_phone ON wa_chat_members (phone);

-- ── per-chat ingest cursor
CREATE TABLE IF NOT EXISTS wa_ingest_state (
  beeper_chat_id  TEXT PRIMARY KEY REFERENCES wa_chats(beeper_chat_id) ON DELETE CASCADE,
  last_sort_key   TEXT,
  last_run_at     TIMESTAMPTZ,
  msg_count       INT NOT NULL DEFAULT 0
);

-- ── unknown-number confirm queue (review-gated attach/create/ignore)
CREATE TABLE IF NOT EXISTS wa_number_queue (
  phone                TEXT PRIMARY KEY,          -- +E164
  wa_name              TEXT,                      -- saved name / pushname seen
  first_seen_chat      TEXT,
  seen_count           INT NOT NULL DEFAULT 1,
  proposed_contact_id  UUID REFERENCES contacts(id),  -- fuzzy candidate, if any
  status               TEXT NOT NULL DEFAULT 'pending' CHECK (status IN
                         ('pending','attached','created','ignored')),
  reviewed_at          TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── extend the (empty) interactions table for message-grain WhatsApp rows
ALTER TABLE interactions
  ADD COLUMN IF NOT EXISTS beeper_message_id   TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS beeper_chat_id      TEXT,
  ADD COLUMN IF NOT EXISTS sender_phone        TEXT,
  ADD COLUMN IF NOT EXISTS sender_lid          TEXT,
  ADD COLUMN IF NOT EXISTS sender_display_name TEXT,
  ADD COLUMN IF NOT EXISTS is_group_msg        BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS message_type        TEXT,
  ADD COLUMN IF NOT EXISTS body_text           TEXT,   -- HTML stripped
  ADD COLUMN IF NOT EXISTS body_html           TEXT,   -- raw as received
  ADD COLUMN IF NOT EXISTS media               JSONB,  -- attachment metadata only
  ADD COLUMN IF NOT EXISTS rdh_code            TEXT,   -- parsed ⌂-code, raw
  ADD COLUMN IF NOT EXISTS source              TEXT NOT NULL DEFAULT 'manual';
CREATE INDEX IF NOT EXISTS idx_interactions_chat_time
  ON interactions (beeper_chat_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_contact_time
  ON interactions (contact_id, occurred_at DESC);

-- ── views ─────────────────────────────────────────────────────────────────

-- per-contact WhatsApp timeline (cockpit contact detail panel)
CREATE OR REPLACE VIEW vw_wa_contact_timeline AS
SELECT i.contact_id, i.occurred_at, i.direction, i.channel,
       COALESCE(w.title,'') AS chat_title, i.is_group_msg,
       i.sender_display_name, i.message_type,
       LEFT(COALESCE(i.body_text, i.summary, ''), 500) AS body,
       i.media IS NOT NULL AS has_media, i.rdh_code, i.id
FROM interactions i
LEFT JOIN wa_chats w ON w.beeper_chat_id = i.beeper_chat_id
WHERE i.contact_id IS NOT NULL;

-- today page: due/overdue tasks
CREATE OR REPLACE VIEW vw_wa_today_tasks AS
SELECT t.id, t.title, t.task_type, t.due_at, t.status, t.priority,
       t.contact_id, c.full_name AS contact_name,
       COALESCE(c.whatsapp_number, c.phone_primary) AS contact_phone,
       (t.due_at < NOW()) AS overdue
FROM tasks t
LEFT JOIN contacts c ON c.id = t.contact_id
WHERE t.status NOT IN ('done','cancelled') AND t.due_at < NOW() + INTERVAL '2 days';

-- gone-quiet: client chats with no exchange in 7+ days
CREATE OR REPLACE VIEW vw_wa_gone_quiet AS
SELECT w.beeper_chat_id, w.title, w.contact_id, c.full_name,
       COALESCE(c.whatsapp_number, c.phone_primary) AS contact_phone,
       w.last_activity,
       EXTRACT(DAY FROM NOW() - w.last_activity)::INT AS quiet_days
FROM wa_chats w
LEFT JOIN contacts c ON c.id = w.contact_id
WHERE w.kind = 'client' AND w.ingest_enabled
  AND w.last_activity < NOW() - INTERVAL '7 days';

-- recent activity feed (non-personal, ingestable chats)
CREATE OR REPLACE VIEW vw_wa_recent_activity AS
SELECT i.occurred_at, i.direction, w.title AS chat_title, w.kind,
       i.is_group_msg, i.sender_display_name, i.contact_id,
       c.full_name AS contact_name, i.message_type,
       LEFT(COALESCE(i.body_text,''), 300) AS body, i.rdh_code, i.id
FROM interactions i
JOIN wa_chats w ON w.beeper_chat_id = i.beeper_chat_id
LEFT JOIN contacts c ON c.id = i.contact_id
WHERE i.source = 'beeper' AND w.ingest_enabled AND w.kind <> 'personal';

-- confirm queue with proposal names
CREATE OR REPLACE VIEW vw_wa_confirm_queue AS
SELECT q.phone, q.wa_name, q.seen_count, q.first_seen_chat, q.status,
       q.proposed_contact_id, c.full_name AS proposed_name
FROM wa_number_queue q
LEFT JOIN contacts c ON c.id = q.proposed_contact_id
WHERE q.status = 'pending'
ORDER BY q.seen_count DESC;

-- group directory + canonical-match coverage
CREATE OR REPLACE VIEW vw_wa_group_directory AS
SELECT w.beeper_chat_id, w.title, w.kind, w.ingest_enabled, w.member_count,
       w.last_activity, w.building_id, b.name AS building_name,
       COUNT(m.member_id) FILTER (WHERE m.contact_id IS NOT NULL) AS matched_members,
       COUNT(m.member_id) AS roster_members
FROM wa_chats w
LEFT JOIN buildings b ON b.id = w.building_id
LEFT JOIN wa_chat_members m ON m.beeper_chat_id = w.beeper_chat_id
WHERE w.chat_type = 'group'
GROUP BY w.beeper_chat_id, w.title, w.kind, w.ingest_enabled, w.member_count,
         w.last_activity, w.building_id, b.name;
