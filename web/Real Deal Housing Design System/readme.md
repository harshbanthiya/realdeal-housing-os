# Real Deal Housing — Design System ("Gallery White")

A mother-and-son run Mumbai real-estate business (Padmini Jain, Director) focused on premium
limited buildings in the Western Suburbs — Goregaon, Andheri, Malad. 15 years in the market.
Signature buildings: **Imperial Heights, Kalpataru Radiance, Ekta Tripolis, Bharat Auravistas**,
plus the **DLF Westpark (Andheri West)** new-launch funnel. Audience: new and old millionaires
evaluating ₹3–5+ crore apartments; the brand's promise is *verification-first calm* — every
fact shown with its verification status, nothing invented.

## Sources

- **Codebase** (mounted, read-only): `Real Deal Housing OS/` — a local-first operations stack.
  The design ground truth lives in `web/` (Next.js 15 + Tailwind 4):
  - `web/src/app/globals.css` — Gallery White theme tokens (copied verbatim into `tokens/colors.css`)
  - `web/src/app/(site)/` — public marketing site (home, buy/rent/sell, projects, blog, FAQ, contact)
  - `web/src/app/(site)/dlf-westpark-andheri-west/` — flagship 10-section launch landing page
  - `web/src/app/cockpit/` + `web/src/components/cockpit/` — internal operations cockpit
  - `web/src/components/ui/primitives.tsx` — Pill, Dot, Card, Mono, PanelTitle
  - `docs/PHASE_7_18_GALLERY_WHITE_APPROVED_DESIGN_SPEC.md` — the approved design direction
- **Logo**: `uploads/rdh_logo(1).png` → `assets/rdh-logo.png` (geometric facet house + wordmark)

## Products represented

1. **Marketing website** (`ui_kits/website/`) — Gallery White editorial site, desktop + mobile
2. **DLF Westpark launch page** (part of website kit) — scroll-storytelling landing, verified-facts ledger
3. **Operations cockpit** (`ui_kits/cockpit/`) — internal white/mist tool: sidebar, pills, ledgers

## CONTENT FUNDAMENTALS

- **Tone**: calm, editorial, honest. Premium restraint — "Apple-inspired, not copied". No
  hype, no exclamation marks, no emoji anywhere.
- **Verification-first voice**: unverified facts are never invented; they render as mono
  "pending" chips (`PRICE_VERIFY`, `RERA_VERIFY`). Footer: *"New project facts shown as
  pending placeholders until verified."* Headlines lean on this: *"Built by DLF — verified
  before it's published."*, *"Every claim, with its verification status."*
- **Casing**: sentence case for headings ("Questions, answered honestly.", "The everyday,
  considered."). Title Case only for proper nouns and pillar titles from legacy copy.
  Uppercase reserved for tiny mono eyebrow labels with wide tracking.
- **Person**: "we/our" for the company, "you" for the client. Personal and named — clients
  WhatsApp "Padmini" directly, not a generic sales line.
- **Punctuation motifs**: mid-dot separators (`Goregaon West · 3 BHK · 1033 sqft`), em-dash
  asides, arrow affordances (`View listings →`), `+` disclosure toggles.
- **Numbers**: Indian price format (₹4,59,00,000 or ₹1,10,000 / mo, or "On request");
  configurations as "2, 3 & 4 BHK"; sqft always numeric.
- **Sample voice**: "Your Future Home Is Right Here" (legacy tagline) · "Request the full
  brief. — Price list, floor plans and brochure… No commitment, no lock-in."

## VISUAL FOUNDATIONS

- **Color**: white-dominant (~85% of surfaces). Deep teal `#1f3d4d` anchors headlines,
  primary buttons, and full-bleed dark "chapter" sections. Body text is `#1a1a1a` ink at
  opacity steps (65/55/50/45/40). Soft surfaces are mist `#eef1ef` (often at /30–/50);
  borders are mist-deep `#e3e8e5`. Warm `#c2493d` is a **budgeted accent — max one warm
  element per viewport** (eyebrow tick dot, "New" badge, WhatsApp CTA, blocked pill).
  `#3e82b0` (info) and `#b6862c` (review) only as cockpit status tones. Logo facet colors
  (crimson/pink/magenta/orange/blue) live only in the logo and email art — never UI chrome.
- **Type**: Montserrat everywhere (the codebase maps it into `--font-manrope`; spec said
  Manrope, code ships Montserrat — Montserrat wins). Hero: `clamp(2.6rem,6.5vw,5.5rem)`
  weight 800, line-height 1.02, tight tracking, teal. H2: 30–36px bold. Body 16–18px at
  ink/65, relaxed leading. IBM Plex Mono strictly for: data/pending tokens, eyebrow
  numerals, pills, micro-labels (10–12px, uppercase, tracking 0.15–0.2em).
- **Spacing**: 1152px container (`max-w-6xl`), 24px side padding, 80–96px section rhythm.
  Cards pad 20–28px. Generous whitespace is the luxury signal.
- **Backgrounds**: flat white; alternating `mist/40` bands; full-bleed teal chapters
  (amenities, testimonial, footer). No gradients, no textures, no patterns. Imagery frames
  until real photography exists: dashed mist-deep border + `mist/50` fill + mono label
  (honest placeholders, never stock).
- **Motion**: one house ease — `cubic-bezier(0.22,1,0.36,1)`, 0.75s fade + 26px rise on
  scroll, once per element, staggered 30–70ms in grids. Sticky mobile CTA slides away
  (300ms) when the enquiry form is visible. No bounces, no loops, no parallax.
- **Hover**: solid buttons → opacity 0.9; outline buttons → mist fill; text links →
  underline (offset 4) or ink→teal color shift; project cards → `mist/40` wash; footer
  links → white. Press states: none defined beyond hover (keep it quiet).
- **Borders/shadows**: a **shadowless system**. Cards = 1px `mist-deep` border + radius.
  Only shadow in the codebase: `0 0 0 1px` ring on the active cockpit sidebar item.
- **Radii**: pills/buttons fully rounded; site cards 16px (`rounded-2xl`); cockpit cards
  and gallery tiles 12px; image wells 8px; pending chips 4px.
- **Transparency/blur**: sticky header only — `bg-white/85 backdrop-blur-md` with
  `mist-deep/60` hairline. Dark sections use white at opacity steps (90/75/65/55/45) and
  `white/15` borders/dividers.
- **Imagery**: cinematic, cool-graded architectural photography (see `assets/imagery/`);
  fixed aspect ratios declared everywhere (21/9 hero, 16/9 project, 4/3 listing/gallery,
  square map) to keep CLS at zero.
- **Layout rules**: sticky top header (64px); mobile two-segment bottom CTA bar
  (teal "Request details" | warm "WhatsApp"); numbered 01–10 section eyebrows with a
  32px hairline; asymmetric numeral-plus-statement layouts on dark chapters; FAQ as
  native `<details>` disclosures; SEO text always real DOM text (never canvas).

## ICONOGRAPHY

- **No icon system.** The codebase uses almost no icons by design. The full inventory:
  one inline WhatsApp SVG (filled, currentColor, 18px) on warm CTAs; unicode glyphs in
  the cockpit (`↗`, `⏻`, `⌘K`, `·`, `—`, `+` disclosure); 8px dots (`Dot`) as status
  indicators; the RDH monogram (white "RDH" on teal, rounded square or circle) as the
  avatar mark. No icon font, no emoji, ever.
- When an icon is genuinely unavoidable, match this vocabulary: filled currentColor SVG,
  16–18px, or a unicode glyph — never an icon-font library by default.
- Logos: `assets/rdh-logo.png` (full stacked logo), `assets/rdh-logo-full.png` (email
  horizontal), `assets/rdh-icon.png` (facet house only).

## Fonts

No font binaries exist in the codebase (loaded via `next/font/google`). This system loads
**Montserrat (400–800)** and **IBM Plex Mono (400–600)** from Google Fonts in
`tokens/fonts.css`. If offline use matters, supply the .woff2 files and we'll switch to
local `@font-face`.

## Intentional additions

- `Button` — formalizes the recurring pill-CTA link pattern (solid teal / outline / warm)
  that is repeated inline throughout the site source.
- `PlaceholderFrame` — formalizes the repeated dashed "honest placeholder" image well.
- `Reveal` — CSS/IntersectionObserver port of the framer-motion `<Reveal/>` (same ease,
  duration, rise, once-only behavior).
- `components/motion/` — **Motion II extension layer** (user-requested, inspired by
  luxury-places.ch and the Halston architecture template; colors/type stay Gallery White):
  `RevealLines` (masked line-by-line headline reveal), `RevealImage` (clip + settle-scale),
  `Parallax`, `CountUp` (verified numbers only), `Ticker` (marquee, max one per page).
  New tokens in `tokens/motion.css` (`--ease-expo`, `--dur-lines`, `--dur-clip`,
  `--dur-kenburns`). Demoed in `ui_kits/website-motion/`.

## Index

- `styles.css` → `tokens/` (fonts, colors, typography, spacing, motion)
- `assets/` — logos + `imagery/` (4 real Westpark visuals)
- `guidelines/` — foundation specimen cards (Design System tab)
- `components/core/` — Pill, Dot, Card, Mono, PanelTitle (from `ui/primitives.tsx`)
- `components/marketing/` — Button, Eyebrow, PendingChip, StatusBadge, PlaceholderFrame, Reveal
- `components/motion/` — RevealLines, RevealImage, Parallax, CountUp, Ticker (Motion II)
- `components/cards/` — ListingCard, ProjectCard
- `components/chrome/` — SiteHeader, SiteFooter, StickyCta
- `ui_kits/website/` — marketing site: home, listings, Westpark landing (+ mobile view)
- `ui_kits/website-motion/` — Motion direction: ken-burns hero slider, masked reveals,
  hover project rows, parallax feature, ticker, count-up stats
- `ui_kits/cockpit/` — operations cockpit: sidebar, portfolio, contacts
- `SKILL.md` — agent skill entry point
- `AUDIT.md` — senior UI/UX audit report (mobile experience verified; fixes logged)
