-- Phase 6.0: Growth, SEO, content, and lead-pipeline foundation.
--
-- Foundation only: schema + read-only dashboard views. NOTHING here publishes to
-- Wix or any channel, and NOTHING sends WhatsApp/SMS/email. Outreach is gated by
-- explicit, default-off flags (campaign_drafts.send_enabled = false) plus the
-- consent (channel_permissions) and suppression (outreach_suppression_list) tables
-- defined below. All AI work lands in ai_agent_tasks with human_review_required
-- defaulting to true.
--
-- Relationship to existing schema (see Task B inspection):
--   * buildings        — canonical building/project anchor; building_web_profiles
--                        adds a marketing/SEO layer on top (1 profile per page/type).
--   * content_items    — existing content store; content_publishing_queue references
--                        both a content_brief (planning) and a content_item (asset).
--   * lead_requirements — parsed requirements from IMPORTED contacts (import-tied).
--                        inbound_leads is a SEPARATE landing zone for fresh web/social/
--                        portal leads captured BEFORE canonical contact creation.
--   * tasks            — operational human task list; ai_agent_tasks is a distinct
--                        AI research/content/SEO/enrichment queue.
--
-- Idempotent: CREATE ... IF NOT EXISTS throughout, safe to re-run via apply_schema.sh.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. building_web_profiles — marketing/SEO profile for a canonical building.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS building_web_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  profile_slug text,
  building_name text,
  area text,
  city text,
  developer text,
  canonical_url text,
  wix_page_id text,
  wix_collection_item_id text,
  seo_status text DEFAULT 'draft',          -- draft, research_needed, ready_for_review, approved, published, needs_update, archived
  page_type text,                            -- building_page, rent_page, sale_page, guide_page, blog_cluster
  target_audience text,
  meta_title text,
  meta_description text,
  h1 text,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bwp_building_id ON building_web_profiles(building_id);
CREATE INDEX IF NOT EXISTS idx_bwp_seo_status ON building_web_profiles(seo_status);
CREATE INDEX IF NOT EXISTS idx_bwp_page_type ON building_web_profiles(page_type);
CREATE INDEX IF NOT EXISTS idx_bwp_profile_slug ON building_web_profiles(profile_slug);
CREATE INDEX IF NOT EXISTS idx_bwp_created_at ON building_web_profiles(created_at);

-- ---------------------------------------------------------------------------
-- 2. seo_keywords — building-level and long-tail keyword targets.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seo_keywords (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  building_web_profile_id uuid REFERENCES building_web_profiles(id),
  keyword text NOT NULL,
  keyword_type text,                         -- building_name, rent, sale, review, location, configuration, broker, long_tail
  target_city text,
  target_area text,
  priority text DEFAULT 'normal',
  difficulty_estimate text,
  intent text,                               -- rent, buy, sell, research, broker, availability
  status text DEFAULT 'planned',             -- planned, researching, content_brief_ready, drafted, published, monitoring, paused
  source text,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_building_id ON seo_keywords(building_id);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_profile_id ON seo_keywords(building_web_profile_id);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_keyword ON seo_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_status ON seo_keywords(status);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_intent ON seo_keywords(intent);
CREATE INDEX IF NOT EXISTS idx_seo_keywords_created_at ON seo_keywords(created_at);

-- ---------------------------------------------------------------------------
-- 3. content_briefs — briefs for blogs/building pages before drafting.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_briefs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  building_id uuid REFERENCES buildings(id),
  building_web_profile_id uuid REFERENCES building_web_profiles(id),
  primary_keyword_id uuid REFERENCES seo_keywords(id),
  content_type text,                         -- building_page, blog, faq, area_guide, comparison, listing_page
  title text,
  slug text,
  target_keyword text,
  search_intent text,
  outline jsonb DEFAULT '{}'::jsonb,
  research_status text DEFAULT 'pending',
  approval_status text DEFAULT 'draft',
  assigned_to text,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_content_briefs_building_id ON content_briefs(building_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_profile_id ON content_briefs(building_web_profile_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_primary_keyword_id ON content_briefs(primary_keyword_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_research_status ON content_briefs(research_status);
CREATE INDEX IF NOT EXISTS idx_content_briefs_approval_status ON content_briefs(approval_status);
CREATE INDEX IF NOT EXISTS idx_content_briefs_created_at ON content_briefs(created_at);

-- ---------------------------------------------------------------------------
-- 4. content_publishing_queue — queue for Wix/social/blog publishing later.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_publishing_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_brief_id uuid REFERENCES content_briefs(id),
  content_item_id uuid REFERENCES content_items(id),
  channel text,                              -- wix_blog, wix_page, instagram, facebook, linkedin, youtube, google_business_profile
  publish_status text DEFAULT 'draft',       -- draft, ready_for_review, approved, scheduled, published, failed, paused
  scheduled_for timestamptz,
  published_at timestamptz,
  published_url text,
  wix_item_id text,
  error_message text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cpq_content_brief_id ON content_publishing_queue(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_cpq_content_item_id ON content_publishing_queue(content_item_id);
CREATE INDEX IF NOT EXISTS idx_cpq_channel ON content_publishing_queue(channel);
CREATE INDEX IF NOT EXISTS idx_cpq_publish_status ON content_publishing_queue(publish_status);
CREATE INDEX IF NOT EXISTS idx_cpq_created_at ON content_publishing_queue(created_at);

-- ---------------------------------------------------------------------------
-- 5. inbound_lead_sources — definitions of future lead sources.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inbound_lead_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name text NOT NULL,
  source_type text,                          -- wix_form, website_chat, instagram_dm, facebook_lead, google_business_profile, magicbricks, housing, whatsapp, manual, referral
  channel text,
  status text DEFAULT 'active',
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ils_source_type ON inbound_lead_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_ils_channel ON inbound_lead_sources(channel);
CREATE INDEX IF NOT EXISTS idx_ils_status ON inbound_lead_sources(status);
CREATE INDEX IF NOT EXISTS idx_ils_created_at ON inbound_lead_sources(created_at);

-- ---------------------------------------------------------------------------
-- 6. inbound_leads — landing zone for new leads before canonical contact creation.
--    lead_name_masked holds only a masked hint (never a raw full name). raw_payload
--    may hold the source's raw fields; dashboard views never expose it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inbound_leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid REFERENCES inbound_lead_sources(id),
  source_file_id uuid REFERENCES source_files(id),
  contact_id uuid REFERENCES contacts(id),
  related_building_id uuid REFERENCES buildings(id),
  related_building_web_profile_id uuid REFERENCES building_web_profiles(id),
  lead_name_masked text,
  lead_status text DEFAULT 'new',            -- new, needs_review, reviewed, converted_to_contact, duplicate, rejected, spam, archived
  lead_intent text,                          -- rent, buy, sell, list_property, owner_contact, tenant_contact, general_inquiry
  property_type text,
  area text,
  city text,
  budget_min numeric,
  budget_max numeric,
  preferred_channel text,
  consent_status text DEFAULT 'unknown',     -- unknown, implied, explicit, opted_out, do_not_contact
  raw_payload jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_source_id ON inbound_leads(source_id);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_source_file_id ON inbound_leads(source_file_id);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_contact_id ON inbound_leads(contact_id);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_building_id ON inbound_leads(related_building_id);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_lead_status ON inbound_leads(lead_status);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_lead_intent ON inbound_leads(lead_intent);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_consent_status ON inbound_leads(consent_status);
CREATE INDEX IF NOT EXISTS idx_inbound_leads_created_at ON inbound_leads(created_at);

-- ---------------------------------------------------------------------------
-- 7. lead_attribution_events — attribution trail from page/campaign/source to lead.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_attribution_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  inbound_lead_id uuid REFERENCES inbound_leads(id),
  source_id uuid REFERENCES inbound_lead_sources(id),
  building_web_profile_id uuid REFERENCES building_web_profiles(id),
  content_brief_id uuid REFERENCES content_briefs(id),
  event_type text,                           -- page_view, form_submit, call_click, whatsapp_click, social_dm, listing_inquiry
  campaign_name text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  landing_page text,
  referrer text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lae_inbound_lead_id ON lead_attribution_events(inbound_lead_id);
CREATE INDEX IF NOT EXISTS idx_lae_source_id ON lead_attribution_events(source_id);
CREATE INDEX IF NOT EXISTS idx_lae_profile_id ON lead_attribution_events(building_web_profile_id);
CREATE INDEX IF NOT EXISTS idx_lae_content_brief_id ON lead_attribution_events(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_lae_event_type ON lead_attribution_events(event_type);
CREATE INDEX IF NOT EXISTS idx_lae_created_at ON lead_attribution_events(created_at);

-- ---------------------------------------------------------------------------
-- 8. channel_permissions — consent/channel-permission groundwork before outreach.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS channel_permissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id),
  inbound_lead_id uuid REFERENCES inbound_leads(id),
  channel text NOT NULL,                     -- email, whatsapp, sms, phone, instagram, facebook, linkedin
  permission_status text DEFAULT 'unknown',  -- unknown, allowed, opted_in, opted_out, do_not_contact, invalid
  consent_source text,
  consent_timestamp timestamptz,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chperm_contact_id ON channel_permissions(contact_id);
CREATE INDEX IF NOT EXISTS idx_chperm_inbound_lead_id ON channel_permissions(inbound_lead_id);
CREATE INDEX IF NOT EXISTS idx_chperm_channel ON channel_permissions(channel);
CREATE INDEX IF NOT EXISTS idx_chperm_permission_status ON channel_permissions(permission_status);
CREATE INDEX IF NOT EXISTS idx_chperm_created_at ON channel_permissions(created_at);

-- ---------------------------------------------------------------------------
-- 9. outreach_suppression_list — global do-not-contact/suppression controls.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_suppression_list (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id uuid REFERENCES contacts(id),
  inbound_lead_id uuid REFERENCES inbound_leads(id),
  channel text,
  reason text,
  status text DEFAULT 'active',
  created_by text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_suppress_contact_id ON outreach_suppression_list(contact_id);
CREATE INDEX IF NOT EXISTS idx_suppress_inbound_lead_id ON outreach_suppression_list(inbound_lead_id);
CREATE INDEX IF NOT EXISTS idx_suppress_channel ON outreach_suppression_list(channel);
CREATE INDEX IF NOT EXISTS idx_suppress_status ON outreach_suppression_list(status);
CREATE INDEX IF NOT EXISTS idx_suppress_created_at ON outreach_suppression_list(created_at);

-- ---------------------------------------------------------------------------
-- 10. campaign_drafts — campaign planning only. send_enabled defaults FALSE; nothing
--     in this phase flips it. consent_required defaults TRUE.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_drafts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_name text NOT NULL,
  campaign_type text,                        -- email_drip, whatsapp_broadcast, owner_reactivation, tenant_requirement, newsletter, listing_alert
  target_segment text,
  channel text,
  status text DEFAULT 'draft',               -- draft, ready_for_review, approved, paused, archived
  content_brief_id uuid REFERENCES content_briefs(id),
  message_template text,
  consent_required boolean DEFAULT true,
  send_enabled boolean DEFAULT false,
  notes text,
  raw_context jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_content_brief_id ON campaign_drafts(content_brief_id);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_channel ON campaign_drafts(channel);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_status ON campaign_drafts(status);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_send_enabled ON campaign_drafts(send_enabled);
CREATE INDEX IF NOT EXISTS idx_campaign_drafts_created_at ON campaign_drafts(created_at);

-- ---------------------------------------------------------------------------
-- 11. ai_agent_tasks — future AI agent task queue. human_review_required defaults TRUE.
--     entity_id is a generic uuid (no FK) so it can point at any entity_type.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_agent_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type text,                            -- building_research, keyword_research, blog_brief, content_draft, seo_monitoring, lead_enrichment, duplicate_review_assist
  entity_type text,                          -- building, contact, lead, content_brief, keyword, campaign
  entity_id uuid,
  status text DEFAULT 'queued',              -- queued, running, completed, failed, needs_human_review, cancelled
  priority text DEFAULT 'normal',
  prompt_summary text,
  result_summary text,
  human_review_required boolean DEFAULT true,
  raw_input jsonb DEFAULT '{}'::jsonb,
  raw_output jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_task_type ON ai_agent_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_entity_type ON ai_agent_tasks(entity_type);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_entity_id ON ai_agent_tasks(entity_id);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON ai_agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_created_at ON ai_agent_tasks(created_at);

-- ---------------------------------------------------------------------------
-- updated_at triggers (tables that carry an updated_at column).
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_building_web_profiles_updated_at ON building_web_profiles;
CREATE TRIGGER trg_building_web_profiles_updated_at
BEFORE UPDATE ON building_web_profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_seo_keywords_updated_at ON seo_keywords;
CREATE TRIGGER trg_seo_keywords_updated_at
BEFORE UPDATE ON seo_keywords
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_briefs_updated_at ON content_briefs;
CREATE TRIGGER trg_content_briefs_updated_at
BEFORE UPDATE ON content_briefs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_content_publishing_queue_updated_at ON content_publishing_queue;
CREATE TRIGGER trg_content_publishing_queue_updated_at
BEFORE UPDATE ON content_publishing_queue
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_inbound_lead_sources_updated_at ON inbound_lead_sources;
CREATE TRIGGER trg_inbound_lead_sources_updated_at
BEFORE UPDATE ON inbound_lead_sources
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_inbound_leads_updated_at ON inbound_leads;
CREATE TRIGGER trg_inbound_leads_updated_at
BEFORE UPDATE ON inbound_leads
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_campaign_drafts_updated_at ON campaign_drafts;
CREATE TRIGGER trg_campaign_drafts_updated_at
BEFORE UPDATE ON campaign_drafts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ai_agent_tasks_updated_at ON ai_agent_tasks;
CREATE TRIGGER trg_ai_agent_tasks_updated_at
BEFORE UPDATE ON ai_agent_tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- Task D — read-only growth dashboard views. Counts/metadata only; no raw
-- personal values (names/phones/emails/addresses) are selected.
-- ===========================================================================

DROP VIEW IF EXISTS vw_growth_pipeline_home;
DROP VIEW IF EXISTS vw_seo_keyword_dashboard;
DROP VIEW IF EXISTS vw_content_pipeline_dashboard;
DROP VIEW IF EXISTS vw_inbound_lead_review_queue;
DROP VIEW IF EXISTS vw_channel_permission_dashboard;
DROP VIEW IF EXISTS vw_campaign_readiness_dashboard;
DROP VIEW IF EXISTS vw_ai_agent_task_dashboard;

-- 1. One-row growth pipeline overview. Status breakdowns are emitted as jsonb
--    objects (status -> count) so the whole pipeline fits one row.
CREATE VIEW vw_growth_pipeline_home AS
SELECT
  (SELECT count(*) FROM building_web_profiles)                                        AS building_web_profiles_total,
  (SELECT COALESCE(jsonb_object_agg(seo_status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(seo_status,'(none)') AS seo_status, count(*) c FROM building_web_profiles GROUP BY 1) s)
                                                                                       AS web_profiles_by_seo_status,
  (SELECT count(*) FROM seo_keywords)                                                 AS seo_keywords_total,
  (SELECT COALESCE(jsonb_object_agg(status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(status,'(none)') AS status, count(*) c FROM seo_keywords GROUP BY 1) s)
                                                                                       AS seo_keywords_by_status,
  (SELECT count(*) FROM content_briefs)                                               AS content_briefs_total,
  (SELECT COALESCE(jsonb_object_agg(approval_status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(approval_status,'(none)') AS approval_status, count(*) c FROM content_briefs GROUP BY 1) s)
                                                                                       AS content_briefs_by_approval_status,
  (SELECT count(*) FROM content_publishing_queue)                                     AS publishing_queue_total,
  (SELECT COALESCE(jsonb_object_agg(publish_status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(publish_status,'(none)') AS publish_status, count(*) c FROM content_publishing_queue GROUP BY 1) s)
                                                                                       AS publishing_queue_by_status,
  (SELECT count(*) FROM inbound_leads)                                                AS inbound_leads_total,
  (SELECT COALESCE(jsonb_object_agg(lead_status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(lead_status,'(none)') AS lead_status, count(*) c FROM inbound_leads GROUP BY 1) s)
                                                                                       AS inbound_leads_by_status,
  (SELECT count(*) FROM campaign_drafts)                                              AS campaign_drafts_total,
  (SELECT COALESCE(jsonb_object_agg(status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(status,'(none)') AS status, count(*) c FROM campaign_drafts GROUP BY 1) s)
                                                                                       AS campaign_drafts_by_status,
  (SELECT count(*) FROM ai_agent_tasks)                                               AS ai_agent_tasks_total,
  (SELECT COALESCE(jsonb_object_agg(status, c), '{}'::jsonb)
     FROM (SELECT COALESCE(status,'(none)') AS status, count(*) c FROM ai_agent_tasks GROUP BY 1) s)
                                                                                       AS ai_agent_tasks_by_status,
  -- Outreach posture: how many campaigns are actually send-enabled (should be 0),
  -- and how many messages have actually been sent (no send pipeline exists yet).
  (SELECT count(*) FROM campaign_drafts WHERE send_enabled = true)                    AS communications_enabled_count,
  (SELECT count(*) FROM content_publishing_queue WHERE publish_status = 'published')  AS content_published_count,
  0::bigint                                                                            AS communications_sent_count,
  now()                                                                               AS generated_at;

-- 2. SEO keyword dashboard.
CREATE VIEW vw_seo_keyword_dashboard AS
SELECT
  k.id                                                                 AS keyword_id,
  COALESCE(b.name, p.building_name)                                    AS building_name,
  k.keyword,
  k.keyword_type,
  k.intent,
  k.priority,
  k.status,
  (SELECT count(*) FROM content_briefs cb WHERE cb.primary_keyword_id = k.id)             AS content_brief_count,
  (SELECT count(*) FROM content_briefs cb
     JOIN content_publishing_queue q ON q.content_brief_id = cb.id
    WHERE cb.primary_keyword_id = k.id AND q.published_url IS NOT NULL)                    AS published_url_count,
  k.created_at
FROM seo_keywords k
LEFT JOIN buildings b ON b.id = k.building_id
LEFT JOIN building_web_profiles p ON p.id = k.building_web_profile_id;

-- 3. Content pipeline dashboard (brief joined to its latest publishing-queue row).
CREATE VIEW vw_content_pipeline_dashboard AS
SELECT
  cb.id                                                                AS content_brief_id,
  COALESCE(b.name, p.building_name)                                    AS building_name,
  cb.title,
  cb.content_type,
  cb.target_keyword,
  cb.research_status,
  cb.approval_status,
  q.publish_status                                                     AS publishing_status,
  q.channel,
  q.published_url,
  cb.created_at
FROM content_briefs cb
LEFT JOIN buildings b ON b.id = cb.building_id
LEFT JOIN building_web_profiles p ON p.id = cb.building_web_profile_id
LEFT JOIN LATERAL (
  SELECT publish_status, channel, published_url
  FROM content_publishing_queue q
  WHERE q.content_brief_id = cb.id
  ORDER BY q.created_at DESC
  LIMIT 1
) q ON true;

-- 4. Inbound lead review queue. Only a masked name hint; no phone/email.
CREATE VIEW vw_inbound_lead_review_queue AS
SELECT
  l.id                                                                 AS inbound_lead_id,
  s.source_name,
  s.source_type,
  l.lead_status,
  l.lead_intent,
  COALESCE(b.name, p.building_name)                                    AS related_building_name,
  l.area,
  l.city,
  l.budget_min,
  l.budget_max,
  l.preferred_channel,
  l.consent_status,
  l.lead_name_masked,
  l.created_at
FROM inbound_leads l
LEFT JOIN inbound_lead_sources s ON s.id = l.source_id
LEFT JOIN buildings b ON b.id = l.related_building_id
LEFT JOIN building_web_profiles p ON p.id = l.related_building_web_profile_id;

-- 5. Channel permission dashboard. IDs/status only; no contact values.
CREATE VIEW vw_channel_permission_dashboard AS
SELECT
  cp.id                                                                AS channel_permission_id,
  cp.contact_id,
  cp.inbound_lead_id,
  cp.channel,
  cp.permission_status,
  cp.consent_source,
  cp.consent_timestamp,
  (SELECT max(sl.status) FROM outreach_suppression_list sl
     WHERE sl.status = 'active'
       AND (sl.contact_id IS NOT DISTINCT FROM cp.contact_id
            OR sl.inbound_lead_id IS NOT DISTINCT FROM cp.inbound_lead_id)
       AND (sl.channel IS NULL OR sl.channel = cp.channel))            AS suppression_status,
  cp.created_at
FROM channel_permissions cp;

-- 6. Campaign readiness dashboard. send_enabled stays false; eligible recipient
--    count is a safe placeholder (0) until a real, consent-checked segment engine
--    exists. blocked_reason explains why a campaign cannot send today.
CREATE VIEW vw_campaign_readiness_dashboard AS
SELECT
  c.id                                                                 AS campaign_id,
  c.campaign_name,
  c.campaign_type,
  c.channel,
  c.status,
  c.consent_required,
  c.send_enabled,
  0::bigint                                                            AS eligible_recipient_count,
  CASE
    WHEN c.send_enabled = false                THEN 'send_disabled'
    WHEN c.status <> 'approved'                THEN 'not_approved'
    WHEN c.consent_required AND true           THEN 'consent_engine_not_built'
    ELSE 'no_send_pipeline_yet'
  END                                                                  AS blocked_reason,
  c.created_at
FROM campaign_drafts c;

-- 7. AI agent task dashboard. Summaries only; no raw private data.
CREATE VIEW vw_ai_agent_task_dashboard AS
SELECT
  t.id                                                                 AS task_id,
  t.task_type,
  t.entity_type,
  t.status,
  t.priority,
  t.human_review_required,
  t.prompt_summary,
  t.result_summary,
  t.created_at
FROM ai_agent_tasks t;
