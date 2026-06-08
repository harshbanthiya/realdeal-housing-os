# Phase 5.8 — First Real Building/Unit Relationship Candidate

**Status: EXECUTED.** The first *real* owner/unit relationship candidate chain was
created from the Phase 5.7 canonical contact. Everything is **review-gated**: no
relationship is approved or activated, and no outreach was sent.

---

## What this phase does

Takes the one canonical contact created in Phase 5.7 (an owner from the
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` audit) and materialises a single reviewable
candidate chain from its source-aware owner/unit signals:

```
canonical owner/unit contact
  -> building (anchor)
  -> building_alias        (status = pending_review)
  -> building_unit         (canonical_status = needs_review)
  -> contact_property_relationship (relationship_status = pending_review)
  -> property_relationship_review_item (status = pending)
  -> NocoDB review views
```

Inputs (this run):

- contact_id: `efb3ed59-0d51-4dc1-be8a-cef22e046f87`
- source review item: `911cb0e3-91ce-4462-a4d5-54f58fb677b4`
- rel-label / tag: `REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001`
- resolved signals: building **Imperial Heights** (`IMPERIAL_HEIGHTS`), unit
  **"Wing A -102"**, relationship_type **owner** (the inventory row links this import
  row as `owner_contact_import_row_id`).

Created (exactly one each, all review-gated):

| Object | Count | State |
|---|---|---|
| buildings | 1 | anchor (tagged phase 5.8) |
| building_aliases | 1 | `pending_review` |
| building_units | 1 | `needs_review` |
| contact_property_relationships | 1 | `pending_review` |
| property_relationship_review_items | 1 | `pending` |

## Guardrails

`scripts/apply_real_property_relationship_candidates.py` is dry-run by default and
writes only with **both** `--real-ok` and `--apply`. It refuses unless: the contact
exists, is `is_test=false` and `canonical_status='active'`, has an applied
`create_contact` merge link (a real source row), has a building signal AND a unit
signal, and no Phase 5.8 candidate already exists for that contact/label. The
transaction asserts exactly one signal row, so at most one chain is created.
Nothing is ever set to `approved`/`active`; the relationship stays `pending_review`.

Invariants held after apply: canonical contacts stayed **3**; the
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` audit batch was unchanged
(contact_import_rows 58, contact_methods 116, contact_property_hints 58,
inventory_import_rows 58, import_review_items 188); zero approved/active
relationships; no communications sent.

## Review in NocoDB

All five Phase 5.1 views now show this candidate (names masked to an initial;
building/unit are property data shown as-is):

- `vw_building_alias_review` — the `IMPERIAL_HEIGHTS` alias, `pending_review`.
- `vw_building_units_review` — unit "Wing A -102", `needs_review`.
- `vw_contact_property_relationship_review` — masked contact ↔ Imperial Heights /
  unit, `owner` / `pending_review`.
- `vw_property_relationship_review_queue` — the `owner_tenant_review` queue item.
- `vw_contact_building_unit_trace` — traces back to `Imperial Heights unit data.xlsx`
  (`unit_resident_workbook`).

## Commands

```bash
# Dry-run (default)
python3 scripts/apply_real_property_relationship_candidates.py \
  --contact-id efb3ed59-0d51-4dc1-be8a-cef22e046f87 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4

# Apply (creates one review-gated candidate chain)
python3 scripts/apply_real_property_relationship_candidates.py \
  --contact-id efb3ed59-0d51-4dc1-be8a-cef22e046f87 \
  --review-item-id 911cb0e3-91ce-4462-a4d5-54f58fb677b4 --apply --real-ok

# Rollback dry-run (default; destructive form needs --apply --real-ok --confirm-real-rollback)
python3 scripts/rollback_real_property_relationship_candidates.py \
  --rel-label REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001
```

Rollback removes only the phase-5.8 / rel-label-tagged rows (review item,
relationship, unit, alias, building anchor) in FK-safe order, **refuses** if any
targeted relationship is already approved/active, and never touches the canonical
contact, contact_methods, or source-aware audit rows.

## Warnings

- **No approved/active relationship yet.** This phase produces *candidates* only;
  promotion to an approved/active owner relationship is a later, explicitly
  instructed phase.
- **No outreach.** No WhatsApp, SMS, email, or message is sent.
