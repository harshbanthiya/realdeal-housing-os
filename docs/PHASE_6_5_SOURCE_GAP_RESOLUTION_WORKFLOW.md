# Phase 6.5 — Source-Gap Resolution Workflow

A **review-gated** workflow that turns the 17 open `content_source_gap_items` (from
Phase 6.4) into actionable, classified resolution tasks and records **safe internal
evidence** (counts only) that may help close them. **Nothing here resolves a gap
automatically**, executes AI, calls an external/Wix API, scrapes the web, sets
`external_calls_allowed=true`, marks content public-ready/published, or sends outreach.

## What this phase added (migration 016)

Three tables + four read-only views:

| Table | Purpose |
| ----- | ------- |
| `source_gap_resolution_tasks` | One actionable, classified task per open gap (internal / human / future-external). |
| `internal_source_evidence` | Safe **count-only** references to internal data that may help resolve a gap. |
| `source_gap_review_items` | Human review queue to accept / resolve / waive each gap. |

Views: `vw_source_gap_resolution_dashboard` (per-gap rollup of tasks/evidence/reviews),
`vw_internal_source_evidence_dashboard`, `vw_source_gap_review_queue`,
`vw_imperial_heights_source_gap_status` (per-brief readiness; `ready_for_publish` is a
hard-coded `false`).

## Source-gap categories (17 open gaps, 3 briefs)

The open gaps fall into the 8 gap types carried over from Phase 6.4:
`inventory_availability_unverified` (3), `owner_listing_permission_needed` (3),
`legal_disclaimer_needed` (3), `landmarks_unverified` (2), `rent_range_missing` (2),
`resale_range_missing` (2), `amenities_unverified` (1), `developer_unverified` (1).

## Resolution task types (one task per open gap → 17 tasks)

Each gap is classified by `gap_type` into a `task_type` with a `resolution_source` and
an `external_calls_required` flag. `external_calls_allowed` is **always `false`** this
phase, regardless of `external_calls_required`.

| gap_type | task_type | resolution_source | external_calls_required | category |
| -------- | --------- | ----------------- | :---: | -------- |
| `inventory_availability_unverified` | `internal_data_check` | `inventory` | false | **internal** |
| `owner_listing_permission_needed` | `owner_data_check` | `owner_relationships` | false | **internal + human** |
| `amenities_unverified` | `human_research` | `human_input` | false | **human** |
| `photos_needed` | `photo_check` | `human_input` | false | **human** |
| `legal_disclaimer_needed` | `legal_disclaimer_review` | `human_input` | false | **human** |
| `developer_unverified` | `web_research_later` | `future_web_research` | true | **future external** |
| `landmarks_unverified` | `web_research_later` | `future_web_research` | true | **future external** |
| `rent_range_missing` | `market_range_estimate` | `future_web_research` | true | **future external** |
| `resale_range_missing` | `market_range_estimate` | `future_web_research` | true | **future external** |

Resulting tasks: `internal_data_check` 3, `owner_data_check` 3, `human_research` 1,
`legal_disclaimer_review` 3, `web_research_later` 3, `market_range_estimate` 4 — all
`pending`. (`photo_check` maps a gap type that has no open gaps in the current data, so 0
are created.) `external_calls_required=7`, `external_calls_allowed=0`.

## Which gaps are internal vs human vs future external research

- **Internally resolvable (have internal evidence):** `inventory_availability_unverified`
  and `owner_listing_permission_needed`. Internal data exists (units, owner
  relationships), but availability still needs verification and owner **permission is a
  human decision** — so these are never auto-closed.
- **Human input required:** `amenities_unverified`, `photos_needed`,
  `legal_disclaimer_needed` (plus the human-permission half of owner listings). These
  need a person to confirm facts, supply photos, or clear a legal disclaimer.
- **Future external/web research:** `developer_unverified`, `landmarks_unverified`,
  `rent_range_missing`, `resale_range_missing`. Flagged `external_calls_required=true`
  but **queued, not executed** — `external_calls_allowed=false`, so no web research,
  scraping, or external API call happens in this phase.

## Internal evidence examples (15 rows, all `candidate`, safe counts only)

Evidence is attached only to the internally-resolvable gaps, scoped to the profile's
building, and every `safe_summary` embeds a **count only** — never a name, phone,
email, address, or website.

| gap_type | evidence_type(s) |
| -------- | ---------------- |
| `inventory_availability_unverified` | `unit_count`, `inventory_hint`, `source_batch_count` |
| `owner_listing_permission_needed` | `active_owner_relationship_count`, `building_alias` |

The `internal_source_evidence` enum also documents `content_brief` and `seo_keyword`
for future use. Evidence is `candidate` until a human accepts it via the review queue.

## Why nothing is resolved automatically

A gap closing means a public-facing factual claim becomes citable. That decision is
reserved for a human: internal counts are only *hints* (e.g. "N units on file" does not
prove live availability), owner listing needs explicit permission, market ranges and
developer/landmark facts require verified external sources we do not call here, and
legal disclaimers need review. So every gap stays `open`, every task stays `pending`,
and all evidence stays `candidate` until reviewed.

## Review queue meaning

Each open gap gets a `gap_classification_review` (17), and each gap that received
internal evidence also gets an `internal_evidence_review` (6) → **23 pending review
items**. A human works the queue in NocoDB (`vw_source_gap_review_queue`): confirm the
classification, accept/reject the internal evidence, and decide to resolve or waive the
gap. `vw_source_gap_resolution_dashboard` shows a `recommended_next_action` per gap;
`vw_imperial_heights_source_gap_status` shows per-brief `ready_for_source_review=true`,
`ready_for_ai_draft=false`, `ready_for_publish=false`, and a `blocked_reason`.

## Cleanup (dry-run) command

```bash
# Dry-run (default): shows the tagged 6.5 rows that would be deleted.
python3 scripts/cleanup_source_gap_resolution.py --profile-slug imperial-heights-goregaon-west

# Apply (only deletes rows tagged phase='6.5'/source='source_gap_resolution_workflow';
# refuses if any task is resolved / external_calls_allowed / communication_sent / published;
# never touches Phase 6.1/6.2/6.3/6.4 rows or the content_source_gap_items themselves):
python3 scripts/cleanup_source_gap_resolution.py --profile-slug imperial-heights-goregaon-west --apply --real-ok
```

## Safety posture (verified after apply)

- **No gaps auto-resolved** — gaps still `open=17`, `resolved=0`.
- **No external API/web calls** — `external_calls_allowed=0`; `external_calls_required=7`
  is a *future-work* flag only, nothing executed.
- **No AI execution** — `ai_agent_tasks` remain `queued` (0 completed).
- **No publishing** — `ready_for_publish=false`, `published=0`, `public_ready=0`.
- **No outreach** — `communication_sent=0`.
- **Phases 6.1–6.4 and real data untouched** — profile 1, keywords 10, briefs 3,
  draft artifacts 7, draft reviews 7, source requirements 20; contacts 4, active owner
  relationships 2.

## Commands

```bash
# Plan resolution tasks/evidence/reviews (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/plan_source_gap_resolution.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
```

## Next recommendation

- Work the `vw_source_gap_review_queue` in NocoDB: confirm each gap's classification,
  accept/reject the internal evidence, and resolve or waive gaps **only** when backed by
  verified, citable sources.
- **Phase 6.6 (built):** the internal evidence acceptance workflow — a human accepts the
  purely-internal, non-personal evidence candidates (the first batch accepted the 3
  `building_alias` rows) without resolving any gap. See
  `docs/PHASE_6_6_INTERNAL_EVIDENCE_ACCEPTANCE.md`.
- **Later (suggested):** a guarded script to apply gap-resolution decisions (mark a gap
  `resolved`/`waived` with `resolution_notes` + a review approval), plus building dedupe
  so `active_owner_relationship_count` can be trusted. Final public drafting + Wix
  publishing remain gated, future, and out of scope until every gap is cleared and all
  Phase 6.2/6.3 checks pass.
