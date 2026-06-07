# Canonical Merge Workflow

Phase 3.8 introduces a fake-only review-to-canonical merge workflow. It proves the shape of a future merge without allowing real contacts to be merged.

## Safety Rules

- Real canonical merge is disabled.
- Merge scripts refuse real batches.
- Merge scripts only allow labels starting with `FAKE_`.
- Only approved `merge_candidate` review items are eligible.
- Dry-run is the default for rollback.
- No messages, WhatsApp, or email are sent.
- Raw names, phone numbers, and emails should not be printed during merge testing.

## Migration 006

`schemas/006_canonical_merge_workflow.sql` adds:

- `canonical_merge_batches`
- `canonical_merge_links`
- `contacts.is_test`
- `contacts.source_import_batch_id`
- `contacts.source_merge_batch_id`
- `contacts.canonical_status`
- `vw_canonical_merge_batches`
- `vw_canonical_merge_links`

These objects keep a reversible audit trail for test canonical contacts.

## Fake Test Flow

Create a fake source-aware import from `.example` data, approve a small number of fake merge candidates, plan the merge, apply the fake merge, and roll it back.

```bash
python3 scripts/plan_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --limit 2

python3 scripts/apply_canonical_merge.py \
  --batch-label FAKE_PHASE_3_8_MERGE_TEST \
  --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE \
  --limit 2

python3 scripts/apply_canonical_merge.py \
  --batch-label FAKE_PHASE_3_8_MERGE_TEST \
  --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE \
  --limit 2 \
  --apply \
  --test-ok
```

The apply command creates test canonical contacts and links test contact methods or lead requirements. It does not touch real import batches.

## Rollback

Rollback is dry-run by default:

```bash
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE
```

Apply rollback only after checking the counts:

```bash
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --apply
```

Rollback unlinks test methods and lead requirements, deletes test canonical contacts, and marks the merge batch as rolled back. Source-aware import rows remain in place for audit.

## Real Merge Policy

Real canonical merge is not enabled yet. The real batch `REAL_PHASE_3_5_TEST_001` remains review-only until a separate, explicit real merge workflow is designed and approved.
