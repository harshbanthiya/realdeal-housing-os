# QA Report — Loop 26
**Date:** 2026-06-22  
**Branch:** qa/full-stack-test-hardening  
**Coverage area:** `batchLabelHuman` UI bug fix + `parseLabeledOutput`/`headline` logic-mirror tests + flaky Leads test hardening

---

## Commands Run

```
# Baseline
python3 -m pytest tests/python/ -q              # 111 passed
cd web && npm test                               # 212 passed (Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 172/173 passed (1 flaky: Leads tab)

# After Loop 26 changes
npm test                                         # 226 passed (+14 Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 173 passed (flaky Leads test fixed)

# Final full suite
python3 -m pytest tests/python/ -q              # 111 passed
npm test                                         # 226 passed
COCKPIT_AUTH_TOKEN=... npx playwright test       # 173 passed
Total: 510
```

---

## Files Changed

| File | Type | Notes |
|---|---|---|
| `web/src/lib/cockpit/contacts-types.ts` | MODIFIED | Fix `batchLabelHuman`: add `.toLowerCase()` before title-casing; all-caps DB labels now render as Title Case in UI |
| `web/src/__tests__/db.test.ts` | MODIFIED | Update 4 stale test expectations (CAPS→Title Case); +7 `parseLabeledOutput` tests; +7 `headline` tests |
| `web/src/__tests__/e2e/cockpit-pages.spec.ts` | MODIFIED | Leads flaky test: add `test.setTimeout(30000)` + `waitForLoadState("networkidle")` |
| `scripts/cleanup_fake_*.py` (6 files) | DELETED | Deletions committed — these were deleted on disk in Loop 25's `_db.py` refactor but not staged |

---

## Tests Passing

| Suite | Pass | Fail | Total |
|---|---|---|---|
| Python — all suites | 111 | 0 | 111 |
| TypeScript Vitest | 226 | 0 | 226 |
| Playwright E2E | 173 | 0 | 173 |
| **Grand total** | **510** | **0** | **510** |

---

## AUDIT findings this loop

### 1. `batchLabelHuman` produces ALL-CAPS output for real DB batch labels (BUG — FIXED)

`batchLabelHuman` in `contacts-types.ts` used `\b\w → toUpperCase` (title-case pattern) but never called `.toLowerCase()` first. Real DB batch labels are uppercase (`REAL_IMPERIAL_HEIGHTS_OWNERS`) so the output was `IMPERIAL HEIGHTS OWNERS` instead of the intended `Imperial Heights Owners`.

**Fix:** Added `.toLowerCase()` before the title-case step.

**Impact:** 3 UI callers:
- `web/src/app/cockpit/contacts/page.tsx:102` — import batch list title
- `web/src/lib/cockpit/contacts.ts:250` — kanban card secondary text
- `web/src/components/cockpit/merge-candidate-card.tsx:44` — "from BATCH_LABEL" text

**Tests:** Updated 4 existing test expectations from CAPS to Title Case.

### 2. `parseLabeledOutput` and `headline` — zero unit tests (LOW-MEDIUM GAP — CLOSED)

Both are private helpers in `actions.ts` (`"use server"`) called multiple times (`parseLabeledOutput` × 6, `headline` × 4). Added as pure logic-mirror suites in `db.test.ts`.

**`parseLabeledOutput` (7 tests):** single line, multiple lines, uppercase-key rejection, no-separator rejection, value with spaces, empty input, last-duplicate-wins.

**`headline` (7 tests):** first non-SQL line, INSERT skip, all-SQL fallback to first line, plain output, whitespace trimming, empty input.

### 3. Leads flaky test (RECURRING FLAKE — HARDENED)

DLF building workspace page runs 11 parallel SSR queries. Even at `timeout: 15000`, the `toBeVisible` check was failing because hydration wasn't complete. Fixed by:
- `test.setTimeout(30000)` scoped to just this test
- `waitForLoadState("networkidle", { timeout: 20000 })` after `page.goto` to ensure all SSR data fetches complete before clicking

### 4. Uncommitted script deletions from Loop 25 (REPO HYGIENE — FIXED)

6 `scripts/cleanup_fake_*.py` files were deleted on disk as part of the Loop 25 `_db.py` refactor but the deletions weren't staged in commit `e8bfd30`. Included in this loop's commit.

---

## Recommended Next QA Loop (Priority Order)

**1. Contact sheet pagination edge cases** — `page=999` (0 rows) and `page=0` (clamped to 1) are correct but untested. Quick Vitest assertion on `getContactSheet` clamping logic.

**2. Audiences page filter role submission** — No test verifies that applying a role filter changes the audience size metric in response.

**3. Contact detail group dropdown show/hide** — No test for "no groups → dropdown hidden, has groups → dropdown visible" state machine (only the "has groups" path is covered).

**4. WhatsApp send gate** — `send_enabled=false` is the hard gate. No test asserts the "Open in WhatsApp" links are present but the queue-send script enforces the flag. Worth one Playwright assertion that "Open in WhatsApp" link exists in the queue row.
