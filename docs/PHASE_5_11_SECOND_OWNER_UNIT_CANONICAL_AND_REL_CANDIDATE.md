# Phase 5.11 — Second Owner/Unit Canonical Contact + Relationship Candidate

**Status: EXECUTED.** Created one more owner/unit canonical contact (the second
approved owner/unit review item) and one review-gated building/unit relationship
**candidate** for it. The second relationship was **not** approved or activated, and
no outreach was sent.

---

## Selected inputs

- review_item_id: `75bb7bad-4232-4da1-8fed-ae25b7778aa9` (`merge_candidate`, `approved`)
- contact_import_row_id: `c26ccdca-bd59-42aa-adfe-8f49656b58e2` (`unit_resident_workbook`)
- canonical merge label: `REAL_PHASE_5_11_OWNER_UNIT_CANONICAL_MERGE_002`
- relationship candidate label: `REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002`
- new canonical contact: `b6ca2b1c-…` (real, active); building **Imperial Heights**,
  unit **"Wing A -203"**, relationship_type **owner**.

Safety pre-checks (all passed): review item approved + `merge_candidate`; row had 2
valid contact methods, a property hint, an inventory row, and building + unit hints;
no unresolved duplicate; not already merged.

## Part 1 — second canonical merge

| Metric | Value |
|---|---|
| planned / created canonical contacts | 1 |
| contact methods linked | 2 |
| contact_property_hints traced | 1 |
| inventory_import_rows traced | 1 |
| canonical_merge_links | 3 |
| building_aliases / building_units / relationships / review_items created | 0 / 0 / 0 / 0 |

Merge batch `REAL_PHASE_5_11_OWNER_UNIT_CANONICAL_MERGE_002`: `is_test=false`,
`status=applied`, `first_real_canonical_merge=false`, `communication_sent=false`.
Canonical contacts **3 → 4**; linked canonical contact methods **7 → 9**. The review
item stayed `approved`; the Phase 5.4 audit batch and review statuses were unchanged.

Rollback dry-run (`scripts/rollback_canonical_merge.py --merge-label
REAL_PHASE_5_11_OWNER_UNIT_CANONICAL_MERGE_002 --real-ok --confirm-real-rollback`):
would delete 1 contact, unlink 2 methods, mark 3 merge links,
`applied -> rolled_back`. Not applied.

## Part 2 — second relationship candidate (review-gated)

`scripts/apply_real_property_relationship_candidates.py --contact-id b6ca2b1c-…
--rel-label REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002 --review-item-id 75bb7bad-…
--apply --real-ok` created exactly one chain, all review-gated:

| Object | State |
|---|---|
| building (anchor for this candidate) | created |
| building_alias | `pending_review` |
| building_unit (Wing A -203) | `needs_review` |
| contact_property_relationship (owner) | `pending_review` |
| property_relationship_review_item | `pending` |

After: canonical contacts **4**; active owner relationships **1** (unchanged);
pending_review relationships **1**; pending property review items **1**; the five
property-relationship review views each show **2** rows; the owner dashboard still
shows the single **active** relationship. The candidate's building is a *separate*
review-gated "Imperial Heights" anchor (buildings 1 → 2); the building-alias review
workflow is the intended place to dedupe it against the existing canonical building.

Rollback dry-run (`scripts/rollback_real_property_relationship_candidates.py
--rel-label REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002 --real-ok
--confirm-real-rollback`): would delete the candidate's building/alias/unit/
relationship/review item (1 each, 0 already approved/active); the canonical contact
and source-aware audit rows are never touched. Not applied.

## Metadata accuracy patch

The candidate was first written with `phase=5.8` because
`apply_real_property_relationship_candidates.py` had a fixed phase tag. The script
now derives the phase tag — an optional `--phase` argument, otherwise inferred from
the rel-label (`PHASE_<maj>_<min>`), otherwise `5.8` for backward compatibility — so
future callers tag the correct phase automatically (the guardrails, dry-run default,
`--real-ok`/`--apply` requirements, and `rel_label` scoping are unchanged). The
existing Phase 5.11 candidate rows were then corrected in place from `phase=5.8` to
`phase=5.11` via a tightly-scoped update keyed on
`rel_label = REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002` (one row each in
`buildings`, `building_aliases`, `building_units`, `contact_property_relationships`,
`property_relationship_review_items`). **`rel_label` remains the primary rollback
scope**, and **no statuses, contacts, source-aware rows, or approvals were changed** —
only the `phase` key in `metadata`/`raw_context`. The Phase 5.8 candidate and the
Phase 5.9 active relationship were left untouched.

## Guardrails

- One approved review item merged → at most one canonical contact (transaction
  asserts exactly one eligible row).
- The relationship candidate is created `pending_review` / `needs_review` / `pending`
  only — **not approved or activated** in this phase.
- Both apply scripts are dry-run by default and require `--real-ok` (+ `--apply`).
- No bulk merge, no bulk candidate creation, no outreach.

## Warnings

- **The second relationship is a candidate only** — not approved or active. Promotion
  is a later, explicitly instructed phase (the same `approve_property_relationship_candidate.py`
  flow used in Phase 5.9, one at a time).
- **No outreach yet.** No WhatsApp, SMS, email, or message is sent.
