# NocoDB Review Workflow

Open NocoDB at:

```text
http://localhost:8080
```

## Before Every Phase

> **Running from an exFAT external drive:** `start.sh` auto-cleans macOS AppleDouble
> junk (`._*`, `.DS_Store`) and stages the Postgres startup with retries. If Postgres
> reports unhealthy, run `./scripts/clean_appledouble_junk.sh --apply` and start again.
> See the README (AppleDouble / exFAT) for details. `docker/.env` is ignored and must
> never be committed.

Start Docker Desktop manually if needed, then run this from the project root:

```bash
./stop.sh
./start.sh
docker ps
./scripts/check_db.sh
```

Continue only if all Real Deal containers are running and `./scripts/check_db.sh` passes.

## AppleDouble Troubleshooting

If Postgres fails after the standard phase startup checklist, check for macOS metadata junk files with a dry run:

```bash
./scripts/clean_appledouble_junk.sh
```

Delete only after reviewing the dry-run output:

```bash
./scripts/clean_appledouble_junk.sh --apply
```

This only removes macOS metadata junk files. It does not repair database corruption.

Use the local Real Deal OS Postgres connection/base. Filter review tables and views by:

```text
REAL_PHASE_3_5_TEST_001
```

## Tables To Inspect

- `import_batches`
- `source_files`
- `contact_import_rows`
- `contact_methods`
- `contact_aliases`
- `contact_property_hints`
- `lead_requirements`
- `inventory_import_rows`
- `contact_duplicate_candidates`
- `import_review_items`

## Views To Inspect

Review in this order:

1. `vw_review_dashboard_summary`
2. `vw_review_batch_sources`
3. `vw_review_business_leads`
4. `vw_review_contact_methods`
5. `vw_review_duplicate_candidates`
6. `vw_review_queue`

The review views mask phone and email values where possible. They are designed for human review, not automatic merge.

## Status Meanings

- `pending`: waiting for human review.
- `approved`: accepted as correct for the current review step.
- `rejected`: rejected as incorrect or not useful.
- `skipped`: intentionally not reviewed or not relevant.
- `needs_more_info`: more investigation is needed.
- `merged`: reserved for a future reviewed merge workflow.

## Review Order

Start with `vw_review_dashboard_summary` to confirm the batch counts and flags:

- `is_real_import`
- `source_aware_only`
- `canonical_merge_done`

Then inspect `vw_review_batch_sources` to confirm the source file and source format.

Next, review `vw_review_business_leads` and `vw_review_contact_methods`.

Then inspect `vw_review_duplicate_candidates`.

Finally, use `vw_review_queue` as the operational task list.

## Warnings

Reviewing does not merge into canonical contacts yet.

Do not send messages, WhatsApp, or email from this system yet.

Do not edit real phone numbers or emails in bulk without a backup and an explicit review plan.

## Safe Summary Command

From the project root:

```bash
python3 scripts/review_batch_summary.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/list_review_views.py
```

Both commands are read-only and print counts/instructions only.

## Review Actions

Phase 3.7 adds safe status-only action scripts:

```bash
python3 scripts/review_queue_summary.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/update_review_item.py --review-item-id <id> --status needs_more_info --reviewed-by admin
python3 scripts/bulk_update_review_items.py --batch-label REAL_PHASE_3_5_TEST_001 --review-type lead_requirement_review --from-status pending --to-status needs_more_info --reviewed-by admin --limit 2
python3 scripts/update_duplicate_candidate.py --candidate-id <id> --status needs_more_info --reviewed-by admin
```

Update scripts are dry-run by default and require `--apply` for writes. They do not merge contacts or send messages. Status changes are logged in `review_action_log`.

## Fake Canonical Merge Review

Phase 3.8 adds fake-only canonical merge test views:

- `vw_canonical_merge_batches`
- `vw_canonical_merge_links`

These are for verifying merge audit trails. As of Phase 4 (2026-06-08), real
canonical merge is enabled for one approved `merge_candidate` review item at a time
(behind `--real-ok`); the first real merge under label
`REAL_PHASE_4_CANONICAL_MERGE_001` created one canonical contact from batch
`REAL_PHASE_3_5_TEST_001`. The remaining review items in that batch stay
review-only (40 pending / 3 approved / 2 needs_more_info, the applied item kept its
`approved` status). Use `vw_canonical_merge_batches` and `vw_canonical_merge_links`
to inspect the audit trail (counts/hints only — no raw contact values). See
`docs/PHASE_4_FIRST_REAL_CANONICAL_MERGE.md`.

Phase 4.1 adds five masked canonical-review views (migration 007):

- `vw_canonical_contacts_review`
- `vw_canonical_contact_methods_review`
- `vw_canonical_source_trace`
- `vw_canonical_lead_requirements_review`
- `vw_canonical_merge_audit`

Open these to review the real canonical contact, trace it to its source
file/import row/review item, and confirm `communication_sent=false`. Names are
masked to an initial and phones/emails are masked. Filter by
`merge_label = REAL_PHASE_4_CANONICAL_MERGE_001`. Full guide:
`docs/CANONICAL_CONTACT_REVIEW.md`.

Phase 4.2 (2026-06-08) added a second canonical contact under merge label
`REAL_PHASE_4_CANONICAL_MERGE_002`. The same five views now show 2 canonical
contacts; filter by either merge label to isolate one. Review statuses are now
40 pending / 4 approved / 1 needs_more_info. See
`docs/PHASE_4_2_SECOND_REAL_CANONICAL_MERGE.md`.
