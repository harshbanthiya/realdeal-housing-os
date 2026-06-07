# Review Actions

Phase 3.7 adds safe tools for updating review statuses in source-aware audit tables. These actions do not merge contacts, create contacts, send messages, send WhatsApp, or send email.

## Review Statuses

Review item statuses:

- `pending`
- `approved`
- `rejected`
- `skipped`
- `needs_more_info`
- `merged_later`

Duplicate candidate statuses:

- `pending_review`
- `not_duplicate`
- `duplicate_confirmed`
- `needs_more_info`
- `skipped`

## Single Review Item Update

Dry-run first:

```bash
python3 scripts/update_review_item.py \
  --review-item-id <review_item_id> \
  --status needs_more_info \
  --reviewed-by admin
```

Apply only after checking the dry-run:

```bash
python3 scripts/update_review_item.py \
  --review-item-id <review_item_id> \
  --status needs_more_info \
  --reviewed-by admin \
  --decision-notes "Needs source check" \
  --apply
```

The script prints only IDs, statuses, review type, batch label, and timestamps.

## Bulk Review Update

Bulk updates are dry-run by default and must be scoped by batch label, review type, and from/to status.

```bash
python3 scripts/bulk_update_review_items.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-type lead_requirement_review \
  --from-status pending \
  --to-status needs_more_info \
  --reviewed-by admin \
  --limit 2
```

Apply only when the count is expected:

```bash
python3 scripts/bulk_update_review_items.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-type lead_requirement_review \
  --from-status pending \
  --to-status needs_more_info \
  --reviewed-by admin \
  --limit 2 \
  --apply
```

Bulk updates only change `import_review_items` status fields and create action log rows.

## Duplicate Candidate Update

Dry-run:

```bash
python3 scripts/update_duplicate_candidate.py \
  --candidate-id <candidate_id> \
  --status needs_more_info \
  --reviewed-by admin
```

Apply:

```bash
python3 scripts/update_duplicate_candidate.py \
  --candidate-id <candidate_id> \
  --status needs_more_info \
  --reviewed-by admin \
  --decision-notes "Review duplicate manually" \
  --apply
```

This does not merge contacts.

## Action History

Status updates are logged in `review_action_log`. NocoDB views show action history counts where useful.

## Rollback Concept

To reverse a mistaken status change, run the same single-item update with the previous status. The action log preserves both changes.

## NocoDB Inspection

Open NocoDB:

```text
http://localhost:8080
```

Inspect:

- `vw_review_dashboard_summary`
- `vw_review_queue`
- `vw_review_duplicate_candidates`
- `review_action_log`

Filter by:

```text
REAL_PHASE_3_5_TEST_001
```

Review approvals do not send messages and do not merge canonical contacts.
