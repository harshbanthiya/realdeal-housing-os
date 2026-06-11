# Phase 7.7 — DLF Westpark Campaign Copy & Consent-Language Review

Phase 7.7 is an **internal** review of the DLF launch campaign copy and consent/opt-out language. It
replaces the now-confirmed project-name placeholder with the public name **DLF Westpark**, records
which draft copy is internally clean vs. which still needs factual verification, and changes nothing
about sending or publishing. No copy is sent, no page is published, no API is called, no contact is
selected, and the WhatsApp provider template is **not** marked provider-approved.

The launch remains **safe_blocked**.

## Project name

The public project name is confirmed as **DLF Westpark** (Phase 7.6). This phase replaces the
`[PROJECT_NAME_CONFIRM]` placeholder with `DLF Westpark` in draft text fields of the message
templates, social drafts, and landing page spec. After this phase, `[PROJECT_NAME_CONFIRM]` count is
**0**. The previous working name `DLF Westend / The Westpark Andheri West` is historical context only.

## What the review tool does

Script: `scripts/review_dlf_campaign_copy.py` (dry-run by default; writes require `--real-ok` +
`--apply`). Each action is opt-in by flag:

| Flag | Effect |
| ---- | ------ |
| `--replace-project-name-placeholders` | `[PROJECT_NAME_CONFIRM]` → `DLF Westpark` in draft text fields only. Factual placeholders are kept. |
| `--approve-safe-internal-copy` | Copy/consent review items whose linked copy has **no** remaining factual placeholder → `approved` (internal copy review only). |
| `--mark-unverified-factual-claims-needs-more-info` | Copy review items whose linked copy still has a factual placeholder → `needs_more_info`. |

`--limit N` caps how many review items are processed. The tool writes only the template/social/
landing **text + raw_context** and the `launch_draft_review_items` review marks. It refuses
`--enable-send`, `--enable-publish`, `--mark-ready-for-launch-push`, and
`--pass-whatsapp-provider-approval`, and an in-transaction guard rolls everything back if any
send/publish/n8n flag would flip.

### Command run

```
python3 scripts/review_dlf_campaign_copy.py \
  --launch-key dlf-westpark-andheri-west --reviewed-by "h b" \
  --decision-notes "Internal copy review after confirming public project name as DLF Westpark. Sending/publishing remains disabled." \
  --replace-project-name-placeholders --approve-safe-internal-copy \
  --mark-unverified-factual-claims-needs-more-info --real-ok --apply
```

## What was approved internally (8)

Copy/consent review items whose linked draft copy contained no unverified factual placeholder:

- whatsapp_copy_review: **5 approved**
- email_copy_review: **1 approved**
- compliance_review: **1 approved**
- consent_review: **1 approved** (the opt-out / consent-language review — internal language only)

"Approved" here means **internal copy review passed**. It is recorded as
`raw_context.internal_copy_reviewed=true` on the linked draft; the template/social `*_status` stays
`draft` and `send_enabled`/`publish_enabled` stay false. It is **not** provider approval and **not** a
send/publish gate.

## What remains needs_more_info (21)

Copy whose draft still contains a factual placeholder that must be verified before use:

- social_copy_review: **15** (every social draft still carries `[RERA_VERIFY]` / `[VERIFY]` /
  `[VISUAL_DIRECTION_PENDING]`)
- whatsapp_copy_review: **2**
- email_copy_review: **3**
- compliance_review: **1**

## Why RERA / price / brochure / Wix placeholders remain

These are factual claims that are not yet verified, so the placeholders are intentionally **kept**:
`[RERA_VERIFY]`, `[PRICE_VERIFY]`, `[BROCHURE_LINK_PENDING]`, `[WIX_PAGE_PENDING]`, `[VERIFY]`, and
`[VISUAL_DIRECTION_PENDING]`. Only the confirmed project name was substituted. RERA registration,
pricing, brochure links, and the Wix page must be verified through their own review steps before
these tokens are resolved.

## Why WhatsApp provider approval is not complete

The `whatsapp_template_approved` readiness check stays **pending**. Internal copy review is not the
same as WhatsApp Business provider template approval, which is an external process. This phase
deliberately does not touch any `launch_readiness_check`, so the consent, lead-privacy, and
WhatsApp-provider blockers all remain open.

## No send / publish / API calls

Nothing was sent or published. No Wix/n8n/WhatsApp/email/social API was called, no webhook created,
no contact selected/created/merged, no lead created. `send_enabled=0`, `publish_enabled=0`,
`external_call_allowed=0`, `active_n8n=0`, `communication_sent=0`, `published=0`,
`ready_for_launch_push=false`, `safety_status=safe_blocked`. Contacts remain `4`; inbound leads `0`.

## Rollback

Script: `scripts/revert_dlf_campaign_copy_review.py` (dry-run by default). Undoes only the Phase 7.7
markers: restores review items to their previous status, swaps `DLF Westpark` back to
`[PROJECT_NAME_CONFIRM]` in the stamped rows, and removes the `internal_copy_reviewed` markers. It
refuses if any send/publish flag was enabled after the review.

```
python3 scripts/revert_dlf_campaign_copy_review.py \
  --launch-key dlf-westpark-andheri-west --reviewed-by "h b" \
  --decision-notes "Dry-run rollback verification for Phase 7.7 campaign copy review." \
  --real-ok --apply
```

(Rollback dry-run for this phase was verified — would restore 29 review items + 12 template / 15
social / 1 landing rows — and **not** applied.)

## Next steps

1. Contact permission / suppression review (consent + suppression blockers).
2. Lead privacy review (`lead_privacy_reviewed`).
3. Wix form / landing page approval.
4. n8n blueprint review (no activation).
5. Controlled test lead capture later, once the above are clear.
