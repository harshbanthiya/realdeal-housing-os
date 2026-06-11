# Phase 7.6 — DLF Launch Blocker Triage & Project-Name Confirmation

Phase 7.6 adds safe operator tooling to **triage launch blockers** and to **confirm the public
project name — but only when an operator explicitly supplies it**. It is three read-only views plus
two guarded write scripts and one revert script. Nothing here sends, publishes, calls an external
API, scrapes, activates n8n, enables any send/publish flag, approves campaigns/copy, or
creates/merges contacts or leads.

The launch remains **safe_blocked**. The single biggest blocker — *the public project name is not
confirmed* — is left **pending** in this phase because the operator did not supply a confirmed
public name. This phase deliberately does **not** invent, assume, or web-verify the name.

## Blocker triage views

Migration `schemas/027_dlf_launch_blocker_triage.sql` adds three views (no new tables):

| View | Purpose |
| ---- | ------- |
| `vw_dlf_launch_blocker_triage` | One row per OPEN blocker (open readiness checks + open operator tasks), grouped into operator-facing areas: `project_identity`, `consent`, `suppression`, `copy_review`, `lead_capture`, `n8n`, `publishing`, `sending`. Each row carries `safe_summary`, `recommended_action`, `can_be_closed_by_operator`, and `requires_external_action`. |
| `vw_dlf_project_identity_status` | The name-confirmation state: current display name, internal alias, possible public name, `project_name_confirmed_status`, RERA status, `public_name_ready_for_copy` (false until confirmed), and `blocked_reason`. Reads state only — never confirms. |
| `vw_dlf_launch_activation_guardrail` | The hard activation guardrail: send/publish/external/n8n counts, `live_lead_capture_ready`, `contacts_approved_for_campaign`, `ready_for_launch_push`, `safety_status`, and `hard_stop_reason`. Reads the existing real gates; cannot make them true. |

No view exposes names, phones, emails, addresses, websites, raw contact rows, raw lead payloads, or
full message/caption bodies. Triage rows are status/severity/safe-summary only.

`can_be_closed_by_operator` is true for `project_identity`, `consent`, `suppression`, and
`copy_review` (an operator can close these by review). `requires_external_action` is true for
`lead_capture`, `n8n`, `publishing`, and `sending` (these need an external system stood up).

## Project-name confirmation workflow

Script: `scripts/confirm_dlf_project_identity.py` (dry-run by default).

```
python3 scripts/confirm_dlf_project_identity.py \
  --launch-key dlf-westpark-andheri-west \
  --confirmed-project-display-name "<OPERATOR-SUPPLIED PUBLIC NAME>" \
  --confirmed-public-slug "<optional-slug>" \
  --confirmed-by "h b" \
  --decision-notes "Operator confirmed public project name." \
  --real-ok --apply
```

On apply (requires BOTH `--real-ok` and `--apply`) it:

- sets `launch_projects.project_display_name` to the confirmed value;
- stamps `launch_projects.raw_context`: `project_name_confirmed=true`,
  `confirmed_project_display_name`, `confirmed_public_slug`, `confirmed_by`, `confirmed_at`,
  `previous_display_name`, and a `confirmation_source` marker;
- passes `launch_readiness_checks[project_name_confirmed]`;
- marks `launch_operator_tasks[verify_project_name]` as `done`.

It **refuses** if the confirmed name or `--confirmed-by` is missing, if `--real-ok`/`--apply` are
missing (write), if the name is already confirmed (revert first), or if any of `--enable-send`,
`--enable-publish`, `--mark-ready-for-launch-push` are passed. An in-transaction guard rolls the
whole confirmation back if any send/publish flag or `ready_for_launch_push` would become true.

### Was the project name confirmed in this phase?

**No.** The operator did not supply an explicit confirmed public name, so the script was run as a
dry-run only and the database was not changed. `project_name_confirmed` remains a **pending
blocker**; `public_name_ready_for_copy` remains **false**. The internal alias `DLF Westend` and the
possible public name `DLF The Westpark / Westpark Phase-I` are **not** treated as confirmed.

When the operator supplies the confirmed public name, run the command above with `--real-ok
--apply`.

## Readiness review tooling

Script: `scripts/review_dlf_launch_readiness_check.py` (dry-run by default).

```
python3 scripts/review_dlf_launch_readiness_check.py \
  --check-type consent_ready --status needs_review \
  --reviewed-by "h b" --decision-notes "..." --real-ok --apply
```

It updates one `launch_readiness_checks` row's status and stamps the reviewer/notes into
`raw_context`. It only ever writes the readiness table. Passing/waiving is **refused** for
`project_name_confirmed` (use the confirmation script) and for n8n activation checks
(`n8n_webhook_planned`, `n8n_workflow_ready`); external/live checks (`wix_landing_page_ready`,
`lead_capture_form_ready`, `wix_form_fields_reviewed`) can only be passed with the explicit
`--allow-non-activation-review` flag. An in-transaction guard rolls back if any send/publish/n8n
activation flag is detected.

## Revert tooling

Script: `scripts/revert_dlf_project_identity_confirmation.py` (dry-run by default).

Undoes only a Phase 7.6 confirmation (identified by its `confirmation_source` marker): restores the
previous display name, sets `project_name_confirmed=false`, and sets the readiness check and
operator task back to `pending`. It **refuses** if any send/publish flag was enabled after the
confirmation. With no confirmation applied, the dry-run reports "nothing to revert".

## Why the launch remains safe_blocked

`vw_dlf_launch_activation_guardrail` and `vw_dlf_operator_safety_posture` both report
`safe_blocked`: `send_enabled_count=0`, `publish_enabled_count=0`, `external_call_allowed_count=0`,
`active_n8n_workflows=0`, `live_lead_capture_ready=false`, `contacts_approved_for_campaign=0`,
`communication_sent=0`, `published_count=0`, `ready_for_launch_push=false`. The primary hard-stop
reason remains *project name not confirmed*. Contacts remain `4`; inbound leads remain `0`.

## Why no sends / publishing / API calls happened

This phase is views + guarded review tooling only. No script in this phase enables sending or
publishing, calls Wix/n8n/WhatsApp/email/social APIs, creates webhooks, imports contacts, or
creates leads. Every write path is dry-run by default and gated behind `--real-ok` + `--apply`, with
in-transaction guards that refuse if any activation flag would flip.

## Next steps

1. Operator supplies the confirmed public project name → run `confirm_dlf_project_identity.py
   --real-ok --apply`.
2. Approve key landing page / message / social drafts (still draft, send/publish off).
3. Review contact permission candidates (consent + suppression).
4. Review lead intake and n8n blueprints (no activation yet).
5. Controlled test lead capture later, once the above are clear.
