-- 072: broker Community roster — track who is saved, invited, and joined.
--
-- WhatsApp has no bulk-add API: a person must exist in the sales phone's
-- address book, and joining is by tapping an invite link. So the automatable
-- part is knowing exactly WHO, in what state, and never asking twice.
-- See docs/NORTH-STAR.md §7.

CREATE TABLE IF NOT EXISTS community_roster (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone         text NOT NULL UNIQUE,        -- +91XXXXXXXXXX
  display_name  text,
  role          text NOT NULL DEFAULT 'broker',
  source        text,                        -- wa_broker_group | wa_offers | drive_sheet | db_contact
  source_detail text,

  in_phonebook  boolean NOT NULL DEFAULT false,  -- present in the sales phone export
  contact_id    uuid REFERENCES contacts(id),

  status        text NOT NULL DEFAULT 'to_save',
    -- to_save → saved → invited → joined | declined | bounced | skip
  saved_at      timestamptz,
  invited_at    timestamptz,
  joined_at     timestamptz,
  invite_token  text,
  notes         text,

  first_seen_at timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS community_roster_status_idx ON community_roster (status);

COMMENT ON TABLE community_roster IS
  'Who belongs in the broker WhatsApp Community and what state they are in. '
  'Rebuilt/refreshed by scripts/build_community_roster.py — safe to re-run.';

CREATE OR REPLACE VIEW vw_community_roster_progress AS
SELECT status, count(*) AS people,
       count(*) FILTER (WHERE in_phonebook) AS in_phone
  FROM community_roster GROUP BY status ORDER BY 2 DESC;
