# Phase 7.2 DLF Contact Segmentation And Permission Review

Phase 7.2 creates a masked, review-gated contact segmentation and permission
review layer for the DLF launch workspace.

No messages were sent, no campaigns were enabled, no contacts were created or
merged, and no contacts were approved for campaign selection.

## Why Existing Owners Matter

Existing owner/building contacts are strong launch targets because they are already
known to the company, are tied to similar-ticket property history, and may be useful
for referrals or investor-style conversations. They still require consent and
suppression review before any outreach.

## Baseline Counts

| Item | Count |
|---|---:|
| canonical contacts | 4 |
| active canonical contacts | 4 |
| active owner relationships | 2 |
| active owner relationship building groups | 2 |
| channel permissions | 0 |
| outreach suppression rows | 0 |
| launch projects | 1 |
| launch lead segments | 6 |
| launch message templates | 13 |
| launch campaign calendar rows | 30 |
| send enabled rows | 0 |
| communication sent rows | 0 |
| inbound leads | 0 |

Contact method counts by type/status:

| Method/status | Count |
|---|---:|
| email / valid | 58 |
| google_maps / unverified | 22 |
| mobile / valid | 59 |
| phone / valid | 20 |
| website / unverified | 22 |

## Migration 023

`schemas/023_launch_contact_segmentation.sql` adds:

- `launch_contact_segment_candidates`
- `launch_contact_permission_review_items`
- `launch_contact_segment_audit_log`

Masked/readiness views:

- `vw_launch_contact_segment_candidate_dashboard`
- `vw_launch_contact_permission_review_queue`
- `vw_dlf_contact_segment_readiness`
- `vw_dlf_owner_audience_summary`

The views use masked names only and never expose phone numbers, emails, websites,
addresses, or raw payloads.

## Segment Logic

The guarded planner creates candidate mappings for:

- active owner contacts in active owner/property relationships
- active canonical contacts with valid phone/mobile/WhatsApp/email methods

In this phase, the owner contacts map to `owner_network_referrals`, while other
warm known contacts map to `old_real_estate_contacts_needs_permission_review`.

Planner command:

```bash
python3 scripts/plan_dlf_contact_segments.py \
  --launch-key dlf-westpark-andheri-west \
  --limit 50 \
  --real-ok
```

Apply command:

```bash
python3 scripts/plan_dlf_contact_segments.py \
  --launch-key dlf-westpark-andheri-west \
  --limit 50 \
  --real-ok \
  --apply
```

## Dry-Run Counts

| Item | Count |
|---|---:|
| candidate rows to create | 5 |
| candidate_status: needs_permission_review | 5 |
| segment_reason: active_owner_relationship | 2 |
| segment_reason: existing_warm_contact | 3 |
| review items to create | 19 |
| segment fit review items | 5 |
| WhatsApp permission review items | 5 |
| email permission review items | 4 |
| suppression review items | 5 |
| send enabled | 0 |
| communication sent | 0 |

## Apply Counts

| Item | Count |
|---|---:|
| candidate rows created | 5 |
| review items created | 19 |
| segment fit review items | 5 |
| WhatsApp permission review items | 5 |
| email permission review items | 4 |
| suppression review items | 5 |
| approved for segment | 0 |
| send enabled | 0 |
| communication sent | 0 |

## Permission And Suppression Gates

Permission is never inferred as allowed. `whatsapp_permission_status` and
`email_permission_status` become `allowed` only when an explicit
`channel_permissions` row says `allowed` or `opted_in`.

In this phase:

| Permission/suppression item | Count |
|---|---:|
| WhatsApp needs review | 5 |
| email needs review | 4 |
| email unknown | 1 |
| suppression needs review | 5 |
| suppressed | 0 |

## Human Review Queue

| Review item | Count |
|---|---:|
| segment_fit_review / pending | 5 |
| whatsapp_permission_review / pending | 5 |
| email_permission_review / pending | 4 |
| suppression_review / pending | 5 |

Operators must review segment fit, channel permission, and suppression before any
contact can be considered for a campaign.

## Readiness

| Item | Count/value |
|---|---:|
| total candidates | 5 |
| pending review | 5 |
| needs permission review | 5 |
| approved_for_segment | 0 |
| ready_for_campaign_selection | false |
| dashboard candidate rows | 5 |
| dashboard review rows | 19 |
| owner audience contacts | 2 |
| owner audience candidates | 2 |
| owner audience approved | 0 |

Readiness stays false because no contacts are approved for segment and all
candidates still need permission/suppression review.

## Cleanup Dry-Run

Cleanup is dry-run by default and deletes only rows tagged
`phase=7.2/source=dlf_contact_segment_planning`.

```bash
python3 scripts/cleanup_dlf_contact_segments.py \
  --launch-key dlf-westpark-andheri-west \
  --real-ok
```

Dry-run result:

| Item | Count |
|---|---:|
| candidate rows to delete | 5 |
| review rows to delete | 19 |
| audit rows to delete | 0 |
| approved_for_segment guard | 0 |
| communication_sent guard | 0 |
| campaign-send audit guard | 0 |

Cleanup was not applied.

## Warnings

- Do not send WhatsApp, SMS, emails, calls, or messages.
- Do not enable campaign sends.
- Do not set `send_enabled=true`.
- Do not approve contacts for campaign selection without explicit permission review.
- Do not expose raw contact names, phone numbers, emails, websites, addresses, or
  raw payloads.

## Next Phase Options

- Approve a tiny permission-reviewed segment after human consent/suppression review.
- Build Wix/n8n lead intake for new inbound leads while keeping existing-contact
  outreach disabled.
