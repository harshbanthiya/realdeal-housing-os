# Phase 7.22 — Manual Wix Staging Site Recorded

Phase 7.22 records the **manually created** Wix staging/preview site (built by the operator outside
the OS) and marks initial Gallery White build progress, while keeping every live/production/API gate
closed. It reuses the Phase 7.20 tracking script — no new migration.

It performs **no** Wix API call, **never** reads/stores a Wix API key, **never** inspects `.env` for
Wix secrets, and does not publish, connect the real domain, enable indexing, create a live
form/webhook, enable tracking, or touch leads/contacts/messages.

## Staging site recorded

- The operator manually created (or duplicated) a Wix staging/preview site **outside the OS**.
- It is now recorded in `wix_staging_sites`:
  - `staging_status` = **`created_manually`**
  - `staging_site_name` = **"Test"** (operator-supplied)
  - `staging_site_url` = recorded — a `*.wixstudio.com` preview URL (stored in the OS DB only;
    the literal URL is intentionally **not** copied into this committed doc)
  - all live flags remain **false**

The staging URL is a Wix Studio preview address, not a credential; it lives in the local database
(git-ignored data), not in the repository.

## Exact safety confirmations (all verified by the operator)

- **No real domain connected** — `real_domain_connected = false`
- **No public indexing** — `public_indexing_enabled = false`
- **Not published** — `page_published = false`
- **No live form** — `live_form_created = false`
- **No live webhook** — `live_webhook_created = false`
- **No external tracking** — `external_tracking_enabled = false`
- **No Wix API / key usage** — `wix_api_call_made = false`; Wix API permission/key usage remains
  **deferred** (re-logged as `api_permission_review_deferred`). No key was requested, read, or stored.

`vw_dlf_wix_staging_build_progress.safety_flags_clean = true`.

## Gallery White shell build started

- The Gallery White shell build is now `in_progress`: hero, navigation, and the eight content
  sections moved `pending → in_progress` (alongside the previously-started setup items) — **12**
  checklist items `in_progress`.
- Safety checklist items (no real domain, no public indexing) and the absence QA checks
  (`domain_not_connected`, `noindex` ×2, `webhook_disabled`, `tracking_disabled`) are **passed** —
  2 checklist `passed`, 5 QA `passed`.
- Visual/content QA was intentionally **not** marked passed (it awaits the actual built UI).

## What remains

- **Finish sections** — complete the content-section, form, consent, FAQ, footer, and sticky-CTA build.
- **Form UI** — build the enquiry form (routes to manual review only; no live submission).
- **Consent UI** — granular unchecked consent fields + privacy/opt-out copy.
- **Placeholder QA** — confirm all unverified facts stay placeholders / branded "pending" copy.
- **Mobile QA** — stacked layout, tap targets, scroll-reveal nav.
- **SEO metadata QA** — titles/meta/H1-H2 in DOM, never canvas.
- **Staging fake lead test** — later, against the staging form.

## Readiness after recording

- `ready_for_manual_staging_build = true`
- `ready_for_staging_qa = true` (staging site created manually + safety flags clean)
- `ready_for_fake_lead_test = false` (until the build + QA complete)
- `ready_for_production_publish = false` (always, this track)
- All `real_domain / public_indexing / page_published / live_form / live_webhook /
  external_tracking` counts = 0; Wix API key profiles active = 0; secrets stored = 0.

## Rollback

```
python3 scripts/revert_dlf_wix_staging_build_progress.py --launch-key dlf-westpark-andheri-west
```

Dry-run by default. `--real-ok --apply` restores the recorded staging-build progress from the
`phase_7_20_*` markers (staging site → `planned`, name/url cleared, checklist/QA statuses restored)
and deletes the manual build action-log rows. It refuses if any staging site reports a
live/domain/index/publish/webhook/api flag or if any inbound lead exists.

## Next phase

Continue the Gallery White staging build, then a **staging QA pass** (mobile/desktop/form/consent/
placeholder/SEO/accessibility/performance), then a **fake staging lead test**. Production publish,
real-domain connection, live forms, tracking, and any Wix API call each remain separate,
explicitly-gated phases.
