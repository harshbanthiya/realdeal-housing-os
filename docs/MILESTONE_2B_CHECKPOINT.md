# Milestone 2B Checkpoint + Data-Quality Dashboard (Phase 5.13)

A read-only snapshot of the system before scaling beyond two owner/unit
relationships. **Dashboard/view/script only** — no data import, no new contacts or
relationships, no review-status changes, no outreach. Added by migration
`schemas/010_milestone_2b_data_quality_dashboard.sql`. Person names are masked via
`mask_name()`; the duplicate `reason` text describes the match *type* only ("matching
normalized phone/email"), never raw values.

---

## What Milestone 2B proves

The full owner/unit pipeline works end-to-end on real data, one row at a time:
real owner/unit source row → source-aware audit → canonical contact (guarded merge) →
building/unit candidate → approved **active owner relationship** → dashboard +
traceability + revert path. Two rows have been taken all the way through.

## Current system counts

| Metric | Count |
|---|---|
| canonical contacts (all active) | 4 |
| active owner relationships | 2 |
| approved owner-relationship reviews | 2 |
| buildings / building units | 2 / 2 |
| approved / pending building aliases | 2 / 0 |
| source batches | 3 |
| owner/unit batch rows (`REAL_PHASE_5_4_…`) | 58 |
| owner/unit rows linked to canonical | 2 |
| owner/unit rows not yet linked | 56 |
| owner/unit duplicate candidates | 14 |
| total duplicate candidates (all batches) | 15 |
| communications sent | 0 |

## Dashboard views (migration 010)

| View | Purpose |
|---|---|
| `vw_milestone_2b_summary` | One-row system snapshot. |
| `vw_owner_unit_batch_quality` | Quality breakdown for the owner/unit audit batch. |
| `vw_owner_unit_candidate_queue` | Not-yet-linked owner/unit candidates with a recommended next action. |
| `vw_owner_relationship_revert_dashboard` | Active owner relationships + revert readiness (masked). |
| `vw_duplicate_risk_dashboard` | Duplicate-risk groups, type-only (no raw contact data). |

A counts-only summary is available: `python3 scripts/milestone_2b_summary.py`.

## What is safe now

- Of 58 owner/unit rows, **50** are safe candidates: a contact method present, a
  property hint present, **no** duplicate-candidate involvement, not yet linked. In
  the candidate queue these read `recommended_next_action = approve_then_merge`.
- The two active owner relationships are **revert-ready** (`revert_allowed = true`,
  no communications, no downstream activity) — fully reversible if needed.

## What is still risky

- **6** owner/unit rows are involved in duplicate candidates
  (`recommended_next_action = duplicate_review_first`) and must not be merged until
  reviewed. Duplicate-risk groups for the batch: 7 `strong` + 7 `medium`, all
  `pending_review`.
- **2 building anchors** named "Imperial Heights" exist (each owner/unit candidate
  created its own anchor). They are review-gated and meant to be consolidated through
  the `building_aliases` workflow before the building layer is treated as canonical.

## Candidate queue & revert-readiness meaning

- **Candidate queue** = owner/unit `merge_candidate` rows not yet promoted to a
  canonical contact, each flagged with the signals (method/hint/inventory/building/
  unit) and a duplicate flag, plus a recommended next action. It is the safe worklist
  for the next merge phase.
- **Revert-readiness** = whether an active relationship can be cleanly reverted. Both
  current relationships are green; readiness flips to false (with a reason) if a
  communication is sent or other downstream activity is recorded.

## Recommendation for Phase 5.14 — Option A

**Phase 5.14 — approve and merge 2 more safe owner/unit canonical contacts, then
create relationship candidates only** (the proven Phase 5.11/5.12 flow, repeated one
row at a time). Why, by counts:

- **50** safe candidates are queued (method + hint, no duplicate) — ample low-risk
  supply; continuing the validated per-row flow is the lowest-risk way to scale.
- Only **6** rows are duplicate-involved; deferring them to a dedicated duplicate
  review (Option B) keeps the safe path moving without touching risky rows.
- The building-anchor duplication (2× "Imperial Heights") is real but small and
  review-gated; **building dedupe (Option C)** is a sensible *follow-up* once a few
  more units exist, not a blocker now.
- A salesperson operating dashboard (**Option D / Phase 6.1**) is premature — only
  **2** active relationships exist; revisit after the owner/unit set grows.

## Warnings

- **No outreach yet.** No WhatsApp, SMS, email, or message is sent from any of this.
- **Do not scale import** or bulk-merge until the duplicate-risk and candidate queues
  have been reviewed; the 6 duplicate-involved rows and the duplicate building anchors
  are the two things to clear as volume grows.

## Update — Phase 5.14 paused; Phase 6.0 started

Owner/unit scaling (Phase 5.14) and dashboard polish are **paused**. Work shifted to
**Phase 6.0** — the growth/SEO/content/lead-pipeline foundation (schema, read-only
views, fake workflow, docs; no publishing, no outreach). See
`docs/GROWTH_SEO_LEAD_PIPELINE.md`. The Milestone 2B numbers above are unchanged
(4 canonical contacts, 2 active owner relationships, 0 communications).
