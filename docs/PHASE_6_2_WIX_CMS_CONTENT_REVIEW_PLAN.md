# Phase 6.2 — Wix CMS Mapping & Content Review Plan

Prepares the Phase 6.1 Imperial Heights SEO/content plan for **future** Wix
publishing — the field mappings, human review queue, and pre-publish checklist —
**without publishing anything**. No Wix/external API is called, no content text is
generated, no outreach is sent, and nothing is marked ready to publish.

## What this phase added (migration 013)

Four tables (read-only dashboards below build on them):

| Table | Purpose |
| ----- | ------- |
| `wix_cms_collections` | Wix CMS collections we expect to publish into later. |
| `wix_cms_field_mappings` | Maps Real Deal OS fields → Wix CMS field keys/types. |
| `content_review_items` | Human review queue for content briefs before drafting/publishing. |
| `publishing_readiness_checks` | Pre-publish checklist results per publishing-queue row. |

Four views: `vw_wix_cms_mapping_dashboard`, `vw_content_review_dashboard`,
`vw_publishing_readiness_dashboard`, `vw_imperial_heights_content_plan`.

## Wix CMS collections planned (2, status `planned`)

- **building_pages** — Wix CMS collection for building SEO pages.
- **blog_posts** — Wix CMS collection for blog/guide content.

`wix_collection_id` is intentionally empty — it is filled only when a real Wix
collection is connected in a future phase.

## Field mappings (12, status `draft`)

Mapped onto `building_pages`:

| Source | Wix field | Type | Required |
| ------ | --------- | ---- | -------- |
| building_web_profiles.building_name | buildingName | text | yes |
| building_web_profiles.profile_slug | slug | text | yes |
| building_web_profiles.area | area | text | no |
| building_web_profiles.city | city | text | no |
| building_web_profiles.developer | developer | text | no |
| building_web_profiles.meta_title | metaTitle | text | yes |
| building_web_profiles.meta_description | metaDescription | text | no |
| building_web_profiles.h1 | h1 | text | no |

Mapped onto `blog_posts`:

| Source | Wix field | Type | Required |
| ------ | --------- | ---- | -------- |
| content_briefs.title | contentTitle | text | yes |
| content_briefs.target_keyword | targetKeyword | text | no |
| content_briefs.content_type | contentType | text | no |
| content_publishing_queue.publish_status | publishStatus | text | no |

All mappings start `draft` and must be reviewed/approved before any future use.

## Content review items (3, status `pending`)

One `brief_review` item per Phase 6.1 content brief (the building page + the two
blog guides), all `pending`, awaiting human review. None are approved.

## Publishing readiness checks (24, status `pending`)

An 8-point checklist per publishing-queue row × 3 rows: `cms_mapping`,
`title_present`, `slug_present`, `meta_present`, `human_approved`,
`no_external_call_required`, `no_outreach`, `wix_ready`. All start `pending` —
this phase scaffolds the checklist; a human/automation verifies each later.

## What still blocks publishing

`vw_publishing_readiness_dashboard.ready_for_publish` is **false** for all 3 rows.
It only flips true when **all** of the following hold (none do yet):

- there is ≥1 readiness check and **no** check is `failed` or `pending`, **and**
- the publishing-queue row's `publish_status` is `approved` or `ready_for_review`
  (all three are still `draft`).

So today every row is blocked with `checks_pending` (and separately
`publish_status_not_approved`). Content review items are also still `pending`.

## Safety posture (verified after apply)

- **No Wix publishing** — `published_count = 0`; all publishing rows `draft`; `ready_for_publish = 0`.
- **No external API/web calls** — every row tagged `external_calls_made=false`; verified 0 rows with `external_calls_made=true`.
- **No outreach** — `communications_sent = 0`; `send_enabled` campaigns = 0.
- **Phase 6.1 + real data untouched** — building_web_profiles 1, seo_keywords 10, content_briefs 3, publishing rows 3, ai_agent_tasks 5; contacts 4, active owner relationships 2.

## Commands

```bash
# Prepare (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/prepare_wix_content_review.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]

# Cleanup / rollback (dry-run default; --apply --real-ok to delete only 6.2 rows;
# refuses if anything is published or made external calls; never deletes 6.1 artifacts):
python3 scripts/cleanup_wix_content_review.py \
  --profile-slug imperial-heights-goregaon-west
```

## Next recommendation

- Inspect `vw_wix_cms_mapping_dashboard`, `vw_content_review_dashboard`, and
  `vw_publishing_readiness_dashboard` in NocoDB; review/approve the field mappings
  and the brief reviews by hand.
- **Phase 6.3 (suggested):** a guarded script to record review decisions
  (approve mappings / briefs) and flip the objective readiness checks
  (`title_present`, `slug_present`, `meta_present`, `no_external_call_required`,
  `no_outreach`) to `passed` — still no publishing, still no `send_enabled`.
- Connecting a real Wix collection (`wix_collection_id`) and any actual publish
  remains future work and must stay behind the readiness gate.
