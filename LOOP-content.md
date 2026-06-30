# DLF Email Drip — CONTENT LOOP
Iterate here until all emails are approved. Exit when every email is marked ✅ APPROVED below.

---

## VERIFIED PROJECT FACTS (source: official sales presenter PDF, July 2025)

**Official name:** DLF The Westpark — Phase I
**Developer:** DLF + Trident Realty (joint venture — Peegen Builders and Developers Pvt. Ltd.)
**MahaRERA:** PR1181012500079 · valid until 30/06/2032
**Website:** thewestpark.dlf.in
**Sales:** +91 88822 88333
**Finance partners:** Kotak Mahindra Investments Ltd + TATA Capital Housing Finance Ltd

**Location:** Andheri West — Jogeshwari–Vikhroli Link Road, adjacent to Proposed Metro Station
**Connectivity:**
- Airport: ~10 min
- Western Express Hwy: direct access
- Metro Line 1 (existing): Versova–Andheri–Ghatkopar (Andheri West station)
- Metro Line 2A (existing): Dahisar–DN Nagar
- Upcoming Metro 7A + 2B: Dahisar–Andheri corridor
- BKC: via metro + road

**Phase 1 towers:** Tower 2, 3, 4, 5 (future development areas also on master plan)

**Unit configuration — ALL 3BHK:**

| Tower | Floors | RERA Carpet (sqft) | Balcony (sqft) | Total (sqft) |
|-------|--------|-------------------|----------------|--------------|
| Tower 2 (typical) | 3–6, 8–12, 14, 16–21, 23–28, 30–35 | 1255.29 | 103.99 | 1359.28 |
| Tower 2 (refuge floors) | 7, 15, 22, 29 | similar | similar | similar |
| Tower 2 (duplex 39–40) | 39th–40th | Larger + private terrace | — | — |
| Tower 3 | 3–12, 14–38 | 1255.29 | 103.99 | 1359.28 |
| Tower 5 | 3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–38 | 1368.37 | 99.45 | 1467.82 |

**Each unit has:** Master bedroom (12×15–16ft), 2 bedrooms (11×12 & 11–12×13ft), living (12×12ft), dining, kitchen with Siemens appliances, maid's room, dry balcony, ODU balcony, 3 toilets

**Amenities — 50+ across 6 categories:**
- Social: Banquet Hall, Amphitheater, Sky Lounge, Café, Business Center, Cards Room
- Active: Gym, TRX Studio, Half Basketball, Cricket Pitch, Pickleball, Badminton, Squash
- Recreational: 25m Pool, Bowling, Table Tennis, Arcade + VR Games, Cabana
- Relaxation: Jacuzzi Steps, Resting Pavilion, Refreshing Pavilion, Sky Lounge
- Wellness: Yoga, Pilates, Spa + Treatment Rooms, Salon, Divine Deck
- Kids: Kids Pool, Outdoor Kids Play, Kids Area, Family Zone
- Outdoor: 25m Main Pool, Jacuzzi, Kids Pool, Yoga Lawn, Amphitheater, Jogging path

---

## MEDIA ASSET INVENTORY

All source files in:
`/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/DLF Westpark/`

### Brochure Renders (extracted from Presenter 1.pdf — artist's impression)
Must label "Artist's impression" if used in marketing materials.

| File (after upload to Wix) | What it shows | Email use |
|--------------------------|---------------|-----------|
| hero-pg1 — lush landscaped courtyard, jogging path, pool glimpse, tower behind | **BEST HERO** — lifestyle, premium green space | Email 1 hero both variants |
| hero-pg2 — full building exterior, golden-hour dusk, 4 towers | Building scale / prestige shot | Email 2, website |
| hero-pg3 — curved pool + Japanese garden, walkway, residents | **BEST LIFESTYLE** — "resort living" | Email 3 / social |
| hero-pg50 — Café interior, bamboo pendant lights, airy natural light | Amenity lifestyle | Email 2 |
| hero-pg55 — Spa treatment room, warm wood tones | Wellness angle | Email 3 / social |

### Show Flat Photos (REAL interiors — NOT renders, taken on site visit)
Strong advantage: these are actual finished interiors, not CGI.

| File | What it shows | Email use |
|------|---------------|-----------|
| IMG_1166 2.HEIC | Living room — marble floor, chandelier, Mumbai city view at dusk | Variant A interior shot |
| IMG_1167 2.HEIC | Living + dining — full flat overview, warm evening light | Email 2 (unit showcase) |
| IMG_1168 2.HEIC | Master bedroom — orange throw, balcony, Mumbai skyline | Email 3 (lifestyle) |
| IMG_1169 2.HEIC | Bathroom — marble, frameless glass shower, backlit vanity | Specs detail |
| IMG_1171 2.HEIC | Study nook — grey wallpaper, built-in shelving, teal chair | WFH/NRI appeal |
| IMG_1172 2.HEIC | Kitchen entry corridor — Siemens fridge, opens to living | Kitchen quality |
| IMG_1173 2.HEIC | Full galley kitchen — Siemens built-in oven + microwave + fridge | Specs detail |

### Kling AI Videos (animated, for social/landing page — label KlingAI generated)
| File | What it shows | Use |
|------|---------------|-----|
| kling_DLFexterior.mp4 | Night-time exterior animation, towers lit | Landing page hero video, social reel |
| kling_DLFLandscapePool.mp4 | Pool + landscape animated flythrough | Social reel, landing page |

### iPhone Site Visit Videos (raw footage — 16MB–1.4GB each)
IMG_1158–1165, 1178–1179 .MOV — unedited walkthrough. Use for: Reels after editing, WhatsApp, social stories.
**Do not use raw in email** — too heavy; extract stills if needed.

### To upload to Wix Media (once decided which to use)
```
sips -s format jpeg -Z 1200 "/Volumes/RDH 5TB/.../IMG_1166 2.HEIC" --out /tmp/living-room.jpg
```
Then upload via Wix MCP or Wix dashboard → paste CDN URL into email `<Img src="..." />`.

---

## STATUS

| Email | Variant A | Variant B | Approved |
|-------|-----------|-----------|----------|
| Email 1 — Awareness | `web/emails/drip-1-variant-a.tsx` | `web/emails/drip-1-variant-b.tsx` | ⏳ pending review |
| Email 2 — Consideration | not written | — | ⏳ waiting on Email 1 |
| Email 3 — Conversion | not written | — | ⏳ waiting on Email 1 |
| Email 4 — Referral | not written | — | ⏳ waiting on Email 1 |

**NEXT ACTION on emails:** Both variants need hero image URL + facts from above patched in (see PATCH NEEDED below).

---

## PATCH NEEDED — Email 1 (both variants)

These are the only things still placeholder in the current templates:

### Variant A (`drip-1-variant-a.tsx`)
1. `heroPlaceholder` section (dark teal block) → replace with `<Img>` using brochure pg1 render (lush courtyard)
2. Reference to "Imperial Heights / Kalpataru" in body copy — this is correct for personalisation, keep
3. RERA number not mentioned — can optionally add in footer: "MahaRERA: PR1181012500079"

### Variant B (`drip-1-variant-b.tsx`)
1. `heroPlaceholder` → same: replace with pg1 render (or kling exterior for drama)
2. Stat "57 yrs DLF track record" — confirmed accurate (DLF est. 1946)
3. "~10–15× avg early-stage returns" — confirmed framing from DLF track record; add "Artist's impression" caveat in disclaimer
4. "12–18% YoY price appreciation" — internal estimate, should add "based on Andheri West market data" caveat

### Both need subject line confirmed before send:
Recommended: "DLF The Westpark — Mumbai's most anticipated pre-launch" (49 chars)

---

## HOW TO PREVIEW

```bash
cd /Volumes/RDH\ 5TB/Real\ Deal\ Housing\ OS/web
npx email preview
# → http://localhost:3000 — select drip-1-variant-a or drip-1-variant-b
```

Or export HTML:
```bash
npx tsx emails/export-previews.ts && open /tmp/rdh-email-previews/variant-a.html
```

---

## CONTENT CHECKLIST (per email, before approval)

- [ ] No placeholder hero (real image URL loaded)
- [ ] RERA number: PR1181012500079 (confirmed)
- [ ] "Artist's impression" label on any render used
- [ ] Unsubscribe link in footer
- [ ] CTA links to `/dlf-westpark-andheri-west`
- [ ] Subject < 50 chars
- [ ] No spam words (FREE, GUARANTEED, CLICK NOW)
- [ ] Financial disclaimer on Variant B

---

## EMAIL SEQUENCE — AFTER EMAIL 1 APPROVED

**Email 2 — Consideration (Day 5): "The numbers behind DLF The Westpark"**
- Lead with real RERA fact: PR1181012500079, valid to 2032 — project is registered and legal
- Unit sizes: 3BHK from 1255–1368 sqft RERA carpet (actual sq footage, not loaded area)
- Amenities count: 50+ across 6 categories; 25m pool, Spa, Café, Sky Lounge, Cricket Pitch
- Connectivity data: adjacent metro station (proposed), WEH, airport 10 min
- Photo: show flat living room (IMG_1166) + pool render (pg3)
- CTA: "Request the floor plan" → WhatsApp or form

**Email 3 — Conversion (Day 12): "We arranged site visits — 3 slots left"**
- Call to action urgency without fake scarcity — site visits are real, slots are limited by logistics
- Include show flat photo: bedroom (IMG_1168) — real, not render
- Body: what a site visit includes (show flat walk, project briefing, Q&A with DLF rep)
- CTA: "Book a slot" → WhatsApp direct

**Email 4 — Referral (Day 20): "If not you, maybe someone you know"**
- Short — 4 sentences max
- Summarise: DLF, first Mumbai project, pre-launch
- Ask: forward or WhatsApp share
- CTA: wa.me share link or forward

---

## SUBJECT LINE OPTIONS

| Option | Chars | For |
|--------|-------|-----|
| DLF The Westpark — Mumbai's most anticipated pre-launch | 55 ❌ too long | — |
| DLF's first Mumbai project. You should know first. | 50 | Variant A |
| DLF The Westpark: pre-launch access for RDH clients | 52 ❌ | — |
| Mumbai's biggest developer debut — early access | 48 ✅ | Variant B |
| DLF just entered Mumbai. Early access for you. | 47 ✅ | Variant A |
| The Westpark: DLF's Mumbai debut, pre-launch | 46 ✅ | Variant B |

---

## LOOP EXIT

- [ ] Email 1 (A or B, or both) reviewed and approved by Padmini
- [ ] Hero image uploaded to Wix CDN, URL patched into template
- [ ] Email 2 written + approved
- [ ] Email 3 written + approved
- [ ] Email 4 written + approved
- [ ] All LOOP-infra.md gates pass
