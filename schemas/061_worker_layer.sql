-- 061: always-on worker layer
-- Daily workers (workers/*.py) log every run here and file findings into a
-- single operator queue. Workers never write canonical data — findings only.

CREATE TABLE IF NOT EXISTS worker_runs (
  id BIGSERIAL PRIMARY KEY,
  worker TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',           -- running | ok | error | skipped
  summary TEXT,
  items_found INTEGER NOT NULL DEFAULT 0,
  detail JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS worker_runs_worker_idx
  ON worker_runs (worker, started_at DESC);

CREATE TABLE IF NOT EXISTS worker_findings (
  id BIGSERIAL PRIMARY KEY,
  worker TEXT NOT NULL,
  kind TEXT NOT NULL,                               -- e.g. stale_queue, dq_orphan_units, listing_ready
  dedupe_key TEXT NOT NULL UNIQUE,                  -- stable key so re-runs don't duplicate
  title TEXT NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  severity TEXT NOT NULL DEFAULT 'info',            -- info | warn | action
  status TEXT NOT NULL DEFAULT 'pending',           -- pending | acked | resolved
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  acked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS worker_findings_status_idx
  ON worker_findings (status, severity, last_seen_at DESC);
