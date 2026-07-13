# MEDIA, SOCIAL & FUNNEL PLAN
### the content engine on top of the good-looking website

*2026-07-13 · charter for one or more FUTURE sessions — nothing here is started. Companion docs: `UX_DEGENERIFICATION_PLAN.md` (design system + what's built), `reference/MEDIA-INTELLIGENCE-SYSTEM.md` (DAM schema in Postgres). Operator wants a dedicated session to figure all this out, including researching how Awwwards-grade sites solve each piece.*

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

## E. Research agenda for the session (the Awwwards question)

How do the best real-estate/architecture sites solve each piece — study before building:
1. Video-led listing pages without weight (facades, HLS, poster strategies) — e.g. luxury brokerage sites (The Agency, Sotheby's), Halston-style studios.
2. Social-proof strips on product pages (embed vs screenshot vs API).
3. Virtual staging disclosure patterns (US MLS listings do this at scale).
4. 3D/scan viewers in listings (Matterport competitors, open alternatives).
5. Newsletter/funnels done tastefully (no popups-on-arrival; exit-intent or scroll-depth, per `popups` skill guidance).
Deliverable of research: a decision memo per topic (adopt/adapt/skip + chosen tool) BEFORE code.

## F. Sequencing & prerequisites

1. **A first** (imagery review) — pure upgrade of what exists, no new backend.
2. **C's suppression/consent plumbing** before ANY outbound (blocks B's distribution and newsletter sends).
3. **B backend** (listing_content) — after A proves the transcode/upload pipeline.
4. **D enhancement** feeds A (better source images); staging/LiDAR are separate pilots.
5. Analytics choice early — everything above wants measurement.

Standing constraints apply throughout: truth = Postgres, honest labels, human-gated outbound, realdealhousing.com Wix prod OFF-LIMITS, robots flip only on operator approval.
