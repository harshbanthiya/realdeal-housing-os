-- migration 064: ₹0-stack SEO LLM worker (ROADMAP §17 item 1)
-- llm_runs = local trace table (Langfuse skipped — 8GB M1 can't run ClickHouse).
-- seo_content_drafts = review-gated blog/brief drafts for the site.
-- answer_opportunities = Reddit/Quora threads worth answering + DRAFT answers.
--   Operator posts by hand from their own accounts (platform ToS + authenticity,
--   Lane A discipline). The worker NEVER posts anywhere.
-- NOTE: §17 had penciled consumer_cases/consent_records as 064 — that moves to 065.

-- ── llm_runs: one row per LLM call, any tier ───────────────────────────────
CREATE TABLE IF NOT EXISTS llm_runs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker       TEXT NOT NULL,               -- content_scout | review_triage | ...
  tier         TEXT NOT NULL CHECK (tier IN ('ollama','gemini','openai_compat')),
  model        TEXT NOT NULL,               -- qwen3:4b | gemini-2.5-flash | ...
  purpose      TEXT NOT NULL,               -- blog_draft | answer_draft | triage | ...
  prompt_chars INT,
  output_chars INT,
  duration_ms  INT,
  status       TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','error','skipped')),
  error        TEXT,
  -- prompt/output stored truncated for audit; full artifacts live in the target tables
  prompt_head  TEXT,
  output_head  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_llm_runs_worker  ON llm_runs (worker, created_at DESC);

-- ── seo_content_drafts: blog posts / briefs, review-gated ──────────────────
CREATE TABLE IF NOT EXISTS seo_content_drafts (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind             TEXT NOT NULL CHECK (kind IN ('blog_post','seo_brief')),
  building_id      UUID REFERENCES buildings(id),
  target_area      TEXT,                    -- Goregaon West | Andheri West | ...
  slug             TEXT NOT NULL,
  title            TEXT NOT NULL,
  excerpt          TEXT,
  body_md          TEXT NOT NULL,
  seo_title        TEXT,
  seo_description  TEXT,
  target_keywords  TEXT[] NOT NULL DEFAULT '{}',
  sources          JSONB NOT NULL DEFAULT '[]'::jsonb,  -- facts used, with table/doc refs
  llm_run_id       UUID REFERENCES llm_runs(id),
  status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                     ('draft','approved','rejected','published')),
  reviewed_by      TEXT,
  reviewed_at      TIMESTAMPTZ,
  decision_notes   TEXT,
  published_url    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (slug, kind)
);
CREATE INDEX IF NOT EXISTS idx_seo_content_drafts_status ON seo_content_drafts (status);

-- ── answer_opportunities: threads found + draft answers, operator posts ────
CREATE TABLE IF NOT EXISTS answer_opportunities (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform         TEXT NOT NULL CHECK (platform IN ('reddit','quora','other')),
  url              TEXT NOT NULL UNIQUE,
  title            TEXT NOT NULL,
  snippet          TEXT,
  community        TEXT,                    -- subreddit / quora topic
  thread_created   TIMESTAMPTZ,
  matched_building UUID REFERENCES buildings(id),
  matched_area     TEXT,
  relevance        TEXT,                    -- worker's one-line why-this-matters
  draft_answer_md  TEXT,                    -- NULL until drafted
  suggested_link   TEXT,                    -- our page to reference, if genuinely relevant
  llm_run_id       UUID REFERENCES llm_runs(id),
  status           TEXT NOT NULL DEFAULT 'found' CHECK (status IN
                     ('found','drafted','approved','rejected','posted','stale')),
  reviewed_by      TEXT,
  reviewed_at      TIMESTAMPTZ,
  decision_notes   TEXT,
  posted_url       TEXT,                    -- operator fills after posting by hand
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_answer_opps_status ON answer_opportunities (status);

-- ── review queues ───────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_seo_draft_review_queue AS
  SELECT id, kind, slug, title, target_area, target_keywords, status, created_at
  FROM seo_content_drafts WHERE status = 'draft' ORDER BY created_at;

CREATE OR REPLACE VIEW vw_answer_review_queue AS
  SELECT id, platform, community, title, url, relevance, status, created_at
  FROM answer_opportunities WHERE status IN ('found','drafted') ORDER BY created_at;
