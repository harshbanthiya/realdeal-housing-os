# Phase 6.1 — Imperial Heights First Real SEO/Content Plan

The first **real, review-gated** SEO/content planning set built on the Phase 6.0
growth schema. It creates planning records only — **no external API/web calls, no
publishing, no outreach**. Everything is reversible via the cleanup script.

## Chosen building anchor

| Field | Value |
| ----- | ----- |
| building_id | `0e72db71-8b93-4ecd-879c-17d8d8f2b206` |
| building_name | Imperial Heights |
| city | Mumbai |
| area used for SEO | Goregaon West |
| active owner relationships | 1 |
| units | 1 |
| aliases | 1 |
| created_at | 2026-06-08 15:01:49 (earliest) |

### Duplicate building-anchor note

There are **two** `buildings` rows named "Imperial Heights" (the second is
`f05bbd01-1a27-4073-98bc-fc0e094d7818`, created later, also with 1 active owner
relationship / 1 unit / 1 alias). This duplication is known from the Milestone 2B
checkpoint. Per the tie-break rule, the **earliest-created** anchor was chosen for
the first SEO profile. **Building dedupe/merge is deliberately deferred to a future
phase** — no buildings were merged or modified here.

## Profile slug

`imperial-heights-goregaon-west`

## What was created (all review-gated, tagged `phase=6.1`, `source=real_building_seo_plan`)

### 1 building_web_profile
`seo_status='draft'`, `page_type='building_page'`, with meta title/description/H1
built from the building + area (no street address).

### 10 seo_keywords (`status='planned'`, `difficulty_estimate='low'`)
- Imperial Heights Goregaon
- Imperial Heights Goregaon West
- Imperial Heights flats for rent
- Imperial Heights resale
- Imperial Heights 3 BHK rent
- Imperial Heights 4 BHK rent
- Imperial Heights owner contact
- Imperial Heights broker
- Imperial Heights property dealer
- Imperial Heights Mumbai

### 3 content_briefs (`research_status='pending'`, `approval_status='draft'`)
1. **building_page** — "Imperial Heights Goregaon West: Flats, Rent, Resale and Owner Listings" (target: *Imperial Heights Goregaon West*)
2. **blog** — "Flats for Rent in Imperial Heights Goregaon West" (target: *Imperial Heights flats for rent*)
3. **blog** — "Imperial Heights Goregaon West Resale Guide" (target: *Imperial Heights resale*)

### 3 content_publishing_queue rows (all `publish_status='draft'`)
- `wix_page` draft → building page
- `wix_blog` draft → rent guide
- `wix_blog` draft → resale guide

### 5 ai_agent_tasks (all `status='queued'`, `human_review_required=true`)
- `building_research` (Imperial Heights)
- `keyword_research` (Imperial Heights)
- `blog_brief` (rent guide)
- `blog_brief` (resale guide)
- `seo_monitoring` (placeholder)

## Safety posture (verified after apply)

- **No external API/web calls** — every row tagged `external_calls_made=false`; verified 0 rows with `external_calls_made=true`.
- **No publishing** — all publishing rows `draft`; `content_published_count = 0`.
- **No outreach** — `communications_sent = 0`; no campaigns created; `send_enabled` campaigns = 0.
- **No new contacts / relationships / inbound leads** — `inbound_leads = 0`; contacts remain 4; active owner relationships remain 2; buildings remain 2.

## Apply command (for reference)

```bash
python3 scripts/apply_real_building_seo_plan.py \
  --building-id 0e72db71-8b93-4ecd-879c-17d8d8f2b206 \
  --building-name "Imperial Heights" \
  --area "Goregaon West" \
  --city "Mumbai" \
  --profile-slug "imperial-heights-goregaon-west" \
  --real-ok --apply
```

Dry-run is the default (omit `--apply`). Real data requires `--real-ok`.

## Cleanup / rollback (dry-run shown; NOT applied in this phase)

```bash
# Dry-run (default):
python3 scripts/cleanup_real_building_seo_plan.py \
  --building-id 0e72db71-8b93-4ecd-879c-17d8d8f2b206 \
  --profile-slug "imperial-heights-goregaon-west"

# To actually delete the planning rows (refuses if anything is published / send-enabled /
# made external calls; never deletes the building, contacts, or relationships):
#   add  --apply --real-ok
```

## Next recommendation

- Inspect the plan in NocoDB (`vw_seo_keyword_dashboard`, `vw_content_pipeline_dashboard`,
  `vw_ai_agent_task_dashboard`, `vw_growth_pipeline_home`) and refine keywords/briefs.
- **Phase 6.2 (suggested):** human research + content drafting for the building page
  (move its brief `research_status → research_needed → in progress`, draft into a
  `content_items` row), still with no publishing.
- Building dedupe for the two "Imperial Heights" anchors remains future work; do it
  before scaling SEO profiles so a single canonical building owns the web profile.
