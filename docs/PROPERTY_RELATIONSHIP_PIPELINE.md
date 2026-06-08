# Property Relationship Pipeline (Phase 5.1)

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

## Fake workflow (test only)

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

- **Do not import owner/property sheets yet.** This phase is schema + fake test only.
  Real owner/unit ingestion is a later, explicitly approved phase.
- **No outreach yet.** No WhatsApp, SMS, email, or message is sent from this pipeline.
