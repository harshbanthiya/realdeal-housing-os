# Phase 5.3 Real Owner Source Dry-Run

Phase 5.3 tested one small real owner/building/unit-style source through the
planning workflow only. No real database import happened, no canonical contacts
were created, no contacts were merged, no property relationships were created, and
no outreach was sent.

## Selected Source

Selected file:

```text
exports/archive_profiles/Archive_2/extracted/Imperial Heights unit data.xlsx
```

Why selected:

- Small enough for a cautious first real owner/unit dry run: 123 source rows.
- One worksheet only.
- Detected as `unit_resident_workbook`.
- Columns include unit/contact structure: flat number, lessee/contact fields,
  contact numbers, email fields, parking fields.
- Safer than larger multi-sheet owner workbooks and unrelated Google Maps lead
  files.

Other candidates reviewed by metadata only:

| File | Detected source format | Rows / sheets | Decision |
|---|---:|---:|---|
| `imports/contacts/raw_samples/KALPATARU OWNERS DATA.csv` | `messy_phonebook_property_csv` | 1138 rows / CSV | Too large for first Phase 5.3 dry run. |
| `imports/contacts/raw_samples/Kalptaru Radiance (1).xlsx` | `structured_owner_workbook` | 858 rows / 5 sheets | Good future candidate, larger than selected file. |
| `exports/archive_profiles/Archive_2/extracted/Windsor Grande Residences Condominium - Member Details (1).xlsx` | `society_member_details_workbook` | 195 rows / 2 sheets | Strong candidate, but includes broader member detail columns. |
| `exports/archive_profiles/Archive_2/extracted/ - Oberoi Esquire data - Copy.xlsx` | `building_owner_tenant_workbook` | 1140 rows / 4 sheets | Too large for first Phase 5.3 dry run. |
| `exports/archive_profiles/Archive_2/extracted/Ekta Tripolis Data new.xlsx` | `project_customer_workbook` | 442 rows / 1 sheet | Larger than selected file. |
| `exports/archive_profiles/Archive/extracted/CSV Files /OBEROI ESQUIRE OWNERS.csv` | `simple_phonebook_csv` | 505 rows / CSV | Owner-looking, but lacks unit columns in detected header. |
| `exports/archive_profiles/Archive/extracted/Excel Files /ONLY KALPATARU OWNERS.csv` | `simple_phonebook_csv` | 695 rows / CSV | Owner-looking, but lacks unit columns in detected header. |
| `exports/archive_profiles/Archive_2/extracted/Oberoi esquire units.xlsx` | `building_owner_tenant_workbook` | 570 rows / 1 sheet | Good future candidate, larger than selected file. |
| `exports/archive_profiles/Archive_2/extracted/72 west Andheri West - 80 nos.xlsx` | `simple_phonebook_csv` | 82 rows / 1 sheet | Small, but not clearly owner/unit structured. |

## Workflow Results

Profile:

- detected file type: `xlsx`
- detected source format: `unit_resident_workbook`
- sheets: 1
- source rows: 123
- detection looked correct for a unit-resident/lessee-style source.

Normalize:

- normalized rows: 188
- source format: `unit_resident_workbook`
- rows with building hints: 188
- rows with wing or unit hints: 188
- rows with raw contact method present: 188
- output: `exports/contacts/normalized_contacts_Imperial_Heights_unit_data_20260608_125822_125521.csv`

Clean:

- cleaned rows: 58
- rejected rows: 130
- rows needing review: 58
- rows with building hints: 58
- rows with unit hints: 58
- rows with role/relationship hints: 58
- rows with valid phone or email: 58
- cleaned output: `exports/contacts/cleaned_contacts_normalized_contacts_Imperial_Heights_unit_data_20260608_125822_125521_20260608_125835_797359.csv`
- rejected output: `exports/contacts/rejected_contacts_normalized_contacts_Imperial_Heights_unit_data_20260608_125822_125521_20260608_125835_797359.csv`
- summary JSON: `exports/contacts/contact_import_summary_normalized_contacts_Imperial_Heights_unit_data_20260608_125822_125521_20260608_125835_797359.json`

Dedupe:

- strong duplicate groups: 2
- strong duplicate pairs: 7
- medium duplicate groups: 2
- medium duplicate pairs: 7
- weak duplicate groups: 0
- weak duplicate pairs: 0

Source-aware import dry-run:

| Planned table | Count |
|---|---:|
| `import_batches` | 1 |
| `source_files` | 1 |
| `contact_import_rows` | 58 |
| `contact_methods` | 116 |
| `contact_aliases` | 58 |
| `contact_property_hints` | 58 |
| `lead_requirements` | 0 |
| `inventory_import_rows` | 58 |
| `contact_duplicate_candidates` | 14 |
| `import_review_items` | 188 |

Plan output:

```text
exports/contacts/source_aware_import_plan_20260608_125904.json
```

## Property Relationship Candidate Planning

`scripts/plan_property_relationship_candidates.py` currently reads candidate sources
from Postgres tables. Because Phase 5.3 intentionally did not apply the cleaned file
to Postgres, the DB-backed planner cannot see the dry-run batch yet.

Observed DB-backed planner result for the hypothetical batch label:

- rows considered: 0
- candidate building aliases: 0
- candidate building units: 0
- candidate contact-property relationships: 0
- skipped rows: 0

CSV-derived estimate from the dry-run output:

- candidate building aliases: 58
- candidate building units: 58
- candidate contact-property relationships: 0
- skipped rows: 58
- expected skip reason: `needs_canonical_contact`

This is expected. Real property relationships require reviewed canonical contacts.
The selected file has source rows and contact methods, not canonical contact IDs.

Smallest safe next change: add a CSV/dry-run input mode to
`scripts/plan_property_relationship_candidates.py` so Phase 5.3-style cleaned files
can produce relationship-candidate counts before DB apply. The alternative is to
wait until Phase 5.4 performs a real source-aware audit import, then run the existing
DB-backed planner against that audit batch.

## Baseline And Safety

Startup checks passed:

- `realdeal-postgres` healthy
- `realdeal-n8n` running
- `realdeal-nocodb` running
- `realdeal-adminer` running
- `./scripts/check_db.sh` passed

Baseline counts before dry-run:

| Item | Count |
|---|---:|
| canonical contacts | 2 |
| buildings | 0 |
| building_aliases | 0 |
| building_units | 0 |
| contact_property_relationships | 0 |
| property_relationship_review_items | 0 |
| source_files | 2 |
| contact_import_rows | 25 |
| contact_property_hints | 3 |
| inventory_import_rows | 0 |

Existing real batch `REAL_PHASE_3_5_TEST_001` counts:

| Item | Count |
|---|---:|
| import_batches | 1 |
| source_files | 1 |
| contact_import_rows | 22 |
| contact_methods | 62 |
| property_hints | 0 |
| lead_requirements | 22 |
| inventory_import_rows | 0 |
| duplicate_candidates | 1 |
| review_items | 45 |
| review_pending | 40 |
| review_approved | 4 |
| review_needs_more_info | 1 |

## Recommendation

Recommendation: **A. Good candidate for Phase 5.4 real source-aware audit import
only**, with one caveat. The selected source is appropriately small and strongly
unit/building-related, but Phase 5.4 should remain audit/import-table only until
canonical contact review happens. Property relationship creation should wait until
canonical contacts exist and review approves relationship candidates.

## Warnings

- No real owner/property data was applied to the database in Phase 5.3.
- No canonical contacts were created.
- No canonical contacts were merged.
- No real property relationships were created.
- No WhatsApp, SMS, email, or other outreach was sent.
- Reports and logs should remain counts-only and must not print raw names, phone
  numbers, emails, websites, addresses, or private client/property data.
