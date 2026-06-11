# Phase 7.4 — DLF n8n Workflow Blueprint

Phase 7.4 prepares the n8n automation architecture for DLF lead intake without building or
activating anything in n8n. It is a database blueprint and review layer only.

> No n8n API calls, no live n8n workflows, no live webhooks, no Wix API calls, no WhatsApp/email
> calls, no inbound real leads, no contacts, no sends, no publishing, and no webhook secrets.

## What the migration adds

`schemas/025_n8n_launch_workflow_blueprint.sql` adds five planning tables:

| Table | Purpose |
| ----- | ------- |
| `launch_n8n_workflow_blueprints` | Planned workflow shells and activation state. |
| `launch_n8n_workflow_nodes` | Planned workflow nodes/steps. |
| `launch_n8n_payload_schemas` | Expected lead-intake payload schema and validation metadata. |
| `launch_n8n_test_cases` | Fake-only dry-run cases for future workflow validation. |
| `launch_n8n_review_items` | Human review queue before build or activation. |

It also adds six dashboards:

- `vw_launch_n8n_workflow_blueprint_dashboard`
- `vw_launch_n8n_node_dashboard`
- `vw_launch_n8n_payload_schema_dashboard`
- `vw_launch_n8n_test_case_dashboard`
- `vw_launch_n8n_review_queue`
- `vw_dlf_n8n_readiness`

The readiness view keeps `ready_to_activate=false` and requires reviews before
`ready_to_build_in_n8n` can become true. In Phase 7.4, `external_call_allowed_count=0`.

## Workflow blueprints

The seed creates six planned blueprints:

| Workflow key | Status | Activation |
| ------------ | ------ | ---------- |
| `wix_lead_intake_webhook` | planned | not_created |
| `lead_payload_validation` | planned | not_created |
| `lead_attribution_and_scoring` | planned | not_created |
| `operator_review_task_creation` | planned | not_created |
| `duplicate_contact_check` | planned | not_created |
| `error_handling_and_dead_letter` | planned | not_created |

No `n8n_workflow_id` is set and no webhook secret is stored.

## Planned nodes

The blueprints include planned nodes for webhook trigger, payload normalization, validation,
consent checks, UTM parsing, duplicate checks, planned inbound-lead/event insert points, scoring,
operator review creation, internal notification planning, dead-letter handling, and retry policy.
Every node remains `planned` and `human_review_required=true`.

## Payload schema

One draft schema, `dlf_lead_intake_payload_v1`, defines field groups only:

- required: name, phone or email, consent flags, source, landing page slug
- optional: budget, configuration, timeframe, site visit interest, message
- PII fields: name, phone, email
- consent fields: WhatsApp opt-in, email opt-in
- UTM fields: source, medium, campaign, content

Dashboard views expose counts of these groups only, not payload values.

## Fake test cases

The seed creates seven fake-only test cases: valid brochure request, missing consent, duplicate
phone/email, missing phone/email, high-budget hot lead, referral lead, and bad payload.
All are `draft`, `uses_fake_data=true`, `creates_real_lead=false`, and
`external_call_allowed=false`.

## Review gates

Review items are created for workflow blueprints, payload schema, privacy, consent, error
handling, activation, and each fake test case. Build and activation remain blocked until a later
human review phase.

## Why nothing is live

Phase 7.4 does not call n8n, create workflows, register webhooks, activate anything, call Wix,
call messaging APIs, or insert inbound leads. It only records the intended architecture and the
human review queue needed before a future build phase.

## Commands

```bash
python3 scripts/seed_dlf_n8n_workflow_blueprint.py \
  --launch-key dlf-westpark-andheri-west --real-ok

python3 scripts/seed_dlf_n8n_workflow_blueprint.py \
  --launch-key dlf-westpark-andheri-west --real-ok --apply

python3 scripts/cleanup_dlf_n8n_workflow_blueprint.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

The cleanup command is dry-run by default. Real deletion requires `--apply --real-ok` and refuses
if any workflow was built or activated, any external call was allowed, any test case executed, or
any inbound lead exists from this blueprint source.

## Next phase

Phase 7.5 added a view-only operator cockpit on top of the launch, lead-intake, and n8n readiness
layers. Phase 7.11 later prepares an ignored, inactive n8n workflow template package for human
inspection only. It still does not call n8n, import a workflow, create a webhook, or activate
anything. See `docs/PHASE_7_11_DLF_N8N_BUILD_PACKAGE.md`.
