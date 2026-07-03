-- migration 059: bounce/complaint/delivery tracking for email drip
ALTER TABLE email_drip_state
  ADD COLUMN IF NOT EXISTS delivered_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS bounced_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS complained_at TIMESTAMPTZ;
