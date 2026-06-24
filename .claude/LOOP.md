# Real Deal Housing OS — Build Loop

<!-- Claude: READ THIS FIRST. ~200 tokens. Do not read anything else until you've checked LOOP STATE. -->
<!-- TOKEN BUDGET: You have ONE task per tick. Read LOOP STATE → do NEXT_ACTION → run audit cmd → update LOOP STATE block ONLY → stop. Do NOT: read other files speculatively, run extra queries, write prose explanations, chain tasks. If tempted to do "one more thing" — stop and write it as the next NEXT_ACTION instead. -->

## LOOP STATE

```
CURRENT_LOOP:   6
CURRENT_TASK:   6b-parse-index2-bulk-snapshots
STATUS:         ready — 496 Index II captures across 2020-2026 in exports/igr_index2_snapshots/

LOOPS DONE:
  1-3: IGR worker + Index II fetch + unit linker (commit b9693b7)
  4:   Kalpataru data cleanup — 1 building/966 units/+58 links/325 name fixes
  5:   promoted 1732 parsed_candidate; worker end-to-end verified; 12 new Wing A records staged
  6a:  operator ran fetch_igr_index2_bulk.py for 2020-2026 → 496 Index II .txt captures

BULK CAPTURE SUMMARY (exports/igr_index2_snapshots/):
  2020: 5 result pages | 32 Index II captures
  2021: 2 result pages | 17 Index II captures
  2022: 1 result page  |  5 Index II captures
  2023: 6 result pages | 54 Index II captures
  2024: 15 result pages| 141 Index II captures
  2025: 21 result pages| 209 Index II captures
  2026: 4 result pages | 38 Index II captures
  TOTAL: 54 result pages + 496 Index II popups across all 7 year folders

SCRIPT: scripts/ingest_igr_bulk_snapshots.py
  Reads BOTH file types per folder:
  - capture_*_results.html  → party names, flat/wing/floor/area, L&L rent/deposit/tenure
  - capture_*_r*.txt        → prices, PAN, age, address, dates, CTS, stamp duty, reg fee
  Merges on doc_no. Cross-validates wing/flat/type between sources. All 4 wings.
  Upserts: UPDATE existing records (enrich price + PAN parties); INSERT new.

NEXT_ACTION:
  Step 1 — dry run (verify parse quality, check cross-validation issues):
    python scripts/ingest_igr_bulk_snapshots.py

  Step 2 — apply:
    python scripts/ingest_igr_bulk_snapshots.py --apply --real-ok

  Step 3 — audit DB result:
    SELECT registration_year, transaction_category,
           COUNT(*) total,
           COUNT(consideration_amount) has_price,
           COUNT(stamp_duty) has_stamp,
           COUNT(tenancy_monthly_rent) has_rent,
           COUNT(tenancy_start_date) has_start_date
    FROM unit_registration_records
    WHERE building_id=(SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%' LIMIT 1)
    GROUP BY 1,2 ORDER BY 1,2;

    SELECT COUNT(*) total_parties,
           COUNT(party_pan) parties_with_pan
    FROM unit_registration_parties p
    JOIN unit_registration_records r ON r.id=p.unit_registration_record_id
    WHERE r.building_id=(SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%' LIMIT 1);

  done when: has_price populated for most records, PANs present where IGR had them

PAUSED_FOR_USAGE: false
```

---

## USAGE PROTOCOL (run every loop, before anything else)

```bash
# Check approximate context pressure — if this session has already done 2+ tasks,
# set PAUSED_FOR_USAGE: true in LOOP STATE and stop. User will restart.
# There is no programmatic usage API — use judgment: if you are in loop 3+ and
# the conversation is long, update LOOP STATE and stop cleanly.
```

Rule: **one atomic task per loop tick**. Do the task, run the audit command, update LOOP STATE, stop. Never chain two tasks in one tick.

---

## LOOP 1 — Wire the Engine

**Goal:** The worker process runs unattended, polls the job queue, dispatches to existing scripts, pauses at CAPTCHA, resumes from cockpit signal. Docker-compose starts everything with `./start.sh`.

**Done when:** `python scripts/worker.py --dry-run` exits 0 and prints "would dispatch N jobs". One real job transitions state in DB without human hand-holding.

---

### Task 1a — Audit the job tables

**What:** Check if `import_jobs` (migration 044) and `igr_registration_search_jobs` (migration 047) overlap in purpose. If yes, decide which one the worker polls. Wrong choice here breaks everything downstream.

**Audit cmd:**
```bash
# Run via docker exec or direct psql
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c "
  SELECT table_name, COUNT(*) as row_count
  FROM information_schema.tables t
  LEFT JOIN (
    SELECT 'import_jobs' as tbl, COUNT(*) FROM import_jobs
    UNION ALL
    SELECT 'igr_registration_search_jobs', COUNT(*) FROM igr_registration_search_jobs
  ) c ON t.table_name = c.tbl
  WHERE t.table_name IN ('import_jobs','igr_registration_search_jobs')
  GROUP BY table_name;
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name='import_jobs' ORDER BY ordinal_position;
"
```

**Done when:** Decision logged here → update LOOP STATE with which table the worker will use.

**Known issue:** migration 044 (`import_jobs`) may be generic; migration 047 (`igr_registration_search_jobs`) is IGR-specific with correct states. Likely use 047 for IGR capture loop, 044 for future generic jobs. Confirm before writing worker.

---

### Task 1b — Write `scripts/worker.py`

**What:** Minimal poll loop. Reads `igr_registration_search_jobs` where `job_status='queued'`, dispatches to the right script, updates status. No new dependencies — stdlib + psycopg2 (already used by other scripts).

**Structure:**
```python
# worker.py — poll loop for igr_registration_search_jobs
# states: planned → queued → running → captcha_required → captured → parse_pending → parsed | error | no_results

JOB_DISPATCH = {
    "search_capture": "fetch_igr_esearch_playwright.py",
    "index2_fetch":   "fetch_igr_esearch_playwright.py",   # TODO: dedicated script (Loop 2)
    "parse_results":  "parse_igr_results_to_staging.py",
    "parse_index2":   "parse_igr_index2_pdfs.py",
}

# ponytail: polling, not LISTEN/NOTIFY — upgrade if <5s latency matters
while True:
    job = claim_next_job(conn)           # FOR UPDATE SKIP LOCKED
    if not job: time.sleep(30); continue
    if job["job_status"] == "captcha_required":
        time.sleep(30); continue         # wait for cockpit to flip status back to queued
    dispatch(job)
```

**Audit cmd:**
```bash
python scripts/worker.py --dry-run
# Expected: prints queued jobs, exits 0, touches nothing
```

**Done when:** `--dry-run` passes. Real run transitions one `planned→queued→running` job.

---

### Task 1c — Add worker to docker-compose

**What:** Add `worker:` service to `docker/docker-compose.yml`. Python image, mounts `../scripts`, runs `worker.py`. Depends on postgres health check.

```yaml
worker:
  image: python:3.11-slim
  container_name: realdeal-worker
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
  environment:
    POSTGRES_HOST: postgres
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - ../scripts:/app/scripts:ro
    - ../exports:/app/exports
  working_dir: /app
  command: python scripts/worker.py
```

**Audit cmd:**
```bash
./start.sh && docker ps | grep realdeal-worker
# Expected: worker container running
docker logs realdeal-worker --tail 20
# Expected: "worker started, polling igr_registration_search_jobs"
```

**Done when:** `./start.sh` brings up worker without errors. Loop 1 complete.

---

### Task 1d — Cockpit CAPTCHA resume

**What:** Add one button in the cockpit outreach or building page: "Mark CAPTCHA solved" → calls a server action → sets job `job_status='queued'` for the paused job. Worker auto-resumes on next poll.

**File:** `web/src/app/cockpit/buildings/[id]/page.tsx` or a new `/cockpit/jobs` page.

**Audit cmd:**
```bash
# Manually set a job to captcha_required, click the button, check DB
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT id, job_status, updated_at FROM igr_registration_search_jobs ORDER BY updated_at DESC LIMIT 3;"
```

**Done when:** Clicking the button transitions `captcha_required → queued` in DB. Worker picks it up within 30s.

---

## LOOP 2 — Close the Index II Gap

**Goal:** Given a doc_no from a staged search result row, the system can fetch the Index II from freeigrsearch, save the snapshot, and auto-queue parsing.

**Done when:** One real Index II document flows from `doc_no` in `unit_registration_records` → snapshot saved under `exports/igr_snapshots/` → parsed → `unit_registration_parties` populated.

**Prerequisite:** Loop 1 complete (worker running).

---

### Task 2a — Audit existing fetch scripts for Index II support

**What:** Check `fetch_igr_esearch_playwright.py` — does it support navigating to a specific doc_no on freeigrsearch, or only list/search views? If not, create `fetch_igr_index2_playwright.py` as a thin wrapper.

**Audit cmd:**
```bash
grep -n "doc_no\|index.2\|documentnumber" scripts/fetch_igr_esearch_playwright.py | head -20
```

**Done when:** Confirmed yes/no. If no, new script spec added here.

---

### Task 2b — Wire doc_no → job queue

**What:** After `parse_igr_results_to_staging.py` runs, any row with `index2_fetch_status='pending'` and a known `doc_no` should auto-create an `igr_registration_search_jobs` row with `job_type='index2_fetch'`.

Can be a small SQL function or added as a post-parse step in the parser script itself.

**Audit cmd:**
```bash
# After running parse_igr_results_to_staging.py on a real file:
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT job_type, job_status, COUNT(*) FROM igr_registration_search_jobs GROUP BY 1,2;"
```

**Done when:** Each unprocessed doc_no has a corresponding queued job.

---

## LOOP 3 — Unit Normalizer

**Goal:** `A-1003 Kalpataru Radiance` → `{wing:A, floor:10, stack:03, confidence:high}` reliably for 80%+ of Kalpataru Wing A-Ora staged records. Low-confidence → review queue.

**Done when:** All 12 Wing A-Ora records have `unit_id` populated or are in `unit_registration_review_items`.

**Prerequisite:** Loop 1 complete.

---

### Task 3a — Audit existing unit parsing

**What:** Check `parse_kalpataru_radiance_xls_timeline.py` and `stage_kalpataru_new_parser_registry.py` — what unit normalization do they already do? Avoid rewriting what works.

**Audit cmd:**
```bash
grep -n "wing\|floor\|stack\|unit_number\|normalize" scripts/parse_kalpataru_radiance_xls_timeline.py | head -30
grep -n "wing\|floor\|stack\|unit_number\|normalize" scripts/stage_kalpataru_new_parser_registry.py | head -30
```

**Done when:** Existing coverage mapped. Only write new code for the gap.

---

### Task 3b — Unit normalizer function

**What:** `normalize_unit_label("A-1003 Kalpataru Radiance") → {wing, floor, stack, confidence}`. Regex-first. If `building_tower_structure` has the wing/floor data, cross-check and boost confidence.

Lives in `scripts/_unit_normalize.py` (shared util, imported by parsers).

```python
import re

PATTERNS = [
    r'(?P<wing>[A-Z])[- ](?P<flat>\d{3,4})',   # A-1003, A 1003
    r'(?P<wing>[A-Z]) [Ww]ing.*?(?P<flat>\d{3,4})',
    r'[Ff]lat [Nn]o\.?\s*(?P<flat>\d{3,4})',
]

def normalize_unit_label(raw: str) -> dict:
    for pat in PATTERNS:
        m = re.search(pat, raw)
        if m:
            flat = m.group('flat')
            wing = m.groupdict().get('wing')
            floor = int(flat[:-2]) if len(flat) == 4 else int(flat[:-2])
            stack = int(flat[-2:])
            return {'wing': wing, 'floor': floor, 'stack': stack, 'confidence': 'high' if wing else 'medium'}
    return {'wing': None, 'floor': None, 'stack': None, 'confidence': 'low'}
```

**Audit cmd:**
```bash
python -c "
from scripts._unit_normalize import normalize_unit_label
cases = ['A-1003','A 1003 Kalpataru Radiance','Flat No 1203','C-2605','A wing 1001']
for c in cases: print(c, '->', normalize_unit_label(c))
"
# Expected: all 5 cases parse with correct wing/floor/stack or confidence:low
```

**Done when:** All 5 test cases parse correctly.

---

## DEFERRED (do not touch until gates met)

| Feature | Gate |
|---|---|
| SEO content agent | 50+ verified facts per building |
| Contact outreach automation | 10+ units with active tenancy timeline |
| Meta custom audiences | Consent framework reviewed by operator |
| Video generation | At least 1 building page live and ranking |
| LangGraph / agent framework | Multi-step reasoning chain needed that survives restarts |
| Legal case research (Manupatra) | RERA complaint IDs confirmed per building |
| n8n complex workflows | Simple cron trigger working first |

---

## KNOWN SCRIPT ISSUES (update as found)

| Script | Issue | Status |
|---|---|---|
| `parse_kalpataru_radiance_xls_timeline.py` | May mis-parse Marathi names in Devanagari-adjacent encoding | unverified |
| `parse_igr_index2_pdfs.py` | PDF Devanagari visual-order matra scramble (skeleton-match workaround exists) | partially fixed (Phase 6.20) |
| `fetch_igr_esearch_playwright.py` | Single-session only, no retry on server down | known gap |
| `worker.py` | Uses _db.py (docker exec) so cannot run inside Docker; host-only. Upgrade: psycopg2 direct TCP when containerization needed | known, accepted |
| `stage_kalpataru_new_parser_registry.py` | May duplicate records on re-run | unverified |

---

## QUICK REFERENCE

```bash
# Start everything
./start.sh

# Check DB tables
bash scripts/check_db.sh

# Apply a migration
bash scripts/apply_schema.sh schemas/047_unit_registration_foundation.sql

# Run a script
python scripts/<name>.py --help

# Worker logs (once added)
docker logs realdeal-worker --tail 50 -f
```

---

## KALPATARU RADIANCE — SOURCE FILES (ground truth)

### IGR Registrations (CTS 260/5A, Pahadi village)
```
imports/igr Registrations/plot 260 /   ← TRAILING SPACE in dirname — use exact path
  SearchResult1.xls          24KB    likely small/recent query
  SearchResult2.xls         1.2MB    full CTS 260 registrations (primary source)
  SearchResult3.xls + (1-3)  ~900KB  page-2 and filtered results
  SearchResult4 (1-8).xls    small   specific unit/party lookups (Index II targets)
```
Access: `cd "imports/igr Registrations/" && ls "plot 260 "` (note the space)

### Brochure (wing structure, unit plans, amenities)
```
imports/buildings/Kalpataru Radiance Brochure/brochure kalpataru .pdf
```
Wing names (from brochure cover):
| Wing | Name       | RERA reg         | Apts/floor | Notes |
|------|------------|------------------|------------|-------|
| A    | ORA        | P51800000591     | 5          | 2/3/4BHK residential |
| B    | BRILLIANCE | P51800000810     | 5+         | 3BHK residential |
| C    | ALLURA     | P51800000482     | TBD        | residential |
| D    | LUMINA     | P51800000579     | TBD        | residential |
| E    | (shops)    | P51800013245     | N/A        | ground floor retail only — NOT residential |

IGR wing_text canonical: "Wing A-Ora", "Wing B-Brilliance", "Wing C-Allura", "Wing D-Lumina"
Short variants in DB: "A","B","C","D" (older imports — Wing E / Patra Chawl rows handled separately)

Unit numbering: `{floor}{apt:02d}` → Floor 1, Apt 1 = "101"; Floor 10, Apt 1 = "1001"
Wing A apt types: Apt1=2BHK, Apt2=4BHK, Apt3=4BHK, Apt4=4BHK, Apt5=3BHK
Complex layout: A=NW, B=NE, C=SW, D=SE. Fronts 13.40m road on both N and S.

### MahaRERA
```
imports/mahaRera/Kalpataru Radiance Maharashtra Real Estate Regulatory Authority.pdf
imports/mahaRera/Maharashtra Real Estate Regulatory Authority.pdf   ← general/index
```

### Known data quality issues (from import analysis)
- `building_units` has two unit_number formats: IGR-seeded (`{floor}{apt:02d}` = "101","1001") vs registry-seeded (`{floor}{apt}` = "22","182") — need normalization pass before join is reliable
- `building_units.wing` uses full label "KALPATARU RADIANCE  A" not just "A" — fixed in `link_units_to_building_units.py` via `RIGHT(TRIM(bu.wing),1)`
- Dir name `plot 260 ` has trailing space — macOS Finder hides files; scripts must use exact literal path

---

## LOOP 4 — Single canonical Kalpataru + clean unit data

**Goal:** 1 building row, clean building_units (no duplicate wing labels), all parseable reg records linked. System testable against brochure ground truth.

**Done when:** `SELECT COUNT(*) FROM buildings WHERE name ILIKE '%kalpataru%'` = 1. All 1731 reg records on `f63d75ab`. 58 linkable records applied.

---

### Task 4a — XLS overlap check (read-only)

**What:** How much of the XLS data is already in the DB? Count distinct `doc_number` in `unit_registration_records` for `f63d75ab` vs row count in SearchResult2.xls. If >90% overlap → skip re-parse, go 4b. If <90% → re-parse in 4e.

**Audit cmd:**
```bash
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT COUNT(DISTINCT doc_number) FROM unit_registration_records WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283' AND doc_number IS NOT NULL;"
python3 -c "
import xlrd, pathlib
wb = xlrd.open_workbook(\"imports/igr Registrations/plot 260 /SearchResult2.xls\")
print('rows:', wb.sheet_by_index(0).nrows)
"
```

**Done when:** overlap % logged in LAST_DONE.

---

### Task 4b — Consolidate to 1 building (guarded, --apply gated)

**What:** Write `scripts/consolidate_kalpataru_buildings.py`. Dry-run by default.
Steps:
1. Re-point `bb53ca24`'s 1 reg record → `f63d75ab`
2. Check if any `building_unit_id` on reg records points to the 11 short-label units in `f63d75ab` (wing IN ('A','B','C','D') short form) → if yes, re-point to matching long-label unit
3. DELETE 11 short-label `building_units` rows from `f63d75ab`
4. DELETE `bb53ca24`'s 702 `building_units`
5. DELETE buildings `bb53ca24` + `8272dc3e`

**Audit cmd:**
```bash
python scripts/consolidate_kalpataru_buildings.py  # dry-run
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT name, COUNT(bu.id) as units FROM buildings b LEFT JOIN building_units bu ON bu.building_id=b.id WHERE b.name ILIKE '%kalpataru%' GROUP BY b.name;"
```
**Done when:** 1 Kalpataru building row, 956 units.

---

### Task 4c — Apply unit links

**What:** Run the wing-join-fixed linker.
```bash
python scripts/link_units_to_building_units.py --apply
```
**Audit cmd:**
```bash
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT COUNT(*) FROM unit_registration_records WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283' AND building_unit_id IS NOT NULL;"
```
**Done when:** linked count increases by ~58 from baseline 1014.

---

### Task 4d — Triage 169 duplicate_doc_number records

**What:** Check if duplicates are true multi-property docs (same doc_no, different units — valid in IGR) or import noise (same doc_no + same property_description_raw).
```bash
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c "
SELECT doc_number, COUNT(*), COUNT(DISTINCT property_description_raw) as distinct_props
FROM unit_registration_records
WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283'
  AND verification_status='duplicate_doc_number'
GROUP BY doc_number ORDER BY COUNT(*) DESC LIMIT 10;"
```
**Done when:** decision logged — how many to promote to `parsed_candidate`, how many to discard.

---

### Task 4e — Re-parse XLS only if 4a shows gap > 10%

**What:** Run `parse_kalpataru_radiance_xls_timeline.py` on all 13 XLS files. `--dry-run` first, then `--apply`.
XLS dir: `imports/igr Registrations/plot 260 /` (trailing space in name)

**Skip if:** 4a shows >90% overlap already in DB.

---

---

## LOOP 5 — Clean candidate pool + first real worker run

**Goal:** `duplicate_doc_number` rows promoted/discarded; at least one `igr_registration_search_jobs` row transitions `queued → captured` via the worker unattended.

**Done when:** `verification_status='duplicate_doc_number'` count ≤ 2 on `f63d75ab`. One job in `captured` state with a real snapshot on disk.

---

### Task 5a — Promote stale duplicate flags

**What:** Write `scripts/promote_duplicate_doc_records.py` (dry-run default, `--apply` gated).
- Singles (153): `UPDATE … SET verification_status='parsed_candidate'` where doc_number appears exactly once for this building.
- Valid pairs (~6): both rows → `parsed_candidate`.
- Noise pairs (~2): keep whichever has `building_unit_id IS NOT NULL` (or higher id as tiebreak) → `parsed_candidate`; other → `discarded`.

**Audit cmd:**
```bash
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT verification_status, COUNT(*) FROM unit_registration_records WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283' GROUP BY 1 ORDER BY 2 DESC;"
```
**Expected:** `duplicate_doc_number` → ~2 rows; `parsed_candidate` increases by ~167.

---

### Task 5b — First real worker end-to-end

**What:** Verify `worker.py --dry-run` shows a queued job, then run one job live. Confirm DB state transition and snapshot on disk.

**Audit cmd:**
```bash
python scripts/worker.py --dry-run
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "SELECT job_type, job_status, COUNT(*) FROM igr_registration_search_jobs GROUP BY 1,2 ORDER BY 1,2;"
```
**Expected:** at least 1 row in `captured` or `parse_pending` after a real run.

---

---

## LOOP 6 — Tenancy Index II acquisition (repeat until all 180 records have rent data)

**Goal:** All 180 Kalpataru tenancy records have `tenancy_monthly_rent`, `tenancy_start_date`, `tenancy_end_date`, `tenancy_deposit` populated. Each year requires one headed Playwright session + CAPTCHA solve.

**Done when:**
```sql
SELECT COUNT(*) FROM unit_registration_records
WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283'
  AND transaction_category='tenancy'
  AND tenancy_monthly_rent IS NULL;
```
= 0 (or operator accepts residual for docs without rent amounts, e.g. error corrections)

**Gap summary (as of 2026-06-23):**
| Year | Total | Has rent | Source |
|------|-------|----------|--------|
| 2023 | 2 | 0 | XLS |
| 2024 | 58 | 1 | XLS (no description text) |
| 2025 | 70 | 0 | XLS (no description text) |
| 2026 | 50 | 23 | XLS + eSearch results |

---

### Task 6a — Queue capture jobs for missing years

```bash
python scripts/queue_tenancy_index2_jobs.py          # dry run — shows years to queue
python scripts/queue_tenancy_index2_jobs.py --apply  # write planned jobs
```
Script auto-skips years that already have a non-error job.

---

### Task 6b — Operator: capture each year (one session per year)

For each planned job (run per year, one CAPTCHA session each):
```bash
python scripts/fetch_igr_esearch_playwright.py \
  --output-label kalpataru-260_5A-{YEAR} \
  --year {YEAR} --district 'Mumbai Suburban' --village 'pahadi goregaon' \
  --cts '260/5A' --building-label 'Kalpataru Radiance' \
  --save-html --save-visible-text --max-captures 20 --apply
```
After capture completes:
```bash
# Advance the job to captured so the worker can parse it
docker exec realdeal-postgres psql -U realdeal_admin -d realdeal_os -c \
  "UPDATE igr_registration_search_jobs SET job_status='captured',
   snapshot_path='exports/igr_snapshots/{SNAPSHOT_FOLDER}', updated_at=now()
   WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283'
   AND search_year={YEAR} AND job_status='planned';"
python scripts/worker.py
```

**What to do during the headed session:**
1. Fill Year + District (Mumbai Suburban) + Village (pahadi goregaon) + Property No (260/5A)
2. Solve CAPTCHA when it appears — script pauses automatically
3. After results load, the script captures the results list
4. Click each **IndexII** link for tenancy/Leave&License rows — script captures each popup
5. Hit Enter in terminal after each capture to continue to next IndexII
6. Type `done` when finished with all IndexII links for that year

---

### Task 6c — Parse and verify (after each capture)

```bash
python scripts/worker.py   # processes the captured snapshot → populates tenancy fields
```

Audit after each year:
```sql
SELECT registration_year,
       COUNT(*) as total,
       COUNT(tenancy_monthly_rent) as has_rent,
       COUNT(tenancy_start_date) as has_start
FROM unit_registration_records
WHERE building_id='f63d75ab-2ef9-48a9-afe2-cab3c4283283'
  AND transaction_category='tenancy'
GROUP BY 1 ORDER BY 1;
```

**Loop until all years hit `has_rent = total`.** Stragglers (docs with no rent amount in Index II, e.g. error-correction docs) → mark `tenancy_monthly_rent = 0` manually after operator review.

---

### Task 6d — Document search fallback (for individual missed docs)

If after all property-search captures some docs still have no rent:
```bash
# Search by individual document number on freesearchigrservice.maharashtra.gov.in
# Tab: दस्त निहाय/Document Number
# Inputs: Year + SRO Code + Document Number
# Capture: python scripts/fetch_igr_esearch_playwright.py --url <doc-search-url> ...
```
Then run worker to parse.

---

<!-- UPDATE ONLY THE LOOP STATE BLOCK EACH TICK. Do not rewrite this document. -->
