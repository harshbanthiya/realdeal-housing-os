# Phase 5.7 First Owner/Unit Canonical Merge

Date: 2026-06-08

Phase 5.7 created exactly one owner/unit canonical contact from one approved
`merge_candidate` review item in the Phase 5.4 owner/unit audit batch.

No building, building unit, property relationship, relationship review item,
message, email, SMS, or WhatsApp outreach was created.

## Selected Candidate

Batch label:

```text
REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001
```

Review item id:

```text
911cb0e3-91ce-4462-a4d5-54f58fb677b4
```

Contact import row id:

```text
6faf5003-e5cb-4467-a2c4-53287424f98f
```

Merge label:

```text
REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001
```

## Guardrails

- one approved `merge_candidate` review item only
- no bulk merge
- no import of new data
- no building, unit, or property relationship creation
- no relationship candidate apply
- no outreach
- counts-only terminal output
- rollback remains dry-run by default

## Candidate Safety

| Item | Result |
|---|---|
| review_type | `merge_candidate` |
| status before apply | `approved` |
| source_format | `unit_resident_workbook` |
| has valid method | yes |
| method count | 2 |
| has contact property hint | yes |
| has inventory import row | yes |
| has building hint | yes |
| has unit hint | yes |
| duplicate conflict detected | no |
| already merged before apply | no |

## Plan Counts

```bash
python3 scripts/plan_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --approved-only
```

| Planned item | Count |
|---|---:|
| contacts to create | 1 |
| contact methods to link | 2 |
| aliases to link | 0 |
| lead requirements to link | 0 |
| property hints to trace | 1 |
| inventory import rows to trace | 1 |
| skips | 0 |

## Apply Counts

Dry-run:

```bash
python3 scripts/apply_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --merge-label REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001 \
  --real-ok
```

Apply:

```bash
python3 scripts/apply_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 \
  --merge-label REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001 \
  --real-ok \
  --apply
```

| Applied item | Count |
|---|---:|
| canonical contacts created | 1 |
| contact methods linked | 2 |
| canonical merge links | 3 |
| property hints traced | 1 |
| inventory import rows traced | 1 |
| lead requirements linked | 0 |

Canonical contacts changed from 2 to 3. Linked canonical contact methods changed
from 5 to 7.

## Post-Apply Verification

| Item | Result |
|---|---:|
| selected review item status | `approved` |
| selected row linked to canonical contact | yes |
| Phase 5.4 contact import rows | 58 |
| Phase 5.4 contact methods | 116 |
| Phase 5.4 contact aliases | 58 |
| Phase 5.4 contact property hints | 58 |
| Phase 5.4 inventory import rows | 58 |
| Phase 5.4 duplicate candidates | 14 |
| Phase 5.4 review items | 188 |
| Phase 5.4 pending review items | 186 |
| Phase 5.4 approved review items | 2 |
| buildings | 0 |
| building aliases | 0 |
| building units | 0 |
| contact property relationships | 0 |
| property relationship review items | 0 |
| communication_sent | false |
| relationship_creation_done | false |

The existing business-lead batch `REAL_PHASE_3_5_TEST_001` remained unchanged.

## Relationship Planner After Merge

`scripts/plan_property_relationship_candidates.py` now resolves canonical contacts
through the applied canonical merge audit trail when direct source hint `contact_id`
fields are still empty.

```bash
python3 scripts/plan_property_relationship_candidates.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --include-property-hints \
  --include-inventory-hints \
  --include-lead-requirements
```

| Planned item | Count |
|---|---:|
| rows considered | 116 |
| building alias candidates | 116 |
| building unit candidates | 116 |
| contact-property relationship candidates | 2 |
| review items | 2 |
| skipped rows | 114 |
| skip:needs_canonical_contact | 114 |

No relationship candidates were applied in Phase 5.7.

## Rollback Dry-Run

Rollback was tested in dry-run mode only:

```bash
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001 \
  --real-ok \
  --confirm-real-rollback
```

| Dry-run item | Count |
|---|---:|
| contacts to delete | 1 |
| contact methods to unlink | 2 |
| lead requirements to unlink | 0 |
| merge batches | 1 |
| merge links to mark | 3 |
| merge batch status change | `applied->rolled_back` |

Rollback was not applied.

## Warnings

- Do not create real building/unit/property relationship rows yet.
- Do not apply property relationship candidates yet.
- Do not send WhatsApp, SMS, email, or messages.
- Do not print raw names, phone numbers, emails, websites, addresses, or private
  client/property data in reports.
