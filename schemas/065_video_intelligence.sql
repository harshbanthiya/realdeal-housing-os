-- migration 065: video intelligence + social posting queue (₹0 media/SEO stack)
-- video_research  = competitor/reference videos found on YouTube: view counts,
--                   transcripts, LLM analysis of why they perform.
-- social_post_drafts = review-gated queue of OUR posts (YouTube/Shorts/Instagram)
--                   built from reviewed media_assets. Nothing posts without
--                   operator approval; Instagram stays manual-post (Lane A).
-- NOTE: §17 item 7 (consumer_cases/consent_records) renumbers to 066.

CREATE TABLE IF NOT EXISTS video_research (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform       TEXT NOT NULL DEFAULT 'youtube',
  video_id       TEXT NOT NULL UNIQUE,
  url            TEXT NOT NULL,
  title          TEXT NOT NULL,
  channel        TEXT,
  views          BIGINT,
  duration_s     INT,
  published_at   TIMESTAMPTZ,
  search_query   TEXT,                    -- how we found it
  transcript     TEXT,                    -- auto-subs, plain text
  analysis       JSONB,                   -- {hook, structure, topics, why_it_works, steal_ideas}
  llm_run_id     UUID REFERENCES llm_runs(id),
  status         TEXT NOT NULL DEFAULT 'found' CHECK (status IN
                   ('found','analyzed','used','ignored')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_video_research_status ON video_research (status, views DESC);

CREATE TABLE IF NOT EXISTS social_post_drafts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  media_asset_id  UUID REFERENCES media_assets(id),
  building_id     UUID REFERENCES buildings(id),
  platform        TEXT NOT NULL CHECK (platform IN
                    ('youtube','youtube_shorts','instagram','facebook')),
  title           TEXT NOT NULL,
  description     TEXT,
  tags            TEXT[] NOT NULL DEFAULT '{}',
  edit_spec       JSONB,                  -- {trim:[start,end], crop:'9:16', captions:bool, notes}
  inspired_by     UUID REFERENCES video_research(id),
  output_path     TEXT,                   -- rendered file after prep_short.sh
  scheduled_for   TIMESTAMPTZ,
  llm_run_id      UUID REFERENCES llm_runs(id),
  status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN
                    ('draft','approved','rendered','scheduled','posted','rejected')),
  reviewed_by     TEXT,
  reviewed_at     TIMESTAMPTZ,
  decision_notes  TEXT,
  posted_url      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_social_post_drafts_status ON social_post_drafts (status);

CREATE OR REPLACE VIEW vw_social_post_review_queue AS
  SELECT d.id, d.platform, d.title, b.name AS building, d.status,
         d.scheduled_for, d.created_at
  FROM social_post_drafts d LEFT JOIN buildings b ON b.id = d.building_id
  WHERE d.status IN ('draft','approved','rendered') ORDER BY d.created_at;

CREATE OR REPLACE VIEW vw_video_research_top AS
  SELECT video_id, title, channel, views, duration_s, status,
         analysis->>'why_it_works' AS why_it_works, url
  FROM video_research ORDER BY views DESC NULLS LAST LIMIT 100;
