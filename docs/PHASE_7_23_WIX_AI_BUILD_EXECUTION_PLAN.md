# Phase 7.23 — Wix AI Build Execution Plan for Gallery White

Phase 7.23 creates the **AI-generated implementation plan and code-artifact package** for building
the approved Gallery White direction into the existing Wix staging/preview site. It is a planning
and local-artifact phase only: no Wix API call, no Wix API key request/read/store, no GitHub/Wix
connection, no publish, no real-domain connection, no indexing, no live form/webhook/tracking, no
lead/contact/message write.

## Why this replaces the manual build-kit approach

Earlier Wix phases prepared a manual staging build path. Phase 7.23 keeps that safety posture but
asks the agent to generate as much of the build package as possible locally:

- reusable Custom Element JavaScript and CSS for the Gallery White landing experience
- Velo page-code glue for preview-only form handling
- static HTML/CSS preview files for code review
- copy, SEO, form, setup, and permission-route notes
- database review rows so a human can approve the route and artifacts before touching Wix

The generated files live in `exports/` and are ignored by Git. The committed repo only tracks the
schema, generator, cleanup script, and this documentation.

## Selected implementation route

Preferred route: **Wix Git Integration + Wix CLI for Sites**, if the operator can connect the Wix
site to GitHub and use the Wix local/preview workflow.

Fallback route: **Wix-hosted Custom Element + Velo page code**, where the operator manually adds the
custom element and pastes/syncs the generated code into the Wix staging site.

Last-resort route: **manual code snippets**, using the generated copy/form/SEO sections as a build
reference in the Wix editor.

Official Wix documentation checked for route selection:

- Git Integration + Wix CLI for Sites: site code can be connected to GitHub, developed locally, and
  previewed/published through the Wix tooling. Publishing remains explicitly blocked in this phase.
- Wix CLI docs: general Wix CLI is not the site-code entry point; Wix sites use Git Integration +
  Wix CLI for Sites.
- Wix API Reference, Data Items API, and Contacts API: useful later for CMS/form/contact workflows,
  but contact/data write permissions are not needed for this local staging build package.

## Permission posture

The Phase 7.21 permission map remains the source of truth:

- useful now: read-first/staging setup concepts and local build workflow planning
- useful later: Wix Data, Forms, Blog/FAQ/media, analytics, consent, and tracking scopes after
  review-gated staging QA
- forbidden now: Publish Metasite, payments, members/roles, Wix Secrets, email/social sends,
  embedded script/marketing-tag writes, live webhook creation, production key usage

No key profile was activated. `external_call_allowed=false` and `secret_value_stored=false` remain
the required posture for Wix key profiles.

## Generated artifacts

`scripts/create_dlf_wix_ai_build_plan.py --real-ok --apply` writes the following local artifacts to:

```text
exports/wix_ai_builds/dlf-westpark-gallery-white-v1/
```

Artifacts:

- `implementation-readme.md`
- `wix-permission-route-analysis.md`
- `wix-git-cli-setup-checklist.md`
- `gallery-white-custom-element.js`
- `gallery-white-custom-element.css`
- `gallery-white-page-code.js`
- `gallery-white-copy-blocks.md`
- `gallery-white-form-config.md`
- `gallery-white-seo-meta.md`
- `gallery-white-static-preview.html`
- `gallery-white-static-preview.css`

These are review artifacts only. They intentionally use placeholder form behavior and must not be
treated as a live lead-capture system.

## Database workflow

Migration `schemas/041_dlf_wix_ai_build_execution_plan.sql` adds:

- `wix_ai_build_execution_plans`
- `wix_ai_build_artifacts`
- `wix_ai_build_steps`
- `wix_ai_build_validation_results`
- `wix_ai_build_review_items`

Read-only views:

- `vw_wix_ai_build_execution_plan_dashboard`
- `vw_wix_ai_build_artifact_dashboard`
- `vw_wix_ai_build_step_dashboard`
- `vw_wix_ai_build_validation_dashboard`
- `vw_wix_ai_build_review_queue`
- `vw_dlf_wix_ai_build_readiness`

The current generated plan has 1 execution plan, 11 generated artifacts, 9 steps, 13 passed
validations, and 9 pending review items. `ready_for_code_review=true` and
`ready_for_operator_setup=true`; `ready_for_wix_implementation=false` until review gates pass.
`ready_for_fake_lead_test=false` remains hard-blocked.

## Operator-only actions

Allowed later, after review:

- enable Velo or connect Wix Git Integration/GitHub
- install/use Wix CLI for Sites locally if the Git route is chosen
- add the custom element to the staging page
- paste/sync generated code into the staging site
- preview the staging site only
- run visual/SEO/accessibility/form-placeholder QA

Blocked in this phase:

- actual code paste/sync into Wix by the agent
- Wix API calls or Wix key reads
- publish, real-domain connection, public indexing
- live form, live webhook, tracking pixels/tags
- fake lead test, real lead creation, contact creation/merge, messages

## Commands

Create or inspect the plan:

```bash
python3 scripts/create_dlf_wix_ai_build_plan.py --launch-key dlf-westpark-andheri-west --preferred-route auto --real-ok
python3 scripts/create_dlf_wix_ai_build_plan.py --launch-key dlf-westpark-andheri-west --preferred-route auto --real-ok --apply
```

Dry-run cleanup:

```bash
python3 scripts/cleanup_dlf_wix_ai_build_plan.py --launch-key dlf-westpark-andheri-west --real-ok
```

Cleanup refuses unsafe states and deletes only Phase 7.23 rows unless artifact deletion is explicitly
requested. The dry-run used in this phase reported 1 execution plan, 11 artifacts, 9 steps, 13
validations, and 9 reviews as the intended deletion set.

## Next phase

Review the generated code artifacts and choose the route. The likely next step is a human-operated
Wix implementation pass on the staging site, with the agent only assisting through local code review
and count/status verification. Publishing, live capture, tracking, API usage, and fake lead testing
remain separate, explicit phases.
