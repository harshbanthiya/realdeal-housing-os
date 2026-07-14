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
- [x] **Wix Headless OAuth Client ID** — DONE 2026-07-08. OAuth app "RDH Next.js headless site" created via API on the **Test** site (site ID e8817980-3301-420f-856c-a4cd5184633e); client ID in `web/.env.local`. NOTE: the operator's first manually-created client ID belonged to a different site (its Amenities schema didn't match) — always verify with a sample read.
- [x] Test-site collections verified: Projects, ProjectFacts, Residences, Amenities, ProjectFAQs, BlogPosts — all `read: ANYONE`, writes CMS_EDITOR+. Added `heroImage` (IMAGE) + `publishedAt` (DATETIME) to BlogPosts (revision 3).
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
- **F-5 PARTIAL** (2026-07-14): newsletter side closed — migration 063 `subscribers` + `email_suppression`, double-opt-in signup (footer + listing pages), `/newsletter/confirm` + `/newsletter/unsubscribe` routes; every sender must check `email_suppression`. Still open: Resend webhook signature verification + wiring drip-contact unsubscribes into the same suppression table. Bulk send remains human-gated. NOTE: `/api/subscribe` needs DATABASE_URL, so prod (Vercel) returns an honest 503 fallback until launch storage is decided.
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

- 2026-07-14: media/social/funnel pass — migration 063; newsletter double-opt-in flow
  (smoke-tested end-to-end locally); `<AmbientVideo>` + Ekta view loop on homepage;
  `/cockpit/content` listing-content panel; About manifesto section; apply_schema.sh
  extended to 063 (F-2 follow-up: 061/062 were also missing).

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

## Publishing workflow (verified end-to-end 2026-07-08)
Editor sets `status = "published"` (+ `publishedAt`) on a BlogPosts item in the Wix CMS → site picks it up within 5 min (ISR). Projects surface when `draft` is false. Tested live: published a post → rendered on /blog + /blog/[slug] with JSON-LD → reverted to draft. All seeded content remains draft/staging (placeholders unverified) — publishing is a human decision.

## Next actions
1. Marketing: verify facts in a BlogPosts item, upload hero image to Wix Media, set status=published.
2. Migrate the 4 catalogue projects (site.ts fixtures) into the Wix Projects collection when ready — cms.ts already merges CMS-over-fixture by slug.
3. Prod guard for cockpit when DATABASE_URL absent.
4. Backup cron (pg_dump + verify) — F-6.
5. Extend `check_db.sh` to 060 — F-7.
6. Vercel project + domain decision for deploy.

## Deployed 2026-07-08 (commit 7c6298b)
- **LIVE**: https://web-gray-seven-44.vercel.app (Vercel project `web`, prj_bpbK8is4jVRISv6QweWGmryoadNX, CLI-linked from `web/.vercel/`). Prod env: WIX_CLIENT_ID, NEXT_PUBLIC_SITE_URL, COCKPIT_AUTH_TOKEN (random; cockpit + /api/cockpit verified 401 in prod).
- **Imagery**: 5 heroes on Wix CDN (IH entrance, Kalpataru elevation, ET night banner, Bharat show flat, DLF brochure render w/ artist's-impression caption). Sources: `RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/` + `exports/media/dlf-westpark/`. Lineage in media_assets (wix_url, upload_status=wix_uploaded, alt_text, reviewed=true). Upload path: `POST /site-media/v1/files/generate-upload-url` via Wix MCP → curl PUT binary.
- **Motion**: DS Motion II ported (rdh-clip/rdh-zoom in globals.css, RevealImage component). Home hero, project grids, detail heroes, listing cards all render CDN imagery with dashed fallback.
- robots stays noindex; site is on a vercel.app URL pending domain decision.

## Production pass (2026-07-14)
- **WIX_CLIENT_ID fixed** locally + on Vercel prod (`bc909fd2-…`, verified with sample
  reads of Projects/Amenities/BlogPosts; operator's spare `b3fd8710-…` also works — same
  Test site — but is unused, can be deleted). CMS reads live in prod, no [cms] errors.
- **Deployed to production** (dpl_Ev538Gry…, aliased web-gray-seven-44.vercel.app):
  ambient loop streams from video.wixstatic.com (+VideoObject JSON-LD), poster on Wix CDN
  with SEO filename (ekta-tripolis-goregaon-west-view.jpg), security headers added
  (nosniff, X-Frame-Options DENY, Referrer-Policy, Permissions-Policy).
- **Grade check passed**: all public routes 200; /cockpit 307→login + /api/cockpit 401
  (fails closed, no DATABASE_URL); /api/subscribe honest 503; sitemap 200; robots still
  noindex (correct — flipping on a vercel.app URL would index the wrong host; flip only
  after the domain lands); JSON-LD ×4 on home; blog serves fixture guides (CMS posts are
  deliberately draft — publishing stays a human decision).
- Media policy: Wix CDN is canonical for CMS-served media (heroes, video). Files in
  `web/public/` (skyline/sea-link stock, 55 DLF plan PNGs) are served from Vercel's edge
  CDN already — migrating them to Wix adds churn, not speed. New media → Wix CDN first.

## Wix Headless capability survey (2026-07-14) — what else to integrate
| Solution | Verdict | Why / trigger |
|---|---|---|
| CMS (Wix Data) | ✅ in use | Projects/Facts/Residences/Amenities/FAQs/BlogPosts on Test site |
| Media Manager | ✅ in use | upload path proven twice; canonical CDN for site media |
| Blog (native) | Adapt later | our BlogPosts collection + ISR already covers SEO posts; native Blog adds categories/RSS when volume justifies |
| **Forms/Submissions → CRM Inbox** | **Adopt next** | replace `/contact` mailto with a real lead capture that lands in Wix CRM/Inbox (operator already lives in Wix dashboard); pairs with our consent rails |
| **Bookings** | **Adopt when ready** | "Book a site visit" per building/listing — scheduling + reminders without building any backend; needs operator to define visit slots |
| Members/Auth | Skip | no gated content; buyers won't create accounts |
| Stores/eCommerce/Pricing Plans | Skip | nothing to sell online; launch pricing is person-to-person by policy |
| Events | Skip for now | only if launch-weekend events become a channel |
| Wix-hosted pages (checkout/booking flows) | Adapt | if Bookings adopted, use Wix-hosted booking page first (zero build), embed later |

## Blockers
- Domain decision + Cloudflare DNS record (CNAME → cname.vercel-dns.com) for the public hostname; then update NEXT_PUBLIC_SITE_URL and flip robots on approval.
- Local commits not yet pushed to origin (github.com/harshbanthiya/realdeal-housing-os).
