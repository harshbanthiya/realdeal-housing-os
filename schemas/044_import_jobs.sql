-- Phase 8.x: Cockpit-driven contact import jobs.
--
-- Tracks an uploaded contact file as it runs through the existing programmatic
-- pipeline (profile -> normalize -> clean -> dedupe -> stage into source-aware
-- review tables). This table is STATE ONLY: it does not store contact PII, does
-- not create canonical contacts, and does not merge or send anything. The
-- pipeline stops at the review queue (audited source-aware staging); canonical
-- merge stays a separate, human-reviewed step.

CREATE TABLE IF NOT EXISTS import_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  original_filename text NOT NULL,         -- basename only (set by server; no path)
  stored_path text,                        -- server-side path under imports/contacts/ (gitignored) — never exposed in views
  mode text NOT NULL DEFAULT 'fake' CHECK (mode IN ('fake', 'real')),
  batch_label text,                        -- set once staging assigns a batch
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'staged', 'failed', 'cleaned')),
  stage text NOT NULL DEFAULT 'queued'
    CHECK (stage IN ('queued', 'profiling', 'normalizing', 'cleaning', 'deduping', 'planning', 'staging', 'done', 'error')),
  rows_normalized integer NOT NULL DEFAULT 0,
  rows_cleaned integer NOT NULL DEFAULT 0,
  duplicate_pairs integer NOT NULL DEFAULT 0,
  review_items_created integer NOT NULL DEFAULT 0,
  error_summary text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_import_jobs_status ON import_jobs (status, created_at DESC);

-- Masked view for the cockpit: exposes status/stage/counts and the basename,
-- but NEVER the server-side stored_path.
CREATE OR REPLACE VIEW vw_import_jobs AS
SELECT
  j.id,
  j.original_filename,
  j.mode,
  j.batch_label,
  j.status,
  j.stage,
  j.rows_normalized,
  j.rows_cleaned,
  j.duplicate_pairs,
  j.review_items_created,
  j.error_summary,
  j.created_by,
  j.created_at,
  j.updated_at
FROM import_jobs j
ORDER BY j.created_at DESC;
