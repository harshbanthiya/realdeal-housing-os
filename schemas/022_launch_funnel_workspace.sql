-- Phase 7.1: DLF launch funnel & campaign draft workspace (schema + dashboards only).
--
-- Builds the full launch funnel scaffolding on top of the Phase 7.0 command center:
-- Audience -> Message -> Landing Page -> Lead Form -> Qualification -> Follow-up -> Site Visit
-- -> Booking Intent -> Closed/Lost/Nurture. Adds landing-page specs, lead-capture form specs,
-- UTM/attribution plans, content pillars, WhatsApp/email/social DRAFT templates, lead-scoring
-- rules, and a human review queue.
--
-- This phase is schema + a review-gated seed ONLY. NOTHING here sends WhatsApp/SMS/email/social,
-- enables a campaign, publishes to Wix, calls any external API, scrapes, imports/selects/creates/
-- merges contacts, or marks ready_for_launch_push. Every send_enabled/publish_enabled defaults
-- false; human_review_required defaults true; readiness gates default pending. Views never expose
-- personal contact data, and the message/social views never expose full body/caption text.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout; safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. launch_landing_page_specs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_landing_page_specs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  page_key text,
  page_title text,
  page_slug text,
  page_status text DEFAULT 'draft',                -- draft, needs_review, approved, ready_for_wix, published, archived
  hero_headline text,
  hero_subheadline text,
  primary_cta text,
  secondary_cta text,
  form_goal text,
  required_sections jsonb DEFAULT '[]'::jsonb,
  trust_disclaimers jsonb DEFAULT '[]'::jsonb,
  rera_disclaimer_required boolean DEFAULT true,
  project_name_confirmation_required boolean DEFAULT true,
  human_review_required boolean DEFAULT true,
  publish_enabled boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llps_launch_project_id ON launch_landing_page_specs(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llps_page_key ON launch_landing_page_specs(page_key);
CREATE INDEX IF NOT EXISTS idx_llps_page_status ON launch_landing_page_specs(page_status);
CREATE INDEX IF NOT EXISTS idx_llps_created_at ON launch_landing_page_specs(created_at);

-- ---------------------------------------------------------------------------
-- 2. launch_lead_capture_forms
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_capture_forms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  form_key text,
  form_status text DEFAULT 'draft',                -- draft, needs_review, approved, active, archived
  form_goal text,                                  -- brochure_request, price_sheet_request, site_visit_request, launch_waitlist, investor_call
  required_fields jsonb DEFAULT '[]'::jsonb,
  qualification_questions jsonb DEFAULT '[]'::jsonb,
  consent_fields jsonb DEFAULT '[]'::jsonb,
  utm_capture_required boolean DEFAULT true,
  whatsapp_optin_required boolean DEFAULT true,
  email_optin_required boolean DEFAULT true,
  human_review_required boolean DEFAULT true,
  publish_enabled boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llcf_launch_project_id ON launch_lead_capture_forms(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llcf_form_key ON launch_lead_capture_forms(form_key);
CREATE INDEX IF NOT EXISTS idx_llcf_form_status ON launch_lead_capture_forms(form_status);
CREATE INDEX IF NOT EXISTS idx_llcf_created_at ON launch_lead_capture_forms(created_at);

-- ---------------------------------------------------------------------------
-- 3. launch_utm_campaign_specs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_utm_campaign_specs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  channel text,
  campaign_name text,
  source text,
  medium text,
  content_angle text,
  funnel_stage text,                               -- awareness, consideration, conversion, nurture, referral
  status text DEFAULT 'draft',
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lucs_launch_project_id ON launch_utm_campaign_specs(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lucs_channel ON launch_utm_campaign_specs(channel);
CREATE INDEX IF NOT EXISTS idx_lucs_campaign_name ON launch_utm_campaign_specs(campaign_name);
CREATE INDEX IF NOT EXISTS idx_lucs_funnel_stage ON launch_utm_campaign_specs(funnel_stage);
CREATE INDEX IF NOT EXISTS idx_lucs_status ON launch_utm_campaign_specs(status);
CREATE INDEX IF NOT EXISTS idx_lucs_created_at ON launch_utm_campaign_specs(created_at);

-- ---------------------------------------------------------------------------
-- 4. launch_content_pillars
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_content_pillars (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  pillar_key text,
  pillar_name text,
  audience_segment text,
  funnel_stage text,
  core_message text,
  proof_needed text,
  draft_status text DEFAULT 'draft',
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lcp_launch_project_id ON launch_content_pillars(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lcp_pillar_key ON launch_content_pillars(pillar_key);
CREATE INDEX IF NOT EXISTS idx_lcp_funnel_stage ON launch_content_pillars(funnel_stage);
CREATE INDEX IF NOT EXISTS idx_lcp_draft_status ON launch_content_pillars(draft_status);
CREATE INDEX IF NOT EXISTS idx_lcp_created_at ON launch_content_pillars(created_at);

-- ---------------------------------------------------------------------------
-- 5. launch_message_templates (DRAFT copy only; send disabled)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_message_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  channel text,                                    -- whatsapp, email, instagram, youtube_shorts, phone_call, referral
  template_key text,
  template_type text,                              -- awareness, pre_launch_interest, brochure_request, site_visit_interest, investor_angle, nri_angle, follow_up, launch_day
  target_segment_key text,
  funnel_stage text,
  template_status text DEFAULT 'draft',            -- draft, needs_review, approved, archived
  subject text,
  body text,
  cta text,
  personalization_fields jsonb DEFAULT '[]'::jsonb,
  consent_required boolean DEFAULT true,
  suppression_check_required boolean DEFAULT true,
  human_review_required boolean DEFAULT true,
  send_enabled boolean DEFAULT false,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lmt_launch_project_id ON launch_message_templates(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lmt_channel ON launch_message_templates(channel);
CREATE INDEX IF NOT EXISTS idx_lmt_template_key ON launch_message_templates(template_key);
CREATE INDEX IF NOT EXISTS idx_lmt_target_segment_key ON launch_message_templates(target_segment_key);
CREATE INDEX IF NOT EXISTS idx_lmt_funnel_stage ON launch_message_templates(funnel_stage);
CREATE INDEX IF NOT EXISTS idx_lmt_template_status ON launch_message_templates(template_status);
CREATE INDEX IF NOT EXISTS idx_lmt_created_at ON launch_message_templates(created_at);

-- ---------------------------------------------------------------------------
-- 6. launch_social_content_drafts (DRAFT only; publish disabled)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_social_content_drafts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  platform text,                                   -- instagram_reel, instagram_story, youtube_short, linkedin, facebook
  content_key text,
  content_type text,                               -- teaser, educational, location_angle, investment_angle, countdown, launch_update, faq, referral
  target_segment_key text,
  funnel_stage text,
  draft_status text DEFAULT 'draft',               -- draft, needs_review, approved, scheduled, published, archived
  hook text,
  caption text,
  visual_direction text,
  cta text,
  hashtags text,
  publish_enabled boolean DEFAULT false,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lscd_launch_project_id ON launch_social_content_drafts(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_lscd_platform ON launch_social_content_drafts(platform);
CREATE INDEX IF NOT EXISTS idx_lscd_content_key ON launch_social_content_drafts(content_key);
CREATE INDEX IF NOT EXISTS idx_lscd_target_segment_key ON launch_social_content_drafts(target_segment_key);
CREATE INDEX IF NOT EXISTS idx_lscd_funnel_stage ON launch_social_content_drafts(funnel_stage);
CREATE INDEX IF NOT EXISTS idx_lscd_draft_status ON launch_social_content_drafts(draft_status);
CREATE INDEX IF NOT EXISTS idx_lscd_created_at ON launch_social_content_drafts(created_at);

-- ---------------------------------------------------------------------------
-- 7. launch_lead_scoring_rules
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_lead_scoring_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  rule_key text,
  rule_status text DEFAULT 'draft',
  signal_type text,                                -- budget, configuration_interest, location_interest, timeframe, site_visit_request, brochure_request, returning_lead, owner_referral, nri, investor
  score_delta integer,
  priority_label text,                             -- cold, warm, hot, urgent
  safe_summary text,
  human_review_required boolean DEFAULT true,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llsr_launch_project_id ON launch_lead_scoring_rules(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_llsr_rule_key ON launch_lead_scoring_rules(rule_key);
CREATE INDEX IF NOT EXISTS idx_llsr_rule_status ON launch_lead_scoring_rules(rule_status);
CREATE INDEX IF NOT EXISTS idx_llsr_created_at ON launch_lead_scoring_rules(created_at);

-- ---------------------------------------------------------------------------
-- 8. launch_draft_review_items (human review queue)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS launch_draft_review_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  launch_project_id uuid REFERENCES launch_projects(id),
  landing_page_spec_id uuid REFERENCES launch_landing_page_specs(id),
  lead_capture_form_id uuid REFERENCES launch_lead_capture_forms(id),
  utm_campaign_spec_id uuid REFERENCES launch_utm_campaign_specs(id),
  content_pillar_id uuid REFERENCES launch_content_pillars(id),
  message_template_id uuid REFERENCES launch_message_templates(id),
  social_content_draft_id uuid REFERENCES launch_social_content_drafts(id),
  lead_scoring_rule_id uuid REFERENCES launch_lead_scoring_rules(id),
  review_type text,                                -- landing_page_review, lead_form_review, utm_review, content_pillar_review, whatsapp_copy_review, email_copy_review, social_copy_review, lead_scoring_review, compliance_review, consent_review, project_name_review
  status text DEFAULT 'pending',                   -- pending, approved, rejected, needs_more_info, skipped
  priority text DEFAULT 'normal',
  assigned_to text,
  reviewed_by text,
  reviewed_at timestamptz,
  decision_notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ldri_launch_project_id ON launch_draft_review_items(launch_project_id);
CREATE INDEX IF NOT EXISTS idx_ldri_review_type ON launch_draft_review_items(review_type);
CREATE INDEX IF NOT EXISTS idx_ldri_status ON launch_draft_review_items(status);
CREATE INDEX IF NOT EXISTS idx_ldri_created_at ON launch_draft_review_items(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (project pattern: set_updated_at() from 001_initial_schema.sql).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_launch_landing_page_specs_updated_at ON launch_landing_page_specs;
CREATE TRIGGER trg_launch_landing_page_specs_updated_at
BEFORE UPDATE ON launch_landing_page_specs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_lead_capture_forms_updated_at ON launch_lead_capture_forms;
CREATE TRIGGER trg_launch_lead_capture_forms_updated_at
BEFORE UPDATE ON launch_lead_capture_forms FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_utm_campaign_specs_updated_at ON launch_utm_campaign_specs;
CREATE TRIGGER trg_launch_utm_campaign_specs_updated_at
BEFORE UPDATE ON launch_utm_campaign_specs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_content_pillars_updated_at ON launch_content_pillars;
CREATE TRIGGER trg_launch_content_pillars_updated_at
BEFORE UPDATE ON launch_content_pillars FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_message_templates_updated_at ON launch_message_templates;
CREATE TRIGGER trg_launch_message_templates_updated_at
BEFORE UPDATE ON launch_message_templates FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_social_content_drafts_updated_at ON launch_social_content_drafts;
CREATE TRIGGER trg_launch_social_content_drafts_updated_at
BEFORE UPDATE ON launch_social_content_drafts FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_lead_scoring_rules_updated_at ON launch_lead_scoring_rules;
CREATE TRIGGER trg_launch_lead_scoring_rules_updated_at
BEFORE UPDATE ON launch_lead_scoring_rules FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_launch_draft_review_items_updated_at ON launch_draft_review_items;
CREATE TRIGGER trg_launch_draft_review_items_updated_at
BEFORE UPDATE ON launch_draft_review_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Read-only dashboards. The message/social views deliberately OMIT full body/caption.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_launch_landing_page_dashboard AS
SELECT p.launch_key, s.page_key, s.page_title, s.page_slug, s.page_status, s.form_goal,
       s.rera_disclaimer_required, s.project_name_confirmation_required,
       s.human_review_required, s.publish_enabled
FROM launch_landing_page_specs s
JOIN launch_projects p ON p.id = s.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_lead_capture_form_dashboard AS
SELECT p.launch_key, f.form_key, f.form_status, f.form_goal,
       jsonb_array_length(f.required_fields) AS required_field_count,
       jsonb_array_length(f.qualification_questions) AS qualification_question_count,
       jsonb_array_length(f.consent_fields) AS consent_field_count,
       f.utm_capture_required, f.whatsapp_optin_required, f.email_optin_required,
       f.human_review_required, f.publish_enabled
FROM launch_lead_capture_forms f
JOIN launch_projects p ON p.id = f.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_utm_campaign_dashboard AS
SELECT p.launch_key, u.channel, u.campaign_name, u.source, u.medium, u.content_angle,
       u.funnel_stage, u.status
FROM launch_utm_campaign_specs u
JOIN launch_projects p ON p.id = u.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_content_pillar_dashboard AS
SELECT p.launch_key, cp.pillar_key, cp.pillar_name, cp.audience_segment, cp.funnel_stage,
       cp.proof_needed, cp.draft_status, cp.human_review_required
FROM launch_content_pillars cp
JOIN launch_projects p ON p.id = cp.launch_project_id;

-- Message templates: metadata + length indicators only; full body/subject NOT exposed.
CREATE OR REPLACE VIEW vw_launch_message_template_dashboard AS
SELECT p.launch_key, t.channel, t.template_key, t.template_type, t.target_segment_key,
       t.funnel_stage, t.template_status, t.cta,
       (t.subject IS NOT NULL) AS has_subject,
       char_length(coalesce(t.body, '')) AS body_char_count,
       t.consent_required, t.suppression_check_required, t.human_review_required, t.send_enabled
FROM launch_message_templates t
JOIN launch_projects p ON p.id = t.launch_project_id;

-- Social drafts: metadata + length indicators only; full caption NOT exposed.
CREATE OR REPLACE VIEW vw_launch_social_content_dashboard AS
SELECT p.launch_key, sc.platform, sc.content_key, sc.content_type, sc.target_segment_key,
       sc.funnel_stage, sc.draft_status, sc.cta,
       char_length(coalesce(sc.caption, '')) AS caption_char_count,
       sc.human_review_required, sc.publish_enabled
FROM launch_social_content_drafts sc
JOIN launch_projects p ON p.id = sc.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_lead_scoring_dashboard AS
SELECT p.launch_key, r.rule_key, r.rule_status, r.signal_type, r.score_delta,
       r.priority_label, r.safe_summary, r.human_review_required
FROM launch_lead_scoring_rules r
JOIN launch_projects p ON p.id = r.launch_project_id;

CREATE OR REPLACE VIEW vw_launch_draft_review_queue AS
SELECT p.launch_key, ri.id AS review_item_id, ri.review_type, ri.status, ri.priority,
       ri.assigned_to, ri.created_at
FROM launch_draft_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id;

-- DLF funnel readiness rollup. ready_for_launch_push is a REAL gate (true only when no
-- consent/name blocker is outstanding AND at least one send- and one publish-enabled asset
-- exist). Phase 7.1 keeps send/publish at 0, so it evaluates false.
CREATE OR REPLACE VIEW vw_dlf_launch_funnel_readiness AS
WITH agg AS (
  SELECT
    p.id, p.launch_key,
    (SELECT count(*) FROM launch_landing_page_specs s WHERE s.launch_project_id = p.id) AS landing_pages,
    (SELECT count(*) FROM launch_lead_capture_forms f WHERE f.launch_project_id = p.id) AS lead_forms,
    (SELECT count(*) FROM launch_utm_campaign_specs u WHERE u.launch_project_id = p.id) AS utm_specs,
    (SELECT count(*) FROM launch_content_pillars cp WHERE cp.launch_project_id = p.id) AS content_pillars,
    (SELECT count(*) FROM launch_message_templates t WHERE t.launch_project_id = p.id) AS message_templates,
    (SELECT count(*) FROM launch_social_content_drafts sc WHERE sc.launch_project_id = p.id) AS social_drafts,
    (SELECT count(*) FROM launch_lead_scoring_rules r WHERE r.launch_project_id = p.id) AS lead_scoring_rules,
    (SELECT count(*) FROM launch_draft_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'pending') AS pending_reviews,
    (SELECT count(*) FROM launch_draft_review_items ri WHERE ri.launch_project_id = p.id AND ri.status = 'approved') AS approved_reviews,
    (SELECT count(*) FROM launch_message_templates t WHERE t.launch_project_id = p.id AND t.send_enabled) AS msg_send_enabled,
    (SELECT count(*) FROM launch_landing_page_specs s WHERE s.launch_project_id = p.id AND s.publish_enabled) AS lp_pub_enabled,
    (SELECT count(*) FROM launch_lead_capture_forms f WHERE f.launch_project_id = p.id AND f.publish_enabled) AS form_pub_enabled,
    (SELECT count(*) FROM launch_social_content_drafts sc WHERE sc.launch_project_id = p.id AND sc.publish_enabled) AS social_pub_enabled,
    (SELECT count(*) FROM launch_readiness_checks rc WHERE rc.launch_project_id = p.id
       AND rc.check_type = 'consent_ready' AND rc.check_status IN ('pending','failed','needs_review')) AS consent_blockers,
    (SELECT count(*) FROM launch_readiness_checks rc WHERE rc.launch_project_id = p.id
       AND rc.check_type = 'project_name_confirmed' AND rc.check_status IN ('pending','failed','needs_review')) AS project_name_blockers
  FROM launch_projects p
)
SELECT
  launch_key, landing_pages, lead_forms, utm_specs, content_pillars, message_templates,
  social_drafts, lead_scoring_rules, pending_reviews, approved_reviews,
  msg_send_enabled AS send_enabled_count,
  (lp_pub_enabled + form_pub_enabled + social_pub_enabled) AS publish_enabled_count,
  consent_blockers, project_name_blockers,
  (consent_blockers = 0 AND project_name_blockers = 0
     AND msg_send_enabled > 0 AND (lp_pub_enabled + form_pub_enabled + social_pub_enabled) > 0) AS ready_for_launch_push,
  CASE
    WHEN project_name_blockers > 0 THEN 'project name not confirmed (operator must verify DLF Westend vs The Westpark)'
    WHEN consent_blockers > 0 THEN 'consent/permission not confirmed for outreach'
    WHEN msg_send_enabled = 0 THEN 'no message template send-enabled (sends intentionally disabled this phase)'
    WHEN (lp_pub_enabled + form_pub_enabled + social_pub_enabled) = 0 THEN 'nothing publish-enabled (publishing intentionally disabled this phase)'
    ELSE 'ready'
  END AS blocked_reason
FROM agg;
