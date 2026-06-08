# Source-Aware Import Schema

Phase 3.3 adds a database layer for traceable, reversible, review-first imports. It does not merge imported people into canonical contacts automatically.

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

Continue only if `realdeal-postgres`, `realdeal-n8n`, `realdeal-nocodb`, and `realdeal-adminer` are running and `./scripts/check_db.sh` passes.

At the end of every phase, run:

```bash
./scripts/check_db.sh
git status --short
```

Do not diagnose Postgres issues until Docker Desktop and the containers have been restarted and `./scripts/check_db.sh` has been run.

## AppleDouble Troubleshooting

On external drives, macOS may create metadata junk files such as `.DS_Store` and `._*`. If Postgres fails after the standard phase startup checklist, inspect these files with a dry run first:

```bash
./scripts/clean_appledouble_junk.sh
```

Delete only after reviewing the dry-run output:

```bash
./scripts/clean_appledouble_junk.sh --apply
```

This only removes macOS metadata junk files. It does not repair database corruption.

## Why `source_files` Exists

`source_files` is the audit trail for each raw file or archive member that was profiled. It stores file identity, archive path, detected format, sheet details, row counts, columns, and safe profile metadata.

This lets a future reviewer answer: which file, sheet, archive member, and import batch produced this row?

## Why `contact_methods` Exists

Older exports often contain many phone numbers, WhatsApp numbers, emails, websites, and map links for one row. Squeezing those into `contacts.phone_primary` or `contacts.email` would lose information.

`contact_methods` stores each method separately with:

- Raw and normalized values.
- Method type such as mobile, landline, email, website, or Google Maps.
- Source file, sheet, and row.
- Validation status.
- Link back to either a canonical contact or a pending import row.

Canonical contacts can later choose primary methods after review.

## Why `lead_requirements` Exists

Property portal, campaign, ad, and inquiry exports describe what a lead wants, not only who the lead is. `lead_requirements` preserves purpose, property type, locality, city, budget, campaign, platform, and requirement text.

These rows should be reviewed before creating follow-up tasks or matching inventory.

## Why `inventory_import_rows` Is Separate

Inventory sheets often describe apartments, units, prices, availability, and owners. Some rows have no contact at all. Treating those as fake contacts would corrupt the CRM.

`inventory_import_rows` preserves unit and listing facts separately from contacts. Matching to canonical `inventory` happens later through review.

## How `import_review_items` Supports NocoDB

`import_review_items` is the human queue. It can point to:

- Contact import rows.
- Inventory import rows.
- Duplicate candidates.
- Source files.
- Lead requirements through context.

Review types include invalid phone/email, duplicate contact, property hint review, inventory match review, lead requirement review, unknown source format, and merge candidate.

NocoDB can use this table and the review views as simple review screens.

## Review Views

Phase 3.3 creates NocoDB-friendly views:

- `vw_import_contact_review`
- `vw_duplicate_review`
- `vw_inventory_import_review`
- `vw_lead_requirements_review`

The contact and duplicate views mask phone and email values where possible.

## Recommended Review Flow

1. Profile raw files and archives.
2. Normalize selected sources into ignored exports.
3. Clean and dedupe.
4. Run dry-run import planning.
5. Review source-aware counts and duplicate candidates.
6. Apply only schema migrations, not contact inserts.
7. Use NocoDB views to inspect review queues once real apply mode is designed.
8. Merge into canonical contacts only after human approval.

## Canonical Contacts Stay Protected

Phase 3.3 deliberately avoids automatic merging into `contacts`. Imported rows remain traceable and reversible until a future reviewed merge workflow is implemented.

## Phase 3.4 Fake Apply Workflow

Phase 3.4 tests the first source-aware DB write path with fake `.example` data only.

The guarded script is:

```bash
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file>
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --apply --fake-ok
```

It requires both `--apply` and `--fake-ok` before writing. It refuses raw samples, raw archives, non-`exports/contacts` inputs, and cleaned rows whose source files do not look like fake sample/example data.

The fake batch is marked with:

```text
FAKE_PHASE_3_4_TEST
```

The script may insert into:

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

It does not create canonical contacts.

`contact_property_hints` are later consumed by the Phase 5.2 property hint to
relationship candidate workflow. That workflow is still guarded and review-first:
it plans counts from hints, requires a canonical/test contact before materializing
relationship candidates, and does not import real owner sheets or send outreach.
See `docs/PROPERTY_HINT_TO_RELATIONSHIP_WORKFLOW.md`.

## Phase 3.4 Rollback Workflow

Fake rows can be removed with:

```bash
python3 scripts/cleanup_fake_import_batch.py
python3 scripts/cleanup_fake_import_batch.py --apply
```

The cleanup script targets only batches whose metadata contains `batch_label = FAKE_PHASE_3_4_TEST`, or one explicit fake `--import-batch-id`. It is dry-run by default.

## What To Inspect In NocoDB

After a fake apply, inspect these tables and views:

- `source_files`
- `contact_methods`
- `lead_requirements`
- `inventory_import_rows`
- `import_review_items`
- `vw_import_contact_review`
- `vw_duplicate_review`
- `vw_inventory_import_review`
- `vw_lead_requirements_review`

Phone and email review views should show masked values where possible. Real imports remain disabled.

## Phase 3.5 Real Audit Import

Phase 3.5 introduces the first controlled real import path into source-aware audit/import tables only.

The apply script is:

```bash
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --apply --real-ok --batch-label REAL_PHASE_3_5_TEST_001
```

It refuses to write unless all of these are present:

- `--apply`
- `--real-ok`
- `--batch-label`

It also refuses batch labels that start with `FAKE`, inputs outside `exports/contacts/`, and files that do not look like `cleaned_contacts_*.csv`.

The import batch metadata is marked:

```json
{
  "is_real_import": true,
  "canonical_merge_done": false,
  "source_aware_only": true,
  "created_by_phase": "3.5"
}
```

Canonical contacts are not created or updated.

## Phase 3.5 Real Rollback

Real rollback is dry-run by default:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001
```

Apply cleanup only after review:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001 --apply
```

The cleanup script requires either `--batch-label` or `--import-batch-id`, and refuses to delete unless the target batch metadata says `source_aware_only=true` and `canonical_merge_done=false`.

For NocoDB review, inspect:

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
- `vw_import_contact_review`
- `vw_duplicate_review`
- `vw_inventory_import_review`
- `vw_lead_requirements_review`

## Phase 3.6 NocoDB Review Views

Phase 3.6 adds a review workflow for the first real source-aware audit batch:

```text
REAL_PHASE_3_5_TEST_001
```

New masked review views:

- `vw_review_dashboard_summary`
- `vw_review_contact_methods`
- `vw_review_business_leads`
- `vw_review_duplicate_candidates`
- `vw_review_queue`
- `vw_review_batch_sources`

Helper functions:

- `mask_phone(text)`
- `mask_email(text)`

Use `vw_review_dashboard_summary` first, then sources, business leads, contact methods, duplicate candidates, and finally the review queue.

Reviewing does not merge into canonical contacts. Do not send messages, WhatsApp, or email from this system yet.

## Phase 3.7 Review Action Statuses

Phase 3.7 adds `review_action_log` and expands review statuses for controlled human review.

Review item updates use:

```bash
python3 scripts/update_review_item.py --review-item-id <id> --status needs_more_info --reviewed-by admin
```

Bulk review updates and duplicate candidate updates are also dry-run by default. All write actions require `--apply`.

Review actions update source-aware review tables only. They do not create canonical contacts, merge contacts, or send messages.

## Phase 3.8 Canonical Merge Test Schema

Phase 3.8 adds fake-only canonical merge tables and views:

- `canonical_merge_batches`
- `canonical_merge_links`
- `vw_canonical_merge_batches`
- `vw_canonical_merge_links`

It also adds nullable/source fields to `contacts`:

- `is_test`
- `source_import_batch_id`
- `source_merge_batch_id`
- `canonical_status`

The merge apply script only accepts fake/test batches and labels beginning with `FAKE_`. Real canonical merge remains disabled.

Use:

```bash
python3 scripts/plan_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --limit 2
python3 scripts/apply_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --limit 2 --apply --test-ok
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --apply
```

See `docs/CANONICAL_MERGE_WORKFLOW.md`.

## Phase 4 — first real canonical merge

The source-aware tables (`source_files`, `contact_import_rows`, `contact_methods`,
`lead_requirements`) are the immutable audit base for canonical merges. Phase 4
(2026-06-08) created the first real canonical contact from one approved
`merge_candidate` review item in `REAL_PHASE_3_5_TEST_001`, linking 2 contact
methods and 1 lead requirement via `canonical_merge_links`. **These source-aware
rows are never mutated or deleted by merge or rollback** — only `contacts` and the
`contact_id` foreign keys on methods/leads change. See
`docs/PHASE_4_FIRST_REAL_CANONICAL_MERGE.md`.

Phase 4.1 (migration `007_canonical_review_dashboard.sql`) adds masked review views
that read this source-aware base read-only — `vw_canonical_source_trace` joins a
canonical contact back through `canonical_merge_links` to its `source_files` /
`contact_import_rows` / `import_review_items` row without exposing raw values. See
`docs/CANONICAL_CONTACT_REVIEW.md`.

Phase 5.1 (migration `008_property_relationship_pipeline.sql`) builds on this base:
`contact_property_relationships` references `source_contact_import_row_id`,
`source_property_hint_id`, `source_inventory_import_row_id`, and `source_file_id`, so
each contact↔building/unit link traces back to the same source-aware rows. The
source-aware `contact_property_hints` are the raw signal that becomes a reviewed
relationship. See `docs/PROPERTY_RELATIONSHIP_PIPELINE.md`.
