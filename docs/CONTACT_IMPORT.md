# Lossless Multi-Source Contact Import

Phase 3 is a lossless import pipeline for old phone exports, messy owner/contact sheets, structured building workbooks, Google Maps business lead exports, and manual CSVs.

The pipeline is review-first. It profiles a source file, normalizes it into a standard intermediate CSV, cleans and parses that intermediate file, creates duplicate candidates, and only then allows a database dry-run. Real inserts require an explicit future `--apply` path.

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

## Why This Is Lossless

The pipeline never changes the original file. Every normalized row preserves:

- Source file.
- Source sheet, when available.
- Source row number.
- Guessed source format.
- Raw name, phone, email, and notes.
- Original row payload as JSON.

Cleaned and parsed values live in separate fields. A messy name such as `OKR A 101 Person Name` is preserved as `raw_name`, while `OKR`, `A`, `101`, and `Person Name` are extracted separately.

## Raw Fields Versus Parsed Fields

Raw fields come directly from the source file:

- `raw_name`
- `raw_phone`
- `raw_email`
- `raw_notes`
- `raw_payload_json`

Parsed fields are structured guesses:

- `cleaned_display_name`
- `phone_normalized`
- `phone_type`
- `email_normalized`
- `parsed_building_code`
- `parsed_building_name`
- `parsed_wing`
- `parsed_unit_number`
- `parsed_role`
- `parsed_tags`
- `parse_confidence`
- `needs_review`

Raw fields are the audit trail. Parsed fields are workflow helpers.

## Source Profiling

Use `scripts/profile_contact_file.py` before cleaning. It prints a safe summary only:

- Source file basename.
- Detected file type.
- Sheet names for XLSX files.
- Row counts.
- Column names.
- Guessed source format.

It does not print phone numbers or emails.

## Supported Source Formats

### Archive Profiling

Use `scripts/profile_archive.py` for zip archives:

```bash
python3 scripts/profile_archive.py imports/contacts/raw_archives/Archive.zip
```

The archive profiler extracts safely into ignored `exports/archive_profiles/`, skips macOS junk such as `__MACOSX/`, `._*`, and `.DS_Store`, prevents path traversal, and writes safe JSON/Markdown reports under `exports/contacts/`.

Recommended archive workflow:

1. Profile archive.
2. Review source-format counts.
3. Choose representative files by format.
4. Normalize selected files.
5. Clean.
6. Generate duplicate report.
7. Run dry-run import only.

### simple_phonebook_csv

Detected from columns like `Name` and `Phone Number`.

The normalizer creates one intermediate row per source row.

### messy_phonebook_property_csv

Detected from columns like `Name`, `Phone`, `Flat No.`, `N`, and `Telephone 1`.

The normalizer can create two intermediate rows:

- One row from the first `Name` and `Phone`.
- Another row from later flat/name/telephone fields, preserving property hints.

This prevents useful later-column owner details from being treated as junk.

### structured_owner_workbook

Detected from columns like `Wing`, `Flat No.`, `Contact Person 1`, `Contact Person 2`, `Telephone 1`, `Telephone 2`, `Email`, and `Source`.

One source row can become multiple contact rows because two people and two phone numbers may be present.

### google_maps_business_csv

Detected from columns like `Title`, `Rating`, `Reviews`, `Phone`, `Industry`, `Address`, `Website`, and `Google Maps Link`.

These rows are treated as business leads, not apartment owners.

Reduced Google Maps files with `Title`, `Phone`, `Industry`, `Address`, and `Website` are also supported.

### google_contacts_csv

Google Contacts exports can include multiple phone and email columns. The normalizer preserves these in `raw_phones_json` and `raw_emails_json`.

### whatsapp_export_csv

WhatsApp exports with `number`, `Name`, and `Push Name` are normalized as contact rows. Push names are preserved as aliases/notes.

### vcf_contacts_file

VCF files are parsed with the Python standard library. `FN`, `N`, `TEL`, `EMAIL`, `ORG`, and `NOTE` are preserved where present. Large VCF files are supported without printing raw values.

### meta_facebook_leads_utf16_tsv

Some Meta/Facebook exports have a `.csv` extension but are UTF-16 tab-delimited files. These are detected by encoding/delimiter and normalized as leads, not owners.

### portal_property_leads_csv

Portal leads preserve property type, purpose, locality, city, budget, and visit intent in `requirement_json`.

### property_inventory_csv and property_inventory_workbook

Inventory files preserve building, wing, unit, typology, area, rent, sale price, and purpose in `inventory_hint_json`. Inventory import should be a separate workflow from contact import.
If no contact name or phone exists, the normalizer writes zero contact rows and reports that the file should go through a future inventory import path.

### Archive 2 Building And Member Workbooks

Archive 2 adds several building-level workbook patterns:

- `building_owner_tenant_workbook`
- `unit_resident_workbook`
- `project_customer_workbook`
- `imperial_unit_inventory_workbook`
- `society_member_details_workbook`

These files often contain title rows before the actual table. XLSX profiling and normalization scan the first 10 rows for likely headers instead of assuming row 1 is the header.

Rows with contact name plus phone/email can enter the contact import flow while preserving unit, member, occupied-by, parking, typology, broker, and inventory hints. Rows that only contain unit/property/inventory facts should wait for future inventory/member import.

Building-level hints can be supplied later with CLI options such as:

```bash
--building-name "Oberoi Esquire"
--building-name "Imperial Heights"
--building-name "Kalpataru Radiance"
--building-name "Windsor Grande Residences"
```

Those options are documented as future workflow hints; current scripts infer from sheets/columns when safe.

### Image And OCR Sources

PNG/JPG screenshots are classified as `image_only_needs_ocr`. Scanned/image-only PDFs are classified as `scanned_pdf_or_image_only`. No OCR is performed in Phase 3.2.

### PDF, DOCX, TXT, XLS

Text-extractable PDFs can be profiled safely. Scanned PDFs and images are marked as needing OCR/manual review; OCR is not implemented. DOCX/TXT files are profiled for extractable text. Old `.xls` files are marked as `unsupported_xls_needs_conversion`.

### unknown_contact_csv

Unknown files can still be normalized conservatively, but they should be reviewed closely.

## Phonebook Name Parsing

The parser reads known building codes, role words, wing/unit hints, and name remnants.

Example:

```text
OKR A 101 Person Name
```

Possible parsed output:

- `parsed_building_code`: `OKR`
- `parsed_building_name`: `Oak Ridge`
- `parsed_wing`: `A`
- `parsed_unit_number`: `101`
- `cleaned_display_name`: `Person Name`

The original remains `raw_name`.

## Building Codes

Private mappings can live in:

```text
config/building_codes.csv
```

If that file is missing, scripts use the fake example mapping:

```text
config/building_codes.csv.example
```

Real mapping files are ignored by Git because `*.csv` is ignored.

## Wing And Unit Extraction

Supported patterns include:

- `A 1001`
- `A-1001`
- `A Wing 1001`
- `Flat 1001`
- `1001`
- `B 2105`

Explicit normalized hints from structured files can override or supplement parser guesses.

## Role And Source Clues

The parser looks for:

- `owner`
- `broker`
- `agent`
- `tenant`
- `buyer`
- `seller`
- `landlord`
- `reference`
- `existing customer`

Structured file hints such as `Source`, Google Maps `Industry`, website, and map links are preserved as notes/tags rather than discarded.

## Duplicate Candidate Rules

Duplicate reports are conservative:

- Strong: any matching normalized phone.
- Medium: any matching normalized email.
- Weak: similar cleaned display name plus same building code/name and unit.
- Weak business duplicate: same business title and website.

Duplicate candidates are not automatic merges.

## Dry Run First

The database import script is dry-run by default. It counts what would be inserted into:

- `source_files`
- `contacts`
- `contact_import_rows`
- `contact_methods`
- `contact_aliases`
- `contact_property_hints`
- `lead_requirements`
- `inventory_import_rows`
- `contact_duplicate_candidates`
- `import_review_items`

At this MVP stage, `--apply` intentionally says apply mode is not implemented.

## Source-Aware Review Layer

Phase 3.3 adds a review-first database layer around contact imports:

- `source_files` records every raw file, archive member, sheet, row count, detected format, and profile summary.
- `contact_methods` stores each phone, WhatsApp, landline, email, website, map link, or social profile separately.
- `lead_requirements` preserves portal/ad/campaign requirements such as purpose, locality, budget, and property type.
- `inventory_import_rows` stores property/unit rows separately from contacts.
- `import_review_items` gives NocoDB a human review queue before merging.

Canonical `contacts` should not be merged automatically yet. Imported rows should stay traceable to source file, sheet, row, and import batch until a future approval workflow is built.

For dry-run source-aware planning:

```bash
python3 scripts/plan_source_aware_import.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
```

The plan output goes to ignored `exports/contacts/` and contains aggregate counts only.

## Fake Source-Aware Apply Test

Phase 3.4 allows fake `.example` data to be written into source-aware audit tables for testing. This is not a real contact import and does not merge into canonical `contacts`.

Use a dedicated ignored output folder:

```bash
python3 scripts/normalize_contact_file.py imports/contacts/sample_simple_phonebook.csv.example --output-dir exports/contacts/phase_3_4_fake
python3 scripts/clean_contacts.py exports/contacts/phase_3_4_fake/<normalized_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/plan_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file>
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --apply --fake-ok
```

The fake apply script refuses raw samples, raw archives, and inputs that do not look like generated fake/example outputs.

Rollback:

```bash
python3 scripts/cleanup_fake_import_batch.py
python3 scripts/cleanup_fake_import_batch.py --apply
```

After fake apply, check these in NocoDB:

- `source_files`
- `contact_methods`
- `lead_requirements`
- `inventory_import_rows`
- `import_review_items`
- `vw_import_contact_review`
- `vw_duplicate_review`
- `vw_inventory_import_review`
- `vw_lead_requirements_review`

Real canonical imports are still disabled.

## Real Source-Aware Audit Import

Phase 3.5 allows one small real cleaned CSV to be imported into source-aware audit/import tables only.

Guarded dry-run:

```bash
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --batch-label REAL_PHASE_3_5_TEST_001
```

Guarded apply:

```bash
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --apply --real-ok --batch-label REAL_PHASE_3_5_TEST_001
```

This writes only to import/audit tables. It does not create or update canonical contacts.

Rollback dry-run:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001
```

Cleanup apply, only after review:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001 --apply
```

The real cleanup script refuses batches unless they are marked `source_aware_only=true` and `canonical_merge_done=false`.

Inspect the batch in NocoDB before deciding whether to roll it back.

## Where To Place Real Files

Put real files here:

```text
imports/contacts/
```

Outputs go here:

```text
exports/contacts/
```

Both locations are ignored by Git. Only fake `.csv.example` templates should be committed.

## Privacy Rules

- Do not commit real contact files.
- Do not commit cleaned exports from real files.
- Do not print full phone numbers or emails in terminal logs.
- Do not expose `docker/.env`.
- Do not import into Postgres without explicit approval.
- Do not auto-merge contacts.
