# UI/UX Audit Report — Real Deal Housing Design System

*Senior UI/UX engineering review · July 7, 2026*

## Scope

All four surfaces were loaded live and probed (DOM measurement + interaction scripting,
not screenshots alone): website kit (Home / Buy / Westpark / Mobile), motion-direction kit,
operations cockpit, and the 24 Design System tab cards.

## Mobile experience — VERIFIED ✅

Probed programmatically inside the 390px phone frame (`ui_kits/website/index.html#mobile`):

- **Sticky two-segment CTA** (teal *Request details* | warm *WhatsApp*): pinned to the frame
  bottom (measured gap 1px), 49px tall — above the 44px minimum hit target.
- **Hide-on-enquiry behavior**: IntersectionObserver fires correctly — scrolling the enquiry
  section into view animates the bar to `translateY(100%)` (measured), and it returns when
  scrolling back up. Matches the source `sticky-cta.tsx` contract (300ms slide, `-40%` bottom margin).
- **Scroll**: inner frame scrolls independently (content 1556px in a 716px viewport);
  type scales down correctly (44px hero vs 88px desktop); pending chips wrap inline cleanly.
- **Hit targets**: all buttons ≥44px; nav pill and CTA segments pass.

## Desktop screens — VERIFIED ✅

- **Home**: hero clamp type, launch banner, project/listing grids, pillars, testimonial —
  all faithful to the Next.js source; reveals fire once with correct stagger.
- **Buy/Rent**: toggle re-filters instantly (6 sale / 4 rent), badges no longer wrap.
- **Westpark**: 10-section scroll story, pending chips, facts ledger with status badges,
  native FAQ disclosures, multi-state map card (Transit/Schools/Retail) all functional.
- **Motion direction**: ken-burns slider + numbered progress pagination, masked line
  reveals settle to identity transform, count-up stats, hover project rows with sticky
  swapping preview, parallax feature, ticker — no console errors; reduced-motion respected.
- **Cockpit**: sidebar states, launch-readiness strip, building stat cards, review/agent/
  blocker rails, contacts funnel + merge queue all render faithfully.

## Defects found & fixed during audit

1. `Button` — long labels wrapped inside pills at narrow widths → `white-space: nowrap`
   set at component level (was previously patched per-instance in SiteHeader, ListingCard).
2. `Pill` — same wrap issue in the cockpit topbar ("3 blockers · go-live locked") → fixed
   at component level.
3. Motion hero — near-white master-layout image gave low headline contrast → removed from
   rotation; scrim deepened to `rgba(31,61,77,0.6)`.
4. Kit pages — silent white page when the compiled bundle was stale → replaced with a
   visible "bundle compiling — reloading…" notice + bounded auto-retry.

## Known limitations (by design / flagged)

- **Fonts** load from Google Fonts (no binaries exist in the codebase). Supply .woff2 for offline.
- **Imagery**: only 4 real Westpark visuals exist; everything else uses the honest dashed
  placeholder per brand rules (never stock).
- **No native mobile app** exists in the source — "mobile" is the responsive site in a phone frame.
- **Hover-dependent motion** (project rows, hover zoom) needs a touch fallback decision
  before production: recommend tap-to-preview or scroll-driven activation on touch devices.
- Cockpit is designed for ≥1280px (internal tool); slight horizontal scroll below ~950px
  is expected and matches the source's fixed 240px sidebar.
- Cockpit Audiences / Outreach / Media screens are intentionally stubbed.

## Verdict

System is consistent, token-complete (123 tokens, 34 compiled components, 24 cards),
faithful to the Gallery White spec, and safe to consume. Mobile experience confirmed working.
