# Phase 5.9 — First Real Property Relationship Approval

**Status: EXECUTED.** Exactly one Phase 5.8 owner/unit relationship candidate was
reviewed and approved, activating exactly one owner relationship. No outreach was
sent and no other candidate was touched (no bulk approval).

---

## Selected candidate

- property_relationship_review_item_id: `d01e7caa-243f-4adb-9501-7592e317ac4f`
- contact_property_relationship_id: `c453b3ca-012f-492c-8939-a066c19df79b`
- building_unit_id: `43cf6ae7-0aad-4254-9ea8-5512a43dfd1e`
- building_id: `0e72db71-8b93-4ecd-879c-17d8d8f2b206`
- building_alias_id: `a1d22e69-fbe2-499c-b09d-e274667d6c8d`
- review_type: `owner_tenant_review`; relationship_type: `owner`
- building **Imperial Heights**, unit **"Wing A -102"**, source `unit_resident_workbook`
- source batch: `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`; canonical contact: active

Pre-checks (all passed): canonical contact non-test + active; review item `pending`
and Phase 5.8-tagged; relationship `pending_review`; no other active/approved
relationship for the same contact or unit; no `communication_sent` flag.

## Status transitions (exactly one each)

| Table | Before | After |
|---|---|---|
| `property_relationship_review_items.status` | pending | **approved** |
| `contact_property_relationships.relationship_status` | pending_review | **active** |
| `building_units.canonical_status` | needs_review | **active** |
| `building_aliases.status` | pending_review | **approved** |
| `property_relationship_action_log` | 0 rows | **1 row** (`approve_property_relationship`) |

Untouched: contacts (stayed 3), contact_methods, and all source-aware audit rows
(`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` unchanged at 58 import rows / 116 methods /
58 hints / 58 inventory rows / 188 import review items). Active owner relationships:
**1**.

## Guardrails

`scripts/approve_property_relationship_candidate.py` is dry-run by default; it writes
only with **both** `--real-ok` and `--apply`. It refuses unless: the review item
exists and is `pending`; it carries the Phase 5.8 marker; the relationship is
`pending_review` (and not already active/approved); the canonical contact exists and
is `active`; exactly one relationship would be affected; and no `communication_sent`
flag is set. The transaction asserts exactly one approvable candidate. It never
updates contacts, contact_methods, or source-aware rows.

## Commands

```bash
# Dry-run (default)
python3 scripts/approve_property_relationship_candidate.py \
  --review-item-id d01e7caa-243f-4adb-9501-7592e317ac4f \
  --reviewed-by "h b" \
  --decision-notes "P5.9 real review: approve first owner/unit relationship candidate; activate relationship only; no outreach" \
  --real-ok

# Apply (add --apply)
python3 scripts/approve_property_relationship_candidate.py \
  --review-item-id d01e7caa-243f-4adb-9501-7592e317ac4f \
  --reviewed-by "h b" --decision-notes "..." --real-ok --apply
```

## Rollback / revert (dry-run shown; destructive form NOT run)

```bash
python3 scripts/revert_property_relationship_approval.py \
  --review-item-id d01e7caa-243f-4adb-9501-7592e317ac4f \
  --reviewed-by "h b" \
  --decision-notes "P5.9 rollback dry-run only: would restore first owner/unit relationship candidate to review state" \
  --real-ok
```

Dry-run reports it would restore: review item `approved -> pending`, relationship
`active -> pending_review`, unit `active -> needs_review`, alias
`approved -> pending_review`, plus one `revert_property_relationship` action-log row.
Revert needs `--apply` and `--real-ok`, **refuses** if any communication was sent or
if downstream action-log activity exists, deletes no rows, and never touches the
canonical contact or source rows.

## Warnings

- **No outreach yet.** Approving a relationship does not contact anyone. No WhatsApp,
  SMS, email, or message is sent.
- **No bulk approval.** Exactly one review item / one relationship per run.
