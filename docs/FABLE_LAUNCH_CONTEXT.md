# FABLE LAUNCH CONTEXT

Working memory for the launch workstream. Append dated entries; don't rewrite history.

## Objective
Take the Next.js site in `web/` live: Wix headless CMS as content backend, Wix CDN for media,
SEO/blog-ready, Gallery White design system, safe cockpit separation.

## Architecture map (verified 2026-07-08)
- **Frontend**: Next.js 16 App Router in `web/`. Two surfaces:
  - `(site)` — public marketing site (home, projects/[slug], buy, rent, sell, blog, about, faq, contact, dlf-westpark landing). Content is static TS today (`src/lib/site.ts`, `src/lib/content.ts`).
  - `/cockpit` — internal ops UI backed by local Postgres (read via `src/lib/db.ts`, pg pool). Password-gated by `src/middleware.ts` (cookie == COCKPIT_AUTH_TOKEN).
- **Design system**: `web/Real Deal Housing Design System/` (tokens, guidelines, ui kits). "Gallery White": white-dominant, teal #1f3d4d anchor, max ONE warm #c2493d accent per viewport, Montserrat + IBM Plex Mono (mono for data/pending tokens only), shadowless 1px-border cards, single ease cubic-bezier(0.22,1,0.36,1), honest dashed placeholders, never invent unverified facts.
- **Motion**: framer-motion; `src/components/reveal.tsx` scroll reveal (SSR-safe).
- **DB**: local Postgres in Docker (APFS sparsebundle). Schemas `schemas/001–060`; applied via `scripts/apply_schema.sh`.
- **Automation**: Python scripts in `scripts/` (IGR parsing, PAN enrichment, RERA), n8n + NocoDB + Adminer in docker-compose (ops tools, not runtime deps of the site).
- **Email**: react-email templates in `web/emails/`, Resend send scripts. NOT launch-blocking; bulk send stays human-gated.
- **Wix**: `@wix/sdk` + `@wix/data` installed but unused by the site. Wix MCP connected; Test site has 7 CMS collections seeded (Projects, ProjectFacts, Residences, Amenities, ProjectFAQs, +2). **realdealhousing.com production Wix site is OFF-LIMITS.**

## Assumptions
- Deployment target: Vercel (Next.js, MCP available). Public site only; cockpit/DB stay local — cockpit routes must not work in prod (no DATABASE_URL there → they fail closed; verify).
- `robots: noindex` stays until domain + verified content are live.
- Placeholder tokens (RERA_VERIFY, PRICE_VERIFY, …) must render visibly, never be faked.

## Credentials / access needed (BLOCKERS for their steps)
- [ ] **Wix Headless OAuth Client ID** (Wix dashboard → Settings → Headless) → `WIX_CLIENT_ID`. Needed for live `@wix/data` reads. Site works on fixtures without it.
- [ ] Wix site ID of the Test site + collection IDs (readable via Wix MCP once pointed at it).
- [ ] Vercel project + env access, and domain/DNS decision (which domain the new site launches on — NOT realdealhousing.com's Wix site).
- [ ] Approval to flip `robots` to index.

## Architecture decisions
- **AD-1** (2026-07-08): CMS access goes through one typed adapter `web/src/lib/cms.ts`. Fixture-backed (current site.ts/content.ts data) when `WIX_CLIENT_ID` unset; `@wix/data` server-side reads when set. No Wix secret ever client-side; all reads in Server Components/ISR.
- **AD-2**: Images come from Wix Media Manager URLs (already CDN, supports `/v1/fit/w_,h_` transforms) via `next/image` with `remotePatterns` for `static.wixstatic.com`.
- **AD-3**: Cockpit and public site share the repo but not the deployment: cockpit is excluded from prod by env absence + middleware; long-term consider separate app if it grows.

## Audit findings (CTO loop)
- **F-1 FIXED** (2026-07-08): middleware matcher covered `/cockpit/:path*` only; `/api/cockpit/media/[id]` served DB-looked-up local files unauthenticated. Matcher extended to `/api/cockpit/:path*`.
- **F-2 FIXED** (2026-07-08): `scripts/apply_schema.sh` stopped at 052; schemas 053–060 exist. List extended.
- **F-3**: No sitemap/robots/canonical/OG/JSON-LD. FIXED this pass (sitemap.ts, robots.ts, metadataBase, org JSON-LD). robots stays noindex until launch.
- **F-4**: Reveal motion didn't respect prefers-reduced-motion. FIXED via `MotionConfig reducedMotion="user"` in (site) layout.
- **F-5 OPEN**: email outbound safety (unsubscribe/suppression/webhook verification) incomplete — bulk send remains human-gated; not launch-blocking for the website.
- **F-6 OPEN**: backups — last logical backup ~2026-06-08; PII/PAN lives locally. Needs a scheduled pg_dump + verification job.
- **F-7 OPEN**: `check_db.sh` validates an older contract; extend after 053–060 apply cleanly.

## Wix CMS collection mapping (plan)
| Collection | Site use | Route |
|---|---|---|
| Projects | project pages + featured grid | `/projects/[slug]` |
| ProjectFacts | verified-facts table (status per fact) | project page |
| Residences | configurations/pricing | project page |
| Amenities | amenity list | project page |
| ProjectFAQs | FAQ + FAQPage JSON-LD | project page, /faq |
| BlogPosts (to create) | SEO blog: title, slug, excerpt, body (rich), heroImage, tags, publishedAt, seoTitle/seoDescription | `/blog`, `/blog/[slug]` |
| Localities (to create) | locality intelligence pages | `/localities/[slug]` |
| Testimonials (to create) | social proof | home |
Publishing workflow: editor edits/publishes in Wix CMS → site revalidates via ISR (`revalidate = 300`) or on-demand revalidation webhook later.

## Changes made
- 2026-07-08: created this doc; middleware matcher fix; apply_schema.sh 053–060; `src/lib/cms.ts` adapter + env example entries; sitemap/robots/JSON-LD/metadataBase; MotionConfig reduced motion. Tests/lint/typecheck run — see below.

## Tests run
- 2026-07-08: `tsc --noEmit` clean · ESLint 0 errors (design-system reference dir excluded; 11 warnings remain) · vitest 310/310 pass · `next build` succeeds (sitemap.xml, robots.txt, SSG project pages w/ 5m ISR) · live prod-server check: `/api/cockpit/*` → 401 unauthenticated, `/cockpit` → 307 login, sitemap 200, robots disallow-all.

## Deployment checklist (Vercel)
1. Build: `npm run build` in `web/` (root dir = `web`). Node ≥ 20.
2. Env (prod): `NEXT_PUBLIC_SITE_URL`, `WIX_CLIENT_ID` (when available). Do NOT set `DATABASE_URL`/`COCKPIT_*` in prod.
3. Set `COCKPIT_AUTH_TOKEN` unset in prod means gate OPEN — cockpit pages will 500 without DB, but add a prod guard before first deploy (block `/cockpit` entirely when no DATABASE_URL).
4. Preview deploys per branch; production = main after review.
5. Rollback: Vercel instant rollback to previous deployment.
6. Health: `/` 200 + sitemap.xml 200.
7. Flip robots to index only with operator approval.

## Next actions
1. Operator: provide `WIX_CLIENT_ID` + Test-site collection IDs.
2. Wire `cms.ts` Wix path to real collections; render `/blog` from BlogPosts.
3. Prod guard for cockpit when DATABASE_URL absent.
4. Backup cron (pg_dump + verify) — F-6.
5. Extend `check_db.sh` to 060 — F-7.

## Blockers
- Wix OAuth Client ID + collection IDs (live CMS reads).
- Vercel/domain/DNS access + approval to deploy.
