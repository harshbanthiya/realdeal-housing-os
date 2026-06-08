# Phase 4.2 — Second Real Canonical Merge

**Status: EXECUTED on 2026-06-08.** A second real canonical contact was created
from one more approved `merge_candidate` review item, under the same maximum
guardrails as Phase 4. No outreach (WhatsApp / SMS / email / message) was sent, and
no raw personal data was printed.

---

## 1. Candidate and label

- Source batch: `REAL_PHASE_3_5_TEST_001`
- Review item id: `14bc4ad4-013e-43bf-b32f-0d3310de7623`
- Source format: `google_maps_business_csv`
- Merge label: `REAL_PHASE_4_CANONICAL_MERGE_002`

This candidate started as `needs_more_info`. It was promoted to `approved` only
after safe-metadata verification confirmed it is a complete `merge_candidate` with
a present display name, 3 contact methods (valid/unverified), 1 lead requirement,
no existing canonical merge link, and **no unresolved duplicate conflict**. The
approval was recorded via `scripts/update_review_item.py` (which also writes a
`review_action_log` entry).

## 2. What was created

| Object | Count |
|---|---|
| canonical contacts (`is_test=false`, `canonical_status='active'`) | 1 |
| contact methods linked | 3 |
| lead requirements linked | 1 |
| `canonical_merge_batches` row (`is_test=false`, `status=applied`) | 1 |
| `canonical_merge_links` (1 create_contact + 3 link_method + 1 link_lead_requirement) | 5 |

Totals after this phase: 2 real canonical contacts, 5 linked contact methods,
2 applied merge batches (+1 older rolled-back fake), 9 source-trace rows.

Unchanged (audit preserved): `source_files` (1), `contact_import_rows` (22),
total `contact_methods` (62), total `lead_requirements` (22),
`import_review_items` (45). Review statuses moved from 40/3/2 to
**40 pending / 4 approved / 1 needs_more_info** (one needs_more_info → approved);
`review_action_log` went 9 → 10 from that single approval. The merge itself writes
no review_action_log rows and leaves the review item `approved`.

## 3. Guardrails

Identical to Phase 4 (see `docs/PHASE_4_FIRST_REAL_CANONICAL_MERGE.md`): real mode
behind `--real-ok`, requires `--apply --batch-label --merge-label --review-item-id`,
refuses non-approved / non-`merge_candidate` items, wrong batch (unless
`--allow-other-batch`), already-linked rows, unresolved duplicate candidates for the
row, and reused merge labels. The transaction asserts exactly one eligible row, so
at most one canonical contact is ever created. No bulk merge, no duplicate merge,
no communications.

## 4. Commands (counts only; no raw values printed)

```bash
# Approve the candidate (dry-run, then --apply)
python3 scripts/update_review_item.py --review-item-id 14bc4ad4-013e-43bf-b32f-0d3310de7623 \
  --status approved --reviewed-by "h b" \
  --decision-notes "P4.2 real review: ... approve for one-contact canonical merge" --apply

# Plan
python3 scripts/plan_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 14bc4ad4-013e-43bf-b32f-0d3310de7623 --approved-only

# Dry-run apply (no writes): omit --apply
python3 scripts/apply_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 14bc4ad4-013e-43bf-b32f-0d3310de7623 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_002 --real-ok

# Real apply
python3 scripts/apply_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 14bc4ad4-013e-43bf-b32f-0d3310de7623 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_002 --real-ok --apply
```

## 5. Rollback (dry-run shown; destructive form NOT run)

```bash
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_002 --real-ok --confirm-real-rollback
```

Dry-run reports: 1 contact to delete, 3 methods to unlink, 1 lead to unlink,
5 merge links to mark, status `applied -> rolled_back`. Real rollback (add
`--apply`) is refused if `communication_sent=true`, never deletes source audit rows
or `review_action_log`, and preserves merge links as audit.

## 5a. Metadata accuracy patch

The merge batch metadata key `first_real_canonical_merge` is now computed, not
hardcoded: `apply_canonical_merge.py` sets it `true` only when no non-test
`canonical_merge_batches` with `status='applied'` existed before the merge (the
flag is captured once at the start of the transaction so the batch and the new
contact agree). The 002 merge batch — which had been written with the old fixed
`true` — was corrected in place to `false` via a guarded UPDATE scoped to
`merge_label = REAL_PHASE_4_CANONICAL_MERGE_002` only. The canonical contact created
by merge 002 carried the same fixed `true` in its contact-level metadata; it was
then corrected with a second tightly-scoped UPDATE (non-test contacts whose
`source_merge_batch_id` belongs to the 002 batch), changing only the
`first_real_canonical_merge` key and preserving all other keys. Result: **both** the
merge-batch metadata and the contact-level metadata now mark only merge 001 as
`first_real_canonical_merge=true` (001 true / 002 false). The rolled-back fake merge,
merge 001, contact_methods, lead requirements, and source audit rows were left
untouched. The script change keeps future merges accurate automatically.

## 6. Warnings

- **No outreach yet.** Phase 4.2 creates a canonical record only.
- **One at a time.** Real canonical merge stays enabled for exactly one approved
  review item per run — no bulk merge, no duplicate merge.
- **Rollback available.** The single new contact can be removed with the command above.
