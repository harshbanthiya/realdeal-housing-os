-- Phase 8.0: WhatsApp assisted outreach + contact activity timeline (7 tables + 6 views).
--
-- Lane A only: free, human-in-loop outreach from the director's PERSONAL number via
-- WhatsApp Web in a second browser tab. The cockpit DRAFTS and QUEUES a warm greeting
-- sequence and renders a wa.me click-to-chat link; a HUMAN sends it. This layer NEVER
-- sends a message itself, never automates WhatsApp Web, never calls any API, and never
-- enables send/publish. send_enabled defaults to false in outreach_settings and is the
-- hard gate. Daily send cap defaults to 10/day on the personal number.
--
-- It also adds a generic contact activity timeline (sent / read / replied / enquired /
-- link_clicked / page_viewed / email_opened / opted_in / opted_out ...) that grows with
-- timestamps to score warm vs cold leads and PROTECT against spamming (cool-down + auto
-- pause for non-engagers). Per-contact website activity is captured via first-party
-- tracked links (outreach_tracked_links), NOT Meta Pixel (pixel is audience-level only).
--
-- Opt-ins captured here are recorded as evidence; an actual channel permission is only
-- ever granted through the existing channel_permissions table (this layer does not grant).
--
-- All views mask person names via mask_name() and expose NO phone/email/address values or
-- full message copy (char counts only). Operational truth (links, message text) lives in
-- the tables, which the cockpit reads directly.
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW; safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. outreach_settings  (key/value config; send_enabled hard gate, daily cap)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_settings (
  setting_key text PRIMARY KEY,
  setting_value text NOT NULL,
  notes text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO outreach_settings (setting_key, setting_value, notes) VALUES
  ('send_enabled', 'false', 'HARD GATE. Lane A is assisted/human-in-loop; this layer never sends. Leave false.'),
  ('daily_send_cap', '10', 'Max assisted WhatsApp sends per day on the personal number (stay under spam radar).'),
  ('cooldown_days', '7', 'Do not re-queue a contact within this many days of the last outbound touch.'),
  ('non_engagement_pause_count', '3', 'After this many outbound touches with 0 opens/clicks/replies, auto-pause the contact (anti-spam).'),
  ('owner_only', 'true', 'Lane A is restricted to owners for now.')
ON CONFLICT (setting_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. contact_activity_events  (fine-grained timeline spine; machine + human appendable)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_activity_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  channel text NOT NULL DEFAULT 'whatsapp_personal',  -- whatsapp_personal, whatsapp_business, email, web, phone, in_person, sms, other
  event_type text NOT NULL,
  direction text NOT NULL DEFAULT 'outbound',         -- inbound, outbound, internal
  occurred_at timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL DEFAULT 'cockpit_assisted',    -- cockpit_assisted, web_tracker, manual_mark, email_pixel, agent, import
  sequence_id uuid,
  sequence_step integer,
  tracked_link_id uuid,
  safe_summary text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT cae_event_type_check CHECK (event_type IN (
    'queued','sent','delivered','read','replied','enquired',
    'link_clicked','page_viewed','email_sent','email_opened',
    'call_made','visit_invited','visit_booked',
    'opted_in','opted_out','bounced','failed','note')),
  CONSTRAINT cae_direction_check CHECK (direction IN ('inbound','outbound','internal'))
);
CREATE INDEX IF NOT EXISTS idx_cae_contact_id ON contact_activity_events(contact_id);
CREATE INDEX IF NOT EXISTS idx_cae_channel ON contact_activity_events(channel);
CREATE INDEX IF NOT EXISTS idx_cae_event_type ON contact_activity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cae_occurred_at ON contact_activity_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_cae_sequence_id ON contact_activity_events(sequence_id);

-- ---------------------------------------------------------------------------
-- 3. outreach_sequences  (warm greeting -> follow-up drip definition)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_sequences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  channel text NOT NULL DEFAULT 'whatsapp_personal',
  owner_only boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'draft',               -- draft, active, paused, archived
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT outreach_sequences_status_check CHECK (status IN ('draft','active','paused','archived'))
);
CREATE INDEX IF NOT EXISTS idx_oseq_status ON outreach_sequences(status);

-- ---------------------------------------------------------------------------
-- 4. outreach_sequence_steps  (ordered steps with delays + message template)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_sequence_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sequence_id uuid NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
  step_number integer NOT NULL,
  delay_days integer NOT NULL DEFAULT 0,              -- days after the previous step
  channel text NOT NULL DEFAULT 'whatsapp_personal',
  message_template text NOT NULL,                     -- supports {{first_name}}, {{building}}, {{link}} placeholders
  link_target text,                                   -- relative path on our site, e.g. /imperial-heights
  goal text,                                          -- e.g. opt_in, re_engage, invite_visit
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (sequence_id, step_number)
);
CREATE INDEX IF NOT EXISTS idx_osstep_sequence_id ON outreach_sequence_steps(sequence_id);

-- ---------------------------------------------------------------------------
-- 5. contact_sequence_enrollments  (which contact is on which step)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_sequence_enrollments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  sequence_id uuid NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
  current_step integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active',              -- active, paused, completed, opted_out, suppressed
  next_due_at timestamptz,
  enrolled_by text,
  paused_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (contact_id, sequence_id),
  CONSTRAINT cse_status_check CHECK (status IN ('active','paused','completed','opted_out','suppressed'))
);
CREATE INDEX IF NOT EXISTS idx_cse_contact_id ON contact_sequence_enrollments(contact_id);
CREATE INDEX IF NOT EXISTS idx_cse_sequence_id ON contact_sequence_enrollments(sequence_id);
CREATE INDEX IF NOT EXISTS idx_cse_status ON contact_sequence_enrollments(status);
CREATE INDEX IF NOT EXISTS idx_cse_next_due_at ON contact_sequence_enrollments(next_due_at);

-- ---------------------------------------------------------------------------
-- 6. outreach_tracked_links  (per-contact first-party links for web activity)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_tracked_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id) ON DELETE CASCADE,
  token text NOT NULL UNIQUE,                         -- opaque short token used in the URL
  target_url text NOT NULL,                           -- where it redirects (our own site)
  channel text NOT NULL DEFAULT 'whatsapp_personal',
  sequence_id uuid,
  sequence_step integer,
  click_count integer NOT NULL DEFAULT 0,
  first_clicked_at timestamptz,
  last_clicked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_otl_contact_id ON outreach_tracked_links(contact_id);
CREATE INDEX IF NOT EXISTS idx_otl_token ON outreach_tracked_links(token);

-- ---------------------------------------------------------------------------
-- 7. whatsapp_assisted_queue  (owners-only queue; NEVER auto-sends)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS whatsapp_assisted_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  enrollment_id uuid REFERENCES contact_sequence_enrollments(id) ON DELETE SET NULL,
  sequence_id uuid REFERENCES outreach_sequences(id) ON DELETE SET NULL,
  sequence_step integer,
  channel text NOT NULL DEFAULT 'whatsapp_personal',
  drafted_message text NOT NULL,                      -- resolved copy the human will send (truth; masked in views)
  wa_link text,                                        -- wa.me/<number>?text=... click-to-chat deep link
  tracked_link_id uuid REFERENCES outreach_tracked_links(id) ON DELETE SET NULL,
  queued_for_date date NOT NULL DEFAULT CURRENT_DATE,
  status text NOT NULL DEFAULT 'pending',             -- pending, skipped, sent_by_human, replied, failed, cancelled
  send_confirmed boolean NOT NULL DEFAULT false,      -- only a HUMAN flips this true after sending in WhatsApp Web
  sent_at timestamptz,
  sent_by text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT waq_status_check CHECK (status IN ('pending','skipped','sent_by_human','replied','failed','cancelled'))
);
CREATE INDEX IF NOT EXISTS idx_waq_contact_id ON whatsapp_assisted_queue(contact_id);
CREATE INDEX IF NOT EXISTS idx_waq_status ON whatsapp_assisted_queue(status);
CREATE INDEX IF NOT EXISTS idx_waq_queued_for_date ON whatsapp_assisted_queue(queued_for_date);

-- ===========================================================================
-- VIEWS (masked; no PII, no full message copy)
-- ===========================================================================

-- vw_contact_activity_timeline : unified chronological feed (existing interactions + new events)
CREATE OR REPLACE VIEW vw_contact_activity_timeline AS
SELECT
  e.contact_id,
  mask_name(c.full_name)        AS contact_masked,
  c.contact_type,
  e.channel,
  e.event_type,
  e.direction,
  e.occurred_at,
  e.source,
  e.sequence_step,
  length(coalesce(e.safe_summary, '')) AS summary_char_count
FROM contact_activity_events e
LEFT JOIN contacts c ON c.id = e.contact_id
UNION ALL
SELECT
  i.contact_id,
  mask_name(c.full_name)        AS contact_masked,
  c.contact_type,
  i.channel,
  'interaction'                 AS event_type,
  i.direction,
  i.occurred_at,
  'interactions_table'          AS source,
  NULL::integer                 AS sequence_step,
  length(coalesce(i.summary, '')) AS summary_char_count
FROM interactions i
LEFT JOIN contacts c ON c.id = i.contact_id
ORDER BY occurred_at DESC;

-- vw_contact_engagement_score : roll the timeline into warm/cold + anti-spam flag
CREATE OR REPLACE VIEW vw_contact_engagement_score AS
WITH ev AS (
  SELECT
    contact_id,
    count(*) FILTER (WHERE event_type IN ('sent','email_sent') AND direction = 'outbound') AS outbound_count,
    count(*) FILTER (WHERE event_type IN ('read','email_opened','link_clicked','page_viewed')) AS open_count,
    count(*) FILTER (WHERE event_type IN ('replied','enquired')) AS reply_count,
    count(*) FILTER (WHERE event_type = 'opted_in')  AS optin_count,
    count(*) FILTER (WHERE event_type = 'opted_out') AS optout_count,
    max(occurred_at) AS last_activity_at,
    max(occurred_at) FILTER (WHERE event_type IN ('read','email_opened','link_clicked','page_viewed','replied','enquired')) AS last_engaged_at
  FROM contact_activity_events
  GROUP BY contact_id
)
SELECT
  ev.contact_id,
  mask_name(c.full_name) AS contact_masked,
  c.contact_type,
  ev.outbound_count,
  ev.open_count,
  ev.reply_count,
  ev.optin_count,
  ev.optout_count,
  ev.last_activity_at,
  ev.last_engaged_at,
  CASE
    WHEN ev.optout_count > 0 THEN 'opted_out'
    WHEN ev.reply_count > 0 OR ev.optin_count > 0 THEN 'hot'
    WHEN ev.open_count > 0 THEN 'warm'
    WHEN ev.outbound_count > 0 THEN 'cold'
    ELSE 'untouched'
  END AS engagement_tier,
  -- anti-spam: many outbound touches, zero engagement -> stop messaging
  (ev.optout_count = 0
   AND ev.open_count = 0
   AND ev.reply_count = 0
   AND ev.outbound_count >= (SELECT setting_value::int FROM outreach_settings WHERE setting_key = 'non_engagement_pause_count')
  ) AS do_not_spam_flag
FROM ev
LEFT JOIN contacts c ON c.id = ev.contact_id;

-- vw_owner_outreach_queue_today : safe inspection of today's owner queue (no copy/phone)
CREATE OR REPLACE VIEW vw_owner_outreach_queue_today AS
SELECT
  q.id AS queue_id,
  mask_name(c.full_name) AS contact_masked,
  c.contact_type,
  q.channel,
  q.sequence_step,
  q.status,
  q.send_confirmed,
  q.queued_for_date,
  length(q.drafted_message) AS message_char_count,
  (q.wa_link IS NOT NULL)   AS has_wa_link,
  (q.tracked_link_id IS NOT NULL) AS has_tracked_link
FROM whatsapp_assisted_queue q
LEFT JOIN contacts c ON c.id = q.contact_id
WHERE q.queued_for_date = CURRENT_DATE
ORDER BY q.created_at;

-- vw_outreach_daily_send_status : sends used today vs cap
CREATE OR REPLACE VIEW vw_outreach_daily_send_status AS
SELECT
  CURRENT_DATE AS for_date,
  (SELECT setting_value::int FROM outreach_settings WHERE setting_key = 'daily_send_cap') AS daily_cap,
  count(*) FILTER (WHERE q.status = 'sent_by_human' AND q.sent_at::date = CURRENT_DATE) AS sent_today,
  count(*) FILTER (WHERE q.status = 'pending' AND q.queued_for_date = CURRENT_DATE) AS pending_today,
  greatest(
    (SELECT setting_value::int FROM outreach_settings WHERE setting_key = 'daily_send_cap')
    - count(*) FILTER (WHERE q.status = 'sent_by_human' AND q.sent_at::date = CURRENT_DATE), 0) AS remaining_today
FROM whatsapp_assisted_queue q;

-- vw_whatsapp_assisted_readiness : REAL GATE (expected hard-false until a human opts in)
CREATE OR REPLACE VIEW vw_whatsapp_assisted_readiness AS
SELECT
  (SELECT setting_value FROM outreach_settings WHERE setting_key = 'send_enabled') AS send_enabled_setting,
  (SELECT count(*) FROM outreach_sequences WHERE status = 'active') AS active_sequences,
  (SELECT count(*) FROM whatsapp_assisted_queue WHERE status = 'pending' AND queued_for_date = CURRENT_DATE) AS pending_today,
  (SELECT count(*) FROM channel_permissions
     WHERE channel = 'whatsapp' AND permission_status IN ('allowed','opted_in')) AS whatsapp_permissions_allowed,
  (SELECT count(*) FROM contact_activity_events WHERE event_type = 'opted_in') AS optins_recorded,
  -- assisted lane is "ready to operate" only as a human-driven tool; never an autosend gate
  (
    (SELECT setting_value FROM outreach_settings WHERE setting_key = 'send_enabled') = 'true'
  ) AS autosend_enabled_should_be_false;

-- vw_owner_outreach_eligibility : who is eligible to enroll (owners, not suppressed, not opted out, not in cooldown)
CREATE OR REPLACE VIEW vw_owner_outreach_eligibility AS
SELECT
  c.id AS contact_id,
  mask_name(c.full_name) AS contact_masked,
  c.contact_type,
  (c.whatsapp_number IS NOT NULL OR c.phone_primary IS NOT NULL
   OR EXISTS (SELECT 1 FROM contact_methods m
                WHERE m.contact_id = c.id
                  AND m.method_type IN ('mobile','phone','whatsapp'))) AS has_number,
  EXISTS (SELECT 1 FROM outreach_suppression_list s
            WHERE s.contact_id = c.id AND s.status = 'active') AS is_suppressed,
  EXISTS (SELECT 1 FROM channel_permissions p
            WHERE p.contact_id = c.id AND p.channel = 'whatsapp'
              AND p.permission_status IN ('opted_out','do_not_contact')) AS is_opted_out,
  EXISTS (SELECT 1 FROM contact_activity_events e
            WHERE e.contact_id = c.id AND e.direction = 'outbound'
              AND e.occurred_at > now() - make_interval(days =>
                  (SELECT setting_value::int FROM outreach_settings WHERE setting_key = 'cooldown_days'))
          ) AS in_cooldown
FROM contacts c
WHERE c.status NOT IN ('do_not_contact','duplicate','archived')
  AND EXISTS (
    SELECT 1 FROM contact_property_relationships r
    WHERE r.contact_id = c.id
      AND r.relationship_type = 'owner'
      AND r.relationship_status IN ('active','approved')
  );
