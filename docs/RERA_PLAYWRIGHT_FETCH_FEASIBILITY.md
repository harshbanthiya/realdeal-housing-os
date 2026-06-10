# RERA Playwright Fetch Feasibility (Phase 6.10 → 6.11)

Setup + **feasibility only** for opening JavaScript-rendered MahaRERA pages with a
browser and capturing **raw, untrusted** snapshots for future parsing. This work does
**not** bulk-scrape, does **not** write to the database, and does **not** turn snapshots
into trusted facts.

**Phase 6.11 update — gate handling.** Manually browsing MahaRERA revealed **two gates**
that stand between a project URL and the rendered project data:

1. **External-site confirmation modal** — the search/result flow can pop a modal:
   *"You are about to proceed to an external website. Click YES to proceed."*
2. **CAPTCHA** — the public project view then shows a **CAPTCHA** form before the project
   detail data renders.

The capture script now **detects** both gates. It will **never** bypass, read, OCR, or
auto-solve a CAPTCHA, and never uses a CAPTCHA-solving service. The only safe path through
the CAPTCHA is a **headed, human-in-the-loop** capture where a human solves it manually.

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

# Headless single fetch — stops safely at whichever gate appears:
python3 scripts/fetch_rera_page_playwright.py \
  --url "https://maharerait.maharashtra.gov.in/public/project/view/6231" \
  --output-label imperial_heights_wing_cd_6231 \
  --save-screenshot --save-visible-text --save-html --save-network-summary \
  --timeout-ms 60000 --apply
```

Hard guards: the URL host must be `maharerait.maharashtra.gov.in` or
`maharera.maharashtra.gov.in`; exactly one URL; no bulk scrape/crawl/loop; no CAPTCHA/auth
bypass, OCR, or solving service; no automatic form submission; no DB writes. It prints only
counts, booleans, and paths — never page contents and never CAPTCHA text.

### Gate-handling flags (Phase 6.11)

| Flag | Effect |
| ---- | ------ |
| `--accept-external-warning` | Click **YES** on the external-site modal — **only** for the single allowlisted URL. Without it, an external-warning modal stops the run with `status=external_warning_required`. |
| `--human-captcha-mode` | Forces a **headed** browser; on CAPTCHA, pauses for a **human** to solve it manually. Without it, a CAPTCHA stops the run with `status=captcha_required`. |
| `--pause-for-human` | Blocks on Enter so the operator can act in the visible browser, then resumes capture. |
| `--captcha-timeout-ms` | Max time to wait for the human / post-resume render signal (default 180000). |
| `--wait-after-human-ms` | Settle time after the human resumes (default 2500). |
| `--wait-for-text`, `--wait-for-selector` | Optional render signals to wait for after load/resume. |
| `--post-load-wait-ms` | Settle time after the initial load before gate detection (default 3500). |
| `--save-response-bodies`, `--response-body-url-filter` | Optionally save **same-host** JSON/HTML response bodies (bounded, query strings redacted) for later review. |

The script **never** reads, OCRs, solves, or auto-submits a CAPTCHA, and **never** prints
its text. In `--human-captcha-mode` a human solves and submits the CAPTCHA **themselves** in
the visible browser; only then does the script continue and capture the rendered page.

### Headed human-in-the-loop capture (the safe CAPTCHA path)

```bash
python3 scripts/fetch_rera_page_playwright.py \
  --url "https://maharerait.maharashtra.gov.in/public/project/view/6231" \
  --output-label imperial_heights_wing_cd_6231_human_captcha \
  --headful --human-captcha-mode --pause-for-human \
  --save-screenshot --save-visible-text --save-html --save-network-summary \
  --apply
```

Flow: the script opens a **visible** Chromium window, detects the CAPTCHA, and prints a
prompt. The **operator** solves the CAPTCHA in that window and submits it; once the project
page renders, the operator presses **Enter** in the terminal. The script then waits, re-checks
that the CAPTCHA gate is gone, captures `screenshot_after_human.png` + HTML + visible text +
network summary, and records `captcha_solved_by_human=true`. If the page still does not
render, it reports honestly (`status=captcha_still_present`) — **no bypass, no retry loop**.

## Where snapshots are saved

Under the **git-ignored** folder
`exports/rera_snapshots/<timestamp>_<output-label>/`, containing (as requested):
`screenshot_before_gate.png`, `screenshot_after_human.png` (only if a human cleared the
CAPTCHA), `page.html`, `visible_text.txt`, `network_summary.json`, optional
`response_body_NNN.{json,html}`, and a `metadata.json` with `url`, `fetched_at`,
`method=playwright`, `status`, `external_call_made=true`, `trusted_for_db=false`,
`human_review_required=true`, `external_warning_detected`,
`external_warning_accepted_by_script`, `captcha_detected`, `captcha_solved_by_human`, and
`db_writes=false`. `exports/` (and an explicit `exports/rera_snapshots/` rule, plus
Playwright trace/video/cache patterns) are in `.gitignore`; snapshots, response bodies, and
browser binaries are **never committed**. Snapshots stay **untrusted** until a human reviews
them — they are raw evidence, not facts.

The `network_summary.json` records **counts only** (total requests/responses, same-host
responses, JSON-like, HTML, failed, candidate-endpoint count, response-body files saved) and
**redacts** cookies, auth headers, tokens, and query strings (stored URLs are path-only).

## Feasibility result (Phase 6.10 — one URL: project view/6231)

- **Page opened successfully:** `http_status=200`, `load_error=none`, ~37 network events
  — no login wall and no block on a single polite load.
- **SPA shell captured:** `page.html` (~32 KB) and `screenshot.png` (~36 KB) were saved.
- **Async data not rendered yet:** `visible_text.txt` was only ~164 bytes; the prototype
  parser detected `registration_number_count=0`. The meaningful project data loads **after**
  the initial DOM (and, as Phase 6.11 found, behind a CAPTCHA gate).

## Gate result (Phase 6.11 — same URL: project view/6231)

- **Test 1 — headless, no human-captcha-mode:** `http_status=200`, **CAPTCHA detected**, the
  script **stopped safely** with `status=captcha_required` and **wrote nothing to the DB**.
  No external-warning modal appeared on the direct project URL (it appears on the
  search/result flow). 37 requests / 37 responses / 9 same-host / 1 JSON-like / 0 candidate
  endpoints captured for review.
- **Test 2 — headed human-in-the-loop:** the **visible browser launched**, the CAPTCHA was
  detected, and the human window opened. With **no human present to solve it** in the
  unattended run, the script reported **honestly** (`status=captcha_still_present`,
  `captcha_solved_by_human=false`) — **no bypass, no OCR, no solver, no retry loop**. A real
  run requires the operator to solve the CAPTCHA in the window and press Enter; the script
  then captures `screenshot_after_human.png` and the rendered HTML/text.
- **Conclusion:** The direct project URL is reachable but the data sits behind a CAPTCHA that
  **must** be solved by a human. The safe, repeatable path is the **headed, human-in-the-loop**
  capture. We deliberately do **not** bypass, OCR, auto-solve, or loop.

## What the prototype parser does

`scripts/parse_rera_snapshot_placeholder.py` reads a snapshot's `visible_text.txt`/
`page.html` (and any `response_body_*` files) and prints only coarse, **non-personal**
signals: `registration_number_token_count`, `project_name_label_present`,
`carpet_area_label_present`, `promoter_label_present`, `complaint_section_present`,
`litigation_section_present`, `captcha_detected_in_snapshot`,
`external_warning_detected_in_snapshot`, `candidate_json_files_count`, and
`parsing_status=prototype_only`. It does **not** insert into the DB, generate trusted facts,
update RERA tables, or print personal names / page text. It is a feasibility stub, not a real
parser. Run against the gated Phase 6.11 snapshot it returns all-zero/false (the data is
behind the CAPTCHA), confirming a snapshot is only parseable **after** a human clears the gate.

## What is NOT allowed

- **No bulk scraping**, no crawling search results, no looping over many projects.
- **No CAPTCHA / login / rate-limit / access-control bypass; no OCR; no CAPTCHA-solving service.**
- **No automatic form submission** — a human solves and submits the CAPTCHA themselves.
- **No automatic DB writes** from snapshots; **no auto-corrections** of building/RERA data.
- **No accepting RERA matches, marking profiles verified, merging buildings, resolving source
  gaps, publishing, or outreach** from this capture path.
- Snapshots are **raw and untrusted** until a human reviews them.

## Future phases

1. **Human-in-the-loop capture of a rendered page** — an operator runs the headed
   `--human-captcha-mode` flow, solves the CAPTCHA, and the script captures a **post-CAPTCHA**
   snapshot with the real project data.
2. **Review-gated snapshot parser** — a real (still review-gated) parser that extracts
   candidate facts from a post-CAPTCHA snapshot into a staging area as `needs_human_review`
   candidates, never trusted automatically. (Alternatively, **continue the manual PDF flow**
   from Phase 6.9 — also fully review-gated.)
3. **Accepted RERA matches** — a human accepts the RERA project match (Phase 6.9 left both
   Imperial Heights anchors as `candidate`).
4. **Building dedupe** — once a RERA match is accepted, consolidate the duplicate Imperial
   Heights anchors (Phase 6.7) on an authoritative basis.

> RERA data remains an **internal verification aid, not legal advice**, and RERA
> address/boundary/lat-long are **not** trusted as building address data.
