# Phase 7.0 — DLF Launch Command Center Foundation

A project-scoped **launch command center** to prepare for a high-priority DLF launch
(in/around **August**) and drive qualified leads across Wix landing pages, SEO, blog/content,
Instagram / YouTube Shorts, WhatsApp, email, phone, referral, and listing portals — with
**later** n8n automation. This phase is **foundation + a review-gated seed only**.

> **No sending, no publishing, no external calls.** No WhatsApp/SMS/email/social send, no Wix
> publish, no external API, no scraping, no contact import, no contact create/merge, no inbound
> lead creation, no raw-contact selection. Every send/publish flag is **false**; readiness gates
> default **pending**.

## Why a launch command center exists

The existing growth tables (`seo_keywords`, `content_briefs`, `campaign_drafts`,
`channel_permissions`, `content_publishing_queue`, …) are building/keyword-scoped and
launch-agnostic. A time-sensitive launch needs a **project layer** on top: per-launch channels,
a content/outreach calendar, target lead **segments** (counts only), an operator checklist, and
explicit **send/publish readiness gates**. Migration
`schemas/021_launch_command_center.sql` adds 6 tables + 7 dashboards for exactly this.

## DLF naming ambiguity (must be resolved by an operator)

The user calls it **“DLF Westend.”** Public sources may refer to **“DLF The Westpark /
Westpark Phase-I, Andheri West.”** **These are not assumed to be the same project.** The seed
records both names, sets `raw_context.name_confirmation_required=true`
(`user_supplied_name='DLF Westend'`, `possible_public_name='DLF The Westpark / Westpark Phase-I'`),
and adds a **blocker** readiness check `project_name_confirmed = pending`. Nothing downstream can
go live until an operator confirms the real project identity. The DLF rollup’s `blocked_reason`
currently reads *“project name not confirmed (operator must verify DLF Westend vs The Westpark).”*

## What was seeded (launch_key `dlf-westpark-andheri-west`)

| Object | Count | Notes |
| ------ | ----- | ----- |
| `launch_projects` | 1 | DLF, Andheri West, Mumbai; `launch_status=planning`; priority high |
| `launch_channels` | 10 | wix, seo, blog, instagram, youtube_shorts, whatsapp, email, phone_call, referral, listing_portal — all `planned`, `send_enabled=false`, `publish_enabled=false` |
| `launch_lead_segments` | 6 | counts only, all `estimated_contact_count=0`, `permission_required=true` |
| `launch_readiness_checks` | 11 | 3 **blocker** (project_name_confirmed, whatsapp_template_approved, consent_ready), 5 high, 3 normal — all `pending` |
| `launch_operator_tasks` | 11 | daily checklist, all `pending` |
| `launch_campaign_calendar` | 30 | next-30-day **placeholders**, all `status=planned`, send/publish disabled |
| `campaign_drafts` (placeholders) | 4 | `status=draft`, `send_enabled=false`, `consent_required=true`, **no copy** |
| `ai_agent_tasks` (placeholders) | 4 | future content/research, `human_review_required=true`, **not executed** |

### Channels created
wix · seo · blog · instagram · youtube_shorts · whatsapp · email · phone_call · referral · listing_portal

### Segments created (no raw contacts — counts only)
`high_budget_buyers` · `investor_buyers` · `andheri_west_buyers` · `nri_buyers` ·
`old_real_estate_contacts_needs_permission_review` (requires permission review) ·
`owner_network_referrals`

### Readiness gates
`project_name_confirmed` (blocker) · `rera_checked` · `wix_landing_page_ready` ·
`lead_capture_form_ready` · `whatsapp_template_approved` (blocker) · `email_template_approved` ·
`consent_ready` (blocker) · `suppression_checked` · `seo_briefs_ready` · `social_calendar_ready` ·
`n8n_workflow_ready`

### Campaign calendar placeholder
30 days of `planned` items rotating across instagram / blog / whatsapp / email /
youtube_shorts / wix — every one `send_enabled=false`, `publish_enabled=false`, no brief/draft
linked. These are scaffolding for an operator to draft into, not scheduled sends.

## Dashboards

`vw_launch_command_center_home`, `vw_launch_channel_dashboard`, `vw_launch_calendar_dashboard`,
`vw_launch_lead_segment_dashboard` (counts only), `vw_launch_operator_task_dashboard`,
`vw_launch_readiness_dashboard`, and the DLF rollup `vw_dlf_launch_priority_dashboard`.
`ready_for_launch_push` is a **real gate**: true only when no blocker is outstanding, the project
name is confirmed, **and** at least one channel each is send- and publish-enabled. In Phase 7.0
it is **false** (`send_enabled_count=0`, `publish_enabled_count=0`, 3 pending blockers).

## Operator daily workflow

1. Open `vw_dlf_launch_priority_dashboard` → read `blocked_reason` / `next_required_action`.
2. Work `vw_launch_operator_task_dashboard` (pending tasks) and `vw_launch_readiness_dashboard`
   (clear blockers, starting with `project_name_confirmed`).
3. Draft content/copy into the calendar + `campaign_drafts` (still no send).
4. Review lead segments + permissions before anything is enabled.

## Cleanup (dry-run only this phase)

`scripts/cleanup_dlf_launch_command_center.py` removes **only** rows tagged
`phase=7.0/source=dlf_launch_command_center_seed`. It refuses if any tagged row has
`send_enabled=true` / `publish_enabled=true`, any calendar/campaign is `sent`/`published`, or any
tag carries `communication_sent=true`; it never deletes contacts/leads/RERA/building rows.

```bash
# Dry-run (counts only; nothing deleted) — 77 tagged rows in scope:
python3 scripts/cleanup_dlf_launch_command_center.py --launch-key dlf-westpark-andheri-west
# Real delete requires BOTH flags (NOT run this phase):
#   ... --apply --real-ok
```

## Seed command

```bash
python3 scripts/seed_dlf_launch_command_center.py \
  --launch-key dlf-westpark-andheri-west \
  --project-display-name "DLF Westend / The Westpark Andheri West" \
  --internal-alias "DLF Westend" \
  --expected-launch-month "August" --real-ok [--apply]
```

## No sends / no publishing

No message sent, no campaign enabled, nothing published, no external API call, no scrape, no
contact selected or printed. `send_enabled_count=0`, `publish_enabled_count=0`,
`communication_sent=0`.

## Next steps

1. **Confirm project name / RERA** — resolve “DLF Westend” vs “DLF The Westpark / Westpark
   Phase-I” and clear the `project_name_confirmed` blocker; then `rera_checked`.
2. **Build the landing-page brief** — turn `wix_landing_page_ready` into a real (draft) page.
3. **Create campaign copy drafts** — fill the `campaign_drafts` placeholders (still no send).
4. **Permission review for contacts** — work the segments (especially
   `old_real_estate_contacts_needs_permission_review`) and `consent_ready` / `suppression_checked`.
5. **n8n lead-intake plan** — design the `n8n_workflow_ready` intake (not yet live).

> **Phase 7.1 update:** the full launch funnel draft workspace (landing page, lead form, UTM
> specs, content pillars, WhatsApp/email/social templates, lead scoring, review queue) is now
> seeded on top of this command center — still review-gated, send/publish disabled. See
> `docs/PHASE_7_1_DLF_LAUNCH_FUNNEL_WORKSPACE.md`.
