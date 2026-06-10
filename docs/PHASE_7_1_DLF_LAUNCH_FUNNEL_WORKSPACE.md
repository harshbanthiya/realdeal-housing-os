# Phase 7.1 — DLF Launch Funnel & Campaign Draft Workspace

Builds the full launch-funnel scaffolding on top of the Phase 7.0 command center so the OS
becomes a **launch conversion command center**, not just a table of drafts. This phase is
**schema + a review-gated draft seed only** — **no sends, no publishing, no external calls**.

> No WhatsApp/SMS/email/social send, no Wix publish, no external API, no scrape, no contact
> import/select/create/merge, no `ready_for_launch_push`. Every `send_enabled` / `publish_enabled`
> is **false**; `human_review_required` is **true**; readiness gates stay **pending**.

## Launch funnel model

`Audience → Message → Landing Page → Lead Form → Qualification → Follow-up → Site Visit →
Booking Intent → Closed/Lost/Nurture`. Migration `schemas/022_launch_funnel_workspace.sql` adds
8 tables + 9 dashboards covering each stage.

## What was seeded (launch_key `dlf-westpark-andheri-west`)

| Object | Count | Notes |
| ------ | ----- | ----- |
| `launch_landing_page_specs` | 1 | `draft`; hero/CTA/sections/disclaimers with `[PROJECT_NAME_CONFIRM]` / `[RERA_VERIFY]` / `[PRICE_VERIFY]` / `[BROCHURE_LINK_PENDING]`; `publish_enabled=false` |
| `launch_lead_capture_forms` | 1 | `draft`; required fields + qualification questions + consent fields (opt-ins); `publish_enabled=false` |
| `launch_utm_campaign_specs` | 8 | seo, blog, instagram, youtube_shorts, whatsapp, email, referral, listing_portal |
| `launch_content_pillars` | 10 | buyer-psychology pillars (DLF brand, Andheri West, launch window, investor, NRI, 3/4 BHK, owner referral, RERA-verified facts, site-visit/brochure, price-sheet waitlist) |
| `launch_message_templates` | 13 | 7 WhatsApp + 4 email + 1 phone script + 1 referral script — all `draft`, `send_enabled=false`, `consent_required=true`, opt-out lines |
| `launch_social_content_drafts` | 15 | reels/stories/shorts — all `draft`, `publish_enabled=false` |
| `launch_lead_scoring_rules` | 10 | budget, 3/4 BHK, site-visit, brochure, Andheri West, NRI, investor, owner-referral, fast timeline, repeat engagement |
| `launch_draft_review_items` | 60 | one per draft (58) + launch-level `project_name_review` + `consent_review` — all `pending` |
| `launch_readiness_checks` (added) | 2 | `lead_scoring_reviewed`, `utm_tracking_ready` (the 11 Phase-7.0 checks already existed → now 13 total) |

### Landing page spec
`[PROJECT_NAME_CONFIRM] — Andheri West Launch`; CTAs *Request brochure* / *Book a site visit*;
sections include hero, highlights, location, floor-plans `[PRICE_VERIFY]`, RERA disclaimer
`[RERA_VERIFY]`, lead form, FAQ; `rera_disclaimer_required=true`,
`project_name_confirmation_required=true`, `publish_enabled=false`.

### Lead capture form spec
Required fields (schema labels, not data): name, phone, email, preferred_configuration.
Qualification: budget_range, configuration (2/3/4 BHK), purchase_timeline, buyer_or_investor,
preferred_locality. Consent: whatsapp_optin, email_optin, privacy_consent.
`utm_capture_required` / `whatsapp_optin_required` / `email_optin_required` all true.

### UTM tracking plan
One spec per channel with `source` / `medium` / `content_angle` / `funnel_stage` named up front
(e.g. `seo/google/organic/awareness`, `whatsapp/messaging/interest_capture/conversion`) so
attribution is consistent before anything goes live.

### Content pillars
10 pillars mapped to audience segment + funnel stage + `proof_needed` (every claim carries a
`[VERIFY]` / `[RERA_VERIFY]` / `[PRICE_VERIFY]` marker).

### WhatsApp / email / social templates
Draft copy only, with compliant guardrails: **no false scarcity, no guaranteed returns, no
unverified RERA, no exact price/area** (anything factual is marked `[VERIFY]`). WhatsApp/email
include opt-out / unsubscribe placeholders. The dashboards expose only `body_char_count` /
`caption_char_count` — **full body/caption text is never exposed** in a view.

### Lead scoring rules
Draft rules with `score_delta` and `priority_label` (cold/warm/hot/urgent) — e.g. site-visit
request +40 (urgent), budget fit +30 (hot), owner referral +25 (hot).

## Review workflow

Every draft has a `launch_draft_review_items` row (`pending`), surfaced by
`vw_launch_draft_review_queue`. Operators approve/reject per asset; nothing is enabled by review
alone. The DLF rollup `vw_dlf_launch_funnel_readiness` shows counts and a real
`ready_for_launch_push` gate.

## Consent / suppression blockers

`consent_ready` (blocker) and `suppression_checked` readiness checks remain **pending**, plus a
launch-level `consent_review` item. Message templates carry `consent_required=true` and
`suppression_check_required=true`. The `old_real_estate_contacts_needs_permission_review` segment
(Phase 7.0) still requires a permission review before any outreach.

## Why nothing is send/publish-enabled

`vw_dlf_launch_funnel_readiness`: `ready_for_launch_push=false`, `send_enabled_count=0`,
`publish_enabled_count=0`, `consent_blockers=1`, `project_name_blockers=1`,
`blocked_reason="project name not confirmed (operator must verify DLF Westend vs The Westpark)"`.
The naming ambiguity from Phase 7.0 (user’s “DLF Westend” vs public “DLF The Westpark / Westpark
Phase-I”) is still an unconfirmed **blocker** — the project name must be confirmed before any push.

## Cleanup (dry-run only this phase)

`scripts/cleanup_dlf_launch_funnel_workspace.py` removes **only** rows tagged
`phase=7.1/source=dlf_launch_funnel_workspace_seed` (120 rows). It refuses if any tagged row has
`send_enabled=true` / `publish_enabled=true`, any draft is `sent`/`published`/`scheduled`, or any
tag carries `communication_sent=true`; it never deletes contacts/leads/RERA/`launch_projects`/
`launch_channels`/Phase-7.0 rows.

```bash
# Dry-run (counts only; nothing deleted) — 120 tagged rows in scope:
python3 scripts/cleanup_dlf_launch_funnel_workspace.py --launch-key dlf-westpark-andheri-west
# Real delete requires BOTH flags (NOT run this phase):
#   ... --apply --real-ok
```

## Seed command

```bash
python3 scripts/seed_dlf_launch_funnel_workspace.py \
  --launch-key dlf-westpark-andheri-west --real-ok [--apply]
```

## Next steps

1. **Operator confirms project name** — resolve “DLF Westend” vs “DLF The Westpark / Westpark
   Phase-I” and clear `project_name_confirmed` + `project_name_review`.
2. **Permission review of contact segments** — work the segments (esp. legacy contacts) and clear
   `consent_ready` / `suppression_checked` / `consent_review`.
3. **Create the Wix form / lead-intake plan** — turn the form spec into a real (draft) Wix form.
4. **Connect the n8n workflow plan** — design lead intake → scoring → operator queue (not live).
5. **Approve the first batch of campaign copy** — review WhatsApp/email/social drafts; still no
   send until consent + name are confirmed and a channel is explicitly enabled.
