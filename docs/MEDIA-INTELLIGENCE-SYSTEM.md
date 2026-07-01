# Media Intelligence System
**Status:** Design approved, not yet built  
**Context:** Discussed 2026-07-01. Records vision + human-in-loop gates so context survives session resets.

---

## The Core Idea

Every piece of media, every listing, every lead, every campaign plugs into one spine: the **building structure**. The building structure is already partially in Postgres from the unit registry work (migrations 047–049). This system extends it.

```
Building
 └── Tower
      └── Floor
           └── Unit  ←── Configuration Type  (3BHK-A, 2BHK-B …)
                │         ├── Floor plan image     (extracted from brochure)
                │         ├── Carpet area, RERA    (extracted from brochure / RERA PDF)
                │         └── Stock media set      (empty layout, show-apt footage)
                ├── IGR registry record            (owner, tenant, reg dates)
                ├── Specific media                 (actual apt photos when available)
                ├── Contacts / leads
                └── Campaigns
```

**Configuration Type** is the missing link. All units that share the same floor plan share the same stock media. C-156 Kalpataru being a 2BHK-B means it gets the 2BHK-B floor plan image and empty layout photos — no per-unit work needed until we have actual photos.

---

## Media Fallback Hierarchy

When the website or a campaign needs an image for a specific unit, the query walks down from most specific to most generic:

```
1. Unit-specific photo    (actual apartment, e.g. C-502 photos on disk)
2. Configuration stock    (empty layout #6 in Tower C = all 2BHK-B units)
3. Show-apartment footage (we shot one 3BHK show flat → covers all 3BHK listings)
4. Tower / floor stock    (exterior of Tower C, lobby, floor-level shots)
5. Building stock         (building exterior, amenities, master layout)
6. Generic RDH stock      (fallback brand imagery)
```

This hierarchy lives in `media_assets.asset_level` and is resolved by a single ranked SQL query.

---

## Three Components

### 1. Brochure Intelligence Pipeline
**Input:** PDF brochure (+ optionally MahaRERA listing page URL, map)  
**Output:** Structured building data + classified images → both fed into Postgres

What it extracts:
- **Images** — classified by type: exterior / floor plan / master layout / amenity / section cut / unit interior
- **Structure** — tower names, floor count, units per floor, typical vs atypical floors (e.g. duplex on floor 40)
- **Configurations** — "3BHK Type A: carpet 1,200 sq ft, units in positions 01 & 02 on each floor"
- **Floor plan → configuration mapping** — which floor plan image covers which unit type
- **RERA refs, carpet area schedule, developer details**

The extracted structure feeds `building_units` (adds `configuration_type` column).  
The extracted images feed `media_assets` (tagged `source=brochure_extract`).

**Human-in-loop gates:**
- `TOWER_NAME_AMBIGUOUS` — brochure says "Wing A" but IGR says "Tower A-ORA" — human confirms canonical name
- `FLOOR_COUNT_MISMATCH` — brochure says 40 floors, RERA PDF says 51 — human picks authoritative source
- `UNIT_POSITION_UNCLEAR` — floor plan shows 8 units but numbering convention unclear — human maps positions to unit numbers
- `ATYPICAL_FLOOR_FLAGGED` — parser sees a different layout on certain floors (duplex, penthouse, service) — human confirms and records the exception
- `IMAGE_CLASSIFICATION_LOW_CONFIDENCE` — extracted image confidence < threshold — human labels it
- `CARPET_AREA_CONFLICT` — brochure carpet ≠ RERA carpet — human resolves, records source

---

### 2. Digital Asset Library (DAM)
**Location of truth:** `/Volumes/RDH 5TB/` (this disk)  
**Postgres table:** `media_assets`

#### Key fields
```sql
id, local_path, building_id, unit_id (nullable),
configuration_type (nullable),        -- "3BHK-A" etc
asset_level,                          -- unit | configuration | tower | building | generic
asset_type,                           -- floor_plan | exterior | interior | amenity |
                                      -- master_layout | video | brochure | virtual_stage
source,                               -- brochure_extract | disk_scan | youtube | manual
wix_url, youtube_url,
alt_text, seo_title, tags[],
reviewed,                             -- gate: nothing goes to website until true
upload_status,                        -- local_only | wix_uploaded | youtube_uploaded
virtual_stage_status,                 -- none | queued | done
metadata jsonb                        -- file size, dimensions, shoot date, photographer etc
```

#### Disk scanner
Script walks `/Volumes/RDH 5TB/` and indexes every media file. Infers `building_id` + `unit_id` from folder path (e.g. `Imperial Heights/C-502/` → match building + unit). Records `local_path`, `asset_type` (guessed from folder name and extension), `asset_level`.

**Human-in-loop gates:**
- `PATH_BUILDING_MATCH_AMBIGUOUS` — folder name "IH exteriors" matches multiple buildings — human confirms
- `PATH_UNIT_MATCH_FAILED` — folder says "C 156" but no `building_unit` row found — human links or creates unit
- `ASSET_TYPE_UNCLEAR` — file is `IMG_4532.jpg` with no folder context — human labels type
- `DUPLICATE_DETECTED` — same content hash found at two paths — human picks canonical

#### Upload pipeline
`upload_to_wix.py` — reads `WHERE reviewed=true AND wix_url IS NULL`, uploads via Wix Media Manager REST API, writes back `wix_url` + `wix_media_id`.  
`record_youtube.py` — operator pastes YouTube URL, script links it to the asset record.

**Human-in-loop gates:**
- `ALT_TEXT_MISSING` — reviewed=true but alt_text is null — human must fill before upload (SEO requirement)
- `UPLOAD_FAILED` — Wix API returned error — human retries or flags as skip

---

### 3. Content Pipeline (later)
Same `media_assets` table extended with:
- `youtube_url` — set by `record_youtube.py` after manual upload
- `social_post_id` — Instagram / LinkedIn post ID once social automation is built
- `virtual_stage_status` — track virtual staging progress per unit
- `content_generation_status` — for n8n-driven SEO copy generation against this asset

Show-apartment footage tagged as `configuration_type=3BHK-A, asset_type=interior, asset_level=configuration` automatically becomes the fallback interior video for every 3BHK-A listing.

---

## What Already Exists in Postgres

| What | Table / Migration |
|------|------------------|
| Building registry | `buildings` |
| Tower + unit structure | `building_units` (migration 047) |
| IGR reg records + parties | `unit_registration_records`, `unit_registration_parties` (047) |
| Ownership / tenancy timeline | migration 048 |
| RERA data | `rera_*` tables (migration 019/020) |
| Contacts + contact methods | `contacts`, `contact_methods` |

**Missing (to build):**
- `configuration_type` column on `building_units`
- `media_assets` table (the whole DAM)
- `brochure_extraction_staging` tables (like the RERA parser pattern)

---

## Build Order

| Phase | What | Trigger |
|-------|------|---------|
| **A** | `media_assets` table + disk scanner | Now — unblocks DLF images + email CDN |
| **B** | Brochure Intelligence Pipeline | DLF Westpark brochure is in `imports/` |
| **C** | `unit_configuration_type` + floor plan linkage | After B validates the config type taxonomy |
| **D** | Cockpit `/cockpit/media` page | When asset count makes CLI review painful |
| **E** | YouTube + virtual staging tracking | When footage exists |
| **F** | pgvector RAG on asset metadata | When asset count > ~200 indexed |
| **G** | Social automation | When content strategy is stable |

---

## RAG Design (Phase F)

pgvector embeddings on: `alt_text + seo_title + tags + configuration_type + asset_type + building_name`

Query example: *"find me 3 images suitable for a high-floor 3BHK listing in Andheri West"*  
→ cosine similarity search → ranked results from own catalogue  
→ operator reviews top 5, selects for listing

One migration (add `embedding vector(1536)` to `media_assets`), nightly embed job via n8n calling OpenAI/Claude embeddings API.

---

## Disk Layout Convention (target)

```
/Volumes/RDH 5TB/
  RDH DATA 2024/
    RDH ALL Footage/
      ALL PROJECTS/
        Imperial Heights/
          building/          ← building-level: exterior, lobby, amenities, master layout
          3BHK-A/            ← config-level: empty layout, show apt (if shot at this building)
          2BHK-B/
          C-502/             ← unit-level: actual apt photos when available
          C-156/
        Kalpataru Radiance/
          ...
        DLF Westpark/
          ...
  exports/                   ← video exports for YouTube (gitignored, not indexed for web)
  brochures/                 ← source PDFs
```

Scanner infers `asset_level` from folder depth. Operator can override.

---

## Human-in-Loop Summary

All automated steps write to staging tables or set `reviewed=false`. Nothing touches the website or gets uploaded until a human approves. The cockpit surfaces the review queue.

| Gate | Triggered by | Blocks |
|------|-------------|--------|
| Tower name ambiguity | Brochure parser | Structure import |
| Floor count mismatch | Brochure vs RERA | Structure import |
| Unit position unclear | Floor plan parser | Configuration mapping |
| Atypical floor | Parser | Floor record |
| Image low confidence | Brochure image extractor | Image import |
| Carpet area conflict | Brochure vs RERA | Fact record |
| Path → building match ambiguous | Disk scanner | Asset indexing |
| Path → unit match failed | Disk scanner | Asset indexing |
| Asset type unclear | Disk scanner | Asset indexing |
| Duplicate detected | Disk scanner | Asset indexing |
| Alt text missing | Upload pipeline | Wix upload |
| Upload failed | Upload pipeline | CDN URL |
