# Phase 5.6 Owner/Unit Review Approval And Merge Prep

Date: 2026-06-08

Phase 5.6 approved exactly two owner/unit `merge_candidate` review items from the
Phase 5.4 real owner/unit audit batch and prepared the canonical merge scripts for
a later contact-only owner/unit merge phase.

No canonical merge apply was run. No canonical contacts, buildings, building units,
property relationships, messages, emails, SMS, or WhatsApp outreach were created.

## Batch

Batch label:

```text
REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001
```

Selected source format:

```text
unit_resident_workbook
```

## Approved Review Items

The following two review items were changed from `pending` to `approved`:

| Review item id | Contact import row id |
|---|---|
| `911cb0e3-91ce-4462-a4d5-54f58fb677b4` | `6faf5003-e5cb-4467-a2c4-53287424f98f` |
| `75bb7bad-4232-4da1-8fed-ae25b7778aa9` | `c26ccdca-bd59-42aa-adfe-8f49656b58e2` |

Approval was done with `scripts/update_review_item.py`, dry-run first, then
`--apply`. Each status change wrote one `review_action_log` row.

## Review Status Counts

After approval:

| Item | Count |
|---|---:|
| Phase 5.4 pending review items | 186 |
| Phase 5.4 approved review items | 2 |
| Selected approved review items | 2 |
| Selected review action log rows | 2 |

## Canonical Merge Planning Results

Each approved review item was planned separately. Counts are identical for both
items:

| Planned item | Count |
|---|---:|
| batch_count | 1 |
| is_real_import | 1 |
| planned_contacts_to_create | 1 |
| planned_contact_methods_to_link | 2 |
| planned_aliases_to_link | 0 |
| planned_lead_requirements_to_link | 0 |
| planned_contact_property_hints_to_trace | 1 |
| planned_inventory_import_rows_to_trace | 1 |
| planned_skips | 0 |

Commands:

```bash
python3 scripts/plan_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --approved-only

python3 scripts/plan_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id 75bb7bad-4232-4da1-8fed-ae25b7778aa9 \
  --approved-only
```

## Merge Script Prep

`scripts/plan_canonical_merge.py` now requires one-row planning for
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` and refuses a targeted review item unless
it is exactly one approved `merge_candidate` from the named batch.

`scripts/apply_canonical_merge.py` now recognizes
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` as an allowlisted future real merge batch.
Dry-run output includes:

- contact methods to link
- aliases to link
- lead requirements to link
- property hints to trace
- inventory import rows to trace
- canonical merge link count
- `relationship_creation_done=false`
- `communication_sent=false`

The future owner/unit merge path remains contact-only. It does not create buildings,
building units, `contact_property_relationships`, or property relationship review
items. Property and inventory evidence is traced through counts and merge metadata
because the current `canonical_merge_links.merge_action` constraint only supports
contact/method/alias/lead merge actions.

## Rollback Review

No rollback was run because no canonical merge apply was run. Existing real rollback
remains dry-run by default, requires `--real-ok --confirm-real-rollback` for real
merge labels, and refuses rollback when `communication_sent=true`.

## Deferred To Phase 5.7

Phase 5.7 may create canonical contacts for these two approved review items, but
only after an explicit final approval to run `scripts/apply_canonical_merge.py` with
`--apply --real-ok`.

Phase 5.7 must still remain contact-only unless a later property relationship phase
is explicitly approved.

## Warnings

- No canonical merge apply was run in Phase 5.6.
- No canonical contacts were created.
- No buildings, building units, or property relationships were created.
- No property relationship candidates were applied.
- No outreach, WhatsApp, SMS, email, or messages were sent.
- Do not print raw names, phone numbers, emails, websites, addresses, or private
  client/property data in reports.
