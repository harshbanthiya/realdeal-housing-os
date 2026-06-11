# Phase 7.15 - Wix Website UX, SEO and Integration Masterplan

Phase 7.15 upgrades the DLF Westpark effort from a single landing-page build package (Phase 7.14)
into a **unified website experience masterplan**: the full Wix site as a premium, mobile-first
lead-generation and SEO system, with every external integration explicitly planned but **not
connected**.

This phase is **planning, schema, and safety-gating only**. It performs NO external calls
(Wix/Meta/WhatsApp/email/n8n/Google), NO publishing, NO live form/webhook creation, and NO sends.
Every integration stays `external_call_allowed=false`, every page stays `publish_enabled=false`, and
`vw_dlf_wix_unified_experience_readiness.ready_to_publish` stays false. Launch remains **safe_blocked**.

## Why upgrade from a landing page to a unified website experience

The user already has a Wix site and wants it redesigned into a premium lead-generation + SEO engine
that will eventually integrate with Real Deal Housing OS, NocoDB/operator dashboards, n8n, Meta
Business/Pixel/CAPI, WhatsApp Business, email campaign software, and SEO/social automation. A single
landing page cannot carry topical SEO authority, brand trust, multi-channel tracking, or a content
hub. This masterplan defines the whole system up front so design and integration work proceed against
one reviewed architecture instead of ad-hoc pages.

## Apple-inspired luxury design direction

The website experience should feel like an **Apple-style real estate site — inspired, not copied**:
clean, premium, minimal, with large whitespace, beautiful typography, and a strong visual hierarchy.
It must read as luxury, calm, trustworthy, and technically polished — never a cluttered broker-style
property portal, loud colors, overstuffed cards, or a cheap real-estate template. This direction is
stored on `wix_site_experience_blueprints` (`design_direction`, `premium_visual_strategy`,
`threejs_component_strategy`) and on the relevant `wix_design_component_specs`. No final UI is
generated in this phase — it is the design brief for a later Fable handoff (Phase 7.16).

1. **Hero-first storytelling** — full-width premium hero, one short headline, one primary CTA, one
   secondary CTA, and quiet trust markers.
2. **Scroll narrative** — each scroll section reveals ONE idea (project identity → location
   advantage → lifestyle → configuration interest → investment/referral angle → verified facts →
   lead form) instead of dumping all details at once.
3. **Typography** — premium sans-serif, large headlines, restrained body text, generous line-height,
   few font weights.
4. **Visual system** — neutral background, soft contrast, black / white / stone / charcoal with a
   restrained gold accent; image-first layouts; cards only where useful; no crowded grids on landing
   pages.
5. **Motion** — subtle scroll reveals, sticky CTA behavior, smooth section transitions; optional
   Three.js / custom visual only as a lightweight premium accent; no heavy animation that hurts
   speed, mobile UX, or SEO.
6. **Conversion** — premium (not spammy) lead form, sticky WhatsApp CTA on mobile, brochure / price /
   site-visit intent capture, trust + privacy language visible near forms, and a thank-you page
   designed for the next action.
7. **SEO** — still supports structured content with clean H1/H2 hierarchy, an SEO FAQ section, and
   internal links to area/building/blog pages; important text never hidden inside canvas/Three.js;
   page speed and mobile performance remain publish blockers.

## Page architecture (`wix_page_blueprints`)

Seven page blueprints (all `draft`, `publish_enabled=false`):

- **homepage** — `home-refresh` (`/`): premium brand + lead entry point.
- **project_landing** — `dlf-westpark-landing` (`/dlf-westpark-andheri-west`): primary conversion page.
- **area_seo_page** — `andheri-west-luxury-property` (`/andheri-west-luxury-property`).
- **building_seo_page** — `mumbai-luxury-real-estate-guide` (`/mumbai-luxury-real-estate-guide`).
- **blog_index** — `dlf-westpark-blog-hub` (`/blog`): content hub.
- **thank_you_page** — `lead-thank-you` (`/thank-you`): conversion confirmation + tracking.
- **privacy_page** — `privacy-consent` (`/privacy`): consent/opt-out basis.

## SEO strategy

Build topical authority around DLF Westpark, Andheri West luxury property, and Mumbai luxury real
estate via the area/building SEO pages and the blog hub, all funnelling to the project landing page.
Factual claims (RERA, price, carpet area) remain placeholders until human-verified — no FAQ/schema
markup ships on unverified content. GSC + GA4 + GTM are planned for measurement; mobile-first
performance and a static-first hero protect Core Web Vitals.

## Integration plan (`wix_integration_readiness_items`)

Eleven integrations, all `planned`, all `external_call_allowed=false`, none `active`:

- `meta_pixel_capi`, `google_search_console`, `ga4`, `google_tag_manager` (tracking)
- `wix_forms`, `wix_cms` (Wix-native)
- `n8n_webhook` (the Phase 7.11-7.13 inactive lead-intake path)
- `whatsapp_chat`, `whatsapp_business_platform`, `email_provider`, `crm_sync` (RDH OS / NocoDB)

`contains_secret_required` flags which integrations will eventually need credentials; no secret is
stored in the repo and none is connected in this phase.

## Meta / WhatsApp / email / n8n readiness

All four remain readiness records only. Meta Pixel + CAPI, WhatsApp chat/Business Platform, the email
provider, and n8n are each represented as a `planned` integration with a pending human review. No
pixel fires, no WhatsApp/email send, no n8n webhook is live, and consent/opt-out language remains a
precondition for any future messaging channel.

## Three.js / custom component strategy (`wix_design_component_specs`)

Eleven design components (all `draft`). The Apple-inspired direction is encoded directly on the key
components:

- `premium-hero` — Apple-style hero-first storytelling: cinematic full-width hero, one headline,
  primary + secondary CTA, quiet trust markers; H1/CTAs stay in the real DOM, static image fallback.
- `dlf-westpark-lead-form` — premium, editorial, trust-forward form with consent/opt-out visible near
  submit; brochure/price/site-visit intent capture; routed to manual review (no live webhook).
- `sticky-whatsapp-cta` — minimal, quiet click-to-WhatsApp that becomes a mobile bottom CTA; deferred
  load, respects reduced-motion, not connected to the WhatsApp API.
- `seo-faq` — clean scannable FAQ with H2 hierarchy and internal links to area/building/blog; real
  DOM text, schema only on verified content.
- `threejs-hero-visual` — **optional** lightweight WebGL accent only: progressive enhancement, static
  cinematic fallback, must not block LCP / hurt mobile UX / hide SEO copy in canvas
  (`performance_risk=high`, `seo_risk=medium`, gated by a `performance_review`).

A `trust-verification-bar`, `location-lifestyle`, `blog-card-grid`, `thank-you-conversion-tracker`,
`mobile-bottom-cta`, and a `fable-design-handoff` placeholder round out the set.

## Future Fable handoff strategy — and why Fable is deferred

A `fable-design-handoff` component is recorded for a **future phase**. High-end visual design via
Fable/Claude (and any Three.js/custom build) is deferred until the UX/SEO/integration brief is clean
and human-approved. Designing premium visuals before the architecture, SEO intent, conversion goals,
and integration constraints are settled would produce rework. Every masterplan row carries
`raw_context.fable_handoff_future_phase=true` to mark this boundary. This phase stays in
Codex/Opus because it is system architecture, not final visual design.

**Phase 7.16** should create a Fable-specific UI/UX handoff package using this Apple-inspired luxury
real-estate direction (hero-first storytelling, scroll narrative, neutral palette with a gold accent,
subtle motion, premium conversion + SEO constraints). Fable is used only after the information
architecture, pages, integrations, CTAs, SEO goals, and safety placeholders are clean — which this
phase establishes.

### Refreshing the design direction

The Apple-inspired direction can be re-applied to the existing Phase 7.15 rows from the seed
constants (UPDATE only — no inserts, no flag/status changes):

```bash
python3 scripts/seed_dlf_wix_ux_integration_masterplan.py \
  --launch-key dlf-westpark-andheri-west --refresh-design --real-ok --apply
```

Dry-run by default; a live guard refuses if any integration is external/active, any page is
publish_enabled, or inbound-lead/contact/send/publish state drifts.

## Why no API call or publish happened

This phase is intentionally inert: it writes only planning rows and review items. The seed's
transaction guard refuses if any integration is `external_call_allowed`/`active`, any page is
`publish_enabled`, or if inbound-lead/contact/send/publish state drifts. Connecting Meta/WhatsApp/
email/n8n/Google, building live forms/webhooks, and publishing Wix pages are each separate, explicit,
review-gated phases.

## Migration

`schemas/035_wix_ux_integration_masterplan.sql` adds tables `wix_site_experience_blueprints`,
`wix_page_blueprints`, `wix_integration_readiness_items`, `wix_design_component_specs`,
`wix_ux_review_items`, and views `vw_wix_site_experience_dashboard`,
`vw_wix_page_blueprint_dashboard`, `vw_wix_integration_readiness_dashboard`,
`vw_wix_design_component_dashboard`, `vw_wix_ux_review_queue`, and
`vw_dlf_wix_unified_experience_readiness` (which hard-pins `ready_to_publish=false`).

## Seed the masterplan

```bash
# Dry-run (default): projected counts only, writes nothing.
python3 scripts/seed_dlf_wix_ux_integration_masterplan.py \
  --launch-key dlf-westpark-andheri-west --real-ok

# Apply: writes the planning rows + review queue.
python3 scripts/seed_dlf_wix_ux_integration_masterplan.py \
  --launch-key dlf-westpark-andheri-west --real-ok --apply
```

The seed refuses if the launch project is missing and refuses duplicate Phase 7.15 rows unless
`--allow-existing`.

## Cleanup dry-run

```bash
python3 scripts/cleanup_dlf_wix_ux_integration_masterplan.py \
  --launch-key dlf-westpark-andheri-west
```

Dry-run by default; deletes only rows tagged `phase='7.15'` /
`source='dlf_wix_ux_integration_masterplan_seed'`. It refuses if any integration is
`external_call_allowed`/`active`/`connected_manually`, any page is `publish_enabled`, or any review is
`approved`. It never touches Phase 7.0-7.14 rows, landing/form specs, field mappings, or Wix build
packages. Writing requires `--real-ok --apply`.

## Verified counts

- site experience blueprints: 1 `draft`
- page blueprints: 7 `draft` (one per page type), `publish_enabled=false`
- integration readiness items: 11 `planned`, `external_call_allowed=false`, `integrations_active=0`
- design component specs: 11 `draft`
- review items: 31 pending (ux/seo/integration/tracking/design/performance/conversion/publish_blocker)
- ready_for_manual_wix_build: false · ready_for_tracking_connection: false · ready_to_publish: false
- external_call_allowed_count: 0 · publish_enabled_count: 0
- inbound leads: 0 · contacts: 4 · communication_sent: 0

## Next phase

Either a **Fable UI/UX handoff package** (once the brief is approved) or a **manual Wix build/review
plan**. Connecting tracking/messaging integrations, building live forms/webhooks, and publishing Wix
pages remain separate explicit phases and stay blocked.
