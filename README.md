# Real Deal Housing OS

Local-first operations stack for Real Deal Housing OS.

## Before Every Phase

Start Docker Desktop manually if needed, then run this from the project root:

```bash
./stop.sh
./start.sh
docker ps
./scripts/check_db.sh
```

Continue only if:

- `realdeal-postgres` is running.
- `realdeal-n8n` is running.
- `realdeal-nocodb` is running.
- `realdeal-adminer` is running.
- `./scripts/check_db.sh` passes.

At the end of every phase, run:

```bash
./scripts/check_db.sh
git status --short
```

Do not diagnose Postgres issues until Docker Desktop and the containers have been restarted and `./scripts/check_db.sh` has been run.

## Phase 3 Contact Import MVP

The contact import flow is lossless and review-first:

```bash
python3 scripts/profile_contact_file.py imports/contacts/test_simple_phonebook.csv
python3 scripts/normalize_contact_file.py imports/contacts/test_simple_phonebook.csv
python3 scripts/clean_contacts.py exports/contacts/<normalized_file>
python3 scripts/contact_dedupe_report.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
```

Database import is dry-run by default. Apply mode is not implemented yet.

Real input files belong in `imports/contacts/`. Generated outputs belong in `exports/contacts/`. Both folders are ignored by Git.

## Phase 3.2 Archive Workflow

For large archives, profile first and only normalize selected files:

```bash
python3 scripts/profile_archive.py imports/contacts/raw_archives/Archive.zip
python3 scripts/profile_contact_file.py exports/archive_profiles/<archive>/extracted/<file>
python3 scripts/normalize_contact_file.py exports/archive_profiles/<archive>/extracted/<file>
python3 scripts/clean_contacts.py exports/contacts/<normalized_file>
python3 scripts/contact_dedupe_report.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
python3 scripts/contact_import_summary.py exports/contacts/<cleaned_file>
```

The importer remains dry-run by default. Do not use `--apply` until the import policy and review screens are ready.

Warnings:

- Some `.csv` files are actually UTF-16 tab-delimited Meta/Facebook exports.
- VCF and Google Contacts files can contain multiple phones/emails; preserve all values.
- PDFs may be text-extractable or scanned/image-only. OCR is not implemented.
- Property inventory sheets should feed a future inventory import path, not only contact import.
- Archive 2 adds building/member workbook patterns and image-only screenshot folders. PNG/JPG files are marked `image_only_needs_ocr`; scanned PDFs remain profile-only.
- XLSX profiling scans the first 10 rows for likely table headers because some workbooks contain title/merged rows before the real table.

## Phase 3.3 Source-Aware Import Schema

Phase 3.3 adds source-aware database tables for review before canonical merge:

- `source_files`
- `contact_methods`
- `lead_requirements`
- `inventory_import_rows`
- `import_review_items`

It also adds review views for NocoDB and a safe planning script:

```bash
python3 scripts/plan_source_aware_import.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
```

Both commands are dry-run only. `--apply` is intentionally disabled for source-aware imports.

Apply/check the schema with:

```bash
./scripts/apply_schema.sh
./scripts/check_db.sh
```

See `docs/SOURCE_AWARE_SCHEMA.md` for the review flow.

## Phase 3.4 Fake Source-Aware Apply Test

Phase 3.4 adds the first guarded write path for fake `.example` data only. It writes into source-aware import/audit tables and does not create or merge canonical contacts.

Example fake workflow:

```bash
python3 scripts/profile_contact_file.py imports/contacts/sample_simple_phonebook.csv.example
python3 scripts/normalize_contact_file.py imports/contacts/sample_simple_phonebook.csv.example --output-dir exports/contacts/phase_3_4_fake
python3 scripts/clean_contacts.py exports/contacts/phase_3_4_fake/<normalized_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/contact_dedupe_report.py exports/contacts/phase_3_4_fake/<cleaned_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/plan_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file>
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --apply --fake-ok
```

Cleanup is also guarded:

```bash
python3 scripts/cleanup_fake_import_batch.py
python3 scripts/cleanup_fake_import_batch.py --apply
```

Real imports remain disabled. Never use this fake apply script with raw samples, raw archives, or real client files.

## Phase 3.5 Real Source-Aware Audit Import

Phase 3.5 allows one controlled real cleaned CSV to be written into source-aware audit/import tables only. Canonical contacts are still protected.

```bash
python3 scripts/profile_contact_file.py imports/contacts/raw_samples/<small_real_file>
python3 scripts/normalize_contact_file.py imports/contacts/raw_samples/<small_real_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/clean_contacts.py exports/contacts/phase_3_5_real/<normalized_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/contact_dedupe_report.py exports/contacts/phase_3_5_real/<cleaned_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/plan_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --apply --real-ok --batch-label REAL_PHASE_3_5_TEST_001
```

Rollback is dry-run first:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001 --apply
```

Real source-aware imports are tagged with `source_aware_only=true` and `canonical_merge_done=false`. Do not merge canonical contacts until a later reviewed workflow exists.
