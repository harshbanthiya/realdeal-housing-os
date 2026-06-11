# Phase 7.10 — DLF Controlled Test Lead Intake

Phase 7.10 proves the DLF Westpark lead-intake validation path using **fake/operator test payloads
only**. It creates no real inbound leads, no contacts, no live webhooks, no API calls, no sends, and
no publishing. The launch remains **safe_blocked** and `ready_for_live_lead_capture` stays **false**.

All test data lives in dedicated `launch_test_lead_*` tables — the real `inbound_leads` and `contacts`
tables are never touched.

## What was added

Migration `schemas/031_dlf_test_lead_intake_harness.sql`:

- **Tables:** `launch_test_lead_payloads`, `launch_test_lead_validation_results`,
  `launch_test_lead_review_items`.
- **Views:** `vw_dlf_test_lead_payload_dashboard`, `vw_dlf_test_lead_validation_dashboard`,
  `vw_dlf_test_lead_review_queue`, `vw_dlf_test_lead_readiness`. Dashboards expose **no** fake
  name/phone/email — only status/type/flags.

Scripts (dry-run by default; writes require `--real-ok` + `--apply`):
`scripts/run_dlf_test_lead_intake.py` and `scripts/cleanup_dlf_test_lead_intake.py`.

## Fake payload scenarios (5)

| test_key | type | scenario | result |
| --- | --- | --- | --- |
| dlf-test-lead-001 | wix_form | valid brochure request | validated |
| dlf-test-lead-002 | wix_form | missing consent | failed (consent) |
| dlf-test-lead-003 | whatsapp_click | missing phone & email | failed (required) |
| dlf-test-lead-004 | instagram_link | high-budget hot lead | validated |
| dlf-test-lead-005 | referral_link | referral lead | validated |

Fake contact values use clearly-fake, non-routable placeholders (`FAKE DLF TEST LEAD 00x`,
`FAKE-PHONE-…`, `…@example.invalid`). They are stored only in the `fake_*` columns, never printed,
and never exposed by any view. Every payload is `uses_fake_data=true`, `creates_real_contact=false`,
`creates_real_lead=false`, `external_call_made=false`.

## Validations performed

Each payload runs 8 validation types — `required_fields`, `pii_mapping`, `consent_fields`,
`utm_mapping`, `attribution_rule`, `lead_scoring`, `duplicate_check`, `review_item_creation` — for
**40** results: **37 passed**, **2 failed** (002 consent, 003 required), **1 needs_review** (003 has
no UTM context for a whatsapp_click). **13** review items were queued (5 fake_payload_review, 5
privacy_review, 2 validation_result_review, 1 cleanup_review), all pending.

## Retained vs cleaned

**Retained.** The fake rows are kept for operator dashboard QA. This is safe because they live in
dedicated test tables (not `inbound_leads`/`contacts`), are flagged fake and tagged
`raw_context.phase='7.10'`/`source='dlf_test_lead_intake'`, and expose no contact values. The cleanup
dry-run was verified (would delete 5 payloads + 40 validations + 13 reviews; real tables untouched)
and **not** applied. To zero them later:

```
python3 scripts/cleanup_dlf_test_lead_intake.py --launch-key dlf-westpark-andheri-west --real-ok --apply
```

(It refuses if any test payload is flagged real/external, and never deletes real leads/contacts.)

## No live webhook / API, no real leads/contacts

No Wix/n8n/WhatsApp/email/social API was called, no webhook created. `inbound_leads` stays **0**;
`contacts` stays **4**; `lead_attribution_events` unchanged. No contact created or merged. An
in-transaction guard refuses if any test payload were flagged real/external, if send/publish were
enabled, if `ready_for_launch_push` or the test `ready_for_live_lead_capture` would become true, or if
any real `inbound_leads` row were created by the harness.

## Why live capture remains blocked

`vw_dlf_test_lead_readiness.ready_for_live_lead_capture` mirrors the real
`vw_dlf_lead_intake_readiness` gate, which is **false**. Live capture requires approved field mappings,
an active endpoint, and operator approval — none of which exist. A passing fake test does **not**
unlock live capture. `send_enabled=0`, `publish_enabled=0`, `external_call_allowed=0`, `active_n8n=0`,
`ready_for_launch_push=false`, `safety_status=safe_blocked`.

## Next steps

1. Approve lead field mappings (move them out of `draft`).
2. Build the inactive n8n workflow (no activation).
3. Run a local webhook test later (still no live external endpoint).
4. Controlled live lead capture only after explicit approval + consent basis.
