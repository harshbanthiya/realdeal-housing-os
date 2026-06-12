# Phase 7.20 — Manual Wix Staging Build Tracking

Phase 7.20 tracks the **human/manual** Wix staging build for the approved Gallery White design
without calling any Wix API, reading any Wix API key, or creating any live production surface. It
adds an append-only audit log and a build-progress dashboard over the Phase 7.19 staging plan.

It performs **no** Wix API call, **never** reads/stores a Wix API key, **never** inspects `.env`
for Wix secrets, and does not connect a domain, enable indexing, publish a page, create a live
form/webhook, enable tracking, enable send/publish, or create leads/contacts.

## Was a manual staging site actually created?

**No.** As of this phase the operator has **not** supplied real staging-site details, so **no actual
Wix staging site was recorded** — the build tracking was **initialized only**. The staging site
record correctly remains `planned`; nothing was fabricated.

When the operator does manually create a Wix staging/preview site, they can record it safely with:

```
python3 scripts/record_dlf_wix_staging_build_progress.py \
  --launch-key dlf-westpark-andheri-west \
  --performed-by "<operator>" \
  --staging-site-name "<real staging site name>" \
  --staging-site-url "<real *.wixsite.com preview url>" \
  --confirm-staging-site-created-manually \
  --confirm-real-domain-not-connected --confirm-public-indexing-disabled \
  --confirm-page-not-published --confirm-no-live-form \
  --confirm-no-live-webhook --confirm-no-external-tracking \
  --mark-setup-started --mark-gallery-white-shell-started --mark-safety-checks-passed \
  --record-api-permission-review-deferred \
  --decision-notes "<notes>" --real-ok --apply
```

The script refuses to flip the site to `created_manually` unless real name/url details are supplied
(it never fabricates a site), and `--mark-safety-checks-passed` requires **all six** `--confirm-*`
safety flags.

## What was recorded this phase

- **Setup checklist started** — the 2 `setup` checklist items moved `pending → in_progress`.
- **API permission review deferred** — one append-only `api_permission_review_deferred` action-log
  row noting the operator reviewed Wix API permissions in the Wix dashboard, but **Wix API
  permission/key usage is deferred to a later capability-map phase**. No API key was requested,
  read, or stored; no `external_call_allowed` flag changed.
- 3 audit rows total in `wix_staging_build_action_log` (2 `checklist_item_started` + 1
  `api_permission_review_deferred`).

## Checklist progress

- `setup`: 2 `in_progress`
- All other categories (hero, navigation, content_sections ×8, form, consent, tracking,
  placeholders, mobile, performance, safety ×2): still `pending`
- QA checks: all 13 still `pending` (no visual/content or safety QA marked passed — safety QA is only
  marked when `--mark-safety-checks-passed` is run with all confirmations, which awaits the manual build)

## Safety flags confirmed

`vw_dlf_wix_staging_build_progress.safety_flags_clean = true`, derived from the staging site
reporting all live flags off: `real_domain_connected=false`, `public_indexing_enabled=false`,
`page_published=false`, `live_form_created=false`, `live_webhook_created=false`,
`external_tracking_enabled=false` (and `wix_api_call_made=false`).

## Wix API status

- The operator reviewed Wix API permissions in the Wix dashboard.
- **API/key usage is deferred** to a later capability-map phase and recorded as such in the audit log.
- **No Wix API call was made. No Wix API key was requested, read, or stored.** This script and view
  never imply API readiness; the integration-readiness items stay `planned` with
  `external_call_allowed=false`.

## What stays blocked

No publish, no real domain, no public indexing, no live form, no live webhook, no external tracking.
`ready_for_production_publish=false` (always), `ready_for_fake_lead_test=false` (until a staging
page/form exists and QA passes), `ready_for_staging_qa=false` (until an operator-confirmed manual
staging site exists). Launch remains safe_blocked.

## Rollback (dry-run command)

```
python3 scripts/revert_dlf_wix_staging_build_progress.py --launch-key dlf-westpark-andheri-west
```

Dry-run by default. `--real-ok --apply` restores the Phase 7.20 status changes from the
`phase_7_20_*` markers, deletes the Phase 7.20 action-log rows, preserves the Phase 7.19 staging
plan, and refuses if any staging site reports a live/domain/index/publish/webhook/api flag or if any
inbound lead exists.

## Next phase options

- **Continue the manual Gallery White staging build** — record the site once created, advance
  checklist items, mark safety checks passed.
- **Run staging QA** after the build is complete (mobile/desktop/form/consent/placeholder/SEO/
  accessibility/performance) and then a **fake staging lead test**.
- **Create a Wix API permission / capability map** as a separate, later, explicitly-gated phase —
  it is intentionally out of scope here.

> **Follow-up:** Phase 7.21 builds that review-gated Wix API permission/capability map (46 permissions
> mapped, 4 planned key profiles, no secrets/keys stored). See
> `docs/PHASE_7_21_WIX_API_PERMISSION_CAPABILITY_MAP.md`.

> **Follow-up:** Phase 7.22 then records the operator's manually created staging site (this script's
> full path) — staging site → `created_manually`, shell build `in_progress`, safety checks passed,
> `ready_for_staging_qa=true`. See `docs/PHASE_7_22_WIX_STAGING_SITE_RECORDED.md`.
