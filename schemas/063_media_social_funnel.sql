-- migration 063: media/social/funnel foundation
-- (docs/MEDIA-SOCIAL-FUNNEL-PLAN.md Tasks B + C — listing↔social content links,
--  newsletter subscribers with double-opt-in, global email suppression list)
-- NOTE: ROADMAP §17 had penciled consumer_cases/consent_records as 063 — that
-- work moves to 064.

-- ── listing_content: media_assets ↔ site listings ─────────────────────────
-- Site listings are static fixtures (web/src/lib/listings.ts), so the link is
-- by slug, with optional building_id for building-level content.
CREATE TABLE IF NOT EXISTS listing_content (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  media_asset_id   UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  listing_slug     TEXT NOT NULL,
  building_id      UUID REFERENCES buildings(id),
  role             TEXT NOT NULL CHECK (role IN
                     ('reel','story','tour','photo_set','ambient_loop','thumbnail')),
  status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                     ('draft','scheduled','posted','retired')),
  platform         TEXT CHECK (platform IN ('instagram','youtube','facebook','site')),
  platform_post_id TEXT,
  post_url         TEXT,          -- permalink once live
  utm_campaign     TEXT,          -- tag used in the caption/bio link back to the listing
  scheduled_for    TIMESTAMPTZ,
  posted_at        TIMESTAMPTZ,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (media_asset_id, listing_slug, role)
);
CREATE INDEX IF NOT EXISTS idx_listing_content_slug   ON listing_content (listing_slug);
CREATE INDEX IF NOT EXISTS idx_listing_content_status ON listing_content (status);

-- ── subscribers: newsletter double-opt-in (local Postgres, no third-party CRM) ──
CREATE TABLE IF NOT EXISTS subscribers (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email             TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
  status            TEXT NOT NULL DEFAULT 'pending' CHECK (status IN
                      ('pending','confirmed','unsubscribed')),
  building_interest TEXT[] NOT NULL DEFAULT '{}',   -- project slugs
  source            TEXT,                           -- footer | listing:<slug> | blog:<slug>
  consent_text      TEXT,                           -- the exact opt-in wording shown
  confirm_token     TEXT NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),
  unsub_token       TEXT NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),
  requested_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  confirmed_at      TIMESTAMPTZ,
  unsubscribed_at   TIMESTAMPTZ
);

-- ── email_suppression: global do-not-mail (closes LAUNCH_CONTEXT F-5 plumbing) ──
-- EVERY sender (drip scripts, future newsletter sends) MUST check this table
-- before sending. Unsubscribes/bounces/complaints land here regardless of which
-- list they arrived through.
CREATE TABLE IF NOT EXISTS email_suppression (
  email      TEXT PRIMARY KEY CHECK (email = lower(email)),
  reason     TEXT NOT NULL CHECK (reason IN ('unsubscribed','bounced','complained','manual')),
  source     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
