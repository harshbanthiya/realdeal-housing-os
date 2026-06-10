-- Phase 7.0: DLF launch command center foundation (schema + dashboards only).
--
-- A project-scoped "launch command center" for time-sensitive launches (e.g. DLF). The existing
-- growth tables (seo_keywords, content_briefs, campaign_drafts, channel_permissions, ...) are
-- building/keyword-scoped and launch-agnostic; these tables add a launch project layer on top:
-- per-launch channels, a content/outreach calendar, target lead SEGMENTS (counts only, never raw
-- contacts), an operator checklist, and send/publish readiness gates.
--
-- This phase is schema + a review-gated seed ONLY. NOTHING here sends WhatsApp/SMS/email,
-- enables a campaign, publishes to Wix, calls an external API, scrapes, imports contacts, or
-- creates/merges contacts. Every send/publish flag defaults to false; readiness gates default
-- pending. Views never expose personal contact data (segments are counts only).
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. launch_projects — one time-sensitive launch.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_key text UNIQUE NOT NULL,
  project_display_name text NOT NULL,
  internal_alias text,
  developer_name text,
  area text,
  city text,
  launch_status text DEFAULT 'planning',          -- planning, pre_launch, launch_live, post_launch, paused, archived
  expected_launch_month text,
  expected_launch_date date,
  rera_registration_number text,
  rera_verification_status text DEFAULT 'not_started',
  wix_page_status text DEFAULT 'not_started',
  seo_status text DEFAULT 'planning',
  campaign_status text DEFAULT 'planning',
  operator_priority text DEFAULT 'high',
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lp_launch_key ON launch_projects(launch_key);
CREATE INDEX IF NOT EXISTS idx_lp_launch_status ON launch_projects(launch_status);
CREATE INDEX IF NOT EXISTS idx_lp_created_at ON launch_projects(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_channels — channels for a launch (send/publish gated off by default).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_channels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  channel text,                                    -- wix, seo, blog, instagram, youtube_shorts, whatsapp, email, phone_call, referral, listing_portal
  channel_status text DEFAULT 'planned',           -- planned, draft_ready, needs_review, approved, active, paused
  owner text,
  send_enabled boolean DEFAULT false,
  publish_enabled boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lc_launch_project_id ON launch_channels(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lc_channel ON launch_channels(channel);
CREATE INDEX IF NOT EXISTS idx_lc_channel_status ON launch_channels(channel_status);
CREATE INDEX IF NOT EXISTS idx_lc_created_at ON launch_channels(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_campaign_calendar — daily content/outreach calendar (placeholders).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_campaign_calendar (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  planned_date date,
  channel text,
  campaign_type text,                              -- awareness, lead_capture, follow_up, seo_blog, reel, story, broadcast, email_newsletter, launch_day_push
  title text,
  status text DEFAULT 'planned',                   -- planned, drafted, reviewed, approved, sent, published, skipped
  send_enabled boolean DEFAULT false,
  publish_enabled boolean DEFAULT false,
  content_brief_id uuid REFERENCES content_briefs(id),
  campaign_draft_id uuid REFERENCES campaign_drafts(id),
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcc_launch_project_id ON launch_campaign_calendar(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcc_planned_date ON launch_campaign_calendar(planned_date);
CREATE INDEX IF NOT EXISTS idx_lcc_channel ON launch_campaign_calendar(channel);
CREATE INDEX IF NOT EXISTS idx_lcc_status ON launch_campaign_calendar(status);
CREATE INDEX IF NOT EXISTS idx_lcc_created_at ON launch_campaign_calendar(created_at);

-- ---------------------------------------------------------------------------
-- 4. launch_lead_segments — target audiences as COUNTS only (no raw contacts).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  segment_key text,
  segment_name text,
  segment_description text,
  estimated_contact_count integer,
  permission_required boolean DEFAULT true,
  whatsapp_allowed_count integer DEFAULT 0,
  email_allowed_count integer DEFAULT 0,
  suppressed_count integer DEFAULT 0,
  status text DEFAULT 'draft',                      -- draft, needs_review, approved, active, archived
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lls_launch_project_id ON launch_lead_segments(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lls_segment_key ON launch_lead_segments(segment_key);
CREATE INDEX IF NOT EXISTS idx_lls_status ON launch_lead_segments(status);
CREATE INDEX IF NOT EXISTS idx_lls_created_at ON launch_lead_segments(created_at);

-- ---------------------------------------------------------------------------
-- 5. launch_operator_tasks — daily human operator checklist.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_operator_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  task_type text,                                  -- verify_project_name, confirm_rera, build_wix_page, draft_blog, draft_reel, approve_whatsapp_copy, approve_email_copy, check_permissions, upload_creatives, review_leads, follow_up_hot_leads
  task_status text DEFAULT 'pending',              -- pending, in_progress, blocked, done, skipped
  priority text DEFAULT 'normal',
  due_date date,
  assigned_to text,
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lot_launch_project_id ON launch_operator_tasks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lot_task_type ON launch_operator_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_lot_task_status ON launch_operator_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_lot_created_at ON launch_operator_tasks(created_at);

-- ---------------------------------------------------------------------------
-- 6. launch_readiness_checks — gates before sending/publishing.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_readiness_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  check_type text,                                 -- project_name_confirmed, rera_checked, wix_landing_page_ready, lead_capture_form_ready, whatsapp_template_approved, email_template_approved, consent_ready, suppression_checked, seo_briefs_ready, social_calendar_ready, n8n_workflow_ready
  check_status text DEFAULT 'pending',             -- pending, passed, failed, waived, needs_review
  severity text DEFAULT 'normal',                  -- low, normal, high, blocker
  safe_summary text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lrc_launch_project_id ON launch_readiness_checks(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lrc_check_type ON launch_readiness_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_lrc_check_status ON launch_readiness_checks(check_status);
CREATE INDEX IF NOT EXISTS idx_lrc_created_at ON launch_readiness_checks(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (project pattern: set_updated_at() from 001_initial_schema.sql).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_launch_projects_updated_at ON launch_projects;
CREATE TRIGGER trg_launch_projects_updated_at
BEFORE UPDATE ON launch_projects FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_channels_updated_at ON launch_channels;
CREATE TRIGGER trg_launch_channels_updated_at
BEFORE UPDATE ON launch_channels FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_campaign_calendar_updated_at ON launch_campaign_calendar;
CREATE TRIGGER trg_launch_campaign_calendar_updated_at
BEFORE UPDATE ON launch_campaign_calendar FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_lead_segments_updated_at ON launch_lead_segments;
CREATE TRIGGER trg_launch_lead_segments_updated_at
BEFORE UPDATE ON launch_lead_segments FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_operator_tasks_updated_at ON launch_operator_tasks;
CREATE TRIGGER trg_launch_operator_tasks_updated_at
BEFORE UPDATE ON launch_operator_tasks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_readiness_checks_updated_at ON launch_readiness_checks;
CREATE TRIGGER trg_launch_readiness_checks_updated_at
BEFORE UPDATE ON launch_readiness_checks FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Read-only dashboards (counts/scalars only; no personal contact data).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_launch_command_center_home AS
SELECT
  p.launch_key,
  p.project_display_name,
  p.launch_status,
  p.expected_launch_month,
  (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id) AS total_channels,
  (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id AND c.channel_status = 'active') AS active_channels,
  (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id AND c.send_enabled) AS send_enabled_channels,
  (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id AND c.publish_enabled) AS publish_enabled_channels,
  (SELECT count(*) FROM launch_campaign_calendar cc WHERE cc.launch_project_id = p.id) AS calendar_items,
  (SELECT count(*) FROM launch_operator_tasks t WHERE t.launch_project_id = p.id AND t.task_status IN ('pending','in_progress','blocked')) AS pending_operator_tasks,
  (SELECT count(*) FROM launch_readiness_checks r WHERE r.launch_project_id = p.id AND r.severity = 'blocker' AND r.check_status IN ('pending','failed','needs_review')) AS blocker_checks,
  (SELECT count(*) FROM launch_lead_segments s WHERE s.launch_project_id = p.id) AS lead_segments,
  p.campaign_status,
  COALESCE(
    (SELECT r.check_type FROM launch_readiness_checks r
       WHERE r.launch_project_id = p.id AND r.check_status IN ('pending','failed','needs_review')
       ORDER BY CASE r.severity WHEN 'blocker' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                r.created_at LIMIT 1),
    'all_checks_clear') AS next_required_action
FROM launch_projects p;

CREATE OR REPLACE VIEW vw_launch_channel_dashboard AS
SELECT
  p.launch_key,
  p.project_display_name,
  c.channel,
  c.channel_status,
  c.send_enabled,
  c.publish_enabled,
  c.human_review_required
FROM launch_channels c
JOIN launch_projects p ON p.id = c.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_calendar_dashboard AS
SELECT
  p.launch_key,
  cc.planned_date,
  cc.channel,
  cc.campaign_type,
  cc.title,
  cc.status,
  cc.send_enabled,
  cc.publish_enabled
FROM launch_campaign_calendar cc
JOIN launch_projects p ON p.id = cc.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_lead_segment_dashboard AS
SELECT
  p.launch_key,
  s.segment_key,
  s.segment_name,
  s.estimated_contact_count,
  s.whatsapp_allowed_count,
  s.email_allowed_count,
  s.suppressed_count,
  s.status
FROM launch_lead_segments s
JOIN launch_projects p ON p.id = s.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_operator_task_dashboard AS
SELECT
  p.launch_key,
  t.task_type,
  t.task_status,
  t.priority,
  t.due_date,
  t.assigned_to,
  t.safe_summary
FROM launch_operator_tasks t
JOIN launch_projects p ON p.id = t.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_readiness_dashboard AS
SELECT
  p.launch_key,
  r.check_type,
  r.check_status,
  r.severity,
  r.safe_summary
FROM launch_readiness_checks r
JOIN launch_projects p ON p.id = r.launch_project_id;

-- DLF-specific rollup. ready_for_launch_push is a REAL gate: it is true only when no blocker
-- check is outstanding, the project name is confirmed, AND at least one channel each is
-- send-enabled and publish-enabled. In Phase 7.0 those are 0, so it evaluates false.
CREATE OR REPLACE VIEW vw_dlf_launch_priority_dashboard AS
WITH agg AS (
  SELECT
    p.id, p.launch_key, p.project_display_name, p.launch_status,
    p.rera_verification_status, p.wix_page_status, p.seo_status, p.campaign_status,
    (SELECT count(*) FROM launch_readiness_checks r WHERE r.launch_project_id = p.id
       AND r.severity = 'blocker' AND r.check_status IN ('pending','failed','needs_review')) AS pending_blockers,
    (SELECT count(*) FROM launch_operator_tasks t WHERE t.launch_project_id = p.id
       AND t.task_status IN ('pending','in_progress','blocked')) AS pending_tasks,
    (SELECT count(*) FROM launch_campaign_calendar cc WHERE cc.launch_project_id = p.id) AS planned_campaign_items,
    (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id AND c.send_enabled) AS send_enabled_count,
    (SELECT count(*) FROM launch_channels c WHERE c.launch_project_id = p.id AND c.publish_enabled) AS publish_enabled_count,
    (SELECT count(*) FROM launch_readiness_checks r WHERE r.launch_project_id = p.id
       AND r.check_type = 'project_name_confirmed' AND r.check_status = 'passed') AS name_confirmed
  FROM launch_projects p
)
SELECT
  launch_key, project_display_name, launch_status,
  rera_verification_status, wix_page_status, seo_status, campaign_status,
  pending_blockers, pending_tasks, planned_campaign_items,
  send_enabled_count, publish_enabled_count,
  (pending_blockers = 0 AND name_confirmed > 0 AND send_enabled_count > 0 AND publish_enabled_count > 0) AS ready_for_launch_push,
  CASE
    WHEN name_confirmed = 0 THEN 'project name not confirmed (operator must verify DLF Westend vs The Westpark)'
    WHEN pending_blockers > 0 THEN pending_blockers || ' blocker readiness check(s) outstanding'
    WHEN send_enabled_count = 0 THEN 'no channel send-enabled (sends intentionally disabled this phase)'
    WHEN publish_enabled_count = 0 THEN 'no channel publish-enabled (publishing intentionally disabled this phase)'
    ELSE 'ready'
  END AS blocked_reason
FROM agg;
