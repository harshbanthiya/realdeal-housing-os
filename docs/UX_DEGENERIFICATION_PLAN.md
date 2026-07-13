# UX DE-GENERIFICATION PLAN
### or: how Real Deal Housing stops looking like a SaaS template and starts looking like the people who know six buildings better than anyone alive

*2026-07-13 · working doc for the redesign workstream. Reference: https://halston-architecture-template.webflow.io/ (Awwwards winner). Companion history: `docs/LAUNCH_CONTEXT.md`. If you're a future Claude reading this because usage ran out mid-flight: welcome, everything you need is here.*

---

## 1. The diagnosis (why the site feels generic)

We audited the live site (web-gray-seven-44.vercel.app) and local `web/` at desktop + mobile:

1. **Card-box grammar.** Nearly every section is a `rounded-2xl border` box in a `max-w-6xl` column. That's dashboard language. Real photography of real towers is imprisoned in padded 50%-width boxes.
2. **Split attention above the fold.** Hero offers FOUR competing actions (View listings, DLF launch chip, phone pill, then a second DLF banner one scroll later). A ₹5Cr buyer's first question is "why trust you?" — not "which link?"
3. **Invisible differentiator.** RDH = few buildings, total depth (registrations, RERA, verified facts, floor-by-floor knowledge). Nothing on the homepage *shows* this. "Vibrant resident communities" is a claim any broker makes.
4. **No narrative.** Sections run hero→banner→projects→listings→pillars→testimonial. Buyer psychology wants: promise → proof → the buildings → what's inside them → reassurance → act.
5. **No arrival moment.** Polite fade-ins. No choreography.

## 2. What we steal from Halston (mechanics, not skin)

| Halston does | We do |
|---|---|
| Giant uppercase statement hero, then full-bleed film | Giant uppercase statement, then full-bleed Ekta Tripolis night aerial with clip reveal |
| Zero boxes; hairline rules + mono chips (`• ACHIEVEMENTS`) | Kill `rounded-2xl border` everywhere; `border-t border-mist-deep` hairlines + our IBM Plex Mono chips |
| Stats as huge editorial numerals | Proof band: 15+ years · 4 flagship towers · 3 suburbs · live listing count (honest numbers only, from site.ts/DB) |
| Full-bleed image = the card (DISCIPLINES) | Full-bleed BUILDING chapters: photo owns the viewport, name in display type, mono chip w/ location |
| Numbered sections, one ease, one palette | Already have the ease + palette (Gallery White untouched); add numbered mono eyebrows site-wide |

**We keep:** teal #1f3d4d, warm #c2493d (max one per viewport), Montserrat + Plex Mono, shadowless, honest placeholders. This is a *grammar* change, not a rebrand.

## 3. The imagery ledger (what exists, where)

Drive root: `/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/`

| Building | Count | Hero-grade finds (vetted by eye) |
|---|---|---|
| Imperial Heights | 2,381 img / 1,414 vid | `7457d59...jpg` entrance (already on Wix CDN). Raw per-flat MOVs (IH D3902.mp4 etc.) → future frame-grabs + walkthrough clips |
| Kalpataru Radiance | 1,294 img / 1,043 vid | `RDH.00_*.Still00N.jpg` are pro video stills BUT have sales-text overlays baked in — unusable as-is. **TODO: ffmpeg frame-grabs from raw .MOV footage** for clean elevation shots. CDN elevation exists. |
| Ekta Tripolis | 452 img / 188 vid | ⭐ `banner1.jpg` (night towers, current site hero, on CDN) · ⭐ `gallery2.jpg` (golden-hour aerial, sunset — Halston-mood, NOT yet on CDN, upload it) |
| DLF Westpark | 24 img / 24 vid | brochure render on CDN (keep artist's-impression caption) |
| Bharat Auras Vistas | 163 img / 343 vid | show-flat interior on CDN; YT thumbnails unusable |

Free skyline layer (already shipped): `web/public/mumbai-skyline-night.jpg` (testimonial backdrop) + `mumbai-sea-link.jpg` (footer duotone band). Pixabay free license. Duotone = CSS (`grayscale` + `bg-teal/60 mix-blend-multiply`) — no image pipeline.

**Video ambition (Phase C):** Halston's hero is a film. We have thousands of clips. Loop candidate: 6–10s muted `<video>` of an elevation/aerial, poster = banner1, `preload="none"`, only after LCP. Do NOT block launch on this.

## 4. Phase A — homepage de-generification (IN PROGRESS as of this doc)

New section order for `web/src/app/(site)/page.tsx`:

1. **HERO** — mono eyebrow chip (`● GOREGAON · ANDHERI · MALAD — 15 YEARS`), giant uppercase statement (see copy options §6), one sentence, ONE CTA (`See what's available →` → /buy). No DLF chip here.
2. **FULL-BLEED IMAGE** — Ekta night aerial, `h-[70vh]` cover, rdh-clip reveal, mono caption chip bottom-left (`EKTA TRIPOLIS · GOREGAON WEST`).
3. **PROOF BAND** — `● 01 — TRACK RECORD` + 4 stats in hairline grid, huge numerals.
4. **BUILDING CHAPTERS** — `● 02 — THE BUILDINGS`; each project = full-width `h-[60vh]` image band, uppercase name overlaid center, hairline rule, mono chip location, links to project page. Dashed honest placeholder band if no image.
5. **INVENTORY** — `● 03 — AVAILABLE NOW`; featured listings, borderless: hairline-top rows, price-first (kept from Tier 1), image left.
6. **DLF CHAPTER** — full-bleed teal block, `● 04 — NEW LAUNCH`, big name, one line, one link. (Replaces the old duplicate banner.)
7. **METHOD** — `● 05 — HOW WE WORK`; pillars re-set as editorial numbered rows (mono 01/02/03 left, content right, hairline dividers, NO boxes).
8. **TESTIMONIAL** — keep (already has skyline backdrop).

Done-ness: `tsc` clean, eslint clean, vitest 310 green, visual check desktop 1280 + mobile ~670 (remember: automation tab freezes animations — inject `*{animation:none!important;transition:none!important}` + force inline opacity=1 before screenshots; scroll with `behavior:'instant'`).

## 4b. Map hero (SHIPPED 2026-07-13) + floor selector (NEXT BIG THING)

**Map hero is live** on the homepage: MapLibre GL + OpenFreeMap positron tiles (free, no key, no usage caps) — weighed against Google Maps embed (key/billing/unstylable), Mapbox (token/billing), custom WebGL (weeks). Component: `web/src/components/map-hero.tsx`; data: `mapBuildings` in `site.ts`. Hero text overlays a draggable, pitched (48°) basemap that happens to match Gallery White almost exactly. Four pins (teal dot + mono label chip, CSS in globals `rdh-pin*`); click → flyTo + verified-facts panel with View building/Listings links. Coords: IH + Kalpataru verified via OSM Nominatim; **Ekta + DLF pins are estimates carrying a PIN_VERIFY chip — operator must confirm**. Future 5th pin: "Kalpataru Vial" (operator to confirm name/location). Perf: map JS lazy-loads via IntersectionObserver, scrollZoom off (no scroll hijack), cooperativeGestures on mobile, LCP stays text. NOTE for QA in automation: maplibre needs rAF → hidden tabs never fire `load`; force `div.opacity=1` to inspect.

**Floor selector — how flostefoy.com/plans does it** (operator asked; many Québec sites use the same agency plugin `do-selecteur-plans`, seen in DOM as `do1011-*` classes). Mechanics, fully replicable, no 3D/WebGL:
1. Building elevation render + absolutely-positioned floor buttons (one per floor, plain divs).
2. Selecting a floor swaps in a per-floor plate image (`Etage-N.png`) with an **SVG overlay** — one polygon per unit as a hover/click hotspot.
3. Clicking a unit opens a panel (`panneau-unites`) fed by CMS data: availability, config, plan PDF.
**Our version:** for **DLF Westpark we already own the assets** — 55 floor-plan PNGs + tower structure T02–T05 + per-config floor ranges in `media_assets` (see `docs/reference/MEDIA-INTELLIGENCE-SYSTEM.md`). Build `/dlf-westpark-andheri-west/plans`: tower picker → floor stack → plate PNG + SVG unit polygons → config panel (carpet area, plan image, enquire CTA). For IH/Kalpataru/Ekta (no plate renders): honest **schematic floor stack** — SVG list of floors from unit_registry, availability dots, click floor → that floor's listings. Matches "Every floor known." exactly.

## 4c. BUILD SPEC — DLF Westpark floor selector (flostefoy-style, NOT yet implemented)

*Self-contained spec: a fresh session should be able to build this without re-deriving anything.*

**Goal:** `/dlf-westpark-andheri-west/plans` — pick a tower (T02–T05) → pick a floor → see the floor-plate plan with each unit as a hover/click hotspot → unit panel shows configuration facts + plan image + enquire CTA. No 3D, no WebGL, no new deps.

**Assets (already exist):**
- 55 PNGs extracted from `Presenter 1.pdf` (DLF brochure) — 20 tower floor plans, 25 configuration unit plans, 10 amenity/structure. Rows in Postgres `media_assets` with `asset_level` ('tower_floor'/'configuration'/'building'), `configuration_type` (e.g. `3BHK-01`, `4BHK-DUPLEX-01`, `STUDIO-01-REFUGE`), `brochure_page`, `alt_text`. Seeded by `scripts/seed_dlf_brochure_extraction.py`. See `docs/reference/MEDIA-INTELLIGENCE-SYSTEM.md`.
- Tower structure: T02: 3BHK-01/02, 4BHK-01, 5BHK-01, 4BHK-DUPLEX-01 · T03: 3BHK-01/02/03/04, 4BHK-03, 4BHK-DUPLEX-01/02 · T04: 3BHK-01/02/03, 4BHK-03, 4BHK-03-FL36, 4BHK-DUPLEX-01 · T05: 3BHK-01/02/03, STUDIO-01-REFUGE, STUDIO-01-FL36, 4BHK-DUPLEX-02/03. Floor ranges, carpet/balcony areas, refuge floors, duplex floors (39/40) all in DB.
- CONSTRAINT: cockpit DB is NOT available in prod (no DATABASE_URL on Vercel). So plans data must be **exported to a static JSON/TS fixture at build time** (script: query media_assets + config table → `web/src/lib/dlf-plans.ts`), or served via Wix CMS later. Do NOT wire pg into the public site.

**Build steps:**
1. Export script `scripts/export_dlf_plans.py`: reads media_assets (+ config/floor tables) → writes `web/src/lib/dlf-plans.ts` with `{towers: [{id:"T02", floors:[{n:7, kind:"refuge"|"typical"|"duplex", plateImage:"/dlf-plans/T02-typical.png", units:[{pos:"01", config:"3BHK-01", carpetSqft, balconySqft, planImage, polygon:[[x,y]…]}]}]}]}`. Copy PNGs (web-compressed ≤200KB, sips formatOptions 65) into `web/public/dlf-plans/`.
2. **Unit polygons**: hand-authored once per distinct plate layout (~5 per tower, NOT per floor — floors sharing a plate share polygons). Workflow: open plate PNG in any SVG editor (Figma/Inkscape), trace each unit as a polygon, export/read the point lists, paste into the fixture as 0–100 viewBox-normalized coords. Store in `dlf-plans.ts` next to the floor entries.
3. Component `dlf-plan-explorer.tsx` (client): three-pane editorial layout in Gallery White — tower picker (mono chips T02–T05) → vertical floor stack (list of floor numbers, refuge/duplex badged, hairline dividers) → main pane: `<div class="relative"><Image plate/><svg viewBox="0 0 100 100" class="absolute inset-0">` with `<polygon points… class="unit-hotspot" data-config…>`. Hover: fill teal at 18% opacity + stroke; click: side panel (reuse the map-hero panel pattern) with config name, carpet/balcony sqft, unit-plan image (25 config PNGs), floors this config appears on, PRICE_VERIFY token (never invent price), and WhatsApp/Request CTA (reuse sticky-cta targets).
4. Page `/dlf-westpark-andheri-west/plans/page.tsx` (server): metadata title "DLF Westpark Floor Plans — T02–T05 configurations", BreadcrumbList JSON-LD; renders explorer with fixture data. Link to it from the DLF landing page hero and section 07 gallery.
5. Mobile: tower chips horizontal scroll; floor stack becomes horizontal strip; panel becomes bottom sheet (same pattern as map-hero panel `inset-x-4 bottom-4`).
6. QA: keyboard focus on polygons (`tabIndex=0`, Enter opens panel, aria-label per unit); all plate/unit images have alt from media_assets alt_text; page weight budget ≤600KB first load; vitest snapshot of fixture shape; Playwright: pick T03 → floor → unit → panel shows config.
7. Honesty rails: any config lacking a verified fact renders the mono pending token; brochure imagery captioned "artist's impression" like the DLF landing hero.

**Same pattern later for IH/Kalpataru/Ekta:** no plate renders exist, so render an SVG *schematic* stack (floor rows from `unit_registry`, availability dots from listings/registrations), click floor → listings filtered to that floor. Positioning payoff: "Every floor known."

> **See also:** `docs/MEDIA-SOCIAL-FUNNEL-PLAN.md` (2026-07-13) — the content-engine charter on top of this design work: imagery/video review pass, social↔listing pipeline + backend, lead funnel/newsletter, AI enhancement/staging/LiDAR, and the Awwwards research agenda. Future session(s); sequenced there.

## 5. Phase B — roll the grammar out

- **Focus-four scope** (operator 2026-07-13): Ekta Tripolis, Imperial Heights, Kalpataru Radiance, DLF Westpark. Bharat Auravistas removed from homepage (data kept in site.ts; its project page still resolves).
- **Listing detail pages**: `listings/[slug]` exists but is thin — needs gallery, facts table, price history hooks, `Residence`/`Offer` JSON-LD, per-building internal links. SEO landing pages per building × intent ("2 BHK for rent in Ekta Tripolis") come after.
- **Projects index + project pages**: chapter treatment, sticky in-page section nav (Overview · Residences · Amenities · FAQ), breadcrumbs + BreadcrumbList JSON-LD.
- **Buy/Rent**: listing rows borderless; filters as mono chips; price-first kept.
- **Blog**: index = editorial list (date mono, title large, hairline dividers — no cards); post = 720px measure, drop-cap optional, hero full-bleed. Blog is CMS-backed via `cms.ts` (Wix BlogPosts), publish flow already verified.
- **About**: manifesto page — "We publish facts, not promises" promoted to brand level (copy exists on DLF page §02).
- **DLF landing**: already the most editorial page (numbered eyebrows exist!) — align its chips/rules with the new shared components.
- **Stats counters** animate once in view (framer, no new deps). **Gemini alt-text batch** for media_assets (key in `web/.env.local`, free tier, expect 429s → backoff).

## 6. Hero copy options (operator picks; workshop freely)

- A. `FEW BUILDINGS. / EVERY FLOOR KNOWN.` ← current implementation
- B. `WE DON'T COVER MUMBAI. / WE COVER SIX BUILDINGS.`
- C. `DEPTH, NOT LISTINGS.`
- D. keep `YOUR FUTURE HOME IS RIGHT HERE` in the new giant treatment (safest, least interesting)

Sub-line stays factual: 2–4 BHK / named towers / Goregaon–Andheri–Malad.

## 7. QA plan (run after each phase)

1. `cd web && npx tsc --noEmit && npx eslint src && npx vitest run` — all green.
2. Visual: 320 / 670 / 1024 / 1280 widths; hamburger menu; card uniformity (equal heights per row); no horizontal scroll.
3. SEO: `next build` → sitemap.xml + robots 200; JSON-LD intact; one `<h1>`/page; images have alt or `alt=""` decorative.
4. Weight: hero images ≤ 250KB source (next/image emits AVIF); no new fonts, no new deps.
5. Motion: `prefers-reduced-motion` honored (MotionConfig user + CSS fallbacks).
6. Playwright (Phase C): mobile nav opens/navigates; sticky CTA on DLF; lead form; project page renders facts table; testimonial/footer images load.

## 8. Standing constraints (do not violate)

README + design system: truth = local Postgres; never fake facts; placeholder tokens stay visible; realdealhousing.com production Wix site OFF-LIMITS; robots stays noindex until operator flips; max ONE warm accent per viewport; mono = data only.
