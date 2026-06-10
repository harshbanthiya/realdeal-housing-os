# MahaRERA Verification Pipeline (Phase 6.8 foundation)

The database foundation, fake workflow, and review workflow for **future** official
MahaRERA-based building verification. This phase is **schema + fake workflow only** —
nothing scrapes MahaRERA, calls an external API, browses the web, auto-corrects building
data, merges buildings, resolves source gaps, publishes, or sends outreach.

> **Legal/disclaimer note:** This is an **internal verification aid** to cross-check
> internal records against official public registers. It is **not legal advice** and is
> not a substitute for the official MahaRERA portal. All official facts must be confirmed
> by a human against the source before any external use.

## Why MahaRERA matters

[MahaRERA](https://maharera.maharashtra.gov.in/) is the Maharashtra Real Estate
Regulatory Authority. For Maharashtra/Mumbai projects it is the **official, public
register** of real-estate projects. It becomes our official verification layer because it
can confirm — independently of our internal imports — whether a project is real,
registered, and in good standing, and what its officially-filed apartment areas are. That
matters here because Imperial Heights currently has **two duplicate building anchors**
(`0e72db71` canonical vs `f05bbd01`); an accepted RERA match gives an authoritative basis
for consolidating them.

## What data MahaRERA can verify

| Internal need | RERA fact |
| ------------- | --------- |
| Is this a real, registered project? | registration number, registration status/date/validity |
| Who is the developer? | official promoter name |
| Where is it? | district / taluka / locality / pincode |
| Are the advertised sizes honest? | official **carpet area** per apartment type/wing |
| Is it risky to promote? | lapsed / revoked / abeyance / deregistered / NCLT / complaints / extensions |

## How RERA links to buildings / SEO / content

Migration `schemas/019_rera_verification_foundation.sql` adds 6 tables:

| Table | Role |
| ----- | ---- |
| `rera_project_profiles` | Official project profile, linked to a `buildings` row and/or a `building_web_profiles` row. |
| `rera_building_match_candidates` | Proposed internal-anchor ↔ RERA-project matches (name/location/pincode/developer signals). |
| `rera_carpet_area_records` | Official carpet-area records per apartment type/wing, for later comparison. |
| `rera_project_status_checks` | Compliance/status/risk flags (`info` / `warning` / `blocker`). |
| `rera_area_mismatch_candidates` | Internal area claim vs RERA carpet area, with a `mismatch_percent` and suspected reason. |
| `rera_verification_review_items` | Human review queue for match / fact / area-mismatch / status-risk decisions. |

Six read-only dashboards expose this safely (no personal contact data):
`vw_rera_project_verification_dashboard`, `vw_rera_building_match_dashboard`,
`vw_rera_area_mismatch_dashboard`, `vw_rera_status_risk_dashboard`,
`vw_rera_verification_review_queue`, and `vw_imperial_heights_rera_readiness`.

The readiness view gates downstream work:
- **`ready_for_building_dedupe`** is true **only** when an **accepted** RERA match exists
  for the building (so dedupe is anchored to an official project, not just a name match).
- **`ready_for_content_fact_use`** is true **only** when a **verified** RERA profile
  exists **and** there is **no blocker-severity** risk present.

## How area-mismatch detection works

For an apartment type/wing, we compare the internal area claim (e.g. a `building_units`
saleable/built-up figure) against the official RERA **carpet** area
(`rera_carpet_area_sqft`). A `rera_area_mismatch_candidates` row records both values, the
`mismatch_percent`, and a `suspected_reason` (`carpet_vs_builtup`, `carpet_vs_saleable`,
`typo`, `unit_mismatch`, `unknown`). Nothing is auto-corrected — a human reviews each
candidate via `rera_area_mismatch_review`. (Carpet area is almost always smaller than
built-up/saleable, so a positive mismatch usually means `carpet_vs_builtup`.)

## Browser-fetch feasibility (Phase 6.10) + gate handling (Phase 6.11)

Because MahaRERA pages are JavaScript-rendered, Phase 6.10 set up **Playwright** and a
**guarded single-URL** capture script (`scripts/fetch_rera_page_playwright.py`) that saves
raw, untrusted snapshots under the git-ignored `exports/rera_snapshots/` — **no bulk
scraping, no DB writes, no CAPTCHA/auth bypass**. Phase 6.10 confirmed the page opens
(HTTP 200, no block) but renders its data asynchronously.

**Phase 6.11** added handling for the two gates an operator observed when browsing
MahaRERA: (1) an **external-site confirmation modal** ("You are about to proceed to an
external website. Click YES to proceed.") on the search/result flow, and (2) a **CAPTCHA**
on the public project view before the project data renders. The script now **detects** both:

- The external modal is detected; **YES is clicked only with `--accept-external-warning`**
  (allowlisted single URL only); otherwise the run stops with `status=external_warning_required`.
- A CAPTCHA is detected; **without `--human-captcha-mode` the run stops** with
  `status=captcha_required`. With `--human-captcha-mode` (headed), the script pauses and a
  **human** solves the CAPTCHA manually in the visible browser; only then does capture
  continue. The script **never** reads, OCRs, solves, auto-submits, or uses a service for the
  CAPTCHA, and never prints its text.

A Phase 6.11 test on `project/view/6231` confirmed: headless → `captcha_required` (safe
stop, no DB writes); headed human-in-the-loop with no human present → reported honestly
(`captcha_still_present`), **no bypass**. The data is reachable only **after a human clears
the CAPTCHA**.

**Phase 6.12** then ran **one operator-assisted capture** on the same URL: a real human
manually solved and submitted the CAPTCHA, and the script captured the rendered page
(`status=captured`, `captcha_solved_by_human=true`). The post-CAPTCHA snapshot contains the
real project detail — `visible_text.txt` ~164 B → **~9.8 KB**, `page.html` ~32 KB →
**~315 KB**, network 37 → **116 requests / 75 JSON-like / 47 candidate endpoints** — and a
counts-only scan found **all eight** expected sections present (Registration Number, Project
Name, Project Status, Promoter, Building, Apartment/Unit summary, Complaint, Litigation). The
snapshot is therefore **suitable for a future review-gated parser**, but stays **raw and
untrusted** until human review. See `docs/RERA_PLAYWRIGHT_FETCH_FEASIBILITY.md`. Across 6.11
and 6.12: **no CAPTCHA bypass/OCR/solver, no DB writes, no RERA match accepted, no profile
verified, no building merged, no source gap resolved, no publishing/outreach.**

## Review-gated snapshot parser (Phase 6.13)

Phase 6.13 parses the Phase 6.12 **post-CAPTCHA** snapshot into **untrusted, review-gated
candidate facts** and compares them against the Phase 6.9 manual rows — **no canonical
writes**. Migration `schemas/020_rera_snapshot_parser_staging.sql` adds 4 staging tables
(`rera_snapshot_captures`, `rera_parsed_fact_candidates`, `rera_snapshot_compare_results`,
`rera_snapshot_review_items`) + 5 dashboards, including
`vw_imperial_heights_rera_parser_readiness` (whose `ready_to_update_rera_profile` /
`ready_for_content_fact_use` are **hard false**). `scripts/parse_rera_snapshot_to_candidates.py`
(dry-run default; `--real-ok` to read, `--apply` to write) extracted **17 candidate facts**
and **10 compare results** (**6 matched / 0 mismatch / 4 pending_review**) — the snapshot
**corroborates** the manual data. Legal-risk sections (complaint/litigation/appeal/
non-compliance) are stored as **counts only**; **no personal names** are stored (a scan of
stored values returns 0 name matches). Canonical rows stayed put: profile
`needs_human_review`, matches `candidate`, carpet 26 / status 13 / review 6, buildings 2.
`scripts/cleanup_rera_snapshot_parser_candidates.py` (dry-run shown only) removes solely the
tagged `phase=6.13` rows. See `docs/PHASE_6_13_RERA_SNAPSHOT_PARSER.md`. Next: **human review**
of the parser candidates via `vw_rera_snapshot_review_queue`.

## Why no bulk scraping / API calls happen in these phases

This phase builds the **destination schema and the human-review workflow** before any
data collection. Pulling official records is a separate, deliberate step with its own
rate, caching, and compliance considerations. Keeping collection out of scripts here
means: no accidental load on the public portal, no brittle scraping baked into the
foundation, and a clean place for a human to paste/confirm official facts later.

## Fake workflow (this phase)

`scripts/seed_fake_rera_verification.py` (dry-run default; `--apply --fake-ok`) seeds a
**clearly-fake, self-contained** test set — one fake building named
`ZZ_FAKE RERA Test Tower (Phase 6.8)` (deliberately **not** matching "Imperial Heights",
so the real readiness view stays clean), plus 1 RERA profile, 1 match candidate, 2
carpet-area records, 3 status checks, 1 area-mismatch candidate, and 4 review items — all
tagged `fake_batch='FAKE_PHASE_6_8_RERA_VERIFICATION'`.
`scripts/cleanup_fake_rera_verification.py --apply` removes **only** those tagged rows
(including the fake building). `scripts/rera_verification_summary.py` is read-only counts.

```bash
python3 scripts/seed_fake_rera_verification.py                 # dry-run
python3 scripts/seed_fake_rera_verification.py --apply --fake-ok
python3 scripts/rera_verification_summary.py
python3 scripts/cleanup_fake_rera_verification.py             # dry-run
python3 scripts/cleanup_fake_rera_verification.py --apply
```

## Manual verification phase (Imperial Heights) — Phase 6.9, done

Phase 6.9 recorded official MahaRERA facts for **Imperial Heights Wing C & D**
(reg `P51800003270`) from a **manually-supplied PDF snapshot** — registration, promoter
company, land/built-up areas, sanctioned wings/floors, 26 carpet-area records (213
apartments), and 13 status/risk/document checks — all **review-gated**
(`needs_human_review` / `candidate` / `pending`), with **no scraping**. RERA
address/lat/long were deliberately **not** trusted (left for operator review). See
`docs/PHASE_6_9_MANUAL_RERA_IMPERIAL_HEIGHTS.md`. A human now works the
`vw_rera_verification_review_queue`.

## Future building dedupe phase using an accepted RERA match

Once `vw_imperial_heights_rera_readiness.ready_for_building_dedupe` is true (an accepted
RERA match exists), the Phase 6.7 `building_duplicate_candidates` row (canonical
`0e72db71` vs duplicate `f05bbd01`) can be consolidated with an **authoritative** basis,
after which the deferred `active_owner_relationship_count` evidence (Phase 6.6) can be
accepted.

## Safety posture (verified via fake test)

- **No real building/content changed** — buildings `2`, Imperial anchors `2`, active
  owner relationships `2`, gaps `open=17 / resolved=0`, `ready_for_ai_draft=0`,
  `ready_for_publish=0`, `communication_sent=0` (all unchanged after seed + cleanup).
- **No MahaRERA/external call, no scraping, no browsing** from any script.
- **No publishing, no outreach.** Fake rows fully removed after the test (all RERA tables `0`).

## Next recommendation

Build the guarded **manual** RERA fact-entry phase for Imperial Heights (human reads the
official portal, records facts, works the review queue), then the RERA-anchored building
dedupe. Public drafting + Wix publishing remain gated and out of scope.
