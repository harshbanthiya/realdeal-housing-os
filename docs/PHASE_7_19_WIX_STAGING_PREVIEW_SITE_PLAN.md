# Phase 7.19 — Wix Staging / Preview-Site Plan

Phase 7.19 sets up a **safe staging/preview-site plan** so the DLF Westpark website (approved
"Gallery White" direction) can be built and tested visually **before touching the live domain**.
The user already runs an existing Wix website; this phase ensures the new build happens on a
separate staging project with the real domain disconnected, public indexing off, no published
production pages, no live forms/webhooks, no external tracking, and no Wix API calls.

It is a planning/tracking phase only: no Wix API call, no n8n call, no Meta/Google/WhatsApp/email
connection, no publishing, no live form/webhook, no real inbound leads, no contact changes.

## Why a staging/preview site first

- The live domain and existing site must stay untouched until the new design is fully QA'd.
- A staging site (free `*.wixsite.com` URL, hidden from search) lets us validate layout, mobile
  behaviour, form/consent UX, placeholders, SEO structure, and performance with **fake/test data
  only**.
- Production publish, real domain connection, live forms, and tracking are each separate, later,
  explicitly-gated steps — never part of this phase.

## Staging-site rules (hard gates)

- **No real domain** — keep the `*.wixsite.com` staging URL; never connect the production domain.
- **No public indexing** — staging stays `noindex` / hidden from search engines.
- **No live webhook** — the form routes to manual review only; no automation is wired.
- **No live tracking** — no GA4 / GTM / Meta pixel fires on staging.
- **No publish** — no production page is published to the live domain.
- **Fake/test data only** — no real contacts, no real leads; placeholders for unverified facts.

These are enforced in the schema: `wix_staging_sites` defaults every live flag to false, and
`vw_dlf_wix_staging_readiness` keeps `ready_for_production_publish` hard-false while
`real_domain_connected_count`, `public_indexing_enabled_count`, `page_published_count`,
`live_form_created_count`, and `live_webhook_created_count` all stay 0.

## Schema (migration 038)

`schemas/038_dlf_wix_staging_site_plan.sql` adds four tables — `wix_staging_sites`,
`wix_staging_build_checklist_items`, `wix_staging_qa_checks`, `wix_staging_review_items` — and
five views: `vw_wix_staging_site_dashboard`, `vw_wix_staging_build_checklist_dashboard`,
`vw_wix_staging_qa_dashboard`, `vw_wix_staging_review_queue`, and the real gate
`vw_dlf_wix_staging_readiness`.

Seed: `scripts/seed_dlf_wix_staging_site_plan.py` (dry-run by default; `--real-ok --apply`).

## Manual setup checklist (operator, in Wix)

1. Create a **new** Wix site (or duplicate) as a separate staging/preview project — never the live site.
2. Do **not** connect the real domain; keep the free `*.wixsite.com` URL.
3. Keep the staging site hidden from search engines (noindex / not discoverable).
4. Lay out the homepage + project-landing shells per the Gallery White page architecture.

## Gallery White build checklist (20 items)

Setup (staging setup, homepage/landing shell), safety (no domain, no indexing), hero
(type-first with above-fold image slice), content sections (01 project → 06 verified facts, FAQ,
footer), navigation (sticky CTA), form (section 07 enquiry → manual review), consent (granular
unchecked fields), tracking (hidden UTM fields, no live pixel), placeholders (factual placeholders
kept verbatim / branded pending), mobile (stacked layout + scroll-reveal nav), and performance
(fixed image aspect ratios for CLS). All seeded as `pending`.

## QA checklist (13 checks, blockers marked)

Safety blockers: `domain_not_connected`, `noindex` (staging + no-publish), `webhook_disabled`,
`tracking_disabled`, `mobile_layout`, `form_fields`, `consent_fields`, `placeholder_integrity`.
Non-blocking quality checks: `desktop_layout`, `seo_metadata`, `accessibility`, `performance`.
All seeded as `pending` and must pass in staging before any production-publish phase is considered.

## Readiness (after seed)

- `ready_for_manual_staging_build = true` — the plan exists and no live flag is set.
- `ready_for_staging_qa = false` — until the manual Wix build is recorded as created.
- `ready_for_production_publish = false` — always, in this phase.
- `real_domain_connected / public_indexing_enabled / page_published / live_form_created /
  live_webhook_created` counts = 0.

## Cleanup (dry-run command)

```
python3 scripts/cleanup_dlf_wix_staging_site_plan.py --launch-key dlf-westpark-andheri-west
```

Dry-run by default. `--real-ok --apply` deletes only Phase 7.19 rows
(`phase='7.19'`, `source='dlf_wix_staging_site_plan_seed'`). It refuses if any staging site has a
real-domain/indexing/publish/live-form/live-webhook/wix-api flag set or if any staging review item
is approved, and never touches Phase 7.0–7.18 rows, leads, or contacts.

## Next phase

Track the **manual Wix staging build** (operator marks the site `created_manually` →
`build_in_progress` → `ready_for_qa`, ticking checklist items), then run a **fake staging lead
test** against the staging form. Production publish, real-domain connection, live forms, tracking,
and indexing each remain separate, explicitly-gated phases and stay blocked.

> **Follow-up:** Phase 7.20 adds the manual build-tracking audit log + progress view
> (`schemas/039_dlf_wix_staging_build_tracking.sql`) and the
> `scripts/record_dlf_wix_staging_build_progress.py` tool (no Wix API call, no API key read; Wix
> API capability mapping deferred). See `docs/PHASE_7_20_WIX_STAGING_BUILD_TRACKING.md`.
