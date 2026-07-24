-- 071: contact-sheet reconciliation — every contact on the drive ends up either
-- in the DB or in front of a human. Nothing silently falls through.
--
-- 162 contact-bearing spreadsheets are catalogued in drive_files (owner/broker/
-- tenant sheets + phonebook exports). This tracks them file-by-file and
-- row-by-row so workers/contact_reconcile.py can chew through them in small
-- batches every 30 minutes and always resume exactly where it stopped.

CREATE TABLE IF NOT EXISTS contact_sheet_files (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  drive_file_id   uuid REFERENCES drive_files(id),
  file_path       text NOT NULL UNIQUE,
  doc_kind        text,
  building_id     uuid REFERENCES buildings(id),
  status          text NOT NULL DEFAULT 'pending',  -- pending|in_progress|done|failed|unreadable
  rows_total      integer,
  rows_done       integer NOT NULL DEFAULT 0,
  header_map      jsonb,       -- which column we read as name/phone/email
  last_error      text,
  started_at      timestamptz,
  finished_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS csf_status_idx ON contact_sheet_files (status);

-- One row per contact found in a sheet. `resolution` is the promise this table
-- makes: every row is matched, created, queued for review, or explicitly
-- skipped with a reason — never simply absent.
CREATE TABLE IF NOT EXISTS contact_sheet_rows (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sheet_file_id    uuid NOT NULL REFERENCES contact_sheet_files(id) ON DELETE CASCADE,
  row_index        integer NOT NULL,
  raw              jsonb NOT NULL,
  parsed_name      text,
  parsed_phone     text,        -- normalised to +91XXXXXXXXXX where possible
  parsed_email     text,

  resolution       text NOT NULL DEFAULT 'pending',
    -- pending | matched_phone | created | review | skipped_no_contact | duplicate_row
  resolution_reason text,
  contact_id       uuid REFERENCES contacts(id),

  -- review payload: the near-miss that a human has to settle
  candidate_contact_id uuid REFERENCES contacts(id),
  candidate_name       text,
  name_similarity      real,
  review_status    text NOT NULL DEFAULT 'none',   -- none | pending | approved | rejected
  reviewed_by      text,
  reviewed_at      timestamptz,
  decision_notes   text,

  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (sheet_file_id, row_index)
);

CREATE INDEX IF NOT EXISTS csr_resolution_idx ON contact_sheet_rows (resolution);
CREATE INDEX IF NOT EXISTS csr_review_idx     ON contact_sheet_rows (review_status) WHERE review_status = 'pending';
CREATE INDEX IF NOT EXISTS csr_phone_idx      ON contact_sheet_rows (parsed_phone) WHERE parsed_phone IS NOT NULL;

COMMENT ON TABLE contact_sheet_rows IS
  'Every contact row found on the drive. resolution != pending is the guarantee '
  'that the row is accounted for: in the DB, or awaiting a human decision.';

-- The accounting view: "is everything in the system?"
CREATE OR REPLACE VIEW vw_contact_reconcile_progress AS
SELECT
  (SELECT count(*) FROM contact_sheet_files)                                  AS sheets_total,
  (SELECT count(*) FROM contact_sheet_files WHERE status = 'done')            AS sheets_done,
  (SELECT count(*) FROM contact_sheet_files WHERE status = 'pending')         AS sheets_pending,
  (SELECT count(*) FROM contact_sheet_files WHERE status IN ('failed','unreadable')) AS sheets_failed,
  (SELECT count(*) FROM contact_sheet_rows)                                   AS rows_seen,
  (SELECT count(*) FROM contact_sheet_rows WHERE resolution = 'matched_phone') AS rows_matched,
  (SELECT count(*) FROM contact_sheet_rows WHERE resolution = 'created')      AS rows_created,
  (SELECT count(*) FROM contact_sheet_rows WHERE review_status = 'pending')   AS rows_in_review,
  (SELECT count(*) FROM contact_sheet_rows WHERE resolution = 'pending')      AS rows_unresolved,
  (SELECT count(*) FROM contact_sheet_rows WHERE resolution LIKE 'skipped%')  AS rows_skipped;
