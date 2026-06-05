# Lossless Multi-Source Contact Import

Phase 3 is a lossless import pipeline for old phone exports, messy owner/contact sheets, structured building workbooks, Google Maps business lead exports, and manual CSVs.

The pipeline is review-first. It profiles a source file, normalizes it into a standard intermediate CSV, cleans and parses that intermediate file, creates duplicate candidates, and only then allows a database dry-run. Real inserts require an explicit future `--apply` path.

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

- Strong: same normalized phone.
- Medium: same normalized email.
- Weak: similar cleaned display name plus same building code/name and unit.

Duplicate candidates are not automatic merges.

## Dry Run First

The database import script is dry-run by default. It counts what would be inserted into:

- `contacts`
- `contact_import_rows`
- `contact_aliases`
- `contact_property_hints`
- `contact_duplicate_candidates`

At this MVP stage, `--apply` intentionally says apply mode is not implemented.

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
