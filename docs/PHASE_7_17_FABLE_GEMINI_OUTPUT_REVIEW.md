# Phase 7.17 — Fable "Gallery White" + Gemini Output Review

Phase 7.17 captures the **manually generated** Fable website design output and the
**Gemini second-opinion critique** for DLF Westpark into review-gated database rows, and
records the concrete design refinements extracted from that critique. It is **capture and
review only**: no Fable call, no Gemini call, no Wix/Meta/WhatsApp/email/n8n call, no
publishing, no live form/webhook, no inbound leads, no contact writes.

The raw Fable/Gemini artifacts live **only on disk under the git-ignored `exports/` tree**.
The database stores filesystem paths plus curated, business-safe summaries and the refinement
actions — never the raw artifact text.

## What was captured

- **Fable output — "DLF Westpark — Gallery White"** (`fable_design_outputs`, status
  `captured`): an editorial, white-dominant luxury design system — deep-teal anchors,
  Manrope typography, monospace placeholder tokens for unverified facts, a type-first hero,
  a seven-section landing narrative (identity → location → lifestyle → residences →
  perspective → verified facts → enquire), a manual-review lead form (no live webhook), a
  motion spec, mobile behavior, imagery direction, performance/SEO budgets, and a Wix build
  map. Design-only — nothing was published or wired.
- **Gemini critique** (`design_second_opinion_reviews`, source `gemini`, status `captured`):
  praises the disciplined premium system and proposes a branding-grounding fix plus ten
  actionable improvements for the Wix build.

## Migration & artifacts

- `schemas/037_fable_design_output_review.sql` adds four tables —
  `fable_design_outputs`, `design_second_opinion_reviews`, `design_refinement_actions`,
  `fable_design_review_items` — and five views:
  `vw_fable_design_output_dashboard`, `vw_design_second_opinion_dashboard`,
  `vw_design_refinement_action_dashboard`, `vw_fable_design_review_queue`, and the real gate
  `vw_dlf_design_output_readiness`.
- Capture script: `scripts/capture_dlf_fable_design_output.py` (dry-run by default;
  `--real-ok --apply` to write). It refuses if the launch project is missing, if any raw
  path is not under `exports/`, or if a text artifact fails the leakage scan (emails,
  phone-like strings, leaked DB UUIDs, secret/API-key patterns). All scans returned 0.
- Raw artifacts remain git-ignored under `exports/`:
  - `exports/fable_outputs/dlf-westpark-gallery-white-v1/fable-output-full.md`
  - `exports/fable_outputs/dlf-westpark-gallery-white-v1/dlf-westpark-gallery-white-preview.png`
  - `exports/fable_outputs/dlf-westpark-gallery-white-v1/gemini-review.md`

> Note: the website Gemini review and preview were saved under `exports/fable_outputs/...`
> rather than `exports/design_reviews/...`; the capture script accepts explicit paths and
> validated them as under `exports/`.

## Top refinement actions (12 proposed, all `proposed`/pending review)

| Action key | Category | Priority |
|---|---|---|
| `hero_visual_context` | hero | high |
| `logo_brand_grounding` | brand | high |
| `branded_placeholder_status` | compliance | high |
| `mobile_nav_scroll_reveal` | navigation | high |
| `semantic_seo_heading_strategy` | seo | high |
| `intent_auto_select` | form_ux | high |
| `fixed_image_aspect_ratios` | performance | high |
| `perspective_asym_layout` | brand | normal |
| `warmth_against_cold_minimalism` | brand | normal |
| `mini_map_toggle` | imagery | normal |
| `input_target_fill` | form_ux | normal |
| `sticky_cta_intersection_hide` | mobile | normal |

## What should be considered for acceptance as the design direction

The "Gallery White" system is a strong, defensible direction: it is premium and editorial,
keeps unverified facts honest via monospace placeholders, routes the lead form to manual
review, and ships a clean Wix build map. The recommended path is to accept it as the working
direction **with the high-priority refinements folded in**, rather than as-is.

## What needs careful handling

- **Logo / brand disconnect** — the warm, multi-faceted Real Deal Housing logo and the
  mass-market name sit in tension with the cold, boutique UI. Ground the palette in the
  logo's deep-teal (`#1F3D4D`) and keep the warm roof facets confined to the specified
  eyebrow ticks (`logo_brand_grounding`).
- **Placeholder fatigue** — a page full of robotic `VERIFY` tokens can read as unfinished.
  A branded "pending" micro-copy is allowed **only as an honest wrapper** and must never
  imply a fabricated value (`branded_placeholder_status`).
- **SEO heading semantics** — the "two type sizes per section" rule limits nested H3/H4
  structure; map visually-quiet text to real H3/H4 on long-form SEO pages while keeping one
  H1 per page (`semantic_seo_heading_strategy`).
- **Mobile navigation** — dropping navigation entirely forces long thumb-scrolling; add a
  scroll-up-reveal section nav (`mobile_nav_scroll_reveal`).
- **Visual warmth** — pure cold minimalism can feel clinical for a home purchase; introduce
  controlled warmth within the one-accent-per-viewport budget (`warmth_against_cold_minimalism`).
- **Form tap targets** — underline-only fields are hard to locate; add a soft mist fill that
  defines the target area (`input_target_fill`).
- **Sticky CTA behavior** — the mobile sticky bar must retract before the form and stay
  hidden through the footer to avoid overlapping form buttons/legal (`sticky_cta_intersection_hide`).
- **Image aspect ratio / CLS** — declare explicit aspect ratios on every Wix image container
  to keep CLS near zero during load (`fixed_image_aspect_ratios`).

## Why no Fable / Gemini / API call happened

Both the Fable output and the Gemini critique were produced **manually by the operator** and
pasted into local files. This phase only reads those files, scans them for leakage, and
records paths + safe summaries. The schema keeps `external_call_made` false across all rows,
and `vw_dlf_design_output_readiness.external_call_made_count` stays `0`.
`ready_for_wix_design_build` stays `false` until a human approves the captured output and at
least one refinement action.

## Cleanup (dry-run command)

```
python3 scripts/cleanup_dlf_fable_design_output_capture.py --launch-key dlf-westpark-andheri-west
```

Dry-run by default. `--real-ok --apply` deletes only Phase 7.17 rows
(`phase='7.17'`, `source='fable_gemini_design_output_capture'`). It refuses if any output is
`accepted_direction`, any review is `accepted_guidance`/`partially_accepted`, any action is
`accepted`, or any row is `external_call_made`. Raw artifacts are preserved unless
`--delete-artifacts` is passed explicitly (and even then only files under `exports/`).

## Counts after capture

- `fable_design_outputs`: 1 (`captured`)
- `design_second_opinion_reviews`: 1 (`gemini`, `captured`)
- `design_refinement_actions`: 12 (`proposed`)
- `fable_design_review_items`: 14 pending (1 output + 1 Gemini + 12 action)
- `external_call_made_count`: 0 · `ready_for_fable_followup`: false · `ready_for_wix_design_build`: false
- inbound leads: 0 · contacts: 4 · send/publish/communication: 0

## Next phase

Approve the captured Fable output (`output_status` → `accepted_direction`) and the chosen
refinement actions (`action_status` → `accepted`) through the review queue, then either craft
a **refined Fable follow-up prompt** that folds in the accepted refinements or author the
**Wix design build spec**. Connecting tracking/messaging, building live forms/webhooks, and
publishing Wix pages remain separate explicit phases and stay blocked.
