# Real Deal Housing OS — Build Loop

<!-- Claude: READ THIS FIRST. ~200 tokens. Do not read anything else until you've checked LOOP STATE. -->

## LOOP STATE

```
CURRENT_LOOP:   3
CURRENT_TASK:   done
STATUS:         done
LAST_DONE:      3c DONE — root cause was wing join: bu.wing='KALPATARU RADIANCE  D' vs extracted 'D'. Fixed with RIGHT(TRIM(bu.wing),1). Audit now shows 58 linkable records (up from 0). Script correct. Run with --apply to write.
NEXT_ACTION:    LOOP 3 COMPLETE. Commit all Loop 1-3 scripts (worker.py, fetch_igr_index2_playwright.py, seed_index2_fetch_queue.py, link_units_to_building_units.py, cockpit jobs/page.tsx, actions.ts). Then optionally run link script --apply to link 58 records.
BLOCKED_BY:     —
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
| Wing | Name       | RERA reg         | Apts/floor |
|------|------------|------------------|------------|
| A    | ORA        | P51800000591     | 5          |
| B    | BRILLIANCE | P51800000810     | 5+         |
| C    | —          | P51800000482     | TBD        |
| D    | —          | P51800000579     | TBD        |
| E    | —          | P51800013245     | TBD (separate phase) |

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

<!-- UPDATE ONLY THE LOOP STATE BLOCK EACH TICK. Do not rewrite this document. -->
