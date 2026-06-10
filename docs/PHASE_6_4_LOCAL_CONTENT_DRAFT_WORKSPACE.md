# Phase 6.4 — Local Content Draft Workspace

A **local-only** workspace that stores **internal, clearly non-final** draft
artifacts for the Imperial Heights content briefs. Nothing here executes AI, calls
an external/Wix API, scrapes the web, generates final public claims, publishes, or
sends outreach.

## What this phase added (migration 015)

Three tables + four read-only views:

| Table | Purpose |
| ----- | ------- |
| `content_draft_artifacts` | Internal, non-public draft artifacts per brief (outline / notes / meta draft). |
| `content_draft_reviews` | Human review queue for those artifacts. |
| `content_source_gap_items` | Specific missing facts/sources needed before public drafting. |

Views: `vw_content_draft_artifact_dashboard` (no full body), `vw_content_draft_review_queue`,
`vw_content_source_gap_dashboard`, `vw_imperial_heights_draft_workspace`.

## Draft artifacts created (7, all `draft`, all `internal_only=true`)

- **3 outlines** — one per content brief (building page, rent guide, resale guide).
- **3 internal_brief_notes** — one per brief, recording that sources are not yet collected.
- **1 meta_tag_draft** — building page only (placeholder meta title/description/H1).

Every artifact carries the safety flags: `internal_only=true`, `public_ready=false`,
`source_verification_required=true`, `human_review_required=true`,
`external_calls_made=false`, `published=false`, `communication_sent=false`.

### Why they are internal-only

The artifact bodies are **outlines and placeholders**, not articles. Every factual
claim is marked `[SOURCE NEEDED]`, each file/body begins with
**"INTERNAL DRAFT — NOT FOR PUBLISHING"** and **"Human review required."**, and no
private contact data appears anywhere. No fact is invented; nothing is public-ready.

## Source gap items created (17, all `open`)

Generated from the unresolved (`needed`) `content_source_requirements` that map to a
gap type — e.g. `rent_range_missing`, `resale_range_missing`, `amenities_unverified`,
`developer_unverified`, `landmarks_unverified`, `inventory_availability_unverified`,
`legal_disclaimer_needed`, `owner_listing_permission_needed` (8 distinct types).
Requirements without a clean gap mapping (`building_facts`, `faq`) are left to the
outline TODOs. Each gap links to its brief's `internal_brief_notes` artifact.

## Review workflow

Each artifact gets one `content_draft_reviews` row (`internal_draft_review`,
`pending`). A human works the queue in NocoDB (`vw_content_draft_review_queue`),
resolves the open source gaps (`vw_content_source_gap_dashboard`), and only then can
a later phase consider promoting an artifact — still never directly to public.

## Export workflow

`scripts/export_content_draft_artifacts.py` writes each artifact to a Markdown file
under **`exports/content/`** (git-ignored). File names use only artifact type, brief
content type, and the artifact UUID — never contact data. Each file is prefixed with
"INTERNAL DRAFT — NOT FOR PUBLISHING".

```bash
python3 scripts/export_content_draft_artifacts.py --profile-slug imperial-heights-goregaon-west            # dry-run
python3 scripts/export_content_draft_artifacts.py --profile-slug imperial-heights-goregaon-west --apply    # writes 7 files
```

## What still blocks public publishing

`vw_imperial_heights_draft_workspace` shows, per brief: `public_ready_count=0`,
`published_count=0`, `external_calls_made_count=0`, with `blocked_reason='open_source_gaps'`
(17 gaps open). Beyond this phase, publishing also requires the Phase 6.3 quality
checks to pass, the Phase 6.2 readiness checks to pass, the publishing-queue row to be
approved, and a human to flip readiness — none of which happens here.

## Safety posture (verified after apply)

- **No AI execution** — no AI/LLM API called; `ai_agent_tasks` remain `queued` (0 completed).
- **No external API/web calls** — all artifacts `external_calls_made=false`; 0 with it true.
- **No publishing** — `published=0`, `public_ready=0`.
- **No outreach** — `communication_sent=0`; global `communications_sent=0`.
- **Phases 6.1/6.2/6.3 and real data untouched** — profile 1, keywords 10, briefs 3, publishing 3, ai tasks 5, collections 2, mappings 12, content reviews 3, readiness checks 24, quality checks 24, source requirements 20, prompt templates 4, execution plans 5; contacts 4, active owner relationships 2.

## Commands

```bash
# Create internal draft artifacts (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/create_local_content_draft_artifacts.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]

# Cleanup / rollback (dry-run default; --apply --real-ok deletes only 6.4 rows;
# refuses if any artifact is public_ready/published/external/comm; never touches 6.1/6.2/6.3):
python3 scripts/cleanup_local_content_draft_artifacts.py \
  --profile-slug imperial-heights-goregaon-west
```

## Next recommendation

- Review the artifacts and the 17 open source gaps in NocoDB; resolve the gaps with
  verified, citable sources (replacing `[SOURCE NEEDED]` markers).
- **Phase 6.5 (built):** the open source gaps are now classified into review-gated
  resolution tasks (internal / human / future-external) with safe internal evidence and
  a human review queue — see `docs/PHASE_6_5_SOURCE_GAP_RESOLUTION_WORKFLOW.md`. Final
  public drafting + Wix publishing remain gated, future, and out of scope until sources
  are verified and all checks pass.
