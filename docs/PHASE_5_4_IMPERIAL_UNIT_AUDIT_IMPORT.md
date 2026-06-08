# Phase 5.4 Imperial Unit Audit Import

Phase 5.4 applied exactly one small real owner/building/unit source into
source-aware audit/import tables only. No canonical contacts were created, no
canonical merge was run, no buildings or units were created, no real property
relationships were created, and no outreach was sent.

## Scope

- selected file: `exports/archive_profiles/Archive_2/extracted/Imperial Heights unit data.xlsx`
- source format: `unit_resident_workbook`
- batch label: `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`
- source rows profiled: 123
- source sheets: 1

Allowed write tables:

- `import_batches`
- `source_files`
- `contact_import_rows`
- `contact_methods`
- `contact_aliases`
- `contact_property_hints`
- `inventory_import_rows`
- `contact_duplicate_candidates`
- `import_review_items`

Protected tables not written in this phase:

- `contacts`
- `buildings`
- `building_aliases`
- `building_units`
- `contact_property_relationships`
- `property_relationship_review_items`

## Preparation Counts

| Step | Count |
|---|---:|
| normalized rows | 188 |
| cleaned rows | 58 |
| rejected rows | 130 |
| valid phone/email rows | 58 |
| building hint rows | 58 |
| unit hint rows | 58 |
| relationship/role hint rows | 58 |
| strong duplicate groups | 2 |
| strong duplicate pairs | 7 |
| medium duplicate groups | 2 |
| medium duplicate pairs | 7 |
| weak duplicate groups | 0 |
| weak duplicate pairs | 0 |

## Dry-Run Plan

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

## Applied Audit Counts

| Applied table | Count |
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

Review statuses for the new batch:

| Status | Count |
|---|---:|
| pending | 188 |
| approved | 0 |
| rejected | 0 |

## Post-Apply Verification

Protected counts after apply:

| Item | Count |
|---|---:|
| canonical contacts | 2 |
| buildings | 0 |
| building_aliases | 0 |
| building_units | 0 |
| contact_property_relationships | 0 |
| property_relationship_review_items | 0 |

Existing real batch `REAL_PHASE_3_5_TEST_001` remained unchanged:

| Item | Count |
|---|---:|
| contact_import_rows | 22 |
| contact_methods | 62 |
| duplicate_candidates | 1 |
| review_items | 45 |
| review_pending | 40 |
| review_approved | 4 |
| review_needs_more_info | 1 |

## Relationship Planner Result

The DB-backed relationship planner was run against
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` after apply:

| Planner item | Count |
|---|---:|
| rows considered | 116 |
| building alias candidates | 116 |
| building unit candidates | 116 |
| contact-property relationships | 0 |
| review items | 0 |
| skipped rows | 116 |
| `skip:needs_canonical_contact` | 116 |

The 116 considered rows reflect both property-hint and inventory signals. No
relationship candidates were created because the imported rows do not yet point to
reviewed canonical contacts.

## Rollback Dry-Run

Dry-run command:

```bash
python3 scripts/cleanup_real_import_batch.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001
```

Rows that would be deleted if cleanup were explicitly applied:

| Table | Count |
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
| `canonical_contacts` | 0 |

Cleanup was **not** applied.

## Warnings

- No canonical contacts were created.
- No canonical merge was run.
- No real buildings or units were created.
- No real property relationships were created.
- No owner/tenant relationship was approved.
- No WhatsApp, SMS, email, or other outreach was sent.
- Reports must remain counts-only and must not print raw names, phone numbers,
  emails, websites, addresses, or private client/property data.
