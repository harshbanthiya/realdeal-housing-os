# Phase 7.3 — DLF Lead Intake And Attribution Plan

Phase 7.3 prepares the DLF launch workspace for future Wix form intake, n8n webhook routing,
UTM attribution, lead review, and operator metrics. It is a planning and review foundation only.

> No Wix API calls, no n8n API calls, no live webhooks, no Wix publishing, no inbound real leads,
> no contact creation/merge, no campaign enablement, and no WhatsApp/SMS/email/social messages.

## What the migration adds

`schemas/024_dlf_lead_intake_attribution.sql` adds five planning tables:

| Table | Purpose |
| ----- | ------- |
| `launch_lead_intake_endpoints` | Planned form, webhook, link, click-to-chat, referral, and manual-entry endpoints. |
| `launch_lead_field_mappings` | Draft map from Wix/form fields to `inbound_leads`, `lead_attribution_events`, and future permission rows. |
| `launch_lead_attribution_rules` | Draft rules derived from Phase 7.1 UTM specs. |
| `launch_inbound_lead_review_items` | Future review queue before inbound leads can become contacts or campaign targets. |
| `launch_operator_daily_metrics` | Daily zero-valued placeholders for launch operators. |

It also adds six read-only dashboards:

- `vw_launch_lead_intake_endpoint_dashboard`
- `vw_launch_lead_field_mapping_dashboard`
- `vw_launch_lead_attribution_rule_dashboard`
- `vw_launch_inbound_lead_review_dashboard`
- `vw_launch_operator_daily_metrics_dashboard`
- `vw_dlf_lead_intake_readiness`

The readiness view keeps `ready_for_live_lead_capture=false` and reports
`external_call_allowed_count=0` in this phase.

## Seeded plan

`scripts/seed_dlf_lead_intake_plan.py` is dry-run by default, requires `--real-ok`, and writes only
with `--apply`. It refuses if the launch project is missing, if the Phase 7.1 lead-capture form is
missing, or if Phase 7.3 rows already exist unless `--allow-existing` is supplied.

Planned endpoints:

| Endpoint key | Status |
| ------------ | ------ |
| `wix_landing_page_form` | planned, not published |
| `n8n_wix_lead_webhook` | planned, no live webhook |
| `instagram_bio_link` | planned |
| `youtube_shorts_link` | planned |
| `whatsapp_click_to_chat` | planned, no message sent |
| `email_campaign_link` | planned, no email sent |
| `referral_link` | planned |
| `listing_portal_manual_entry` | planned |

## Wix form mapping

The seed creates 18 draft mappings for form labels only: name, phone, email, interested
configuration, budget range, buying purpose, timeframe, location preference, site visit interest,
brochure requested, WhatsApp opt-in, email opt-in, source, UTM source/medium/campaign/content,
and landing-page slug.

The fields that can carry personal or consent data are marked with a `pii_type`; dashboard views
show mapping metadata only, not submitted values.

## n8n webhook plan

The `n8n_wix_lead_webhook` endpoint records a planned path and requires external work later, but
`external_call_allowed=false`. No n8n workflow is created, no endpoint is active, and no live lead
capture is possible from this phase alone.

## Attribution rules

Attribution rules are copied from the Phase 7.1 `launch_utm_campaign_specs` rows and left in
`draft`. They map source/medium/campaign/funnel-stage metadata to launch channels and broad
segments for future review.

## Privacy and consent

The plan includes explicit consent fields (`whatsapp_optin`, `email_optin`) and Phase 7.3
readiness checks for privacy, duplicate-review readiness, field review, webhook planning, and
attribution review. Inbound leads must pass a future review queue before conversion to contacts or
campaign targeting.

## Operator daily metrics

The seed creates 30 zero-valued daily metric placeholders. These are for future manual or computed
rollups: new leads, reviewed leads, hot leads, follow-ups due, site visits requested, replies, SEO
leads, and referral leads.

## Why live capture is still blocked

Live capture needs a later explicit approval phase because field mappings, attribution rules,
privacy handling, duplicate review, endpoint security, and n8n/Wix configuration still need human
review. Phase 7.3 keeps every endpoint planned, every field/rule draft, and every external call
disabled.

## Commands

```bash
python3 scripts/seed_dlf_lead_intake_plan.py \
  --launch-key dlf-westpark-andheri-west --real-ok

python3 scripts/seed_dlf_lead_intake_plan.py \
  --launch-key dlf-westpark-andheri-west --real-ok --apply

python3 scripts/cleanup_dlf_lead_intake_plan.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

The cleanup dry-run deletes nothing. Real deletion requires `--apply --real-ok` and refuses if any
endpoint is active, any external call is allowed, any inbound lead exists from the Phase 7.3 seed,
or any contact appears tagged to this seed.

## Next phase

Phase 7.4 adds the n8n workflow blueprint layer: planned workflows, planned nodes, a draft payload
schema, fake-only test cases, and review gates. It still creates no n8n workflows, live webhooks,
inbound leads, contacts, sends, or publishing. See
`docs/PHASE_7_4_DLF_N8N_WORKFLOW_BLUEPRINT.md`.

Phase 7.10 later exercised this lead-intake plan with a **fake/test-only** harness (5 fake payloads,
40 validations) in dedicated `launch_test_lead_*` tables — no real `inbound_leads`/contacts, no
webhooks/API, `ready_for_live_lead_capture` stays false. See
`docs/PHASE_7_10_DLF_TEST_LEAD_INTAKE.md`.
