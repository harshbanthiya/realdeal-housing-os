# IGR eSearch Index II capture (Phase 6.18)

`scripts/fetch_igr_esearch_playwright.py` is the **IGR analogue** of the MahaRERA capture
(`fetch_rera_page_playwright.py`). It opens the Maharashtra IGR free-search portal
(`freesearchigrservice.maharashtra.gov.in`) in a **headed** browser so a **human** can run a
property search and capture the raw Index II results.

> **Operator-driven, human CAPTCHA, no DB writes.** The script does NOT auto-fill-and-submit the
> search and NEVER reads, OCRs, solves, auto-submits, or uses a service for the CAPTCHA — the
> operator enters the search and solves the CAPTCHA themselves. It captures snapshots only when the
> operator presses Enter. No crawling/looping over many properties. Snapshots are raw and untrusted
> until the (future) review-gated Index II parser runs.

## Why human-driven

IGR eSearch is **property-number first** (year × district × tahsil/village × CTS/survey) and is
**CAPTCHA-gated** — it is not building-name searchable. The selectors are fragile and a wrong
auto-fill could mis-query, so the operator drives the form and the script's job is provenance +
capture, not automation.

## Prerequisites

Playwright + Chromium are already installed (from Phase 6.10, in the user cache). If missing:

```bash
python3 -m pip install -r requirements-rera-fetch.txt
python3 -m playwright install chromium
```

## Usage (example: Kalpataru Radiance A — CTS 260/5A, village Pahadi)

```bash
# Dry run (no browser, no external call) — prints the plan and the snapshot path:
python3 scripts/fetch_igr_esearch_playwright.py \
  --output-label kalpataru-260-5A-2023 --building-label "Kalpataru Radiance A" \
  --year 2023 --district "Mumbai Suburban" --village Pahadi --cts "260/5A"

# Live session (opens a visible browser; you solve the CAPTCHA):
python3 scripts/fetch_igr_esearch_playwright.py \
  --output-label kalpataru-260-5A-2023 --building-label "Kalpataru Radiance A" \
  --year 2023 --district "Mumbai Suburban" --village Pahadi --cts "260/5A" --apply
```

In the live session:
1. In the **window**: choose year / district / tahsil / village, enter the CTS (260/5A), **solve the
   CAPTCHA**, click Search.
2. Back in the **terminal**: press **Enter** to capture the results page.
3. Open each **Index II** in the window; press **Enter** to capture each (optionally type a short tag).
4. Type **`done`** when finished.

The `--year` / `--district` / `--village` / `--cts` flags are **provenance only** (recorded in
`metadata.json`); the operator still enters them in the form. Run **one job per year**; loop years
yourself across sessions (2010 onward first, per the pipeline plan).

## Output

Under the **git-ignored** `exports/igr_snapshots/<timestamp>_<label>/`:
`capture_NNN_<tag>.{png,html,txt}` per page, `network_summary.json` (counts only, queries
redacted), and `metadata.json` (`trusted_for_db=false`, `human_review_required=true`,
`captcha_solved_by_human`, search provenance, capture list). **These snapshots contain party PII**
and are never committed.

## Hard guards

Host-locked to `freesearchigrservice.maharashtra.gov.in`; headed only; no CAPTCHA/auth bypass; no
OCR; no solver services; no DB writes; bounded by `--max-captures` (default 40); dry-run unless
`--apply`.

## Next step

A review-gated **Index II parser** reads a captured snapshot and proposes
`unit_registration_records` + `unit_registration_parties` (replacing the Phase 6.18 illustrative
rows), exactly as the Phase 6.13 MahaRERA snapshot parser did — counts/PII handled carefully, no
canonical writes without human review.
