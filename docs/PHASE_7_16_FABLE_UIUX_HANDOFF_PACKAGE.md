# Phase 7.16 - Fable UI/UX Handoff Package for DLF Westpark

Phase 7.16 distills the approved Phase 7.15 Wix UX/SEO/integration masterplan into a clean,
token-efficient, privacy-safe **Fable handoff package**: two local Markdown artifacts a human can
paste into Fable to generate the premium UI/UX design for the Real Deal Housing / DLF Westpark
website.

This phase **prepares** the handoff — it does NOT design the final UI and does NOT call Fable. It
performs NO Fable call, NO Wix/Meta/WhatsApp/email/n8n API call, NO publishing, NO live form/webhook,
and NO sends. Artifacts contain only public/business-safe design direction. `fable_call_made` and
`external_call_made` stay false, and `vw_dlf_fable_handoff_readiness.ready_for_fable_use` stays false
until human reviews are approved. Launch remains **safe_blocked**.

## Why Fable is used only after the strategy is clean

Fable/Claude has a larger token budget and should be used carefully and intentionally. Codex/Opus
builds the information architecture, page set, integrations, CTAs, SEO goals, and safety placeholders
first (Phases 7.14-7.15); only once that brief is clean and review-gated does Fable receive a tight,
self-contained prompt for UI/UX design. This keeps Fable focused on design — not on re-deriving
strategy — and avoids wasting its budget on context Codex already settled.

## Artifacts generated

Both are written under the git-ignored `exports/fable_handoffs/` directory:

- **Concise Fable prompt** — `exports/fable_handoffs/dlf-westpark-fable-prompt-concise.md`
  (~2.2 KB, well under the token-efficiency budget): a single paste-ready prompt.
- **Detailed Fable design brief** — `exports/fable_handoffs/dlf-westpark-fable-design-brief.md`:
  the full 14-section brief.

The artifact SHA-256 is recorded in `fable_uiux_handoff_packages.raw_context`.

## What was included

Pulled from the approved Phase 7.15 blueprint, pages, and design components (public design content
only): project (DLF Westpark) and Real Deal Housing website context; the Apple-inspired luxury
real-estate direction; the 7-page site architecture; the DLF landing-page hero-first scroll flow;
mobile-first behavior; typography and motion direction; Three.js guidance; Wix constraints; SEO
constraints; CTAs and conversion goals; form/consent UX requirements; and placeholder rules.

Tracked as 12 `fable_uiux_handoff_sections` (brand_direction, target_audience, page_architecture,
landing_page_flow, visual_language, motion_language, conversion_goals, seo_constraints,
component_requirements, threejs_guidance, wix_constraints, placeholder_rules), 11 of which are also
in the concise prompt.

## What was excluded

No contact names, phone numbers, emails, raw lead/contact data, secrets, DB identifiers (UUIDs),
internal source paths, or raw imports/exports. A direct scan of both artifacts confirmed zero UUID /
email / phone / secret leakage.

## Apple-inspired design direction

Apple-inspired (not copied) luxury real estate: clean, premium, minimal, calm, trustworthy. Neutral
palette (black / white / stone / charcoal with a restrained gold accent), large whitespace, premium
sans-serif typography, hero-first storytelling, scroll-based narrative, cinematic imagery, subtle
motion only, optional lightweight Three.js accent, mobile-first, and SEO text never hidden inside a
canvas.

## Placeholder rules

The artifacts keep unverified facts as verbatim placeholders — Fable must not invent values:
`RERA_VERIFY`, `PRICE_VERIFY`, `BROCHURE_LINK_PENDING`, `WIX_PAGE_PENDING`, `VERIFY`,
`VISUAL_DIRECTION_PENDING`. No false scarcity or guaranteed-return language is permitted (the
generator's `placeholders_preserved` validation rejects affirmative scarcity/guarantee claims while
allowing negated compliance disclaimers).

## Validation checks

The generator validates both artifacts before writing. All nine passed: `no_contact_data`,
`no_secrets`, `no_internal_db_ids`, `placeholders_preserved`, `apple_inspired_not_copied`,
`mobile_first`, `seo_constraints_present`, `wix_constraints_present`, `fable_token_efficiency`.

## Migration

`schemas/036_fable_uiux_handoff_package.sql` adds tables `fable_uiux_handoff_packages`,
`fable_uiux_handoff_sections`, `fable_uiux_handoff_validation_results`,
`fable_uiux_handoff_review_items`, and views `vw_fable_uiux_handoff_package_dashboard`,
`vw_fable_uiux_handoff_section_dashboard`, `vw_fable_uiux_handoff_validation_dashboard`,
`vw_fable_uiux_handoff_review_queue`, and `vw_dlf_fable_handoff_readiness` (which keeps
`fable_call_made_count`/`external_call_made_count` at 0 and gates `ready_for_fable_use` on review).

## Generate the handoff package

```bash
# Dry-run (default): projected counts + validations, writes nothing.
python3 scripts/create_dlf_fable_uiux_handoff_package.py \
  --launch-key dlf-westpark-andheri-west --real-ok

# Apply: writes the two ignored Markdown artifacts and DB rows.
python3 scripts/create_dlf_fable_uiux_handoff_package.py \
  --launch-key dlf-westpark-andheri-west --real-ok --apply
```

The generator refuses to write if any validation fails, and a transaction guard refuses if a prior
Phase 7.16 package is marked called/external/contact/secret/approved, or if inbound/contacts/send/
publish state drifts.

## Why no Fable / API call happened

This phase is intentionally inert beyond writing local artifacts and tracking rows. Calling Fable is a
deliberate human step performed outside this system by pasting the reviewed concise prompt into Fable.
No automated Fable call, no Wix/Meta/WhatsApp/email/n8n call, and no publishing are part of this
phase.

## Cleanup dry-run

```bash
python3 scripts/cleanup_dlf_fable_uiux_handoff_package.py \
  --launch-key dlf-westpark-andheri-west
```

Dry-run by default; deletes only rows tagged `phase='7.16'` /
`source='dlf_fable_uiux_handoff_package'`. It refuses if any package is marked `fable_call_made`,
`external_call_made`, or has status `approved_for_fable`/`used_in_fable`. It never touches
Phase 7.0-7.15 rows. Artifact deletion is opt-in via `--delete-artifacts` and still requires
`--real-ok --apply`.

## Verified counts

- handoff packages: 1 `generated`
- sections: 12 `draft` (11 also in the concise prompt)
- validation results: 9 passed (0 failed)
- review items: 7 pending (fable_prompt / design_direction / privacy / seo / conversion / wix_feasibility / threejs)
- fable_call_made_count: 0 · external_call_made_count: 0 · ready_for_fable_use: false
- inbound leads: 0 · contacts: 4 · send/publish/communication: 0

## Next phase

Review and approve the Fable handoff package (the seven pending reviews → `approved_for_fable`), then
a human pastes the concise prompt into Fable manually to generate the UI/UX design. Connecting
tracking/messaging integrations, building live forms/webhooks, and publishing Wix pages remain
separate explicit phases and stay blocked.

> **Follow-up:** Phase 7.17 captures the resulting Fable output ("DLF Westpark — Gallery White")
> and the Gemini second-opinion critique into review-gated rows and extracts 12 design refinement
> actions. See `docs/PHASE_7_17_FABLE_GEMINI_OUTPUT_REVIEW.md`.
