# Phase 7.26 — Wix Test Site: CMS Layer Built + Editor Build Handoff

This phase executed the first real build on the **Test** Wix Studio site via the connected Wix MCP
(local Claude Code). It built the entire **data / CMS / blog / SEO / OS-integration layer** through
the Wix REST API, and hands off the **visual layer** (pages, sections, motion) to the Wix Studio
editor, because Wix REST APIs cannot construct editor pages/sections (Wix docs: *"REST APIs aren't
intended for use in Wix site development"* — that is Velo/SDK + editor work).

## Target (confirmed via connector)

- **Site:** `Test` — id `e8817980-3301-420f-856c-a4cd5184633e`
- **Preview URL:** https://hbanthiya.wixstudio.com/test
- **Editor:** Wix Studio · **Locale:** en / India / Asia-Kolkata / INR
- **Off-limits (NOT touched):** `Real Deal Housing` (`3c37cbd6-…`, realdealhousing.com, Premium, custom domain)

## Built on Test (live, via Wix MCP)

- **Velo / Wix Code:** provisioned (was disabled; required for CMS).
- **7 native CMS collections** (admin-write; content read=ANYONE, enquiries read=ADMIN):

| Collection | Rows | Purpose | Read |
|---|---|---|---|
| `Projects` | 1 | DLF Westpark master record (OS anchor `osAnchorId`) | ANYONE |
| `Residences` | 3 | Unit layouts (all `PRICE_VERIFY` / `VERIFY`) | ANYONE |
| `ProjectFacts` | 9 | Verified-facts ledger (per-fact `verificationStatus`) | ANYONE |
| `Amenities` | 5 | Lifestyle/amenity slots (`VERIFY`) | ANYONE |
| `ProjectFAQs` | 6 | FAQ (SEO text, native disclosures) | ANYONE |
| `BlogPosts` | 5 | SEO blog drafts (`status=draft`) | ANYONE |
| `EnquiriesPreview` | 0 | Private preview-only enquiry store (no live capture) | ADMIN |

All placeholders preserved: `RERA_VERIFY`, `PRICE_VERIFY`, `BROCHURE_LINK_PENDING`, `VERIFY`. No facts invented.

## NOT done (correctly blocked / out of API scope)

- No publish, no domain connect, no indexing, no live form/webhook, no tracking, no automation.
- No contacts/leads written (`EnquiriesPreview` is empty + private).
- The live Test template is unchanged (CMS data does not appear on the live site until bound + published).

## Editor build handoff — operator / Velo (the visual layer)

Build in the Wix Studio editor for site **Test** only. Bind sections to the collections above via
datasets/repeaters. Generated copy/SEO/Velo code lives in (git-ignored)
`exports/wix_ai_builds/dlf-westpark-gallery-white-v1/`.

**Site shell (8 pages):** Home, Buy, Rent, Sell, Projects, Blog, About, Contact.
- Apply Gallery White spec (`docs/PHASE_7_18_GALLERY_WHITE_APPROVED_DESIGN_SPEC.md`): ~85% white,
  deep-teal `#1F3D4D` anchors, Manrope, one warm accent/viewport, native scroll reveals, sticky CTA.
- `Projects` page → repeater bound to `Projects`. `Blog` page → repeater bound to `BlogPosts`.

**DLF landing `/dlf-westpark-andheri-west` (12 blocks) → binding map:**
1. Hero → `Projects.heroTagline` / `title`
2. Project overview → `Projects.overview`
3. DLF trust/developer → `ProjectFacts` (developer/project_name rows)
4. Location (Andheri W / D.N. Nagar / Link Road) → `Projects.microMarket` + `ProjectFacts` location
5. Lifestyle & amenities → repeater bound to `Amenities`
6. Residences → repeater bound to `Residences`
7. Gallery/video → placeholder frames (labelled; no stock)
8. Verified-facts ledger → repeater bound to `ProjectFacts` (show `factLabel` + `factValue` + `verificationStatus`)
9. Preview-only enquiry → fields name/contact/intent/message/consent×2; submit label
   "Preview only - no live submission"; **no live submit** (manual-review). Optional: write to
   `EnquiriesPreview` only behind admin/preview gate.
10. FAQ → repeater bound to `ProjectFAQs` (native collapsible, SEO text in DOM)
11. Footer
12. Sticky CTA → two-segment (Request details ｜ WhatsApp), intersection-hide before form

**Velo page code:** once a Studio page is in Dev Mode, paste/sync
`gallery-white-page-code.js` (preview-only form handling) and, if a custom element is used,
`gallery-white-custom-element.js` / `.css`. SEO meta: `gallery-white-seo-meta.md`.

## Verify / dashboards

- CMS data dashboard: `https://manage.wix.com/dashboard/e8817980-3301-420f-856c-a4cd5184633e/database`
- Preview: https://hbanthiya.wixstudio.com/test (live template unchanged until editor build + publish)

## Pending verification (must stay placeholder until approved)

RERA registration (`RERA_VERIFY`), pricing (`PRICE_VERIFY`), configurations/carpet/possession
(`VERIFY`), official brochure (`BROCHURE_LINK_PENDING`), real photography, developer/project facts.
