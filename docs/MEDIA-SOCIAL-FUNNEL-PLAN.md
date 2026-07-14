# MEDIA, SOCIAL & FUNNEL PLAN
### the content engine on top of the good-looking website

*2026-07-13 · charter. **2026-07-14 UPDATE: executed** — Task A pilot shipped (ambient loop + `<AmbientVideo>`), Task B backend shipped (migration 063 `listing_content` + `/cockpit/content` + `scripts/manage_listing_content.py`), Task C plumbing shipped (`subscribers`/`email_suppression`, double-opt-in signup on footer + listing pages, confirm/unsubscribe routes — F-5 newsletter side closed). Task D/E resolved as decision memos (§E below). Remaining: bulk transcode more clips, first real social post through the cockpit loop, analytics install pending operator's PostHog answer (ROADMAP §17). Companion docs: `UX_DEGENERIFICATION_PLAN.md`, `reference/MEDIA-INTELLIGENCE-SYSTEM.md`.*

## 0. What we're sitting on (asset inventory — verified 2026-07-13)

| Where | What |
|---|---|
| `/Volumes/RDH 5TB/RDH DATA 2024/RDH/Export/` | **146GB of EDITED, export-ready video**: per-flat tour films (IH A-2105, C-804, Kalpataru C-311, Ekta Penthouse…), Insta-reel cuts (with/without logo), show-apartment films, `EXPORT FOR ADS/`, `REELS & SHORTS/`, thumbnails (`TN/`), V-cards |
| `RDH ALL Footage/ALL PROJECTS/` | 4,000+ raw photos, 3,000+ raw clips per building (see UX plan §3 ledger) |
| YouTube @RealDealHousing | Published channel, top videos 84K/10K views; building-matched tours already embedded on site (commit cefe0a0) |
| Instagram `realdealhousing_mumbai` · Facebook `realdealhousingpvtltd` | Active socials, now in footer + `sameAs` schema |
| Wix Media CDN | 5 hero images live; upload path proven (`POST /site-media/v1/files/generate-upload-url` via Wix MCP → curl PUT) |
| Postgres `media_assets` | DAM with `configuration_type`/`asset_level`/`alt_text`/lineage (migration 056); 60 DLF rows seeded |

## TASK A — Imagery design review pass (website)

One structured pass over every page of the base site asking: *where does a better image, a video snippet, or a 3–6s ambient loop beat what's there?* Output = shot-list + placement map, THEN execution.

- Candidates: hero ambient loop (muted 6s elevation clip, poster-first, post-LCP); listing cards with hover-scrub video thumbs; project pages with per-flat tour films (the Export/ .movs, transcoded to web AV1/H.264 ≤3MB snippets); About page with the RDH AV film.
- Pipeline: pick from Export/ → `ffmpeg` transcode presets (snippet: 720p 6s muted loop; feature: 1080p full tour) → Wix CDN upload → `media_assets` row with lineage → component (`<AmbientVideo>` facade, same pattern as `youtube-embed.tsx`).
- Rule: motion never blocks LCP; every video has a poster; reduced-motion gets the poster only.

## TASK B — Social content pipeline (listing ↔ social, both directions)

Goal: a listing's page shows its social media (reel, story frames, tour video); social posts deep-link back to the listing/building page. "Hammer SEO for those buildings" = every asset canonically lives on OUR page first, social is distribution.

- **Backend** (this is the real build): `listing_content` table linking media_assets → listings with role (reel/story/tour/photo-set), status (draft/scheduled/posted), platform post IDs + permalinks once live. Cockpit UI: attach content to listing, preview, mark scheduled.
- **Scheduling**: start human-in-loop (cockpit queue + operator posts natively — same Lane A philosophy as WhatsApp outreach); evaluate Meta Graph API / YouTube Data API automation only after the manual loop proves the cadence.
- **Site surface**: listing page gets a "Seen on Instagram/YouTube" strip (embed facades, not SDK bloat); building pages already have YT tours.
- **Loop closure**: UTM-tagged links in bios/captions → listing pages; site social links already live. Measure in GA4/Plausible (pick analytics in this session too — nothing installed yet).

## TASK C — Lead funnel + newsletter

- Opt-in: email newsletter signup (footer + blog posts + listing pages "get new listings in this building first"). Resend is already wired for transactional (web/emails/); needs: list storage (Postgres `subscribers` table — NOT a third-party CRM yet), double-opt-in flow, suppression list (F-5 in LAUNCH_CONTEXT is still open — unsubscribe/suppression must land BEFORE any bulk send).
- Funnel: social → building/listing page → WhatsApp/call/enquiry → cockpit contact record (contacts pipeline exists!) → nurture email per building interest. Define funnel events + dashboards.
- Compliance rails: consent records (channel_permissions schema exists from Phase 7.9), per-building interest tags.

## TASK D — AI image enhancement, staging & capture

Operator pain: building photos are old/pixelated. Wants: upscale/enhance; virtual staging (add furniture to empty flats) AND de-staging (remove furniture); later LiDAR capture via iPhone for 3D models.

- **Upscale/enhance**: Real-ESRGAN (open-source, runs local on M-series) as the free default; compare vs Gemini image editing (key already in web/.env.local) and paid APIs (Topaz, Magnific) on 5 test images per building. Batch via media_assets so lineage records `enhanced_from`.
- **Ethics/honesty rail (non-negotiable, fits brand)**: enhanced ≠ misrepresented. Sharpening/denoising fine silently; virtual staging MUST be labelled ("virtually staged") like US MLS practice; never alter structure, view, or condition.
- **Virtual staging**: research pass — open models (SDXL inpainting) vs staging SaaS (VirtualStagingAI etc.); needs the empty-flat photo set (configuration stock in the DAM model is literally designed for this — see MEDIA-INTELLIGENCE §"Configuration stock").
- **LiDAR/3D (later)**: iPhone Pro LiDAR apps (Polycam, Scaniverse, RoomPlan API) → floor-accurate 3D scans per flat → embeddable 3D viewer (`<model-viewer>`/Three.js) or auto floor plans. Prereq: one pilot scan of a currently-listed flat.

## E. Decision memos (resolved 2026-07-14)

1. **Video-led listing pages — ADOPT facades, SKIP streaming.** Poster-first `<AmbientVideo>` (IntersectionObserver mount, muted loop, reduced-motion → poster) is the pattern luxury sites use minus their weight. Short loops stay ≤3MB H.264 MP4 served from `web/public/` (pilot: 0.7MB). HLS/AV1 only if we ever ship >30s films outside YouTube — YouTube embeds (already facaded) cover full tours.
2. **Social-proof strips — ADAPT, no embed SDKs.** Instagram/Facebook official embeds pull ~200KB+ JS and tracking consent baggage. Instead: `listing_content` stores the permalink + our own DAM thumbnail → render a styled outbound "Seen on Instagram/YouTube" card. Revisit oEmbed only if operator wants live like-counts.
3. **Virtual staging disclosure — ADOPT US MLS practice.** "Virtually staged" label in the visible caption AND alt text, never structure/view/condition edits. `media_assets.virtual_stage_status` already models it. Sharpen/denoise silently; anything additive gets the label.
4. **3D/scan viewers — DEFER behind a pilot.** One iPhone-Pro LiDAR scan (Polycam or Scaniverse, free tiers) of a currently-listed flat first; embed via `<model-viewer>` if the scan is good. Matterport SKIP (subscription + per-space cost, closed viewer).
5. **Newsletter taste — ADOPT inline-only.** Footer + listing-sidebar forms (shipped), double-opt-in, honest consent line. NO arrival popups. A scroll-depth prompt is allowed only after analytics prove deep engagement pages.
6. **Analytics — PostHog cloud, pending operator sign-off** (open question already in ROADMAP §17; free tier, EU cloud if offered). Plausible is the fallback if the operator rejects data-leaves-machine.
7. **AI enhancement (Task D) — Real-ESRGAN local ADOPT** as the free default upscaler; run the 5-images-per-building bake-off vs Gemini image editing before batching; Topaz/Magnific SKIP unless both fail. Lineage via `media_assets.metadata.enhanced_from`. Staging models: decide only after the bake-off, with the disclosure rail from memo 3.

## F. Sequencing & prerequisites (status 2026-07-14)

1. ✅ **A pilot** — Ekta view ambient loop live on homepage (`web/public/ekta-view-loop.mp4`, DAM row w/ lineage, `<AmbientVideo>` reusable). Next: per-flat tour snippets on listing pages via the same pipeline.
2. ✅ **C plumbing** — `subscribers` + `email_suppression` + double-opt-in + unsubscribe shipped and smoke-tested. Every future sender MUST check `email_suppression`. No bulk sends yet (still human-gated).
3. ✅ **B backend** — `listing_content` + cockpit attach/lifecycle UI + guarded script. Posting stays native/human; permalinks recorded after the fact.
4. **D enhancement** — bake-off pending (memo 7); staging/LiDAR separate pilots.
5. **Analytics** — blocked on operator's PostHog answer.

Standing constraints apply throughout: truth = Postgres, honest labels, human-gated outbound, realdealhousing.com Wix prod OFF-LIMITS, robots flip only on operator approval.
