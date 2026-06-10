# RERA Playwright Fetch Feasibility (Phase 6.10)

Setup + **feasibility only** for opening JavaScript-rendered MahaRERA pages with a
headless browser and capturing **raw, untrusted** snapshots for future parsing. This phase
does **not** bulk-scrape, does **not** write to the database, and does **not** turn
snapshots into trusted facts.

## Why Playwright is needed

The MahaRERA project pages (e.g.
`https://maharerait.maharashtra.gov.in/public/project/view/6231`) are
**JavaScript-rendered single-page apps**: a plain HTTP GET returns an app shell, and the
actual project facts (registration, promoter, carpet-area table, status/risk sections) are
loaded asynchronously by client-side JS. A real browser engine (Playwright + Chromium) is
needed to let that JS run before a snapshot is taken. `requests`/`curl` alone returns the
shell without the data.

## Setup (local / user environment only)

Playwright is an **optional** dev dependency — install it only to run the single-page
capture. Browser binaries download into the per-user cache, never into this repo.

```bash
python3 -m pip install -r requirements-rera-fetch.txt
python3 -m playwright install chromium
```

(Verified install: `playwright 1.60.0`; Chromium downloaded to
`~/Library/Caches/ms-playwright/`.)

## How to run the single-page capture

`scripts/fetch_rera_page_playwright.py` opens **exactly one** user-supplied MahaRERA URL.

```bash
# Dry-run (no browser, no external call) — shows the plan:
python3 scripts/fetch_rera_page_playwright.py \
  --url "https://maharerait.maharashtra.gov.in/public/project/view/6231" \
  --output-label imperial_heights_wing_cd_6231

# Actual single fetch (one external call to the official URL):
python3 scripts/fetch_rera_page_playwright.py \
  --url "https://maharerait.maharashtra.gov.in/public/project/view/6231" \
  --output-label imperial_heights_wing_cd_6231 \
  --save-screenshot --save-visible-text --save-html --save-network-summary \
  --timeout-ms 60000 --apply
```

Hard guards: the URL host must be `maharerait.maharashtra.gov.in` or
`maharera.maharashtra.gov.in`; exactly one URL; a single polite page load; no form
submission, no clicks, no downloads, no CAPTCHA/auth bypass. It prints only counts and
paths — never page contents.

## Where snapshots are saved

Under the **git-ignored** folder
`exports/rera_snapshots/<timestamp>_<output-label>/`, containing (as requested):
`screenshot.png`, `page.html`, `visible_text.txt`, `network_summary.json`, and a
`metadata.json` with `url`, `fetched_at`, `method=playwright`, `external_call_made=true`,
`trusted_for_db=false`, `human_review_required=true`. `exports/` (and an explicit
`exports/rera_snapshots/` rule, plus Playwright trace/video/cache patterns) are in
`.gitignore`; snapshots and browser binaries are **never committed**.

## Feasibility result (one URL: project view/6231)

- **Page opened successfully:** `http_status=200`, `load_error=none`, **37 network events**
  — **no CAPTCHA, no login wall, no block** on a single polite load.
- **SPA shell captured:** `page.html` (~32 KB) and `screenshot.png` (~36 KB) were saved.
- **Async data not fully rendered yet:** `visible_text.txt` was only ~164 bytes, and the
  prototype parser detected `registration_number_count=0`, `project_name_label_present=false`,
  `carpet_table_row_estimate=0`. The meaningful project data loads **after** the initial
  DOM, so a `domcontentloaded` + short settle is **not enough** to capture it.
- **Conclusion:** Playwright is a viable approach (the site is reachable and not blocking a
  single visit), but a future capture must **wait for the data to render** — e.g.
  `wait_until="networkidle"` and/or wait for a specific result selector, with a longer
  timeout — before the snapshot is meaningful for parsing. We deliberately did **not**
  retry-loop or work around this here.

## What the prototype parser does

`scripts/parse_rera_snapshot_placeholder.py` reads a snapshot's `visible_text.txt`/
`page.html` and prints only coarse, **non-personal** signals (registration-number-token
count, project-name label presence, rough carpet-row estimate, `parsing_status=prototype_only`).
It does **not** insert into the DB, generate trusted facts, update RERA tables, or print
personal names. It is a feasibility stub, not a real parser.

## What is NOT allowed

- **No bulk scraping**, no crawling search results, no looping over many projects.
- **No CAPTCHA / login / rate-limit / access-control bypass.**
- **No automatic DB writes** from snapshots; **no auto-corrections** of building/RERA data.
- Snapshots are **raw and untrusted** until a human reviews them.

## Future phases

1. **Snapshot parser** — a real (still review-gated) parser that, after a proper render
   wait, extracts candidate facts from a snapshot into a staging area.
2. **Review-gated candidate facts** — parsed facts become `needs_human_review` candidates,
   never trusted automatically.
3. **Accepted RERA matches** — a human accepts the RERA project match (Phase 6.9 left both
   Imperial Heights anchors as `candidate`).
4. **Building dedupe** — once a RERA match is accepted, consolidate the duplicate Imperial
   Heights anchors (Phase 6.7) on an authoritative basis.

> RERA data remains an **internal verification aid, not legal advice**, and RERA
> address/boundary/lat-long are **not** trusted as building address data.
