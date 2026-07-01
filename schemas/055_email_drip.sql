-- migration 055: email drip state + unsubscribe token
CREATE TABLE IF NOT EXISTS email_drip_state (
  contact_id      UUID REFERENCES contacts(id) ON DELETE CASCADE,
  template_key    TEXT,
  sent_at         TIMESTAMPTZ,
  opened_at       TIMESTAMPTZ,
  clicked_at      TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  resend_id       TEXT,
  error_msg       TEXT,
  PRIMARY KEY (contact_id, template_key)
);

ALTER TABLE contacts
  ADD COLUMN IF NOT EXISTS unsub_token TEXT
    DEFAULT encode(gen_random_bytes(16), 'hex');

-- backfill any NULL tokens (idempotent)
UPDATE contacts SET unsub_token = encode(gen_random_bytes(16), 'hex')
  WHERE unsub_token IS NULL;
