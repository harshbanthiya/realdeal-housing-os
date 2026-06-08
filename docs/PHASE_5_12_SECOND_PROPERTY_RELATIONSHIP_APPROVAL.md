# Phase 5.12 — Second Property Relationship Approval

**Status: EXECUTED.** The second pending owner/unit relationship candidate (from
Phase 5.11) was approved and activated. There are now **two** active owner
relationships. No outreach was sent and no other candidate was touched (no bulk
approval).

---

## Selected candidate

- property_relationship_review_item_id: `28947264-d0b3-4e78-8c5d-ea53afd9cb9a`
- contact_property_relationship_id: `5ce27b3d-249e-498f-be0e-da7dccccb66a`
- building_unit_id: `5b4251ee-d943-4b2b-a0b8-63e06a0e52a7`
- building_id: `f05bbd01-1a27-4073-98bc-fc0e094d7818`
- building_alias_id: `9bb5da54-a885-4987-baa8-bf6ebdc1c84e`
- rel_label: `REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002`; phase tag: `5.11`
- review_type `owner_tenant_review`; relationship_type `owner`
- building **Imperial Heights**, unit **"Wing A -203"**, source `unit_resident_workbook`,
  batch `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`; canonical contact active.

Pre-checks (all passed): canonical contact non-test + active; review item `pending`
and carries the real-candidate source marker; relationship `pending_review`; no other
active/approved relationship for the same contact or unit; no `communication_sent`
flag; exactly one pending candidate for the rel-label.

## Approve/revert scripts made phase-agnostic

Phase 5.11 retagged its candidate `phase=5.8` → `phase=5.11`, but
`approve_property_relationship_candidate.py` / `revert_property_relationship_approval.py`
previously hard-required `phase=5.8`. Their candidate guard now keys on the candidate
**source marker** (`raw_context`/`metadata` `source = 'real_property_relationship_candidate'`)
instead of a fixed phase value, so they work for any phase. The `rel_label` scoping
(which alias/unit belong to this candidate) is unchanged, and no guardrail was
weakened — the scripts still require `pending` review + `pending_review` relationship
+ active contact + exactly one affected relationship + no communication flag.

## Status transitions (exactly one each)

| Table | Before | After |
|---|---|---|
| `property_relationship_review_items.status` | pending | **approved** |
| `contact_property_relationships.relationship_status` | pending_review | **active** |
| `building_units.canonical_status` | needs_review | **active** |
| `building_aliases.status` | pending_review | **approved** |
| `property_relationship_action_log` | 1 row | **2 rows** (+1 `approve_property_relationship`) |

After approval: active owner relationships **1 → 2** (Wing A -102 and Wing A -203);
pending relationship candidates **1 → 0**; approved property review items **1 → 2**.
Untouched: canonical contacts (stayed 4), contact_methods, and all source-aware audit
rows (`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` unchanged at 58/116/58/58/188). All
five dashboard views show 2 rows; both relationships are revert-ready.

## Commands

```bash
# Dry-run (default), then apply (add --apply)
python3 scripts/approve_property_relationship_candidate.py \
  --review-item-id 28947264-d0b3-4e78-8c5d-ea53afd9cb9a \
  --reviewed-by "h b" \
  --decision-notes "P5.12 real review: approve second owner/unit relationship candidate; activate relationship only; no outreach" \
  --real-ok --apply
```

## Revert (dry-run shown; destructive form NOT run)

```bash
python3 scripts/revert_property_relationship_approval.py \
  --review-item-id 28947264-d0b3-4e78-8c5d-ea53afd9cb9a \
  --reviewed-by "h b" \
  --decision-notes "P5.12 revert dry-run only: would restore second owner/unit relationship to review state" \
  --real-ok
```

Dry-run reports it would restore: review item `approved -> pending`, relationship
`active -> pending_review`, unit `active -> needs_review`, alias
`approved -> pending_review`, plus one `revert_property_relationship` action-log row.
Revert needs `--apply` + `--real-ok`, refuses if any communication was sent or
downstream activity exists, deletes no rows, and never touches the canonical contact
or source rows.

## Warnings

- **No outreach yet.** Approving a relationship contacts no one. No WhatsApp, SMS,
  email, or message is sent.
- **No bulk approval.** Exactly one review item / one relationship per run.
