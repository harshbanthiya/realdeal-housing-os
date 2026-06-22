# QA Report — Loop 27
**Date:** 2026-06-22  
**Branch:** qa/full-stack-test-hardening  
**Coverage area:** contacts-types.ts pure functions + sheet/action validation mirrors + audiences metrics + unit registry Playwright

---

## Commands Run

```
# Baseline
python3 -m pytest tests/python/ -q              # 111 passed
cd web && npm test                               # 226 passed (Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 173 passed

# After Loop 27 additions
npm test                                         # 301 passed (+75 Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 177 passed (+4 Playwright)

# Final full suite
python3 -m pytest tests/python/ -q              # 111 passed
npm test                                         # 301 passed
COCKPIT_AUTH_TOKEN=... npx playwright test       # 177 passed
Total: 589
```

---

## Files Changed

| File | Type | Notes |
|---|---|---|
| `web/src/__tests__/db.test.ts` | MODIFIED | +75 tests: statusTone(8) + strengthTone(4) + roleLabel(8) + reviewTypeLabel(4) + statusLabel(8) + pagination mirrors(17) + limit clamp(6) + groupSlug(6) + UUID_RE(6) + action allowlist(8) |
| `web/src/__tests__/e2e/cockpit-pages.spec.ts` | MODIFIED | +4 tests: audiences metric grid values(1) + role filter render(1) + Kalpataru unit stats(1) + DLF unit registry clean(1) |

---

## Tests Passing

| Suite | Pass | Fail | Total |
|---|---|---|---|
| Python — all suites | 111 | 0 | 111 |
| TypeScript Vitest | 301 | 0 | 301 |
| Playwright E2E | 177 | 0 | 177 |
| **Grand total** | **589** | **0** | **589** |

---

## AUDIT findings this loop

### 1. Five pure functions in contacts-types.ts — zero unit tests (GAP — CLOSED)

`statusTone`, `strengthTone`, `roleLabel`, `reviewTypeLabel`, `statusLabel` are all called in multiple UI components with no test coverage. Added 32 tests covering all switch branches and fallbacks.

### 2. getContactSheet pagination/sort/dir clamping — zero logic tests (GAP — CLOSED)

The guards at `contacts.ts:295-298`:
- `page = Math.max(1, Math.floor(opts.page ?? 1))` — clamps page to ≥1
- `pageSize = Math.min(Math.max(opts.pageSize ?? 25, 5), 100)` — clamps to 5–100
- `sort` — whitelist check against `SHEET_SORTS` keys
- `dir` — only "asc" passes through, everything else is "desc"

Added 17 logic-mirror tests.

### 3. buildOutreachQueue / clearQueueRow / recordOutreachActivity validation — zero tests (GAP — CLOSED)

Key discovery: `Math.max(1, Math.min(50, Number(raw) || 10))` — `limit=0` produces 10, NOT 1, because `0` is falsy in the `|| 10` fallback. This is a subtle footgun documented in the test.

### 4. Audiences metric grid — metric values untested (GAP — CLOSED)

Added 2 Playwright tests: metric labels visible with integer values on page load; metric grid still renders after role filter is applied.

### 5. Unit registry stats strip for real buildings (GAP — CLOSED)

Added 2 Playwright tests: Kalpataru has real IGR registrations so the stats strip must show a number; DLF (no units) must render cleanly without error.

### 6. "no groups → dropdown hidden" — DB-state-dependent (DEFERRED)

`contact-outreach-controls.tsx:73` hides the group select when `groups.length === 0`. `getContactGroups()` returns ALL groups in the DB. Since the live DB always has groups (Test Group etc.), this state is unreachable in Playwright. Only testable in isolation (e.g., component test with mock props). Not worth mocking just to cover a CSS `{groups.length > 0 && ...}` guard.

---

## Recommended Next QA Loop (Priority Order)

**1. `q` search sanitisation edge cases** — `getContactSheet` sanitises `q` to max 100 chars, strips NUL, trims. Only the basic ILIKE pattern is tested (Loop 5). Add: NUL strip, 101-char truncation, LIKE metachar escape (`%`, `_`, `\`).

**2. `updateReviewItem` / `updateBuildingMode` validation** — `updateReviewItem` checks `ALLOWED_STATUSES` (6 values); `updateBuildingMode` checks `ALLOWED_MODES` (4 values). Both have Vitest tests but the mode/status ALLOWLIST membership isn't directly tested as its own suite.

**3. `logContactNote` note length clamp** — note is trimmed to 500 chars server-side. Test the 501-char case to confirm it's silently truncated (not rejected).

**4. Outreach page — empty queue state** — If queue is empty, an empty-state message should show. No test verifies this path.

**5. Contact detail — "In outreach" badge vs "Add to outreach" mutual exclusion** — When a contact is in the queue, "Add to outreach" should be replaced by "In outreach · status (step N)". No Playwright test verifies the mutual exclusion.
