# Phase 6.7 — Building-Anchor Dedupe Planning (Imperial Heights)

A **review-gated, planning-only** step that identifies the duplicate Imperial Heights
building anchors, proposes a canonical anchor, and queues a human review — **without
merging, moving, or deleting anything**. No buildings/relationships/SEO/content rows are
changed, no source gaps are resolved, and there are **no external/web/AI calls, no
publishing, and no outreach**.

## The data-quality issue

Phase 6.6 evidence review surfaced that the Imperial Heights SEO profile's
`active_owner_relationship_count` was **understated**. The cause is two duplicate
building anchors, both named "Imperial Heights" (Mumbai), both with building code
`IMPERIAL_HEIGHTS`:

| building_id | role | SEO profile | content briefs | active owner rel | units | aliases |
| ----------- | ---- | :---: | :---: | :---: | :---: | :---: |
| `0e72db71` | **proposed_canonical_anchor** | 1 | 3 | 1 | 1 | 1 |
| `f05bbd01` | **merge_into_canonical** | 0 | 0 | 1 | 1 | 1 |

The two active owner relationships (total 2) are **split** across the anchors, so the
SEO profile's anchor (`0e72db71`) only "sees" 1. Until these are consolidated, building-
level internal evidence for the profile cannot be fully trusted.

## Proposed canonical anchor

**`0e72db71`** — selected because it carries the `imperial-heights-goregaon-west` web
profile and all 3 content briefs. Selection order in `plan_building_dedupe.py`:
(1) building linked to the `--profile-slug` profile → (2) any web profile →
(3) most active owner relationships → (4) earliest `created_at`.

## Duplicate anchor

**`f05bbd01`** — same name and `IMPERIAL_HEIGHTS` code, no web profile, no content
briefs, but holds the second active owner relationship. Duplicate strength: **strong**
(same name + same building code).

## What this phase added

Migration `schemas/018_building_dedupe_review_workflow.sql` — 3 tables + 3 views:

| Table | Purpose |
| ----- | ------- |
| `building_duplicate_candidates` | Tracks possible duplicate anchors (canonical ↔ duplicate, strength, status). |
| `building_dedupe_review_items` | Human review queue before any consolidation. |
| `building_dedupe_action_log` | Future audit log for merge/consolidation actions (empty for now). |

Views: `vw_building_dedupe_dashboard` (side-by-side anchor counts + review status),
`vw_imperial_heights_building_anchor_summary` (one row per anchor with a
`recommended_role`), `vw_building_dedupe_review_queue`.

## What was planned (apply)

- **1** `building_duplicate_candidates` row: canonical `0e72db71`, duplicate `f05bbd01`,
  strength `strong`, status `pending_review`, group key `imperial-heights`.
- **1** `building_dedupe_review_items` row: `duplicate_building_review`, status `pending`.

Every planning row is tagged in `raw_context` (`phase=6.7`,
`source=building_dedupe_planning`, `merged=false`).

## What was NOT changed

No building was merged or deleted; no unit, alias, or relationship was moved; no
`building_web_profiles`, SEO keyword, or content row was touched; no source gap was
resolved. Verified after apply: buildings `2`, units `2`, aliases `2`, active owner
relationships still **split 1 / 1** (total `2`), gaps `open=17 / resolved=0`,
`ready_for_ai_draft=0`, `ready_for_publish=0`, `communication_sent=0`, action log `0`.

## Future consolidation steps (not done here)

`scripts/plan_building_dedupe_consolidation.py` is **dry-run only** (no `--apply`) and
reports, for the candidate, what a future approved merge **would** move from `f05bbd01`
onto `0e72db71`: `aliases_to_move=1`, `units_to_move=1`, `relationships_to_move=1`
(1 active), `web_profiles_to_move=0`, `seo_keywords=0`, `content_briefs=0`. After such a
merge the canonical anchor would correctly hold **2** active owner relationships.

The actual merge is a **separate, future, explicitly-approved phase** that would: move
the duplicate's aliases/units/relationships to the canonical anchor, set the candidate
`status='merged'`, and write a `building_dedupe_action_log` entry — only after a human
approves the `building_dedupe_review_items` row.

## Cleanup (dry-run) command

```bash
# Dry-run (default): shows the tagged 6.7 rows that would be deleted.
python3 scripts/cleanup_building_dedupe_plan.py --building-name "Imperial Heights"

# Apply (deletes only phase='6.7'/source='building_dedupe_planning' rows; refuses if any
# candidate is merged/approved_for_merge; never touches buildings/relationships/SEO/content):
python3 scripts/cleanup_building_dedupe_plan.py --building-name "Imperial Heights" --apply --real-ok
```

## Commands

```bash
# Plan dedupe candidates (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/plan_building_dedupe.py --building-name "Imperial Heights" \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]

# Consolidation preview (DRY-RUN ONLY, no --apply):
python3 scripts/plan_building_dedupe_consolidation.py --candidate-id <uuid>
```

## Safety posture (verified after apply)

- **No buildings/relationships/content changed** — buildings 2, units 2, aliases 2,
  active owner relationships 2 (split 1/1); no merge, move, or delete.
- **No gaps resolved** — gaps `open=17`, `resolved=0`.
- **Not ready for drafting/publishing** — `ready_for_ai_draft=0`, `ready_for_publish=0`.
- **No external API/web calls, no publishing, no outreach** — `communication_sent=0`.

## Next recommendation

- Work `vw_building_dedupe_review_queue` in NocoDB and approve the
  `duplicate_building_review` only when confident the two anchors are the same building.
- **Official verification first (Phase 6.8 + 6.9):** the MahaRERA verification foundation
  exists, and Phase 6.9 entered real review-gated RERA rows for Imperial Heights Wing C &
  D (reg `P51800003270`) from an official PDF snapshot. Both internal anchors (`0e72db71`,
  `f05bbd01`) now have a `candidate` RERA match — an *accepted* match gives the
  authoritative basis for consolidating them. See
  `docs/PHASE_6_9_MANUAL_RERA_IMPERIAL_HEIGHTS.md` and `docs/RERA_VERIFICATION_PIPELINE.md`.
- **Then (separate, approved phase):** implement the guarded merge that moves the
  duplicate's aliases/units/relationships onto `0e72db71`, logs to
  `building_dedupe_action_log`, and re-runs the Phase 6.6 evidence acceptance so
  `active_owner_relationship_count` can finally be accepted (it is currently
  `defer_until_building_dedupe`). Public drafting + Wix publishing remain gated and out
  of scope until all gaps are resolved.
