# Growth, SEO, Content & Lead Pipeline (Phase 6.0)

This is the **foundation** for Real Deal Housing OS's growth engine: schema, read-only
dashboards, a fake end-to-end test workflow, and this doc. It is deliberately
inert — **nothing here publishes to Wix or any channel, and nothing sends WhatsApp /
SMS / email**. It exists so that lead generation, SEO, content, and (much later)
consented outreach can be built on a reviewed, traceable data model.

> **Phase 6.0 is foundation only.** No external publishing. No outreach. No external
> API calls. Outreach is triple-gated: `campaign_drafts.send_enabled` defaults to
> `false`, consent lives in `channel_permissions`, and suppression lives in
> `outreach_suppression_list`. AI work lands in `ai_agent_tasks` with
> `human_review_required` defaulting to `true`.

## How it fits into Real Deal Housing OS

The earlier milestones built the **system of record**:

- Milestone 1 — source-aware imports → review → canonical contacts.
- Milestone 2B — owner/unit rows → canonical contacts → active owner relationships.

Phase 6.0 adds the **system of growth** in front of it. The website and social
channels attract people; their interest is captured as `inbound_leads`; a human
reviews each lead; only then (in a future phase) does a lead become a canonical
`contact`. The growth layer references the record layer (`buildings`, `contacts`,
`source_files`, `content_items`) but never mutates it automatically.

```
   SEO pages / blogs / social ──┐
   (building_web_profiles,       │  attract
    seo_keywords, content_briefs,│
    content_publishing_queue)    ▼
            Wix site / portals ── inbound_leads ── review ──> (future) contacts
                     ▲                  │
        attribution  │                  │ consent + suppression gate
   (lead_attribution_events)            ▼
                              channel_permissions / outreach_suppression_list
                                         │
                                         ▼
                              campaign_drafts (send_enabled = false)
```

## The Wix website's role

Wix is the **public front end**: building/project pages, area guides, and a blog,
plus lead-capture forms. Phase 6.0 only *models* Wix — `building_web_profiles` and
`content_publishing_queue` carry `wix_page_id` / `wix_item_id` / `published_url`
fields that a **future** n8n→Wix integration will fill in. No Wix API is called now.

## Building SEO pages — `building_web_profiles`

A marketing/SEO profile layered on top of a canonical `buildings` row (one profile
per page/type via `page_type`: `building_page`, `rent_page`, `sale_page`,
`guide_page`, `blog_cluster`). Holds `profile_slug`, `meta_title`,
`meta_description`, `h1`, `target_audience`, `canonical_url`, and the Wix
identifiers. `seo_status` moves `draft → research_needed → ready_for_review →
approved → published → needs_update → archived`.

## Keyword tracking — `seo_keywords`

Building-level and long-tail keyword targets, linked to a building and/or a web
profile. Captures `keyword_type` (building_name, rent, sale, review, location,
configuration, broker, long_tail), `intent`, `priority`, `difficulty_estimate`, and
a `status` lifecycle (`planned → researching → content_brief_ready → drafted →
published → monitoring → paused`).

## Content briefs — `content_briefs`

The plan for a page or blog **before** drafting: `content_type`, `title`, `slug`,
`target_keyword`, `search_intent`, a JSON `outline`, plus `research_status` and
`approval_status`. A brief links to its building, web profile, and primary keyword.

## Publishing queue — `content_publishing_queue`

Where approved content waits to be published to a `channel` (wix_blog, wix_page,
instagram, facebook, linkedin, youtube, google_business_profile). References both a
`content_brief` (the plan) and a `content_items` row (the existing content asset
store). `publish_status` is `draft → ready_for_review → approved → scheduled →
published → failed → paused`. **Nothing advances past `draft`/`ready_for_review`
automatically in this phase.**

## Inbound lead capture — `inbound_lead_sources` + `inbound_leads`

`inbound_lead_sources` defines where leads come from (wix_form, website_chat,
instagram_dm, facebook_lead, google_business_profile, magicbricks, housing,
whatsapp, manual, referral). `inbound_leads` is the **landing zone** for fresh leads
*before* canonical contact creation. It stores only a masked name hint
(`lead_name_masked`), intent, area/city, budget range, preferred channel, and
`consent_status` — the raw submission goes in `raw_payload` and is never surfaced by
the dashboards.

> **Distinct from `lead_requirements`:** that existing table holds requirements
> parsed from *imported* contacts (import-tied). `inbound_leads` is for *new*
> web/social/portal capture and is reviewed before becoming a contact.

## Attribution — `lead_attribution_events`

The trail from a page/campaign/source to a lead: `event_type` (page_view,
form_submit, call_click, whatsapp_click, social_dm, listing_inquiry), `campaign_name`,
UTM fields, `landing_page`, `referrer`. Lets us answer "which page/keyword/campaign
produced this lead".

## Consent & channel permissions — `channel_permissions`

Per-channel consent groundwork for a contact or inbound lead: `channel` (email,
whatsapp, sms, phone, instagram, facebook, linkedin) and `permission_status`
(unknown, allowed, opted_in, opted_out, do_not_contact, invalid) with a
`consent_source` and `consent_timestamp`. **No outreach may occur without an explicit
allow/opt-in here** (enforced by future send logic, not by this phase).

## Suppression — `outreach_suppression_list`

Global do-not-contact / suppression controls (optionally per `channel`), with a
`reason` and `status`. A suppression entry always wins over any permission.

## Campaign drafts — `campaign_drafts`

Campaign **planning only**: `campaign_type` (email_drip, whatsapp_broadcast,
owner_reactivation, tenant_requirement, newsletter, listing_alert), `target_segment`,
`channel`, `message_template`, and a `status` lifecycle. Two safety flags:
`consent_required` defaults `true`, and `send_enabled` defaults `false`. **Nothing in
Phase 6.0 flips `send_enabled` to true**, and there is no send pipeline yet.

## AI agent task queue — `ai_agent_tasks`

A queue for future AI research/content/SEO/lead-enrichment work: `task_type`
(building_research, keyword_research, blog_brief, content_draft, seo_monitoring,
lead_enrichment, duplicate_review_assist), a generic `entity_type`/`entity_id`
target, `status`, `prompt_summary`/`result_summary`, and `raw_input`/`raw_output`
JSON. `human_review_required` defaults `true` so AI output is always reviewed before
it affects anything.

## Dashboards (read-only, masked)

Open these in NocoDB (host `postgres`, db `realdeal_os`, schema `public`):

| View | Shows |
| ---- | ----- |
| `vw_growth_pipeline_home` | One-row overview: totals + per-status JSON breakdowns for every stage, plus `communications_enabled_count` and `communications_sent_count` (both 0). |
| `vw_seo_keyword_dashboard` | Keywords with building, intent, status, and brief/published counts. |
| `vw_content_pipeline_dashboard` | Briefs joined to their latest publishing-queue status/channel/URL. |
| `vw_inbound_lead_review_queue` | Leads with source, intent, area/city, budget, consent — masked name hint only, no phone/email. |
| `vw_channel_permission_dashboard` | Per-channel permission status + effective suppression status (IDs only, no contact values). |
| `vw_campaign_readiness_dashboard` | Campaigns with `send_enabled`, a safe placeholder `eligible_recipient_count` (0), and a `blocked_reason`. |
| `vw_ai_agent_task_dashboard` | AI tasks with type, status, priority, summaries (no raw private data). |

## Fake test workflow

A self-contained, reversible end-to-end exercise of every table — **fake data only**:

```bash
python3 scripts/seed_fake_growth_pipeline.py                 # dry-run (default)
python3 scripts/seed_fake_growth_pipeline.py --apply --fake-ok
python3 scripts/growth_pipeline_summary.py                   # counts only
python3 scripts/cleanup_fake_growth_pipeline.py              # dry-run (default)
python3 scripts/cleanup_fake_growth_pipeline.py --apply
```

Every fake row is tagged `fake_batch='FAKE_PHASE_6_0_GROWTH_PIPELINE'`, `phase='6.0'`,
`is_test=true`. Cleanup deletes **only** those tagged rows (FK-safe order) and never
touches real contacts, buildings, leads, or source rows. The fake lead is not linked
to any real contact.

## First real plan (Phase 6.1)

The first real, review-gated SEO/content plan was created for **Imperial Heights**
(Goregaon West) using `scripts/apply_real_building_seo_plan.py` (dry-run default;
`--real-ok` + `--apply` to write) and is reversible via
`scripts/cleanup_real_building_seo_plan.py`. It added 1 web profile, 10 keywords,
3 content briefs, 3 draft publishing rows, and 5 queued AI tasks — **no external
calls, no publishing, no outreach**. See `docs/PHASE_6_1_IMPERIAL_HEIGHTS_SEO_PLAN.md`.

## Wix CMS readiness (Phase 6.2)

Phase 6.2 added the Wix-publishing **readiness** layer (migration 013): `wix_cms_collections`
+ `wix_cms_field_mappings` (how Real Deal OS fields map to Wix CMS), `content_review_items`
(human review queue for briefs), and `publishing_readiness_checks` (pre-publish checklist).
Dashboards: `vw_wix_cms_mapping_dashboard`, `vw_content_review_dashboard`,
`vw_publishing_readiness_dashboard`, `vw_imperial_heights_content_plan`. A publishing row
becomes `ready_for_publish` only when every readiness check passes **and** its
`publish_status` is approved/ready_for_review — and even then publishing is a separate,
future, guarded step. Built via `scripts/prepare_wix_content_review.py` (reversible with
`scripts/cleanup_wix_content_review.py`). **Still no Wix calls, no publishing, no outreach.**
See `docs/PHASE_6_2_WIX_CMS_CONTENT_REVIEW_PLAN.md`.

## What is NOT done yet

- **No publishing.** No Wix/social/blog content is pushed anywhere.
- **No outreach.** No WhatsApp/SMS/email/calls. `send_enabled` stays `false`.
- **No external API calls.** Wix and channel identifiers are placeholders.
- **No automated contact creation.** Inbound leads are reviewed by a human first.

## Future n8n / Wix integration (later phases)

- n8n workflows will read `content_publishing_queue` (status `approved`/`scheduled`)
  and publish to Wix, then write back `published_url` / `wix_item_id` / `published_at`.
- Wix forms and social webhooks will create `inbound_leads` + `lead_attribution_events`
  via n8n.
- A consent-checked segment engine will compute real `eligible_recipient_count`s and
  only then may a campaign's `send_enabled` be turned on — guarded, reviewed, and
  honouring `channel_permissions` and `outreach_suppression_list`.
