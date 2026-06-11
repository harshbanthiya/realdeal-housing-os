# Phase 7.13 - DLF n8n Manual Import Verification

Phase 7.13 creates the guarded recordkeeping path for a human-only inactive n8n manual import.
This phase did not perform the manual import. The package remains approved for manual import only,
and activation remains blocked.

## Current outcome

- Manual import was not performed.
- One pending no-import check was recorded in `launch_n8n_manual_import_checks`.
- The build package remains `approved_for_manual_import`.
- `workflow_created_in_n8n=false`.
- `activation_requested=false`.
- All workflow blueprints remain `planned` / `not_created`.
- `ready_for_inactive_manual_import=true`, meaning the package may be manually imported as inactive.
- `ready_to_activate=false`.

No n8n API was called, no workflow was created/imported programmatically, no live webhook was
created, no inbound leads were created, no contacts were created or merged, no messages were sent,
and no publishing happened.

## Migration

`schemas/033_dlf_n8n_manual_import_verification.sql` adds:

- `launch_n8n_manual_import_checks`
- `vw_dlf_n8n_manual_import_check_dashboard`
- `vw_dlf_n8n_manual_import_readiness`

The readiness view keeps `ready_to_activate=false` by design. It separates inactive manual-import
readiness from activation readiness.

## Manual inactive import checklist

Use this checklist only when a human operator imports the ignored template artifact through the n8n
UI. Do not use API import, activation, or webhook creation.

1. Open the ignored template artifact from `exports/n8n_templates/`.
2. Import it manually in n8n as an inactive workflow.
3. Confirm the workflow is not active.
4. Confirm there are no credentials attached.
5. Confirm there is no live webhook URL or exposed webhook secret.
6. Confirm no test payload was sent to a live endpoint.
7. Record only the inactive workflow id/name with the guarded script.

## Record a pending no-import check

This is the path used in Phase 7.13 because no operator-supplied n8n workflow id/name was provided:

```bash
python3 scripts/record_dlf_n8n_manual_import_check.py \
  --launch-key dlf-westpark-andheri-west \
  --checked-by "h b" \
  --decision-notes "Manual import not yet performed. Workflow package remains approved for manual import only." \
  --real-ok --apply
```

This records `check_status=pending` and does not update build package or workflow blueprint state.

## Record an imported-inactive verification later

Run this only after a human operator has manually imported the workflow as inactive and supplies the
workflow id/name:

```bash
python3 scripts/record_dlf_n8n_manual_import_check.py \
  --launch-key dlf-westpark-andheri-west \
  --checked-by "h b" \
  --operator-reported-workflow-id "<OPERATOR_SUPPLIED_ID>" \
  --operator-reported-workflow-name "<OPERATOR_SUPPLIED_NAME>" \
  --confirm-imported-inactive \
  --confirm-no-credentials \
  --confirm-no-live-webhook \
  --confirm-not-active \
  --decision-notes "Operator manually imported DLF workflow into n8n as inactive. No activation requested." \
  --real-ok --apply
```

The script refuses incomplete confirmations. It never calls n8n, never sets activation requested,
and never makes `ready_to_activate` true.

## Rollback dry-run

```bash
python3 scripts/revert_dlf_n8n_manual_import_check.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

The rollback helper is dry-run by default and reverts only Phase 7.13 manual-import check records
and any Phase 7.13 inactive-created package/blueprint marks. It refuses if activation was requested
or if any workflow is active. It does not delete the ignored n8n template artifact and does not
touch leads, contacts, messages, or publishing.

## Verified counts

- manual import checks: 1 pending
- imported inactive verifications: 0
- build package: 1 `approved_for_manual_import` / `workflow_created_in_n8n=false` / `activation_requested=false`
- workflow blueprints: 6 `planned` / `not_created`
- active workflows: 0
- inbound leads: 0
- contacts: 4
- send/publish/communication counts: 0

## Next phase options

Next work can be one of:

- perform the human inactive manual import and record imported-inactive verification,
- complete Wix landing/form approval,
- run a controlled local webhook test after inactive import.

Activation, live webhook exposure, live lead capture, messaging, and publishing remain separate
explicit phases.
