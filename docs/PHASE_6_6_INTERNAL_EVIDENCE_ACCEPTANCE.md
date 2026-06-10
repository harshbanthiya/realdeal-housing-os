# Phase 6.6 — Internal Evidence Acceptance

A **review-gated** step that lets a human accept the **purely-internal, non-personal**
evidence candidates created in Phase 6.5, so the system records which internal facts can
be trusted for *future* content drafting. **Nothing here resolves a source gap**, changes
a resolution-task status, marks content ready for AI/public drafting, publishes, or sends
anything; there are **no AI/external/web calls**.

## What this phase added

- `scripts/review_internal_source_evidence.py` — dry-run-default reviewer that sets
  `internal_source_evidence.evidence_status` (accepted / rejected / needs_review) for a
  chosen, tiny set of rows and moves the linked `source_gap_review_items`
  (`internal_evidence_review`) `pending -> approved / rejected / needs_more_info`. Every
  change is tagged in `raw_context` (`evidence_review_phase=6.6` + previous status) for a
  clean revert. Guards: requires `--real-ok`; refuses non-candidate rows (unless
  `--allow-existing`), evidence outside the profile, any `safe_summary` matching a
  phone/email-like pattern, or more than `--limit` rows.
- `scripts/revert_internal_source_evidence_review.py` — dry-run-default rollback that
  reverts only the `6.6`-marked rows (evidence → `candidate`, reviews → `pending`) and
  refuses if any gap was resolved or any brief became `ready_for_ai_draft`.
- Migration `schemas/017_internal_evidence_acceptance_dashboard.sql` — two read-only
  views: `vw_internal_evidence_acceptance_dashboard` (per-evidence status + linked
  review status + `recommended_next_action`) and `vw_imperial_heights_evidence_readiness`
  (per-profile rollup; `ready_for_publish` hard-coded false).

## Evidence types reviewed (15 candidates → 5 types × 3)

| evidence_type | recommendation | this phase |
| ------------- | -------------- | ---------- |
| `building_alias` | accept_internal_evidence | **accepted (3)** |
| `source_batch_count` | accept_internal_evidence | deferred to a later batch |
| `unit_count` | accept_internal_evidence | deferred to a later batch |
| `inventory_hint` | needs_human_review | held — may imply availability |
| `active_owner_relationship_count` | defer_until_building_dedupe | held — duplicate building anchor |

## What was accepted

The **3 `building_alias`** rows — known internal building aliases used for matching. They
are purely structural, count-based, contain no personal contact values, and do **not**
depend on building dedupe. Accepting them moved the **3 owner-gap**
`internal_evidence_review` items `pending -> approved`.

> Note on the per-gap review model: a `source_gap_review_items` row is **per gap**, while
> evidence is **per row**. Approving an owner gap's evidence review reflects that its
> *structural* internal evidence (the alias) is accepted; that gap's
> `active_owner_relationship_count` evidence stays `candidate` (deferred) and the gap
> itself stays **open**. So "review approved" ≠ "gap resolved".

## What was deferred (and why)

- **`active_owner_relationship_count`** — the SEO profile is tied to building anchor
  `0e72db71`, which has **1** active owner relationship; the second belongs to a separate
  **duplicate** Imperial Heights anchor. The count's meaning depends on building dedupe
  (deferred), so this evidence is **not** accepted yet → `defer_until_building_dedupe`.
- **`inventory_hint`** — a building-units count that could be read as an availability
  signal; availability must be human-verified before drafting → `needs_human_review`.
- **`source_batch_count` / `unit_count`** — safe structural counts, but held back to keep
  this first acceptance batch tiny (≤5). They remain `candidate` for a later batch.

## Why gaps remain open

Accepting internal *evidence* only records which internal facts are trustworthy. A gap
closing means a public-facing factual claim becomes citable — a separate, human decision
that is explicitly **out of scope** here. All **17** source gaps stay `open`, and all
**17** `source_gap_resolution_tasks` stay `pending`.

## Why content is still not ready for AI/public drafting

`vw_imperial_heights_evidence_readiness` shows `gaps_open=17`,
`ready_for_ai_draft=false`, `ready_for_publish=false`, `blocked_reason='open_source_gaps'`.
AI/public drafting additionally requires the Phase 6.2 readiness checks, the Phase 6.3
quality checks, and a human to flip readiness — none of which happens here.

## Commands

```bash
# Review/accept evidence (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/review_internal_source_evidence.py \
  --profile-slug imperial-heights-goregaon-west \
  --evidence-id <uuid[,uuid...]> --status accepted --reviewed-by <name> --real-ok [--apply]
# (or --accept-safe-batch --limit 5 to auto-select safe count-based evidence)
```

## Rollback (dry-run) command

```bash
# Dry-run (default): shows the 6.6-marked rows that would revert.
python3 scripts/revert_internal_source_evidence_review.py --profile-slug imperial-heights-goregaon-west

# Apply (reverts only phase 6.6 evidence-review changes; refuses if any gap resolved
# or any brief became ready_for_ai_draft; never touches gaps/tasks/content/contacts):
python3 scripts/revert_internal_source_evidence_review.py \
  --profile-slug imperial-heights-goregaon-west --apply --real-ok
```

## Safety posture (verified after apply)

- **No gaps resolved** — gaps `open=17`, `resolved=0`; tasks `pending=17`, `resolved=0`.
- **Not ready for drafting/publishing** — `ready_for_ai_draft=0`, `ready_for_publish=0`,
  `public_ready=0`, `published=0`.
- **No external API/web calls** — `external_calls_allowed=0`, `external_calls_made=0`;
  no AI tasks completed.
- **No outreach** — `communication_sent=0`.
- **Real data untouched** — canonical contacts `4`, active owner relationships `2`; no
  contact/relationship created, merged, or approved.

## Next recommendation

- In a later batch, accept the remaining safe structural counts (`source_batch_count`,
  `unit_count`) and set `inventory_hint` to `needs_review`.
- **Building dedupe (planned in Phase 6.7):** the duplicate Imperial Heights anchors
  (`0e72db71` canonical vs `f05bbd01`) are now identified and queued for review — see
  `docs/PHASE_6_7_BUILDING_DEDUPE_PLANNING.md`. Once consolidated, the previously-deferred
  `active_owner_relationship_count` evidence can be accepted.
- Only after gaps are resolved with verified, citable sources (a separate gated step)
  does AI/public drafting + Wix publishing become eligible — still future and out of scope.
