# Phase 7.8 — DLF Consent, Suppression & Lead-Privacy Readiness

Phase 7.8 reviews the **process-level** consent / suppression / lead-privacy posture of the DLF
Westpark launch and records the decisions in an audit log — **without** granting any contact
permission, approving any contact for campaign, passing WhatsApp provider approval, or enabling
send/publish. The launch remains **safe_blocked**.

## What was added

Migration `schemas/029_dlf_consent_privacy_readiness.sql`:

- **Table** `launch_consent_privacy_review_log` — audit log of process-level consent/privacy review
  decisions (never changes a contact permission).
- **Views** (counts/status only, no contact values):
  - `vw_dlf_consent_privacy_readiness` — one-row posture: form/consent/PII counts, pending permission
    & suppression reviews, channel permissions allowed, suppressed contacts, consent/lead-privacy
    process status, and the campaign/lead-capture readiness flags.
  - `vw_dlf_contact_permission_gap_dashboard` — who is blocked by unknown consent, grouped by
    candidate/permission/suppression status, with a recommended action (no names).
  - `vw_dlf_lead_form_privacy_dashboard` — lead-form consent/PII posture and privacy review status.
  - `vw_dlf_suppression_readiness_dashboard` — suppression-process posture and blocked reason.

Scripts (dry-run by default; writes require `--real-ok` + `--apply`):
`scripts/review_dlf_consent_privacy_readiness.py` and
`scripts/revert_dlf_consent_privacy_readiness.py`.

## Consent / privacy process reviewed

The review (`--approve-lead-form-privacy-process --approve-suppression-process
--mark-contact-permissions-needs-review`) recorded four audit rows: `lead_form_consent` and
`privacy_field_mapping` = **process_approved**, `suppression_process` = **process_approved**, and
`contact_permission_queue` = **needs_more_info**.

## Lead-form privacy status

The lead capture form has consent fields (3) and PII field mappings (name/email/phone = 3), and no
live lead capture is enabled, so the **lead_privacy_reviewed** readiness check was marked **passed**
at the process level. The form stays `draft` with `publish_enabled=false`; passing this check does
not enable anything. Factual placeholders in copy remain (see Phase 7.7).

## Suppression process status

The suppression-check **process** is logged as `process_approved`. The **suppression_checked**
readiness gate is intentionally left **pending**: there are 0 suppression entries and actually
running suppression against contacts is a separate, later step. Process-approved ≠ executed.

## Contact-level permission remains unresolved

There are **0** `channel_permissions` with an `allowed` status, so there is no explicit consent basis
for any contact. The 9 WhatsApp/email permission review items (with no allowed record) were moved to
**needs_more_info**, and **consent_ready** was set to **needs_review** (explicitly **not** passed).
The 5 segment_fit and 5 suppression review items remain pending. No segment candidate was approved.

## Why no contacts are approved for campaign

A contact may only be used with an explicit `channel_permissions` allowed record plus suppression
clearance and human approval — none of which exist. `approved_for_segment` stays **0** and
`ready_for_campaign_selection` stays **false**. The script never sets a candidate to
approved_for_segment and never inserts a channel permission; an in-transaction guard rolls back if
either would happen.

## Why WhatsApp template approval remains pending

`whatsapp_template_approved` is provider-side (WhatsApp Business template approval) and external to
this repo. This phase never touches it; it stays **pending**. Internal copy review (Phase 7.7) is not
provider approval.

## Why no send / publish / API calls happened

Nothing was sent or published. No Wix/n8n/WhatsApp/email/social API was called, no webhook created,
no contact/lead created or merged. `send_enabled=0`, `publish_enabled=0`, `external_call_allowed=0`,
`active_n8n=0`, `ready_for_launch_push=false`, `safety_status=safe_blocked`. Contacts remain `4`;
inbound leads `0`. An in-transaction guard refuses if any send/publish/n8n flag, `ready_for_launch_push`,
a channel permission, an approved-for-segment candidate, a passed `consent_ready`, or a passed
`whatsapp_template_approved` would result.

## Rollback

```
python3 scripts/revert_dlf_consent_privacy_readiness.py \
  --launch-key dlf-westpark-andheri-west --reviewed-by "h b" \
  --decision-notes "Dry-run rollback verification for Phase 7.8 consent/privacy review." \
  --real-ok --apply
```

It deletes the Phase 7.8 log rows, restores `lead_privacy_reviewed` and `consent_ready` to their
prior status, and restores the permission review items. Refuses if send/publish was enabled after the
review. (The dry-run for this phase was verified — would revert 4 log rows + 2 checks + 9 permission
items — and **not** applied.)

## Next steps

1. Explicit contact permission review (record real `channel_permissions` allowed/denied basis before
   any contact use).
2. WhatsApp provider template approval planning (external).
3. Controlled test lead capture later, once consent + suppression + provider approval are in place.
