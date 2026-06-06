# Source-Aware Import Schema

Phase 3.3 adds a database layer for traceable, reversible, review-first imports. It does not merge imported people into canonical contacts automatically.

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
