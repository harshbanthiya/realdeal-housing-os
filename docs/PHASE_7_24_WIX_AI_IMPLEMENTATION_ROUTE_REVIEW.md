# Phase 7.24 - Wix AI Implementation Route Review

Phase 7.24 reviews the Phase 7.23 generated Wix AI build artifacts and records the least-manual
implementation path for the blank Wix staging site. This is not a manual drag/drop build plan. The
goal remains to let Codex/Claude build or sync as much of the Gallery White site as Wix allows, with
the operator doing only unavoidable platform setup.

No Wix API call was made. No Wix API key was requested, read, stored, or used. No publishing, real
domain connection, public indexing, live form, live webhook, tracking, lead creation, contact change,
or message send happened.

## Selected Route

Selected route: `wix_git_cli`

Fallback route: `wix_custom_element_velo`

Reason: the Phase 7.23 package already contains code artifacts that can be reviewed and then synced
or pasted by an AI-assisted workflow. Wix Git Integration + Wix CLI for Sites is the least-manual
route if available. If it is not available for the staging site, the fallback is one Wix-hosted
Custom Element plus Velo page code. Snippet/embed is a last resort only.

## Artifact Review Summary

Reviewed 11 ignored artifacts under:

```text
exports/wix_ai_builds/dlf-westpark-gallery-white-v1/
```

All 11 artifact review rows passed. The review checked presence, rough file size/line counts, no
secret assignment, no API key value, no webhook URL, no real email/phone-like values, no literal Wix
preview URL, placeholder preservation where required, Custom Element suitability, Velo suitability,
and SEO text in the static preview DOM.

The generated artifacts remain ignored and are not committed.

## Minimum Operator Setup Tasks

Primary Git/CLI route:

1. `check_git_integration_available` - confirm whether Wix Git Integration + Wix CLI for Sites is
   available on the blank staging site.
2. `connect_github_repo` - if available, connect the staging site to a GitHub repository controlled
   by the operator.
3. `install_wix_cli` - install/use Wix CLI for Sites only when explicitly approved by the operator.
4. `preview_site` - preview the staging site after AI-assisted sync/paste is complete.
5. `report_status` - report whether Git/CLI setup succeeded or whether fallback is needed.

Fallback if Git/CLI is unavailable:

6. `enable_velo` - enable Velo/dev mode for the Custom Element fallback.
7. `add_custom_element` - add one Custom Element container for the generated component.

These are platform setup tasks only. They are not section-by-section visual build tasks.

## AI Execution Steps After Setup

After review and operator setup clear, Codex/Claude can proceed with:

1. `sync_generated_code` - sync or prepare generated Gallery White code through the chosen route.
2. `verify_local_preview` - verify the local/staging preview with DOM SEO text, placeholders, and no
   live submission path.
3. `report_build_status` - report build status and remaining blocked gates without printing the
   staging URL.

Current status: all three steps are `planned`, not ready for execution yet.

## Review And Readiness

Created:

- 1 route decision: `wix_git_cli`, `pending`
- 11 artifact reviews: all `passed`
- 7 operator setup tasks: all `pending`
- 3 AI execution package steps: all `planned`
- 8 implementation review items: all `pending`

Readiness:

- `ready_for_operator_setup=true`
- `ready_for_ai_execution_after_setup=false`
- `ready_for_code_paste_or_sync=false`
- `ready_for_fake_lead_test=false`
- `ready_for_production_publish=false`

All route flags stay safe:

- `requires_wix_api_key_count=0`
- `requires_publish_permission_count=0`
- `requires_live_webhook_count=0`
- `manual_drag_drop_required_count=0`

## What Remains Blocked

- Wix API usage and Wix API key creation/use
- publishing
- real-domain connection
- public indexing
- live form submission
- live webhook creation
- tracking pixels/tags
- fake lead test
- production publish
- launch push
- contact creation/merge
- messages/outreach

## Cleanup Dry-Run

```bash
python3 scripts/cleanup_dlf_wix_ai_implementation_route_review.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

The dry-run reports only Phase 7.24 rows as the deletion set and preserves Phase 7.23 execution
plans/artifacts plus ignored `exports/` files.

## Next Phase

1. Check Git Integration + Wix CLI availability.
2. If available, connect Git/Wix CLI and report status.
3. If unavailable, enable Velo and add one Custom Element.
4. Then let Codex/Claude perform the AI-assisted code sync/paste.
5. Preview the staging site.
6. Run staging QA.

Fake lead testing remains a later, separately gated phase.
