# DLF Email Drip — CONTENT LOOP
Iterate design + copy here until Padmini approves. One design round = one commit.

---

## CURRENT DESIGN STATUS

| Variant | File | Design Version | Status |
|---------|------|----------------|--------|
| A — "The Private Invite" | `web/emails/drip-1-variant-a.tsx` | v2 (dark prestige, near-black hero, amber) | ⏳ awaiting review |
| B — "The Launch Bulletin" | `web/emails/drip-1-variant-b.tsx` | v2 (editorial bold, tabloid headline, two-col) | ⏳ awaiting review |

**How to preview:**
```bash
cd /Volumes/RDH\ 5TB/Real\ Deal\ Housing\ OS/web
npx tsx emails/export-previews.ts
open /tmp/rdh-email-previews/variant-a.html
open /tmp/rdh-email-previews/variant-b.html
```
Or live preview: `npx email preview` → http://localhost:3000

---

## DESIGN ITERATION LOG

| Version | Direction | Status |
|---------|-----------|--------|
| v1 | Variant A: white letter, teal header bar, facts strip · Variant B: dark hero, stat rows, structured sections | ❌ rejected — unhappy with design |
| v2 | A: near-black `#0c1a23` hero overlay + full-bleed render image, amber gold accents, minimal copy · B: 58px tabloid bold headline "SOLD OUT in 7 days", two-col editorial, amber standout box | ⏳ review pending |

**To request another redesign:** Describe what feels wrong (too dark? too editorial? not luxury enough? needs more images?) and I'll do a v3.

---

## VERIFIED PROJECT FACTS

**Official name:** DLF The Westpark — Phase I (now Phase 2 launching)
**Developer:** DLF + Trident Realty JV (Peegen Builders & Developers Pvt. Ltd.)
**MahaRERA:** PR1181012500079 · valid until 30/06/2032
**Website:** thewestpark.dlf.in · Sales: +91 88822 88333

**Scale:**
- 18-acre landmark development
- 8 towers total · 40 storeys each
- Phase 1: Towers 1–4 (or 2–5) — SOLD OUT in ONE WEEK of launch
- Phase 2: Towers 6 & 7 — NOW OPEN FOR EOI

**Units:** Ultra Luxury 4BHK residences
- Refuge floor plans explicitly show: Master + Bed 2 + Bed 3 + Bed 4 = 4BHK
- RERA carpet area range: ~1,255–1,368 sqft (per brochure floor plans)

**Amenities — 3 levels, 60,000+ sq ft:**
- Fine Dining Restaurant + Café (both on-site)
- 25m pool · Jacuzzi Steps · Kids Pool
- Sky Lounge · Business Center · Banquet Hall · Amphitheater
- Spa + Treatment Rooms · Yoga · Pilates · Salon
- Gym · TRX Studio · Multipurpose Studio
- Cricket Pitch · Pickleball · Badminton · Squash · Half Basketball
- Bowling · Table Tennis · Arcade Games · VR Games
- Jogging path · Bridge · Cabana · Day Bed
- Proposed Metro Station adjacent to site
- Seniors Lounge · Medical Room (accessible amenities)

**Investor highlights (from Phase 2 official copy):**
- No lock-in period
- Lifetime maintenance by DLF
- Excellent capital appreciation potential
- EOI open now — secures queue position before public price list

**Connectivity:**
- Airport: ~10 min
- Western Express Highway: direct
- Proposed Metro Station: adjacent
- Metro Line 1 (existing): Andheri West station
- Metro Lines 2B, 7A (upcoming): Dahisar–Andheri corridor
- BKC: metro + road

---

## MEDIA ASSET INVENTORY

Source: `/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/DLF Westpark/`

### Brochure renders (artist's impression — must label)

| What | Best for | Used in |
|------|----------|---------|
| pg1 — lush garden courtyard, jogging path, pool glimpse | Hero — lifestyle, green space | Variant A hero |
| pg2 — full exterior 4 towers, golden dusk | Scale shot | Variant B hero |
| pg3 — curved pool + Japanese garden | Pool lifestyle | Variant B second image |
| pg50 — Café interior, bamboo lights, airy | Amenity detail | Email 2 |
| pg55 — Spa treatment room | Wellness | Email 3 / social |

### Show flat photos (REAL interiors — not renders, taken on site visit)

| File | What | Use |
|------|------|-----|
| IMG_1166 2.HEIC | Living room · marble · chandelier · Mumbai dusk | Variant A second image |
| IMG_1167 2.HEIC | Living + dining full view | Email 2 |
| IMG_1168 2.HEIC | Master bedroom · balcony · Mumbai skyline | Email 3 |
| IMG_1169 2.HEIC | Bathroom · marble · glass shower | Specs detail |
| IMG_1171 2.HEIC | Study nook · shelving · teal chair | WFH/NRI angle |
| IMG_1172 2.HEIC | Kitchen corridor · Siemens fridge | Kitchen quality |
| IMG_1173 2.HEIC | Full Siemens kitchen | Specs |

### Kling AI videos (animated, label KlingAI)

| File | What | Use |
|------|------|-----|
| kling_DLFexterior.mp4 | Night exterior animation | Landing page hero, Reels |
| kling_DLFLandscapePool.mp4 | Pool + gardens flythrough | Social Reels, landing page |

### Upload to Wix before sending
Convert HEIC → JPG first:
```bash
sips -s format jpeg -Z 1200 "/Volumes/RDH 5TB/.../IMG_1166 2.HEIC" --out /tmp/dlf-living.jpg
```
Then upload via Wix Media Manager → paste CDN URL into email `<Img src="..." />`.

**Current placeholder URLs in templates (swap once uploaded):**
- `dlf-westpark-garden.jpg` → brochure pg1 render
- `dlf-westpark-living.jpg` → IMG_1166 show flat
- `dlf-westpark-exterior.jpg` → brochure pg2 render
- `dlf-westpark-pool.jpg` → brochure pg3 render

---

## APPROVAL CHECKLIST (before any email sends)

- [ ] Design approved by Padmini
- [ ] Hero images uploaded to Wix CDN, URLs patched in
- [ ] No placeholder CDN URLs (`static.wixstatic.com/media/dlf-westpark-*`) still pointing to non-existent files
- [ ] Subject line confirmed (< 50 chars)
- [ ] CTA links tested → `/dlf-westpark-andheri-west`
- [ ] WhatsApp link correct: `wa.me/918291293889`
- [ ] Unsubscribe link live
- [ ] MahaRERA number in footer: PR1181012500079
- [ ] "Artist's impression" label on all renders
- [ ] Financial disclaimer on Variant B
- [ ] Test send to `hbanthiya@gmail.com` lands in inbox (not spam)
- [ ] LOOP-infra.md Phase 5 test passes

---

## SUBJECT LINE OPTIONS (Phase 2 angle)

| Option | Chars | Variant |
|--------|-------|---------|
| Phase 1 sold out in 7 days. Phase 2 now open. | 46 ✅ | B |
| DLF's first Mumbai project — Phase 2 now open | 47 ✅ | A |
| DLF Westpark: Phase 1 sold out. Phase 2 is yours. | 50 ✅ | A |
| The Westpark Phase 2 — EOI open now | 37 ✅ | B |
| DLF Phase 2 opens today. Phase 1 was gone in 7 days. | 53 ❌ | — |

---

## EMAIL SEQUENCE — AFTER EMAIL 1 APPROVED

**Email 2 — Consideration (Day 5): "Inside the numbers"**
- RERA carpet sizes, 3-level amenity detail, connectivity data
- Show flat photos: living (IMG_1166) + dining (IMG_1167)
- CTA: "Request floor plans" → WhatsApp

**Email 3 — Conversion (Day 12): "Site visit arranged — join us"**
- Show flat photos: master bedroom (IMG_1168)
- Real urgency: limited units in Towers 6 & 7
- CTA: "Book a slot" → WhatsApp

**Email 4 — Referral (Day 20): "If not you, maybe someone you know"**
- Short, 4 sentences
- CTA: share link / forward

---

## LOOP EXIT

- [ ] Email 1 design approved (A, B, or both)
- [ ] All 4 emails written and approved
- [ ] Images uploaded, URLs live in templates
- [ ] LOOP-infra.md all gates pass
- [ ] Wave 1 (50 contacts) delivered clean
