# Phase 7.11 — DLF Inactive n8n Workflow Build Package

Phase 7.11 prepares a local, importable **inactive** n8n workflow template for DLF Westpark lead
intake. It does not call n8n, does not create a workflow, does not create a live webhook, does not
activate anything, and does not send or publish.

The generated artifact is intentionally ignored:

`exports/n8n_templates/dlf-westpark-lead-intake-inactive-template.json`

## What was added

Migration `schemas/032_dlf_n8n_build_package.sql`:

- **Tables:** `launch_n8n_build_packages`, `launch_n8n_build_validation_results`,
  `launch_n8n_build_review_items`.
- **Views:** `vw_dlf_n8n_build_package_dashboard`, `vw_dlf_n8n_build_validation_dashboard`,
  `vw_dlf_n8n_build_review_queue`, `vw_dlf_n8n_build_readiness`.

Scripts:

- `scripts/create_dlf_n8n_workflow_template.py`
- `scripts/cleanup_dlf_n8n_build_package.py`

Both are dry-run by default; writes require `--real-ok --apply`.

## Generated package

The generator creates one inactive template package for:

`DLF lead intake webhook -> validate -> normalize -> attribution -> scoring -> create review task placeholder`

The template uses a placeholder test path:

`/webhook-test/dlf-westpark-lead-intake-placeholder`

It includes a disabled no-op placeholder for messaging-related outputs. It does not contain WhatsApp,
email, SMS, social, Wix, or n8n credentialed send nodes.

## Validation checks

Seven validation results were created and all passed:

- `no_credentials`
- `no_live_webhook_url`
- `no_activation`
- `placeholder_paths_only`
- `fake_payload_compatible`
- `no_send_nodes_enabled`
- `no_external_credentials`

Five review items remain pending: build package, security, privacy, manual import, and activation
blocker review.

## Safety state

Current Phase 7.11 counts:

- build packages: 1 validated
- validation results: 7 passed
- review items: 5 pending
- `workflow_created_in_n8n=0`
- `activation_requested=0`
- active n8n workflows: 0
- `ready_for_manual_import=false`
- `ready_to_activate=false`

The launch remains `safe_blocked`. `inbound_leads=0`, contacts remain 4, send/publish counts remain
0, and no communications were sent.

## Manual inspection before import

A human must inspect the JSON before any later import attempt:

1. Confirm `active=false`.
2. Confirm no `credentials` block exists.
3. Confirm no live URL is present.
4. Confirm the webhook path is placeholder/test-only.
5. Confirm send-related nodes are disabled/no-op placeholders.
6. Confirm review items are resolved before any manual import.

Manual import is **not approved in this phase**. Activation remains blocked even if manual import is
approved later.

## Cleanup dry-run

```bash
python3 scripts/cleanup_dlf_n8n_build_package.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

The cleanup script deletes only Phase 7.11 package rows when run with `--apply --real-ok`. It refuses
if any package has `workflow_created_in_n8n=true`, `activation_requested=true`, or
`package_status='approved_for_manual_import'`. Artifact deletion is opt-in with `--delete-artifacts`.

## Next phase

Next work should be manual review of the build package, or a later controlled inactive import phase.
No live capture, workflow activation, webhook exposure, sends, or publishing should happen without an
explicit activation phase.
