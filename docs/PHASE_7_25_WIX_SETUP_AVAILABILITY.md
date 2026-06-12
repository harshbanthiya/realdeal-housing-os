# Phase 7.25 - Wix Git/CLI Availability Check

Phase 7.25 records the operator setup availability state for the DLF Westpark Wix implementation
route selected in Phase 7.24.

This phase does not implement the site. It records that the operator has not yet confirmed whether
Wix Studio supports the preferred Git Integration + Wix CLI route or the fallback Custom Element +
Velo route.

## Current Decision

- selected path: `blocked`
- path status: `needs_more_info`
- availability checks: 6 `needs_more_info`
- setup review items: 5 `pending`
- operator setup readiness: `true`
- AI code execution readiness: `false`
- fake lead test readiness: `false`
- production publish readiness: `false`

This is not a final implementation rejection. It is a safe pause until the operator checks Wix Studio
capabilities.

## Migration

Migration `schemas/043_dlf_wix_setup_availability_check.sql` adds:

- `wix_ai_setup_availability_checks`
- `wix_ai_selected_execution_paths`
- `wix_ai_setup_review_items`

Read-only views:

- `vw_wix_ai_setup_availability_dashboard`
- `vw_wix_ai_selected_execution_path_dashboard`
- `vw_wix_ai_setup_review_queue`
- `vw_dlf_wix_ai_setup_readiness`

## Applied Safe Path

The applied Phase 7.25 path is `needs_more_info` because no operator-confirmed capability result was
provided.

Dry-run command:

```bash
python3 scripts/record_dlf_wix_setup_availability.py \
  --launch-key dlf-westpark-andheri-west \
  --reported-by "h b" \
  --decision-notes "Operator has not yet confirmed Wix Git Integration, Wix CLI, Velo, or Custom Element availability. Setup path remains needs_more_info." \
  --mark-needs-more-info \
  --confirm-no-wix-api-key \
  --confirm-no-wix-api-call \
  --confirm-real-domain-not-connected \
  --confirm-public-indexing-disabled \
  --confirm-page-not-published \
  --confirm-no-live-form \
  --confirm-no-live-webhook \
  --confirm-no-external-tracking \
  --real-ok
```

Apply command adds `--apply` to the same command. The script is dry-run by default and refuses to run
without all safety confirmations.

## Operator Step

The exact next operator step is to check Wix Studio for these capabilities and report only the status:

1. Git Integration availability.
2. Wix CLI for Sites availability.
3. GitHub repository connection availability.
4. Velo availability.
5. Custom Element availability.
6. Code paste availability.

Do not provide or create a Wix API key. Do not publish, connect a real domain, enable public indexing,
create a live form, create a live webhook, or enable tracking.

## AI Step After Setup

After the operator reports capability status:

- if Git Integration + Wix CLI are available, select `wix_git_cli` and have AI sync the generated code
  after setup review clears;
- if Git/CLI is unavailable but Velo + Custom Element are available, select
  `wix_custom_element_velo` and have AI prepare/paste/sync the Custom Element and Velo page code after
  setup review clears;
- if neither path is available, keep the implementation blocked and do not perform manual drag/drop.

No AI code execution happens while path status is `needs_more_info`.

## Safety Guardrails

Phase 7.25 confirms:

- no Wix API call
- no Wix API key requested, read, stored, or used
- no real domain connected
- no public indexing enabled
- no page published
- no live form created
- no live webhook created
- no external tracking enabled
- no inbound leads created
- no contacts created or merged
- no messages sent
- no generated `exports/` artifacts staged

## Cleanup Dry-Run

```bash
python3 scripts/cleanup_dlf_wix_setup_availability.py \
  --launch-key dlf-westpark-andheri-west \
  --real-ok
```

Expected cleanup dry-run counts:

- availability checks: 6
- selected paths: 1
- setup reviews: 5
- Phase 7.24 route decisions/artifact reviews preserved: 1/11
- ignored `exports/` artifacts untouched
