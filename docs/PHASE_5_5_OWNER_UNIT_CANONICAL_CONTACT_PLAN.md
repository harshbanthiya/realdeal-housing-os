# Phase 5.5 Owner/Unit Canonical Contact Plan

Phase 5.5 analyzed the Phase 5.4 owner/unit audit batch and selected a tiny first
set of rows that can be reviewed for future canonical contact creation. This phase
is planning only: no review statuses were changed, no canonical contacts were
created, no buildings/units/relationships were created, and no outreach was sent.

## Current Batch State

- batch label: `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`
- source format: `unit_resident_workbook`
- contact import rows: 58
- contact methods: 116
- contact aliases: 58
- contact property hints: 58
- inventory import rows: 58
- duplicate candidates: 14
- import review items: 188 pending

Canonical contact baseline:

- canonical contacts: 2
- canonical contact methods linked: 5

Protected property tables remain empty:

- buildings: 0
- building_units: 0
- contact_property_relationships: 0
- property_relationship_review_items: 0

`REAL_PHASE_3_5_TEST_001` remained unchanged:

- contact import rows: 22
- contact methods: 62
- duplicate candidates: 1
- review items: 45
- review status: 40 pending / 4 approved / 1 needs_more_info

## Why Canonical Contacts Come First

Property relationships need a reviewed `contacts.id` before they can safely point
to a person. The Phase 5.4 owner/unit rows are still source-aware audit rows. They
can contain duplicates, stale unit facts, incomplete labels, or ambiguous ownership
signals. Creating relationship rows before canonical contact review would make the
relationship graph hard to trust and hard to roll back.

The relationship planner therefore correctly skipped the Phase 5.4 signals as
`needs_canonical_contact`.

## Candidate Analysis Counts

Generated with:

```bash
python3 scripts/owner_unit_candidate_summary.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --limit 2 \
  --source-format unit_resident_workbook
```

Counts:

| Item | Count |
|---|---:|
| total import rows | 58 |
| rows with valid contact method | 58 |
| rows with multiple contact methods | 58 |
| rows with property hint | 58 |
| rows with inventory hint | 58 |
| rows with unit hint | 58 |
| rows with building hint | 58 |
| rows with duplicate candidate involvement | 6 |
| rows already linked to canonical contacts | 0 |
| candidate rows safe for review | 52 |
| risky rows | 6 |

Review items by type/status:

| Review type | Status | Count |
|---|---|---:|
| duplicate_contact | pending | 14 |
| inventory_match_review | pending | 58 |
| merge_candidate | pending | 58 |
| property_hint_review | pending | 58 |

Duplicate candidate status:

| Status | Count |
|---|---:|
| pending_review | 14 |

Risk reason:

| Reason | Count |
|---|---:|
| duplicate_review_first | 6 |

## Selected Tiny First Candidate Set

These rows are not duplicate-involved and have contact methods, building hints,
unit hints, and inventory hints.

| contact_import_row_id | review_item_id | source_row_number | recommended_action | reason |
|---|---|---:|---|---|
| `6faf5003-e5cb-4467-a2c4-53287424f98f` | `911cb0e3-91ce-4462-a4d5-54f58fb677b4` | 2 | approve_for_canonical_contact | complete_owner_unit_audit_row |
| `c26ccdca-bd59-42aa-adfe-8f49656b58e2` | `75bb7bad-4232-4da1-8fed-ae25b7778aa9` | 3 | approve_for_canonical_contact | complete_owner_unit_audit_row |

## Dry-Run Approval Commands

Run these first in a later approval phase. They do not write because `--apply` is
omitted:

```bash
python3 scripts/update_review_item.py \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --status approved \
  --reviewed-by "h b" \
  --decision-notes "P5.5 owner/unit review: safe candidate for future canonical contact creation; audit-only, no relationship creation"

python3 scripts/update_review_item.py \
  --review-item-id 75bb7bad-4232-4da1-8fed-ae25b7778aa9 \
  --status approved \
  --reviewed-by "h b" \
  --decision-notes "P5.5 owner/unit review: safe candidate for future canonical contact creation; audit-only, no relationship creation"
```

## Apply Commands For Later

These commands were generated but **not run** in Phase 5.5:

```bash
python3 scripts/update_review_item.py \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --status approved \
  --reviewed-by "h b" \
  --decision-notes "P5.5 owner/unit review: safe candidate for future canonical contact creation; audit-only, no relationship creation" \
  --apply

python3 scripts/update_review_item.py \
  --review-item-id 75bb7bad-4232-4da1-8fed-ae25b7778aa9 \
  --status approved \
  --reviewed-by "h b" \
  --decision-notes "P5.5 owner/unit review: safe candidate for future canonical contact creation; audit-only, no relationship creation" \
  --apply
```

## Canonical Merge Script Gap Analysis

- `scripts/plan_canonical_merge.py` can see `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`
  and accepts a `--review-item-id`, but it plans only approved `merge_candidate`
  items. The selected review items are still pending, so current output is
  `planned_contacts_to_create=0` and `skip_reason_not_approved=1`.
- `scripts/apply_canonical_merge.py` real mode requires `--review-item-id`,
  `--real-ok`, `--merge-label`, and `--batch-label`, and creates at most one
  canonical contact at a time.
- `scripts/apply_canonical_merge.py` currently has a default real-batch guard for
  `REAL_PHASE_3_5_TEST_001`; Phase 5.4 owner/unit merge would require either
  `--allow-other-batch` or a Phase 5.6-specific allowed batch update.
- The apply script links `contact_methods` and `lead_requirements`; it does not link
  `contact_property_hints` or `inventory_import_rows`.
- The apply script sets `inventory_hints_linked=0` and does not create buildings,
  units, or property relationships, which is good for keeping Phase 5.6 contact-only.
- `scripts/rollback_canonical_merge.py` can dry-run and roll back canonical contacts
  and method/lead links for real merge batches. It does not need to touch property
  hints or inventory rows if Phase 5.6 remains contact-only.

Changes needed before Phase 5.6:

- Add or document an explicit Phase 5.6 owner/unit real-batch allowlist for
  `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`.
- Keep one approved review item per merge.
- Keep unresolved duplicate guard.
- Add owner/unit-specific metadata/tags such as phase `5.6` and source format
  `unit_resident_workbook`.
- Decide whether to record `contact_property_hints` and `inventory_import_rows` in
  `canonical_merge_links` metadata without creating relationship rows.
- Preserve the current rule: no building/unit/property relationship creation during
  canonical contact merge.

## Relationship Planner Follow-Up

For `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`:

| Planner item | Count |
|---|---:|
| rows considered | 116 |
| building alias candidates | 116 |
| building unit candidates | 116 |
| contact-property relationships | 0 |
| review items | 0 |
| skipped rows | 116 |
| `skip:needs_canonical_contact` | 116 |

## Recommendation For Phase 5.6

Phase 5.6 should approve at most the two selected `merge_candidate` review items,
then run a guarded one-at-a-time canonical contact merge dry-run before any apply.
It should remain canonical-contact-only: link contact methods, preserve source
traceability, and do not create buildings, building units, or property
relationships.

## Warnings

- No review status changes were applied in Phase 5.5.
- No canonical contacts were created.
- No canonical contacts were merged.
- No buildings, units, or property relationships were created.
- No WhatsApp, SMS, email, or other outreach was sent.
- Reports must remain counts-only and must not print raw names, phone numbers,
  emails, websites, addresses, or private client/property data.
