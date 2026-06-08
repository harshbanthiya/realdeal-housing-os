# Owner / Building / Unit Dashboard (Phase 5.10)

Read-only, masked NocoDB views to inspect, audit, trace, and revert-check the first
active owner/building/unit relationship before scaling. Added by migration
`schemas/009_owner_building_unit_dashboard.sql`. Person names are masked to an initial
via `mask_name()`; no phones, emails, websites, or addresses are exposed.
Building/unit/property fields are business data and shown as-is.

This is dashboard/view polish only — no data was imported, no canonical contacts or
relationships were created, nothing was approved, and no outreach was sent.

---

## Views to open in NocoDB

| View | Purpose |
|---|---|
| `vw_owner_relationship_dashboard` | One row per **active** owner/unit relationship: masked contact hint, building/unit, unit status, alias status, source file/format/row, review status + reviewer. |
| `vw_building_unit_owner_summary` | Building/unit rollup: owner/active/pending relationship counts, source-file count, last updated. |
| `vw_contact_property_trace_full` | Full chain: canonical contact → relationship → building/unit → source import (batch/file/row) → canonical merge (label/status) → property review item + action-log count. |
| `vw_property_relationship_revert_readiness` | Whether each relationship can be safely reverted: `revert_allowed` + `reason_if_not_allowed`, with `communication_sent` and `has_downstream_activity` flags. |

## Inspect the first active owner relationship

1. Open `vw_owner_relationship_dashboard` — expect **1** row: a masked owner contact,
   building **Imperial Heights**, unit **"Wing A -102"**, `unit_status=active`,
   `alias_status=approved`, `relationship_status=active`, `review_status=approved`.
2. Open `vw_building_unit_owner_summary` — the unit shows `owner_relationship_count=1`,
   `active_owner_count=1`, `pending_relationship_count=0`, `source_file_count=1`.

## Trace it back to source

Open `vw_contact_property_trace_full` and read the row left-to-right:

- masked contact → `relationship_id` (`owner`, `active`)
- building/unit → `Imperial Heights` / `Wing A -102`
- source import → `source_batch_label = REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`,
  `source_file`, `source_row_number`, `contact_import_row_id`
- canonical merge → `canonical_merge_label = REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001`,
  `canonical_merge_status = applied`
- review → `property_review_item_id`, `property_review_status = approved`,
  `property_action_log_count = 1`

This is the full audit trail from the active relationship back to the original
owner/unit source row and the approval that created it.

## Check revert readiness

Open `vw_property_relationship_revert_readiness`. For the current relationship:
`relationship_status=active`, `review_status=approved`, `communication_sent=false`,
`has_downstream_activity=false`, `action_log_count=1`, **`revert_allowed=true`**,
`reason_if_not_allowed=(none)`. If a revert is ever needed, use
`scripts/revert_property_relationship_approval.py` (dry-run by default). `revert_allowed`
becomes false (with a reason) once a communication is sent or other downstream
activity is recorded.

A counts-only summary is available (no DB writes):

```bash
python3 scripts/owner_relationship_dashboard_summary.py
# optional filters: --building-name --relationship-status --relationship-type --contact-id
```

## Why no outreach yet

The owner relationship is **active and audited but not actioned**. Outreach
(WhatsApp / SMS / email / message) is intentionally out of scope until an explicitly
approved later phase. Activating a relationship does not contact anyone.

## Before scaling to more owner rows

The Phase 5.4 batch holds 58 owner/unit rows; only one has been promoted end-to-end.
Before scaling, confirm on this single live example that: the dashboard reads
cleanly, the full trace resolves to source + merge + review, revert readiness is
green, and the masking holds (no raw personal values anywhere). Then the same
guarded per-row flow (candidate → review → approve) can be repeated one row at a
time — there is deliberately no bulk path.

Phase 5.11 exercised exactly that next step: a second owner/unit canonical contact
plus one more review-gated relationship **candidate** (`pending_review`). The owner
dashboard still shows one **active** relationship (candidates do not appear until
approved), while `vw_property_relationship_review_queue` and the other review views
now show two rows. See `docs/PHASE_5_11_SECOND_OWNER_UNIT_CANONICAL_AND_REL_CANDIDATE.md`.

Phase 5.12 then approved that second candidate, so `vw_owner_relationship_dashboard`
now shows **two** active owner relationships (units "Wing A -102" and "Wing A -203"),
and `vw_property_relationship_revert_readiness` reports both as revert-ready. See
`docs/PHASE_5_12_SECOND_PROPERTY_RELATIONSHIP_APPROVAL.md`.
