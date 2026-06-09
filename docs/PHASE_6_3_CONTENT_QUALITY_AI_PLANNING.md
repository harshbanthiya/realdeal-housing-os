# Phase 6.3 — Content Quality & AI Task Execution Planning

Makes the Imperial Heights content plan **reviewable and ready for future
AI-assisted drafting** — quality checklists, source requirements, reusable AI prompt
templates, and per-task execution plans — while staying **local and non-publishing**.
No AI task is executed, no external/Wix API is called, no final article text is
generated, nothing is published, and no outreach is sent.

## What this phase added (migration 014)

Four tables + five read-only views:

| Table | Purpose |
| ----- | ------- |
| `content_quality_checks` | Per-brief checklist before AI drafting/publishing. |
| `content_source_requirements` | Research/sources needed before a brief is drafted. |
| `ai_prompt_templates` | Reusable, safety-ruled prompt templates for future AI execution. |
| `ai_task_execution_plans` | How each queued `ai_agent_task` should run later (default: manual, no external calls, human review required). |

Views: `vw_content_quality_dashboard`, `vw_content_source_requirements_dashboard`,
`vw_ai_prompt_template_dashboard` (no full prompt text), `vw_ai_task_execution_plan_dashboard`,
`vw_imperial_heights_content_readiness`.

## Quality checks created (24 = 8 × 3 briefs, all `pending`)

`target_keyword_present`, `search_intent_present`, `outline_present`,
`source_requirements_present` (high), `local_market_claims_reviewed` (high),
`no_unverified_claims` (**blocker**), `cms_mapping_exists`,
`human_review_required` (**blocker**). None are auto-passed.

## Source requirements created (20, all `needed`, each with a `[SOURCE URL NEEDED]` placeholder)

- **Building page (8):** building_facts, amenities, location_landmarks, rental_range, resale_range, internal_inventory, owner_relationships, legal_disclaimer.
- **Rent guide (6):** rental_range, internal_inventory, owner_relationships, location_landmarks, faq, legal_disclaimer.
- **Resale guide (6):** resale_range, internal_inventory, owner_relationships, developer_info, faq, legal_disclaimer.

## Prompt templates created (4, status `draft`)

`building_research_template`, `keyword_research_template`, `blog_brief_template`,
`seo_monitoring_template`. Each carries `safety_rules`:

- cite or mark `[SOURCE NEEDED]`
- do not invent building facts
- do not include contact/private data
- do not promise availability
- no outreach
- human review required

Templates emit research notes / outlines / plans only — never a final published article.

## AI execution plans created (5, `execution_status='planned'`)

One per existing Phase-6.1 queued `ai_agent_task` for the profile
(building_research, keyword_research, 2× blog_brief, seo_monitoring), each linked to
the matching prompt template (and to its content brief where the task targets one).
All have `execution_mode='manual'`, `external_calls_allowed=false`,
`requires_human_review=true`.

## What still blocks drafting / publishing

`vw_imperial_heights_content_readiness` shows, for all 3 briefs:

- `ready_for_ai_draft = false` — every brief has open **blocker** quality checks
  (`no_unverified_claims`, `human_review_required`) and outstanding source
  requirements (all still `needed`). It flips true only when there is **no** open
  blocker check **and** no source requirement is still `needed`/`needs_human_review`.
- `ready_for_publish = false` — always, by design in this phase; publishing is a
  separate, future, gated step (also requires the Phase 6.2 readiness checks to pass
  and the publishing row to be approved).

## Safety posture (verified after apply)

- **No AI execution** — only plans/templates/checklists were created; `ai_agent_tasks` remain `queued`.
- **No external API/web calls** — every row tagged `external_calls_made=false`; 0 plans with `external_calls_allowed=true`; verified 0 rows with `external_calls_made=true`.
- **No publishing** — `published_count = 0`; `ready_for_publish = 0`.
- **No outreach** — `communications_sent = 0`.
- **Phases 6.1 + 6.2 and real data untouched** — profile 1, keywords 10, briefs 3, publishing 3, ai tasks 5, collections 2, mappings 12, content reviews 3, readiness checks 24; contacts 4, active owner relationships 2.

## Commands

```bash
# Prepare (dry-run default; real data needs --real-ok; writing needs --apply):
python3 scripts/prepare_content_quality_plan.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]

# Cleanup / rollback (dry-run default; --apply --real-ok deletes only 6.3 rows;
# refuses if anything is published or made external calls; never touches 6.1/6.2):
python3 scripts/cleanup_content_quality_plan.py \
  --profile-slug imperial-heights-goregaon-west
```

## Next recommendation

- In NocoDB, review `vw_content_quality_dashboard`, `vw_content_source_requirements_dashboard`,
  `vw_ai_prompt_template_dashboard`, and `vw_imperial_heights_content_readiness`.
- **Phase 6.4 (suggested):** a guarded script for a human to record decisions —
  collect/verify source requirements, pass the objective quality checks, and approve
  prompt templates — so `ready_for_ai_draft` can legitimately become true for a brief.
- **Then** a **local, dry-run** AI execution step that produces an *outline / research
  notes* (never a final article, no external calls), written back to
  `ai_task_execution_plans` for human review — still no publishing, still no outreach.
