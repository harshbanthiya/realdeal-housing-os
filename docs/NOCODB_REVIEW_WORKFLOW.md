# NocoDB Review Workflow

Open NocoDB at:

```text
http://localhost:8080
```

## Before Every Phase

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
