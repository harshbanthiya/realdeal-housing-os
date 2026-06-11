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

## Content quality & AI planning (Phase 6.3)

Phase 6.3 added the content-quality and AI-execution-planning layer (migration 014):
`content_quality_checks` (per-brief checklist), `content_source_requirements`
(research/sources needed, each with a `[SOURCE URL NEEDED]` placeholder),
`ai_prompt_templates` (reusable, safety-ruled templates), and `ai_task_execution_plans`
(how each queued AI task runs later — `manual`, `external_calls_allowed=false`,
`requires_human_review=true`). `vw_imperial_heights_content_readiness` surfaces
`ready_for_ai_draft` (true only when no blocker check is open and no source requirement
is still needed) and `ready_for_publish` (false in this phase). Built via
`scripts/prepare_content_quality_plan.py` (reversible with
`scripts/cleanup_content_quality_plan.py`). **No AI execution, no external calls, no
publishing, no outreach.** See `docs/PHASE_6_3_CONTENT_QUALITY_AI_PLANNING.md`.

## Local content draft workspace (Phase 6.4)

Phase 6.4 added the internal draft workspace (migration 015): `content_draft_artifacts`
(internal, non-public outlines/notes/meta drafts — `internal_only=true`,
`public_ready=false`), `content_draft_reviews` (human review queue), and
`content_source_gap_items` (specific missing facts before drafting). Dashboards:
`vw_content_draft_artifact_dashboard`, `vw_content_draft_review_queue`,
`vw_content_source_gap_dashboard`, `vw_imperial_heights_draft_workspace`. Built via
`scripts/create_local_content_draft_artifacts.py`, optionally exported to the
git-ignored `exports/content/` by `scripts/export_content_draft_artifacts.py`, and
reversible with `scripts/cleanup_local_content_draft_artifacts.py`. Artifact bodies
are outlines/placeholders with `[SOURCE NEEDED]` markers and an
"INTERNAL DRAFT — NOT FOR PUBLISHING" header — **no AI execution, no external calls,
no publishing, no outreach.** See `docs/PHASE_6_4_LOCAL_CONTENT_DRAFT_WORKSPACE.md`.

## Source-gap resolution workflow (Phase 6.5)

Phase 6.5 added the review-gated source-gap resolution workflow (migration 016):
`source_gap_resolution_tasks` (one classified task per open gap — internal /
human / future-external; `external_calls_allowed` always false),
`internal_source_evidence` (safe **count-only** references to internal data — units,
owner relationships, aliases, source batches; no personal values), and
`source_gap_review_items` (human accept/resolve/waive queue). Dashboards:
`vw_source_gap_resolution_dashboard`, `vw_internal_source_evidence_dashboard`,
`vw_source_gap_review_queue`, `vw_imperial_heights_source_gap_status` (`ready_for_publish`
hard-coded false). Built via `scripts/plan_source_gap_resolution.py` and reversible with
`scripts/cleanup_source_gap_resolution.py`. **No gap is auto-resolved** (gaps stay open),
and there is **no AI execution, no external/web calls, no publishing, no outreach.**
See `docs/PHASE_6_5_SOURCE_GAP_RESOLUTION_WORKFLOW.md`.

## Internal evidence acceptance (Phase 6.6)

Phase 6.6 lets a human accept the purely-internal, non-personal evidence candidates from
Phase 6.5. `scripts/review_internal_source_evidence.py` sets
`internal_source_evidence.evidence_status` (accepted/rejected/needs_review) for a tiny
chosen set and moves the linked `internal_evidence_review` accordingly, tagging each
change (`evidence_review_phase=6.6`) for a clean revert via
`scripts/revert_internal_source_evidence_review.py`. Migration 017 adds two read-only
views (`vw_internal_evidence_acceptance_dashboard`, `vw_imperial_heights_evidence_readiness`;
`ready_for_publish` hard-coded false). The first batch accepted the 3 `building_alias`
rows (count-based, non-personal); `active_owner_relationship_count` is deferred pending
building dedupe and `inventory_hint` needs human review. **No gap is resolved** (still 17
open), content is **not** ready for AI/public drafting, and there is **no AI execution, no
external/web calls, no publishing, no outreach.**
See `docs/PHASE_6_6_INTERNAL_EVIDENCE_ACCEPTANCE.md`.

## Building-anchor dedupe planning (Phase 6.7)

Phase 6.7 plans the consolidation of two duplicate "Imperial Heights" building anchors
(`0e72db71` with the SEO profile/briefs vs `f05bbd01`) that split the active owner
relationships and understated the profile's evidence counts. Migration 018 adds 3 tables
(`building_duplicate_candidates`, `building_dedupe_review_items`,
`building_dedupe_action_log`) and 3 views (incl.
`vw_imperial_heights_building_anchor_summary`, `vw_building_dedupe_dashboard`).
`scripts/plan_building_dedupe.py` (dry-run default) seeds 1 `pending_review` candidate
(canonical `0e72db71`, strength `strong`) + 1 pending review item;
`scripts/plan_building_dedupe_consolidation.py` is dry-run-only and previews the move
(1 alias / 1 unit / 1 relationship). **No building is merged/deleted, no relationship
moved, no SEO/content changed, no gap resolved**, and there is **no AI execution, no
external/web calls, no publishing, no outreach.** Reversible via
`scripts/cleanup_building_dedupe_plan.py`. See `docs/PHASE_6_7_BUILDING_DEDUPE_PLANNING.md`.

## MahaRERA verification foundation (Phase 6.8)

Phase 6.8 adds the **schema + fake-workflow** foundation for future official MahaRERA
building verification (the official layer for Maharashtra/Mumbai projects) — **no
scraping, no API calls, no browsing** from scripts. Migration 019 adds 6 tables
(`rera_project_profiles`, `rera_building_match_candidates`, `rera_carpet_area_records`,
`rera_project_status_checks`, `rera_area_mismatch_candidates`,
`rera_verification_review_items`) and 6 dashboards (incl.
`vw_imperial_heights_rera_readiness`). An accepted RERA match is what will later unlock
the Phase 6.7 building dedupe; a verified profile with no blocker risk gates
content-fact use. The fake workflow (`scripts/seed_fake_rera_verification.py` /
`cleanup_fake_rera_verification.py` / `rera_verification_summary.py`) was seeded then
fully cleaned, leaving **no real building/SEO/content change, no MahaRERA/external call,
no publishing, no outreach.** RERA is an internal verification aid, not legal advice.
See `docs/RERA_VERIFICATION_PIPELINE.md`.

## Manual MahaRERA verification — Imperial Heights (Phase 6.9)

Phase 6.9 entered **real but review-gated** MahaRERA rows for Imperial Heights Wing C & D
(reg `P51800003270`) from a manually-supplied official PDF snapshot (no scraping/API):
1 profile (`needs_human_review`), 2 `candidate` building matches, 26 carpet-area records
(213 apartments), 13 status/risk/document checks (litigation/complaint/non-compliance as
counts only — **no personal names**), 6 pending review items. RERA address/lat/long are
**not** trusted (operator review); no building merged, no internal address changed, no gap
resolved, nothing verified/accepted/published/sent. Reversible via
`scripts/cleanup_manual_rera_verification.py`. See
`docs/PHASE_6_9_MANUAL_RERA_IMPERIAL_HEIGHTS.md`.

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

## Launch command center (Phase 7.0)

For time-sensitive launches, a **project layer** sits on top of these growth tables.
Migration `schemas/021_launch_command_center.sql` adds `launch_projects`, `launch_channels`,
`launch_campaign_calendar`, `launch_lead_segments` (counts only — never raw contacts),
`launch_operator_tasks`, and `launch_readiness_checks`, plus 7 dashboards (incl.
`vw_dlf_launch_priority_dashboard`). A launch's `launch_campaign_calendar` items can link to
`content_briefs` and `campaign_drafts`; segments are described as counts with per-channel
`whatsapp_allowed_count` / `email_allowed_count` / `suppressed_count`. **All send/publish flags
default false and readiness gates default pending** — `ready_for_launch_push` only turns true
when no blocker is outstanding, the project name is confirmed, and a channel is explicitly
send- AND publish-enabled. The first seeded launch is the review-gated DLF workspace
(`dlf-westpark-andheri-west`); see `docs/PHASE_7_0_DLF_LAUNCH_COMMAND_CENTER.md`. No sends,
publishing, external calls, or contact selection happen at the foundation stage.

## Launch funnel workspace (Phase 7.1)

On top of the launch command center, `schemas/022_launch_funnel_workspace.sql` adds the full
funnel draft workspace: `launch_landing_page_specs`, `launch_lead_capture_forms`,
`launch_utm_campaign_specs`, `launch_content_pillars`, `launch_message_templates`,
`launch_social_content_drafts`, `launch_lead_scoring_rules`, and a `launch_draft_review_items`
queue, plus 9 dashboards. Message/social dashboards expose only `body_char_count` /
`caption_char_count` (never full copy). All drafts are `send_enabled=false` /
`publish_enabled=false` / `human_review_required=true`; copy uses compliant placeholders
(`[PROJECT_NAME_CONFIRM]`, `[RERA_VERIFY]`, `[PRICE_VERIFY]`, `[BROCHURE_LINK_PENDING]`) with
opt-out lines — no false scarcity, guaranteed returns, unverified RERA, or exact price. The
`vw_dlf_launch_funnel_readiness` rollup keeps `ready_for_launch_push` false until consent +
project-name blockers clear and a channel is explicitly enabled. Seeded review-gated for the DLF
workspace; see `docs/PHASE_7_1_DLF_LAUNCH_FUNNEL_WORKSPACE.md`. No sends, publishing, external
calls, or contact selection happen here.

## Launch contact segmentation (Phase 7.2)

Migration `schemas/023_launch_contact_segmentation.sql` adds the contact segmentation and
permission-review layer for launch projects: `launch_contact_segment_candidates`,
`launch_contact_permission_review_items`, `launch_contact_segment_audit_log`, and masked
dashboards for operator review. The DLF planner created 5 review-gated candidates and 19 pending
permission/suppression review items. No candidate is approved, no contact is added to a live
campaign, and `send_enabled` remains 0. See
`docs/PHASE_7_2_DLF_CONTACT_SEGMENTATION_PERMISSION_REVIEW.md`.

## Launch lead intake and attribution plan (Phase 7.3)

Migration `schemas/024_dlf_lead_intake_attribution.sql` adds the planning layer that will later
connect Wix forms, UTM links, n8n routing, lead review, and operator metrics:
`launch_lead_intake_endpoints`, `launch_lead_field_mappings`,
`launch_lead_attribution_rules`, `launch_inbound_lead_review_items`, and
`launch_operator_daily_metrics`, plus six dashboards. The DLF seed creates 8 planned endpoints,
18 draft field mappings, attribution rules copied from the Phase 7.1 UTM specs, 30 zero-valued
metric placeholders, and 5 pending readiness checks. `vw_dlf_lead_intake_readiness` keeps
`ready_for_live_lead_capture=false` and `external_call_allowed_count=0`. No Wix/n8n APIs are
called, no live webhook exists, no inbound leads or contacts are created, and nothing is sent or
published. See `docs/PHASE_7_3_DLF_LEAD_INTAKE_ATTRIBUTION_PLAN.md`.

## n8n workflow blueprint (Phase 7.4)

Migration `schemas/025_n8n_launch_workflow_blueprint.sql` adds a blueprint layer for the future
n8n lead-intake flow: `launch_n8n_workflow_blueprints`, `launch_n8n_workflow_nodes`,
`launch_n8n_payload_schemas`, `launch_n8n_test_cases`, and `launch_n8n_review_items`, plus six
dashboards. The DLF seed creates 6 planned workflow blueprints, 20 planned nodes, 1 draft payload
schema, 7 fake-only test cases, and 18 pending review items. `vw_dlf_n8n_readiness` keeps
`ready_to_build_in_n8n=false`, `ready_to_activate=false`, and `external_call_allowed_count=0`.
No n8n/Wix/messaging APIs are called, no workflow or webhook is created, no inbound leads or
contacts are created, and nothing is sent or published. See
`docs/PHASE_7_4_DLF_N8N_WORKFLOW_BLUEPRINT.md`.

## DLF operator cockpit (Phase 7.5)

Migration `schemas/026_dlf_operator_cockpit.sql` adds a view-only daily cockpit over the DLF
launch stack: home, today tasks, combined review backlog, 14-day campaign calendar, audience
readiness, lead-intake readiness, n8n readiness, content readiness, and safety posture. The
summary helper `scripts/dlf_operator_cockpit_summary.py` prints counts only. The cockpit is
designed to show why the launch is blocked while keeping `send_enabled=0`, `publish_enabled=0`,
no external automation, no live lead capture, no communications, and no publishing. See
`docs/PHASE_7_5_DLF_OPERATOR_COCKPIT.md`.

## DLF launch blocker triage & project-name confirmation (Phase 7.6)

Migration `schemas/027_dlf_launch_blocker_triage.sql` adds three views (no new tables):
`vw_dlf_launch_blocker_triage` (open readiness checks + operator tasks grouped into blocker areas
with `recommended_action`, `can_be_closed_by_operator`, `requires_external_action`),
`vw_dlf_project_identity_status` (name-confirmation state; `public_name_ready_for_copy=false` until
confirmed), and `vw_dlf_launch_activation_guardrail` (the hard activation guardrail and
`hard_stop_reason`). Three guarded scripts (dry-run by default; writes require `--real-ok` +
`--apply`): `confirm_dlf_project_identity.py` confirms the public name **only from an
operator-supplied value**, `review_dlf_launch_readiness_check.py` records non-activation readiness
reviews, and `revert_dlf_project_identity_confirmation.py` undoes a confirmation. In this phase the
operator confirmed the public name **DLF Westpark** (slug `dlf-westpark-andheri-west`), applied via
the tool: `project_name_confirmed=true`, readiness check passed, `verify_project_name` task done,
previous name `DLF Westend / The Westpark Andheri West` captured — an operator-confirmed identity,
not web-verified. The launch still stays `safe_blocked` (`send_enabled=0`, `publish_enabled=0`, no
external automation, no activation, `ready_for_launch_push=false`) because consent, suppression,
copy, lead capture, and n8n remain not ready. See `docs/PHASE_7_6_DLF_LAUNCH_BLOCKER_TRIAGE.md`.

## DLF Westpark campaign copy & consent review (Phase 7.7)

Internal copy review. `scripts/review_dlf_campaign_copy.py` (dry-run by default; writes need
`--real-ok` + `--apply`) replaces `[PROJECT_NAME_CONFIRM]` → **DLF Westpark** in draft text fields
(templates/social/landing) and marks copy/consent `launch_draft_review_items`: internally-clean copy
→ `approved`, copy still carrying a factual placeholder (RERA/price/brochure/Wix/`[VERIFY]`/
visual-direction) → `needs_more_info`. This phase: project-name placeholder count 0; 8 approved, 21
needs_more_info; factual placeholders preserved. It writes only draft text + `raw_context` and review
marks; never enables send/publish, never passes a readiness check (so `whatsapp_template_approved`
stays pending — provider approval is separate), never touches contacts/leads. Launch stays
`safe_blocked`, send/publish 0, contacts 4, leads 0. Reversible via
`scripts/revert_dlf_campaign_copy_review.py`. See `docs/PHASE_7_7_DLF_CAMPAIGN_COPY_REVIEW.md`.

## DLF consent, suppression & lead-privacy readiness (Phase 7.8)

Migration `schemas/029_dlf_consent_privacy_readiness.sql` adds 1 audit table
(`launch_consent_privacy_review_log`) + 4 dashboards (`vw_dlf_consent_privacy_readiness`,
`vw_dlf_contact_permission_gap_dashboard`, `vw_dlf_lead_form_privacy_dashboard`,
`vw_dlf_suppression_readiness_dashboard`). Script `scripts/review_dlf_consent_privacy_readiness.py`
(dry-run by default; writes need `--real-ok` + `--apply`) logs the lead-form-consent /
privacy-field-mapping / suppression PROCESS as process_approved, passes **lead_privacy_reviewed**
(consent fields + PII mappings present, no live capture), moves 9 WhatsApp/email permission reviews to
**needs_more_info**, and sets **consent_ready needs_review** (never passed — 0 channel_permissions
allowed). It never grants a permission, never approves a contact for campaign, never passes
`whatsapp_template_approved` (provider approval external) or `suppression_checked` (process ≠
executed); an in-transaction guard enforces all of this. Launch stays `safe_blocked`, send/publish 0,
contacts 4, leads 0. Reversible via `scripts/revert_dlf_consent_privacy_readiness.py`. See
`docs/PHASE_7_8_DLF_CONSENT_PRIVACY_READINESS.md`.

## DLF contact permission evidence & suppression review (Phase 7.9)

Migration `schemas/030_dlf_contact_permission_evidence.sql` adds 3 tables
(`launch_contact_permission_evidence`, `launch_contact_suppression_checks`,
`launch_contact_permission_decision_log`) + 4 masked views (evidence / suppression-check / decision
dashboards + `vw_dlf_campaign_selection_guardrail`). Script
`scripts/review_dlf_contact_permission_evidence.py` (dry-run by default; writes need `--real-ok` +
`--apply`) created 10 evidence rows (5 candidates × whatsapp/email, all **needs_more_info** — 0
allowed since 0 channel_permissions allowed), 5 suppression checks (all **clear**, no list write),
approved the 5 suppression_review items (list-clear only, not consent), logged 30 audit rows. A
`permission_decision='allowed'` is only ever derived from a real `channel_permissions` allowed row; an
in-transaction guard refuses any unbacked allow/suppress, approved-for-segment, granted permission,
passed consent_ready/whatsapp_template_approved, or send/publish/n8n activation. Candidates stay
needs_permission_review, approved_for_segment 0, ready_for_campaign_selection false, launch
`safe_blocked`, contacts 4, leads 0. Reversible via
`scripts/revert_dlf_contact_permission_evidence.py`. See
`docs/PHASE_7_9_DLF_CONTACT_PERMISSION_EVIDENCE.md`.

## DLF controlled test lead intake (Phase 7.10)

Migration `schemas/031_dlf_test_lead_intake_harness.sql` adds 3 tables (`launch_test_lead_payloads`,
`launch_test_lead_validation_results`, `launch_test_lead_review_items`) + 4 views (payload /
validation / review-queue dashboards + `vw_dlf_test_lead_readiness`; dashboards expose no fake
name/phone/email). Script `scripts/run_dlf_test_lead_intake.py` (dry-run by default; writes need
`--real-ok` + `--apply`) created 5 fake payloads (valid brochure / missing consent / missing
phone+email / high-budget / referral → 3 validated, 2 failed), 40 validation results (37 passed, 2
failed, 1 needs_review), 13 review items. All payloads `uses_fake_data=true`,
`creates_real_lead/contact=false`, `external_call_made=false`. It never touches real
`inbound_leads`/`contacts` (still 0/4), calls no API/webhook; an in-transaction guard refuses any
real/external residue or activation. `ready_for_live_lead_capture` mirrors the real false gate. Test
rows retained for dashboard QA (tagged `phase=7.10`); remove via
`scripts/cleanup_dlf_test_lead_intake.py`. See `docs/PHASE_7_10_DLF_TEST_LEAD_INTAKE.md`.
