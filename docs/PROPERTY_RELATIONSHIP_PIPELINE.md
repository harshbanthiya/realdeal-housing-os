# Property Relationship Pipeline (Phases 5.1-5.2)

Schema foundation for linking canonical contacts to buildings and units with a
reviewed relationship type. **Schema + fake test only** — no real owner or property
sheets are imported in this phase, and no outreach is sent.

Added by migration `schemas/008_property_relationship_pipeline.sql`.

---

## Why these tables exist

- **`building_aliases`** — real-world building data arrives with messy, inconsistent
  names and codes (`IMP-HTS`, `Imperial Hts`, a Google Maps name, a sheet tab name).
  Aliases map each messy form to one canonical `buildings` row so the same building
  isn't created five times. Each alias is review-gated (`status` pending → approved).

- **`building_units`** — a building has many units/flats (wing A, unit 1001, 2BHK,
  carpet area, …). This table holds canonical / semi-canonical units so a contact can
  be linked to a *specific* unit, not just a building. Imported unit data is messy, so
  the `(building_id, wing, unit_number)` index is intentionally **non-unique**.

- **`contact_property_relationships`** — the heart of the pipeline: it links a
  canonical `contacts` row to a `buildings` and/or `building_units` row with a
  `relationship_type` and a `relationship_status`. It records where the link came from
  (`source_contact_import_row_id`, `source_property_hint_id`,
  `source_inventory_import_row_id`, `source_file_id`) for full traceability.

- **`property_relationship_review_items`** — a dedicated review queue for relationship
  candidates (separate from the import `import_review_items` queue), with its own
  statuses, priority, reviewer fields, and notes.

- **`property_relationship_action_log`** — an audit trail of relationship review
  decisions (separate from `review_action_log`, which logs import review items).

## Relationship types

`relationship_type` is constrained to: `owner`, `tenant`, `broker`, `agent`, `buyer`,
`seller`, `landlord`, `business_lead`, `interested_buyer`, `interested_tenant`,
`unknown`. This supports future workflows such as *owner of A-1001 Imperial Heights*,
*tenant in B-2105 Kalpataru Radiance*, *broker connected to Oberoi Esquire*, and
*buyer/tenant lead interested in a building or area*. Source-aware
`contact_property_hints` become reviewed relationships through this pipeline.

`relationship_status`: `pending_review`, `approved`, `rejected`, `active`, `inactive`,
`superseded`, `needs_more_info`.

## NocoDB views (safe, masked)

Person names are masked to an initial via `mask_name()`; building/property names are
business data and shown as-is. No phones, emails, websites, or addresses are exposed.

| View | Purpose |
|---|---|
| `vw_building_alias_review` | Review building aliases → canonical building. |
| `vw_building_units_review` | Review canonical units (building, wing, unit, typology). |
| `vw_contact_property_relationship_review` | Contact (masked) ↔ building/unit + relationship type/status. |
| `vw_property_relationship_review_queue` | The relationship review queue (status/priority/title). |
| `vw_contact_building_unit_trace` | Trace contact → relationship → building/unit → source file/row. |

## Phase 5.2: property hints -> relationship candidates

Phase 5.2 adds a guarded candidate workflow that turns source-aware property hints
into reviewable building/unit/contact relationship candidates. It does **not** import
real owner sheets, create canonical contacts, merge contacts, or send outreach.

Candidate planning is read-only and prints counts only:

```bash
python3 scripts/plan_property_relationship_candidates.py
python3 scripts/plan_property_relationship_candidates.py --fake-only
python3 scripts/plan_property_relationship_candidates.py --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS --fake-only
```

The planner considers:

- `contact_property_hints`
- parsed building/unit fields from `contact_import_rows` that do not already have
  a `contact_property_hints` row
- `inventory_import_rows`
- `lead_requirements`

Rows without a canonical/test contact are skipped as `needs_canonical_contact`, and
owner/tenant-style rows without unit detail are skipped as `owner_tenant_needs_unit`.
Every materialized relationship remains `pending_review` and receives a
`property_relationship_review_items` queue item.

Phase 5.2 includes a fake-only end-to-end harness:

```bash
# Seed one fake source-aware property hint (dry-run by default)
python3 scripts/seed_fake_property_hints.py
python3 scripts/seed_fake_property_hints.py --apply --fake-ok

# Materialize one fake candidate chain (dry-run by default)
python3 scripts/apply_fake_property_relationship_candidates.py --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS
python3 scripts/apply_fake_property_relationship_candidates.py --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS --apply --fake-ok

# Remove only tagged Phase 5.2 fake candidate rows, then the fake seed
python3 scripts/cleanup_fake_property_relationship_candidates.py --apply
python3 scripts/seed_fake_property_hints.py --cleanup --apply
```

`apply_fake_property_relationship_candidates.py` refuses non-`FAKE_` batches and
refuses any hint that resolves to a real (`is_test=false`) contact.

## Phase 5.4: first real owner/unit audit import

Phase 5.4 imported one small real unit-resident source into source-aware audit/import
tables only under batch `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`. It created
`contact_property_hints` and `inventory_import_rows` for review, but did **not**
create canonical contacts, buildings, building units, or
`contact_property_relationships`.

The DB-backed relationship planner considered 116 property/inventory signals for
the new batch and skipped all 116 as `needs_canonical_contact`. Relationship
candidate creation remains a later reviewed phase. See
`docs/PHASE_5_4_IMPERIAL_UNIT_AUDIT_IMPORT.md`.

## Phase 5.5: canonical contact planning before relationships

Phase 5.5 analyzed the Phase 5.4 owner/unit audit rows and selected two safe
`merge_candidate` review items for a later canonical-contact approval phase. No
statuses were changed and no contacts or relationships were created. See
`docs/PHASE_5_5_OWNER_UNIT_CANONICAL_CONTACT_PLAN.md`.

## Phase 5.6: owner/unit review approval and merge prep

Phase 5.6 approved exactly two selected owner/unit `merge_candidate` review items
and prepared the canonical merge scripts for a future contact-only apply phase. The
planning path now traces `contact_property_hints` and `inventory_import_rows` counts
for those approved rows, but no canonical contacts, buildings, building units,
`contact_property_relationships`, or property relationship review items were
created. See
`docs/PHASE_5_6_OWNER_UNIT_REVIEW_APPROVAL_AND_MERGE_PREP.md`.

## Phase 5.7: first owner/unit canonical contact

Phase 5.7 created exactly one canonical contact from one approved owner/unit review
item. The relationship planner remains read-only, but now resolves canonical
contacts through applied canonical merge links when source hint `contact_id` fields
are still empty. After the merge, the Phase 5.4 batch plans 2 contact-property
relationship candidates and still skips 114 rows as `needs_canonical_contact`.
No relationship candidates were applied. See
`docs/PHASE_5_7_FIRST_OWNER_UNIT_CANONICAL_MERGE.md`.

## Phase 5.1 fake workflow (test only)

A self-contained fake chain (building → alias → unit → contact → relationship →
review item), every row tagged `fake_batch = FAKE_PHASE_5_1_REL_001` plus `is_test`
markers so it can be removed precisely. Both scripts print counts only.

```bash
# Create (dry-run by default; writing needs BOTH flags)
python3 scripts/apply_fake_property_relationships.py                 # dry-run
python3 scripts/apply_fake_property_relationships.py --apply --fake-ok

# Inspect (counts only; optional --contact-id / --building-name / --relationship-status)
python3 scripts/property_relationship_summary.py

# Remove the fake rows (dry-run by default)
python3 scripts/cleanup_fake_property_relationships.py               # dry-run
python3 scripts/cleanup_fake_property_relationships.py --apply
```

Cleanup deletes **only** rows carrying the fake batch tag, and the contact/building
deletes additionally require the `is_test` marker, so real canonical contacts
(`is_test=false`) and real buildings are never touched.

## Warnings

- **Do not import additional owner/property sheets yet.** Phase 5.4 imported exactly
  one small real source into audit/import tables only. Further owner/unit ingestion
  needs a later, explicitly approved phase.
- **No outreach yet.** No WhatsApp, SMS, email, or message is sent from this pipeline.
