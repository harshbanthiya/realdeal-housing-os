# Phase 4 — First Real Canonical Merge

**Status: EXECUTED on 2026-06-08.** The first real canonical contact was created
from a single approved review item, behind maximum guardrails. No outreach of any
kind (WhatsApp / SMS / email / message) was sent, and no raw personal data was
printed at any point.

---

## 1. What Phase 4 does

Phase 4 promotes **exactly one** approved `merge_candidate` review item from the
real audit batch into the canonical `contacts` table, with full source
traceability and a one-command rollback. It is deliberately the smallest possible
real merge: **one review item → at most one canonical contact**.

- Source batch: `REAL_PHASE_3_5_TEST_001`
- Review item id: `0da30fd3-84a8-450a-b759-1d71a18db0f9`
- Merge label: `REAL_PHASE_4_CANONICAL_MERGE_001`

What was created:

| Object | Count |
|---|---|
| canonical contacts (`is_test=false`, `canonical_status='active'`) | 1 |
| contact methods linked | 2 |
| lead requirements linked | 1 |
| `canonical_merge_batches` row (`is_test=false`, `status=applied`) | 1 |
| `canonical_merge_links` (1 create_contact + 2 link_method + 1 link_lead_requirement) | 4 |

Unchanged (audit preserved): `source_files` (1), `contact_import_rows` (22),
total `contact_methods` (62), total `lead_requirements` (22),
`import_review_items` (45), `review_action_log` (9), review statuses
(40 pending / 3 approved / 2 needs_more_info). The review item itself stays
`approved` — Phase 4 does not change review statuses.

## 2. Exact guardrails

Real mode lives entirely behind `--real-ok` in `scripts/apply_canonical_merge.py`.
A real merge is **refused** unless ALL of these hold:

- `--apply`, `--real-ok`, `--batch-label`, `--merge-label`, `--review-item-id` all present.
- The review item exists, is type `merge_candidate`, and is `approved`.
- The review item's import row belongs to the named batch.
- The batch is `REAL_PHASE_3_5_TEST_001` (any other batch requires the explicit
  `--allow-other-batch` escape hatch).
- No more than one review item at a time (single `--review-item-id`; `--limit`,
  if given, must be `1`).
- No canonical contact is already linked for that import row.
- No **unresolved** duplicate candidate (`status='pending_review'`) references that row.
- The merge label is unused.
- The DB transaction itself asserts exactly **1** eligible row, or it raises and
  rolls back — a hard cap of one canonical contact per real merge.

The merge batch is written with `is_test=false`, `status=applied`, the merge
label, and metadata `phase=4`, `first_real_canonical_merge=true`,
`source_aware_only=false`, `communication_sent=false`. The new contact is written
with `is_test=false`, `source_import_batch_id`, `source_merge_batch_id`, and
`canonical_status='active'`. Existing canonical contacts are never updated in this
phase, duplicates are never merged, and the script never sends any communication.

## 3. Commands used (counts only; no raw values printed)

```bash
# Plan (read-only)
python3 scripts/plan_canonical_merge.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 \
  --approved-only

# Dry-run apply (no DB writes)
python3 scripts/apply_canonical_merge.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 \
  --real-ok

# Real apply (writes exactly one canonical contact)
python3 scripts/apply_canonical_merge.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 \
  --real-ok --apply
```

## 4. Rollback (dry-run shown; destructive form NOT run)

```bash
# Dry-run (default; safe — no changes)
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 \
  --real-ok --confirm-real-rollback
```

Dry-run reports: 1 contact to delete, 2 methods to unlink, 1 lead to unlink,
4 merge links to mark, merge batch `applied -> rolled_back`.

To actually roll back (only when explicitly approved), add `--apply`:

```bash
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 \
  --real-ok --apply --confirm-real-rollback
```

Real rollback is **refused** if the merge batch metadata has
`communication_sent=true` (checked both in Python and inside the transaction).
Rollback deletes the one canonical contact and unlinks its methods/leads, marks
the merge batch `rolled_back`, and **preserves** `canonical_merge_links` as audit
(only flagging them `rolled_back`). It never deletes source audit rows
(`source_files`, `contact_import_rows`) or `review_action_log`.

## 5. Warnings

- **No outreach yet.** Phase 4 creates a canonical record only. No WhatsApp, SMS,
  email, or message is sent by any script, and `communication_sent=false` is
  recorded on the merge batch.
- **One at a time.** Real canonical merge is enabled for exactly one approved
  review item per run. There is no bulk merge and no duplicate merge.
- **Rollback available.** The old exFAT `data/postgres` and the APFS cluster both
  hold the data; the single contact can be removed with the rollback command above.
