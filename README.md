# Real Deal Housing OS

Local-first operations stack for Real Deal Housing OS.

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
