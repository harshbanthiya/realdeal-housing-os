# Phase 7.9 — DLF Contact Permission Evidence & Suppression Review

Phase 7.9 builds an **evidence-based** permission and suppression review for the DLF Westpark launch
candidates. It records, per candidate and channel, whether an **explicit** channel permission exists,
and records a suppression-check result — **without** granting any permission, approving any contact
for campaign, writing to the suppression list, or enabling send/publish. The launch remains
**safe_blocked**.

## Why explicit permission is required

A contact may only be messaged on a channel where there is an explicit `channel_permissions` **allowed**
record (consent basis). There are **0** such records today, so no candidate is contactable. This phase
makes that gap explicit rather than assuming permission. A `permission_decision` of `allowed` is
**only** ever derived from a real `channel_permissions` allowed row — never invented.

## What was added

Migration `schemas/030_dlf_contact_permission_evidence.sql`:

- **Tables:** `launch_contact_permission_evidence`, `launch_contact_suppression_checks`,
  `launch_contact_permission_decision_log` (append-only audit).
- **Views** (mask names via `mask_name()`, no phone/email/address):
  `vw_dlf_contact_permission_evidence_dashboard`, `vw_dlf_contact_suppression_check_dashboard`,
  `vw_dlf_contact_permission_decision_dashboard`, `vw_dlf_campaign_selection_guardrail`.

Scripts (dry-run by default; writes require `--real-ok` + `--apply`):
`scripts/review_dlf_contact_permission_evidence.py` and
`scripts/revert_dlf_contact_permission_evidence.py`.

## Evidence rows created

For each of the 5 candidates × {whatsapp, email} = **10** evidence rows. Because there are 0
`channel_permissions` allowed records, every row is `evidence_type=unknown`,
`evidence_status=needs_review`, `permission_decision=needs_more_info`. **0** rows are `allowed`. An
in-transaction guard refuses if any evidence row were `allowed` without a backing
`channel_permissions` row.

## Suppression check status

**5** suppression checks created, all `clear` — the contacts are not on `outreach_suppression_list`
(which has 0 rows). The check **never writes** to `outreach_suppression_list`. Because the list is
clear, each candidate's `suppression_status` became `clear` and its `suppression_review` item became
`approved` — this is **suppression-list-clear only**, *not* a consent approval. A guard refuses if any
check were marked `suppressed` without a backing suppression-list row.

## Why contacts remain blocked / why no candidate was approved

- `whatsapp_permission_status` / `email_permission_status` stay `needs_review` / `unknown`.
- `candidate_status` stays `needs_permission_review` for all 5 (none approved).
- `approved_for_segment` = **0**; `channel_permissions` allowed = **0**;
  `vw_dlf_campaign_selection_guardrail.ready_for_campaign_selection` = **false** (hard stop: *no
  explicit channel permission on record*).
- `consent_ready` stays `needs_review`; `suppression_checked` and `whatsapp_template_approved` stay
  `pending`.

Suppression being clear does **not** make a contact contactable — that still requires explicit opt-in
evidence plus human campaign approval.

## Why no send / publish / API calls happened

Nothing was sent or published. No Wix/n8n/WhatsApp/email/social API was called, no webhook created,
no contact/lead created or merged, no row written to `channel_permissions` or
`outreach_suppression_list`. `send_enabled=0`, `publish_enabled=0`, `external_call_allowed=0`,
`active_n8n=0`, `ready_for_launch_push=false`, `safety_status=safe_blocked`. Contacts remain `4`;
inbound leads `0`. The in-transaction guard refuses if any of: send/publish/n8n activation,
ready_for_launch_push, a granted channel permission, an approved-for-segment candidate, a passed
consent_ready / whatsapp_template_approved, an unbacked `allowed` evidence row, or an unbacked
`suppressed` check would result.

## Rollback

```
python3 scripts/revert_dlf_contact_permission_evidence.py \
  --launch-key dlf-westpark-andheri-west --reviewed-by "h b" \
  --decision-notes "Dry-run rollback verification for Phase 7.9 permission evidence review." \
  --real-ok --apply
```

It deletes the Phase 7.9 evidence / suppression-check / decision-log rows, restores candidate
`suppression_status`, and restores the `suppression_review` items. Refuses if send/publish was enabled
or any candidate was approved_for_segment. (The dry-run for this phase was verified — would revert 10
evidence + 5 checks + 30 log rows + 5 review items + 5 candidate statuses — and **not** applied.)

## Next steps

1. Collect explicit opt-in evidence (record real `channel_permissions` allowed rows per
   contact/channel) before any contact use.
2. WhatsApp template provider approval planning (external).
3. Controlled test lead capture later, once explicit consent + provider approval are in place.
