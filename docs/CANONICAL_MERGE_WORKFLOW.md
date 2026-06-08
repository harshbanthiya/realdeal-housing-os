# Canonical Merge Workflow

Phase 3.8 introduces a fake-only review-to-canonical merge workflow. It proves the shape of a future merge without allowing real contacts to be merged.

## Safety Rules

- Fake/test mode is the default; real canonical merge is gated behind `--real-ok`.
- In fake mode, merge scripts refuse real batches and only allow `FAKE_` labels.
- In real mode (Phase 4+), merge is allowed for **one** approved `merge_candidate`
  review item at a time, only for batch `REAL_PHASE_3_5_TEST_001` (unless
  `--allow-other-batch`), and creates at most one canonical contact. See the
  Real Merge Policy section below.
- Only approved `merge_candidate` review items are eligible.
- Dry-run is the default for rollback; real rollback also needs
  `--confirm-real-rollback` and is refused if `communication_sent=true`.
- No messages, WhatsApp, or email are sent.
- Raw names, phone numbers, and emails are never printed (counts only).

## Migration 006

`schemas/006_canonical_merge_workflow.sql` adds:

- `canonical_merge_batches`
- `canonical_merge_links`
- `contacts.is_test`
- `contacts.source_import_batch_id`
- `contacts.source_merge_batch_id`
- `contacts.canonical_status`
- `vw_canonical_merge_batches`
- `vw_canonical_merge_links`

These objects keep a reversible audit trail for test canonical contacts.

## Fake Test Flow

Create a fake source-aware import from `.example` data, approve a small number of fake merge candidates, plan the merge, apply the fake merge, and roll it back.

```bash
python3 scripts/plan_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --limit 2

python3 scripts/apply_canonical_merge.py \
  --batch-label FAKE_PHASE_3_8_MERGE_TEST \
  --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE \
  --limit 2

python3 scripts/apply_canonical_merge.py \
  --batch-label FAKE_PHASE_3_8_MERGE_TEST \
  --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE \
  --limit 2 \
  --apply \
  --test-ok
```

The apply command creates test canonical contacts and links test contact methods or lead requirements. It does not touch real import batches.

## Rollback

Rollback is dry-run by default:

```bash
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE
```

Apply rollback only after checking the counts:

```bash
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --apply
```

Rollback unlinks test methods and lead requirements, deletes test canonical contacts, and marks the merge batch as rolled back. Source-aware import rows remain in place for audit.

## Real Merge Policy

Real canonical merge is enabled **only** for one approved `merge_candidate` review
item at a time, behind `--real-ok` plus the full guard matrix in
`scripts/apply_canonical_merge.py`. As of Phase 4 (2026-06-08) the first real merge
has been applied for review item `0da30fd3-84a8-450a-b759-1d71a18db0f9` from batch
`REAL_PHASE_3_5_TEST_001` under merge label `REAL_PHASE_4_CANONICAL_MERGE_001`,
creating exactly one canonical contact. There is no bulk merge and no duplicate
merge, and no communications are sent. See
[PHASE_4_FIRST_REAL_CANONICAL_MERGE.md](PHASE_4_FIRST_REAL_CANONICAL_MERGE.md) for
the exact commands, guardrails, and rollback procedure.

```bash
# Dry-run apply (no writes): omit --apply
python3 scripts/apply_canonical_merge.py \
  --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id <approved_merge_candidate_id> \
  --merge-label <REAL_..._MERGE_label> --real-ok
# add --apply to write exactly one canonical contact

# Rollback dry-run (default): add --apply only when explicitly approved
python3 scripts/rollback_canonical_merge.py \
  --merge-label <REAL_..._MERGE_label> --real-ok --confirm-real-rollback
```

## Reviewing a Canonical Contact (Phase 4.1)

After a real merge, review and trace the canonical contact through the masked views
added by `schemas/007_canonical_review_dashboard.sql` — `vw_canonical_contacts_review`,
`vw_canonical_contact_methods_review`, `vw_canonical_source_trace`,
`vw_canonical_lead_requirements_review`, `vw_canonical_merge_audit`. Use
`vw_canonical_merge_audit` to confirm `status=applied`, `rollback_allowed=true`, and
`communication_sent=false`. A counts-only summary is available via
`python3 scripts/canonical_contact_summary.py --merge-label <label>`. Full details:
`docs/CANONICAL_CONTACT_REVIEW.md`.

Real merges applied so far (one approved review item each):

| Merge label | Review item | Contact | Methods | Lead reqs |
|---|---|---|---|---|
| `REAL_PHASE_4_CANONICAL_MERGE_001` | `0da30fd3-…` | 1 | 2 | 1 |
| `REAL_PHASE_4_CANONICAL_MERGE_002` | `14bc4ad4-…` (`google_maps_business_csv`) | 1 | 3 | 1 |

A `needs_more_info` candidate may be promoted to `approved` via
`scripts/update_review_item.py` only after safe-metadata verification (complete
`merge_candidate`, has method + lead, no existing link, no unresolved duplicate).
See `docs/PHASE_4_2_SECOND_REAL_CANONICAL_MERGE.md`.

## Owner/Unit Canonical Contact Planning (Phase 5.5)

Phase 5.5 does not run canonical merge. It analyzes owner/unit audit rows from
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` and selects a tiny set of safe pending
`merge_candidate` review items for a later approval phase. Existing merge scripts
can create one canonical contact from one approved review item, but Phase 5.6 needs
an explicit owner/unit batch allowlist decision and should remain contact-only: no
buildings, building units, or property relationships. See
`docs/PHASE_5_5_OWNER_UNIT_CANONICAL_CONTACT_PLAN.md`.

## Owner/Unit Review Approval And Merge Prep (Phase 5.6)

Phase 5.6 approves exactly two selected owner/unit `merge_candidate` review items
from `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` and prepares the merge scripts for a
future contact-only owner/unit canonical merge phase. `plan_canonical_merge.py`
requires `--review-item-id` for this batch and refuses non-approved or wrong-batch
review items. `apply_canonical_merge.py` recognizes the batch in dry-run and records
future property/inventory trace counts, but Phase 5.6 does **not** run apply.

For each approved item, dry-run planning returns 1 planned contact, 2 methods, 0
aliases, 0 lead requirements, 1 property hint trace, 1 inventory row trace, and 0
skips. No buildings, units, property relationships, or outreach are created. See
`docs/PHASE_5_6_OWNER_UNIT_REVIEW_APPROVAL_AND_MERGE_PREP.md`.

## First Owner/Unit Canonical Merge (Phase 5.7)

Phase 5.7 applies exactly one of the approved owner/unit review items under merge
label `REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001`. It creates 1 canonical
contact, links 2 contact methods, records 3 canonical merge links, and traces 1
property hint plus 1 inventory row through merge metadata. It remains contact-only:
no buildings, building units, property relationships, or outreach are created.

The rollback path was verified in dry-run mode only and would delete 1 contact,
unlink 2 methods, mark 3 merge links, and change the merge batch status from
`applied` to `rolled_back`. See
`docs/PHASE_5_7_FIRST_OWNER_UNIT_CANONICAL_MERGE.md`.
