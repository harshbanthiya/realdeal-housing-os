# Phase 7.5 — DLF Operator Cockpit

Phase 7.5 creates a human-friendly operator cockpit for the DLF launch. It is view-only plus a
read-only summary script: no sends, no publishing, no external APIs, no live webhooks, no inbound
real leads, and no contact creation/merge.

## Purpose

The cockpit answers the daily operator questions:

- what is blocked
- what must be handled today
- which drafts need review
- which contact-segment rows need permission or suppression review
- which lead-intake and n8n items are not ready
- which campaign/calendar items are coming up
- whether the launch is safe to send or publish

In this phase the answer to send/publish readiness remains **no**.

## Dashboard views

Migration `schemas/026_dlf_operator_cockpit.sql` adds nine views:

| View | Purpose |
| ---- | ------- |
| `vw_dlf_operator_cockpit_home` | One-row launch home with readiness gates, blockers, and next action. |
| `vw_dlf_operator_today_tasks` | Operator tasks plus high-priority readiness/review blockers. |
| `vw_dlf_operator_review_backlog` | Combined draft, permission, inbound-lead, and n8n review queues. |
| `vw_dlf_operator_campaign_calendar_next_14_days` | Upcoming campaign placeholders and send/publish blockers. |
| `vw_dlf_operator_audience_readiness` | Contact-segment readiness counts only. |
| `vw_dlf_operator_lead_intake_readiness` | Lead-intake readiness counts. |
| `vw_dlf_operator_n8n_readiness` | n8n blueprint/build/activation readiness counts. |
| `vw_dlf_operator_content_readiness` | Funnel/content review readiness counts. |
| `vw_dlf_operator_safety_posture` | Safety flags and final blocked/safe status. |

No cockpit view exposes full names, phone numbers, emails, addresses, websites, raw contact values,
raw lead payloads, or full message/caption body text.

## Daily use

Start at `vw_dlf_operator_cockpit_home`, then work through:

1. `vw_dlf_operator_safety_posture`
2. `vw_dlf_operator_today_tasks`
3. `vw_dlf_operator_review_backlog`
4. `vw_dlf_operator_campaign_calendar_next_14_days`
5. the audience, lead-intake, n8n, and content readiness views

The helper script prints the same posture as counts:

```bash
python3 scripts/dlf_operator_cockpit_summary.py \
  --launch-key dlf-westpark-andheri-west
```

## Safe blocked

`safe_blocked` means the launch remains intentionally inert: no send/publish flags, no external
automation, no active n8n workflows, no live lead capture, no approved campaign contacts, no
communications sent, and no publishing detected.

`blocked_not_ready` means a safety counter changed and must be investigated before any launch work
continues.

## Before live launch

The following must happen in later explicit phases before any send/publish activation:

1. project name confirmation
2. RERA/project fact confirmation
3. landing/form approval
4. consent/suppression review
5. n8n workflow review/build
6. test lead intake
7. controlled first send/publish approval

## Safety statement

Phase 7.5 does not change launch activation state. It does not call Wix, n8n, WhatsApp, email, or
social APIs. It does not create webhooks, create inbound leads, create or merge contacts, send
messages, or publish content.
