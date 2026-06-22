# QA Report — Loop 24
**Date:** 2026-06-22  
**Branch:** qa/full-stack-test-hardening  
**Coverage area:** `agentLabel` / `buildingFromRaw` / `taskTone` unit tests + home dashboard panel Playwright tests

---

## Commands Run

```
# Baseline
python3 -m pytest tests/python/ -q              # 111 passed
npx vitest run                                   # 170 passed
COCKPIT_AUTH_TOKEN=... npx playwright test       # 159 passed (pre-loop)

# After export fix + 19 new Vitest tests (agentLabel + buildingFromRaw + taskTone)
npx vitest run                                   # 189 passed ✓

# After 11 new Playwright tests (home dashboard panels) + timeout hardening
COCKPIT_AUTH_TOKEN=... npx playwright test       # 170 passed ✓

# Final full suite
python3 -m pytest tests/python/ -q              # 111 passed
npx vitest run                                   # 189 passed
COCKPIT_AUTH_TOKEN=... npx playwright test       # 170 passed
```

---

## Files Changed

| File | Type | Notes |
|---|---|---|
| `web/src/lib/cockpit/data.ts` | MODIFIED | `export` added to `agentLabel`, `buildingFromRaw`, `taskTone` (no behavioral change) |
| `web/src/__tests__/db.test.ts` | MODIFIED | 19 new tests: 5 `agentLabel` + 5 `buildingFromRaw` + 9 `taskTone` → 189 total |
| `web/src/__tests__/e2e/cockpit-pages.spec.ts` | MODIFIED | 11 new home dashboard panel tests + timeout 5000→10000 for pre-existing flaky Leads test → 170 total |
| `logs/audit-report.md` | MODIFIED | Loop 24 findings appended |

---

## Tests Passing

| Suite | Pass | Fail | Total |
|---|---|---|---|
| Python — all suites | 111 | 0 | 111 |
| TypeScript Vitest | 189 | 0 | 189 |
| Playwright E2E | 170 | 0 | 170 |
| **Grand total** | **470** | **0** | **470** |

---

## AUDIT findings this loop

### `agentLabel` / `buildingFromRaw` / `taskTone` — private helpers with zero unit tests (MEDIUM GAP) — CLOSED

**Finding:** All three are pure deterministic functions used in `getAgentActivity()` and `getGlobalBlockers()`. They were private (no `export`) so Vitest couldn't import them directly. Zero tests.

**Fix:** Added `export` to all three function declarations in `data.ts` (one-word change each, no behavioral change).

**Tests added (19):**
- `agentLabel` (5): single underscore word, multi-segment, already titled, empty string fallback, single word
- `buildingFromRaw` (5): null input, building_name present, prefers building_name over launch_key, title-cases launch_key fallback, empty object
- `taskTone` (9): completed/done→ready, running/in_progress→review, failed/error→blocked, queued/pending/empty→neutral

### Home dashboard panels — zero Playwright coverage (MEDIUM GAP) — CLOSED

**Finding:** The home dashboard (`/cockpit`) had only 4 tests covering the Launch readiness streams. The Buildings list, portfolio summary line, Needs review panel, Blockers panel, and Agents panel had zero test coverage.

**Tests added (11):**
- Portfolio summary shows building count (regex `/\d+ buildings/`)
- Portfolio summary shows `1 in launch`
- Buildings panel heading visible
- At least one building card links to `/cockpit/buildings/[slug]`
- DLF Westpark card present (`.first()` to avoid strict mode violation)
- Needs review heading via `getByRole("heading")`
- Needs review shows at least one `ul li`
- Blockers heading via `getByRole("heading")`
- BLK-xxx IDs present (`.first()` to avoid strict mode violation)
- Agents heading via `getByRole("heading")`
- Agents `ul li` always has at least one row (real tasks or fallback)

### Pre-existing flaky test hardened

**Finding:** "Leads tab on launch building shows pre-launch interest message" was failing intermittently in the full suite (5000ms timeout too tight after 11 new home dashboard tests added ~8s to suite). Passed in isolation.

**Fix:** Timeout 5000ms → 10000ms. Not a weakened assertion — same check, more buffer for full-suite server load.

---

## Recommended Next QA Loop (Priority Order)

**1. `createContactGroup` + `addContactsToGroup` validation guard unit tests** — early-return paths (invalid slug, empty IDs, name too short/long) are untested. Server actions with `"use server"` directive; test the validation logic as inline pure functions mirroring the guard expressions.

**2. `buildWhere()` filter safety** — private function in `audiences.ts`. Parameterized query approach can be tested indirectly via `parseAudienceFilters` + `getAudienceSummary` with special-char building names. Low risk since it uses `$N` params.

**3. `parseLabeledOutput()` helper** — private, parses key: value lines from script stdout. Could be tested by checking `fields` in ActionResult from a script invocation.

**4. Contact sheet pagination edge cases** — no test for `page=999` (beyond end) or `page=0` (invalid).

**5. Building card stat tiles** — Playwright test that navigates to a building card and verifies the stats grid (people/leads/listings/reviews tiles) renders four cells.
