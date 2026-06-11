# Phase 7.14 - DLF Wix Landing Page and Lead Form Build Package

Phase 7.14 produces a safe, human-buildable Wix landing page + lead form build package for
**DLF Westpark** (`dlf-westpark-andheri-west`). It generates one local Markdown artifact plus
tracking/validation/review DB rows so a human can build the page manually in Wix.

This phase did NOT call Wix APIs, did NOT create or publish a Wix page, did NOT create a live
form/webhook, did NOT send any message, and did NOT create real inbound leads or contacts. All
unverified facts remain placeholders. `publish_enabled`, `ready_for_live_lead_capture`, and
`ready_for_launch_push` all stay false.

## Generated build package

- artifact: `exports/wix_build_packages/dlf-westpark-wix-landing-build.md` (git-ignored under `exports/`)
- artifact type: `wix_landing_page_build_markdown`
- package status: `validated` (not yet `approved_for_manual_build`)
- the artifact SHA-256 is recorded in `launch_wix_build_packages.raw_context`

The artifact is an operator checklist only. It is not connected to Wix and contains no live
form/webhook, no secrets, and no raw contact data.

## Sections included

1. Page identity (title, slug suggestion)
2. Hero section (headline/subheadline, visual direction placeholder, RERA line placeholder)
3. CTA sections (primary/secondary, brochure placeholder)
4. Lead form field list (from `launch_lead_field_mappings` — label/type/required/pii_type/status only)
5. Consent / opt-in fields (explicit, unchecked by default, opt-out + privacy link required)
6. UTM hidden fields (capture only, not displayed)
7. SEO title / meta placeholders
8. Content sections (from `launch_content_pillars`)
9. Unresolved factual placeholders
10. Publish blockers
11. Operator checklist for the manual Wix build

## Preserved factual placeholders

These remain unresolved in the artifact and must be human-verified with sources before any
publish review:

- `RERA_VERIFY`
- `PRICE_VERIFY`
- `BROCHURE_LINK_PENDING`
- `WIX_PAGE_PENDING`
- `VERIFY`
- `VISUAL_DIRECTION_PENDING`

## Consent / form fields

The form section lists each mapped field with its `pii_type` and required flag (no lead values).
Consent and opt-in checkboxes are explicit and unchecked by default, with a privacy-policy link and
opt-out notice required near the submit button. WhatsApp and email opt-ins are separate checkboxes.

## Validation checks

The generator validates the rendered Markdown before writing. All eight passed:

- `no_secrets`
- `no_contact_data`
- `factual_placeholders_preserved` (also rejects false scarcity / guaranteed-return claims; negated
  compliance disclaimers such as "no guaranteed returns" are allowed)
- `consent_fields_present`
- `utm_fields_present`
- `no_publish_enabled`
- `no_live_webhook`
- `seo_sections_present`

## Migration

`schemas/034_dlf_wix_landing_build_package.sql` adds tables:

- `launch_wix_build_packages`
- `launch_wix_build_validation_results`
- `launch_wix_build_review_items`

and views:

- `vw_dlf_wix_build_package_dashboard`
- `vw_dlf_wix_build_validation_dashboard`
- `vw_dlf_wix_build_review_queue`
- `vw_dlf_wix_build_readiness`

`vw_dlf_wix_build_readiness` keeps `ready_to_publish=false` by design and reports `wix_pages_created`,
`wix_pages_published`, and `live_forms_created` (all 0).

## Generate the build package

```bash
# Dry-run (default): prints projected counts and validations, writes nothing.
python3 scripts/create_dlf_wix_landing_build_package.py \
  --launch-key dlf-westpark-andheri-west --real-ok

# Apply: writes the ignored Markdown artifact and DB rows.
python3 scripts/create_dlf_wix_landing_build_package.py \
  --launch-key dlf-westpark-andheri-west --real-ok --apply
```

The generator refuses to write if any local validation fails, and a transaction guard refuses if a
prior Phase 7.14 package is marked created/published/live/external, or if inbound/contacts/send/
publish state drifts.

## Cleanup dry-run

```bash
python3 scripts/cleanup_dlf_wix_landing_build_package.py \
  --launch-key dlf-westpark-andheri-west
```

Cleanup is dry-run by default and deletes only rows tagged `phase='7.14'` /
`source='dlf_wix_landing_build_package'`. It never touches Phase 7.0-7.13 rows, landing/form specs,
field mappings, or content pillars. It refuses if any package is marked `wix_page_created`,
`wix_page_published`, `live_form_created`, or has status `built_in_wix`/`published`. Artifact deletion
is opt-in via `--delete-artifacts` and still requires `--real-ok --apply`.

## Verified counts

- wix build packages: 1 `validated`
- validations: 8 passed (0 failed)
- review items: 6 pending (landing_page_build / lead_form_build / seo / consent / factual_claim / publish_blocker)
- wix_page_created: 0
- wix_page_published: 0
- live_form_created: 0
- ready_for_manual_wix_build: false (blocked: pending human build-package reviews)
- ready_to_publish: false
- inbound leads: 0
- contacts: 4
- send/publish/communication counts: 0
- ready_for_live_lead_capture: false
- ready_for_launch_push: false

## Safety

- No Wix API calls.
- No Wix page created or published.
- No live form or live webhook created.
- No n8n API calls.
- No WhatsApp/SMS/email/social messages sent.
- No campaigns enabled; `send_enabled` and `publish_enabled` remain false.
- No real inbound leads; no contacts created or merged (contacts remain 4).
- No secrets, no raw contact data, and no unverified claims in the artifact.
- The artifact stays git-ignored under `exports/wix_build_packages/`.

## Next phase

Either a human review that approves the package for manual Wix build
(`package_status=approved_for_manual_build` after the six pending reviews clear), or a controlled
Wix page draft recording phase. Publishing, live form/webhook creation, live lead capture,
messaging, and campaign activation remain separate explicit phases and stay blocked.
