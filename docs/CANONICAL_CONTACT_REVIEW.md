# Canonical Contact Review (Phase 4.1)

A safe, NocoDB-friendly review layer for the first real canonical contact. Every
view masks raw personal values: names are reduced to a single initial via
`mask_name()`, phone/email go through `mask_phone()` / `mask_email()`, and
websites/links become `[LINK_PRESENT]`. No view exposes a full name, phone, email,
website, or address.

Added by migration `schemas/007_canonical_review_dashboard.sql`.

---

## Views to open in NocoDB

Open NocoDB (see `docs/NOCODB_REVIEW_WORKFLOW.md` for the URL) and add these views
from the `realdeal_os` Postgres source:

| View | Purpose |
|---|---|
| `vw_canonical_contacts_review` | One row per canonical contact: masked display hint, status, provenance ids, method/lead/source-file counts, merge label + status. |
| `vw_canonical_contact_methods_review` | Masked contact methods linked to canonical contacts (type, masked value, validation, source file/row). |
| `vw_canonical_source_trace` | Canonical contact → merge link → source file / import row / review item. |
| `vw_canonical_lead_requirements_review` | Lead requirement metadata (purpose, property_type, locality, city, budget) linked to canonical contacts. |
| `vw_canonical_merge_audit` | Merge batch status, counts, `rollback_allowed`, and `communication_sent`. |

## Filter by merge label

In every relevant view, filter on the merge label to isolate the Phase 4 contact:

```
merge_label = REAL_PHASE_4_CANONICAL_MERGE_001
```

`vw_canonical_contacts_review`, `vw_canonical_source_trace`, and
`vw_canonical_merge_audit` carry `merge_label` directly. For
`vw_canonical_contact_methods_review` and `vw_canonical_lead_requirements_review`,
filter by `contact_id` (copy the `contact_id` from `vw_canonical_contacts_review`).

## Trace a canonical contact back to its source

1. In `vw_canonical_contacts_review`, find the row (filter `merge_label`). Note its
   `contact_id`, `method_count` (2), `lead_requirement_count` (1),
   `source_file_count` (1).
2. In `vw_canonical_source_trace`, filter that `contact_id`. You will see the
   merge actions (`create_contact`, `link_method` ×2, `link_lead_requirement`),
   each tied to a `source_file`, `source_row_number`, `contact_import_row_id`, and
   the originating `review_item_id` / `review_type` / `review_status` /
   `reviewed_by` / `reviewed_at`.
3. The `review_item_id` should be `0da30fd3-84a8-450a-b759-1d71a18db0f9` with
   `review_type = merge_candidate` and `review_status = approved`.

## Confirm contact methods

In `vw_canonical_contact_methods_review`, filter the `contact_id`. Expect **2**
rows. Values are masked (e.g. `[MASKED]1234` for phones, `x[MASKED]@domain` for
emails) — this is correct; raw values are intentionally never shown here.

## Confirm lead requirements

In `vw_canonical_lead_requirements_review`, filter the `contact_id`. Expect **1**
row showing the requirement metadata (purpose, property_type, locality, city,
budget range, `lead_status`, `needs_review`) and its `source_file` /
`source_row_number`. No raw contact identifiers appear.

## Confirm no communications were sent

In `vw_canonical_merge_audit`, filter `merge_label`. Confirm:

- `status = applied`
- `communication_sent = false`
- `rollback_allowed = true`

`communication_sent` is read from the merge batch metadata; Phase 4 recorded it as
`false` and no script sends outreach.

## Rollback dry-run

The merge is reversible. The dry-run reports what *would* change and makes **no**
changes (it omits `--apply`):

```bash
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 --real-ok --confirm-real-rollback
```

Expected dry-run counts: 1 contact to delete, 2 methods to unlink, 1 lead to
unlink, 4 merge links to mark, status `applied -> rolled_back`. Real rollback
(`--apply`) is refused if `communication_sent = true`, never deletes source audit
rows or `review_action_log`, and preserves merge links as audit.

A quick counts-only summary (no DB writes) is available via:

```bash
python3 scripts/canonical_contact_summary.py --merge-label REAL_PHASE_4_CANONICAL_MERGE_001
```

## Warning — no outreach yet

Phase 4.1 is review and traceability only. **Do not send any WhatsApp, SMS, email,
or message** to the canonical contact. Outreach is out of scope until a later,
explicitly approved phase.

## Phase 4.2 — second canonical contact

As of Phase 4.2 (2026-06-08) there are **2** real canonical contacts. The same
views work for the second merge — filter `merge_label = REAL_PHASE_4_CANONICAL_MERGE_002`
in `vw_canonical_contacts_review`, `vw_canonical_source_trace`, and
`vw_canonical_merge_audit` (or list both with no filter). Expect: 1 contact,
3 methods, 1 lead requirement, 5 source-trace rows, `status=applied`,
`communication_sent=false`, `rollback_allowed=true`. Counts-only summary:
`python3 scripts/canonical_contact_summary.py --merge-label REAL_PHASE_4_CANONICAL_MERGE_002`.
The no-outreach warning above applies equally. See
`docs/PHASE_4_2_SECOND_REAL_CANONICAL_MERGE.md`.

## Linking contacts to properties (Phase 5.1)

Canonical contacts can be linked to buildings/units via the Phase 5.1 property
relationship pipeline (`contact_property_relationships`). The masked view
`vw_contact_property_relationship_review` shows a canonical contact (name masked to an
initial) alongside the building/unit and `relationship_type`/`relationship_status`,
and `vw_contact_building_unit_trace` traces it back to the source file/row. This is
schema + fake test only for now — no real owner sheets are imported and no outreach is
sent. See `docs/PROPERTY_RELATIONSHIP_PIPELINE.md`.

## Phase 5.7 — first owner/unit canonical contact

As of Phase 5.7 (2026-06-08) there are **3** real canonical contacts. The third was
created from one approved owner/unit `merge_candidate` review item under merge label
`REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001`. Use the same masked canonical
review views and filter by that merge label. Expect: 1 contact, 2 methods, 0 lead
requirements, 3 merge links, `communication_sent=false`, and
`relationship_creation_done=false`.

No building, unit, or property relationship rows were created in Phase 5.7. The
relationship planner can now see 2 possible relationship candidates for the Phase
5.4 owner/unit batch, but candidate application is deferred to a later explicit
phase. See `docs/PHASE_5_7_FIRST_OWNER_UNIT_CANONICAL_MERGE.md`.
