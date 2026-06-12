# Phase 7.18 — Gallery White: Approved Design Direction & Refined Spec

Phase 7.18 records the human review decision for DLF Westpark's public website design.
**"Gallery White" is accepted as the selected design direction**, the Gemini critique is
accepted as guidance, and all twelve refinement actions are accepted. This is a review/spec
phase only: no Fable, Gemini, Wix, Meta, WhatsApp, email, or n8n call; no publishing; no live
forms/webhooks; no contact/lead/message changes. Raw Fable/Gemini artifacts remain git-ignored
under `exports/` and are never copied into the repo or this document.

## Status after approval

- `fable_design_outputs`: 1 → **`accepted_direction`**
- `design_second_opinion_reviews` (Gemini): 1 → **`accepted_guidance`**
- `design_refinement_actions`: 12 → **`accepted`**
- `fable_design_review_items`: 14 → **`approved`** (0 pending)
- `vw_dlf_design_output_readiness`: `ready_for_fable_followup = true`, `ready_for_wix_design_build = true`
- `external_call_made_count = 0` · `ready_for_launch_push = false` · send/publish = 0 · inbound_leads = 0 · contacts = 4

`ready_for_wix_design_build` is a **computed design-readiness signal** (the captured output is
accepted, refinements accepted, and no design review is left pending). It is **not** a launch
or publish gate — `ready_for_launch_push` stays false and all send/publish flags stay disabled.

## Approved design principles (Gallery White)

- **Apple-inspired, not copied** — premium, editorial restraint; no real-estate-template clutter.
- **Clean premium whitespace** — white dominant (~85% of surfaces), generous spacing scale.
- **Manrope / system sans** — large headlines, restrained body, few weights; monospace reserved
  strictly for unverified data tokens so placeholders read as provisional.
- **Deep-teal grounding** — `#1F3D4D` anchors headlines, primary buttons, dark "chapter" sections.
- **Restrained warm logo-facet accents** — crimson/pink/orange roof facets only as eyebrow ticks;
  never more than one warm accent per viewport.
- **Scroll-based storytelling** — one idea per section across the seven-section landing narrative.
- **Image-first luxury real-estate feel** — cinematic, cool-graded architectural imagery; flat
  labelled placeholder frames until real photography exists (never stock).
- **Mobile sticky CTA** — two-segment bottom bar (Request details ｜ WhatsApp) that yields to the form.
- **SEO text in the DOM** — semantic H1/H2, FAQ as native disclosures, internal links as real text.
- **No canvas text, ever** — any optional Three.js accent is decorative, lazy-loaded, with a static
  fallback, and carries no SEO-critical copy.

## Accepted Gemini refinements (12)

| Refinement | Category | Priority | Essence |
|---|---|---|---|
| Hero visual context (`hero_visual_context`) | hero | high | Reveal a slice of the hero image above the fold to anchor the eye. |
| Logo/brand grounding (`logo_brand_grounding`) | brand | high | Ground the palette in logo teal; confine warm facets to ticks so the mark reads as one brand. |
| Branded placeholder status (`branded_placeholder_status`) | compliance | high | Replace robotic `VERIFY` display with an honest branded "pending" micro-copy — never a fabricated value. |
| Mobile scroll-reveal nav (`mobile_nav_scroll_reveal`) | navigation | high | Add a scroll-up-reveal section nav instead of removing mobile navigation. |
| Semantic SEO headings (`semantic_seo_heading_strategy`) | seo | high | Map visually-quiet text to real H3/H4 on long-form SEO pages; keep one H1 per page. |
| Intent-driven form preselection (`intent_auto_select`) | form_ux | high | "Request details" on a residence row auto-selects the matching intent pill. |
| Fixed image aspect ratios (`fixed_image_aspect_ratios`) | performance | high | Declare explicit aspect ratios on Wix image containers to keep CLS near zero. |
| Section 05 asymmetry (`perspective_asym_layout`) | brand | normal | Asymmetric numeral-plus-statement layout to avoid a text wall. |
| Warmer minimalism (`warmth_against_cold_minimalism`) | brand | normal | Controlled warmth within the one-accent-per-viewport budget. |
| Pseudo-interactive map toggle (`mini_map_toggle`) | imagery | normal | Multi-state static map card (Transit/Schools/Retail); live embed stays deferred. |
| Input background fill (`input_target_fill`) | form_ux | normal | Soft mist fill that defines the field target area, fading to white on focus. |
| Sticky CTA intersection hide (`sticky_cta_intersection_hide`) | mobile | normal | Fade the mobile sticky bar out before the form and keep it hidden through the footer. |

## Wix implementation implications

- Build with Wix sections/strips, repeaters for stat/ledger/fact rows, image placeholders with
  **fixed aspect ratios**, native collapsible FAQ, and sticky-positioned CTA elements.
- The lead form is a Wix Form routed to a **manual-review inbox** — no live webhook, no published
  endpoint in this phase. Intent preselection is an optional Velo/URL-parameter enhancement.
- The location map ships as a **multi-state static card**; a live embed waits for tracking review.
- Placeholder tokens (RERA / price / brochure / visual) stay as honest branded "pending" strings;
  no value is invented to fill them.
- Reveal animations use Wix native viewport animations (fade-up, once); custom easing is optional later.

## What remains blocked

- **Verified facts** — RERA / pricing / brochure values stay placeholders until separately verified.
- **Real photography** — frames stay as labelled placeholders until a photo brief is shot.
- **Wix build** — no Wix page is created or published in this phase.
- **Live forms** — the lead form remains a manual-review design, not a live capture.
- **Tracking** — conversion/analytics tags stay disabled until tracking review passes.
- **Publishing** — `publish_enabled` stays false; `ready_for_launch_push` stays false.

## Raw artifacts

The Fable output, preview image, and Gemini review remain git-ignored under
`exports/fable_outputs/dlf-westpark-gallery-white-v1/`. The database stores only paths plus
business-safe summaries — never raw artifact text. The separate cockpit critique under
`exports/design_reviews/rdh-cockpit-apple-linear-stripe-v1/` is unrelated and reserved for a
future RDH Cockpit UI/UX phase.

## Reversibility

`scripts/revert_dlf_gallery_white_design_review.py` (dry-run by default; `--real-ok --apply`)
restores the Phase 7.18 status changes from the `phase_7_18_*` markers in `raw_context`. It
preserves the captured Phase 7.17 rows and raw artifacts, never touches contacts/leads/messages,
and refuses if any external/send/publish/Wix-publish flag is present.

## Next phase

With the direction approved, the next step is either a **refined Fable follow-up prompt** that
folds in the twelve accepted refinements, or a **Wix staging/preview-site build plan** against
the approved spec. Verified facts, photography, live forms, tracking, and publishing remain
separate, explicitly gated phases.
