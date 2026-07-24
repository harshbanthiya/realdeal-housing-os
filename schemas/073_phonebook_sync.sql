-- 073: phonebook two-way sync — her iPhone as both a target and a source.
--
-- Her saved names encode role + building + wing + unit ("(IMHO) OD 2802 IH"),
-- which for many units is data we do not otherwise hold. So this stores her
-- phonebook as a snapshot, and every proposed change in EITHER direction as a
-- review-gated row. Nothing writes to her phone or to canonical tables here.
--
-- See docs/PHONEBOOK-PLAN.md.

CREATE TABLE IF NOT EXISTS phonebook_snapshot (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  captured_on    date NOT NULL,
  source_file    text NOT NULL,
  card_index     integer NOT NULL,
  phone          text,                    -- +91XXXXXXXXXX, NULL if card had none
  original_name  text NOT NULL,

  -- what her name string parsed to
  parsed_role    text,                    -- owner | tenant | broker | landlord | lead
  parsed_building_id uuid REFERENCES buildings(id),
  parsed_wing    text,
  parsed_unit    text,
  parsed_person  text,
  parse_confidence text,                  -- high | medium | low | none

  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (captured_on, source_file, card_index)
);

CREATE INDEX IF NOT EXISTS pbs_phone_idx ON phonebook_snapshot (phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS pbs_parsed_idx ON phonebook_snapshot (parsed_building_id, parsed_wing, parsed_unit);

COMMENT ON TABLE phonebook_snapshot IS
  'Point-in-time copy of the sales phone. Also the rollback point: original_name '
  'is what we restore to if a rename pass goes wrong.';

-- Every proposed change, both directions, one row each.
CREATE TABLE IF NOT EXISTS phonebook_proposals (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id    uuid REFERENCES phonebook_snapshot(id) ON DELETE CASCADE,
  phone          text NOT NULL,
  direction      text NOT NULL,           -- to_phone | to_db
  change_type    text NOT NULL,
    -- to_phone: rename | enrich_note
    -- to_db:    link_unit | set_role | new_contact | add_phone_to_unit
  current_value  text,
  proposed_value text,
  note_block     text,                    -- the NOTE payload for to_phone rows

  contact_id     uuid REFERENCES contacts(id),
  building_id    uuid REFERENCES buildings(id),
  building_unit_id uuid REFERENCES building_units(id),
  role           text,
  confidence     text NOT NULL DEFAULT 'medium',
  conflicts      jsonb NOT NULL DEFAULT '{}'::jsonb,

  status         text NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|applied
  reviewed_by    text,
  reviewed_at    timestamptz,
  applied_at     timestamptz,
  decision_notes text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (phone, direction, change_type)
);

CREATE INDEX IF NOT EXISTS pbp_status_idx ON phonebook_proposals (status, direction);

COMMENT ON TABLE phonebook_proposals IS
  'Review-gated changes between the sales phone and the DB, both directions. '
  'A wrong unit link is worse than a missing one — nothing auto-applies.';

CREATE OR REPLACE VIEW vw_phonebook_sync_progress AS
SELECT direction, change_type, status, count(*) AS n
  FROM phonebook_proposals GROUP BY 1,2,3 ORDER BY 1,2,4 DESC;
