-- 074: iCloud CardDAV card store — the only way to update her phone in place.
--
-- Her .vcf exports carry NO UID (Apple strips it on share-sheet export), so an
-- exported card cannot be mapped back to the card on the server. Re-importing
-- would create duplicates. The only safe write path is CardDAV: pull the live
-- cards (which have href + etag + UID), modify, PUT back with If-Match.
--
-- original_vcard is the rollback: it is the exact body we replaced.

CREATE TABLE IF NOT EXISTS icloud_cards (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  href           text NOT NULL UNIQUE,     -- CardDAV resource path
  uid            text,                     -- vCard UID from the server
  etag           text,                     -- for If-Match on write
  display_name   text,
  phone          text,                     -- first normalised mobile, for matching
  raw_vcard      text NOT NULL,
  pulled_at      timestamptz NOT NULL DEFAULT now(),

  -- write state
  original_vcard text,                     -- body before our first write (rollback)
  written_at     timestamptz,
  write_error    text
);

CREATE INDEX IF NOT EXISTS icloud_cards_phone_idx ON icloud_cards (phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS icloud_cards_written_idx ON icloud_cards (written_at);

COMMENT ON TABLE icloud_cards IS
  'Live mirror of the sales phone address book via iCloud CardDAV. '
  'original_vcard is the rollback point for every card we modify.';

CREATE OR REPLACE VIEW vw_icloud_write_progress AS
SELECT
  count(*)                                        AS cards_pulled,
  count(*) FILTER (WHERE phone IS NOT NULL)       AS with_mobile,
  count(*) FILTER (WHERE written_at IS NOT NULL)  AS written,
  count(*) FILTER (WHERE write_error IS NOT NULL) AS errored
FROM icloud_cards;
