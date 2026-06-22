# QA Report — Loop 28
**Date:** 2026-06-22  
**Branch:** qa/full-stack-test-hardening  
**Coverage area:** updateReviewItem validation + outreach empty state + contact timeline + Owners tab real data

---

## Commands Run

```
# Baseline
python3 -m pytest tests/python/ -q              # 111 passed
cd web && npm test                               # 301 passed (Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 177 passed

# After Loop 28 additions
npm test                                         # 310 passed (+9 Vitest)
COCKPIT_AUTH_TOKEN=... npx playwright test       # 182 passed (+5 Playwright)

# Final full suite
python3 -m pytest tests/python/ -q              # 111 passed
npm test                                         # 310 passed
COCKPIT_AUTH_TOKEN=... npx playwright test       # 182 passed
Total: 603
```

---

## Files Changed

| File | Type | Notes |
|---|---|---|
| `web/src/__tests__/db.test.ts` | MODIFIED | +9 tests: updateReviewItem validation mirror (UUID / ALLOWED_STATUSES / reviewedBy guards) |
| `web/src/__tests__/e2e/cockpit-pages.spec.ts` | MODIFIED | +5 tests: outreach empty state (2) + contact timeline (1) + Kalpataru Owners tab (2) |

---

## Tests Passing

| Suite | Pass | Fail | Total |
|---|---|---|---|
| Python — all suites | 111 | 0 | 111 |
| TypeScript Vitest | 310 | 0 | 310 |
| Playwright E2E | 182 | 0 | 182 |
| **Grand total** | **603** | **0** | **603** |

---

## AUDIT findings this loop

### 1. `updateReviewItem` — 3 validation guards, zero tests (GAP — CLOSED)

Guards in `actions.ts`:
1. `UUID_RE.test(input.reviewItemId)` — "Invalid review item id." on fail
2. `ALLOWED_STATUSES.has(input.status)` — "Invalid status: ${status}" on fail (6 allowed values)
3. `(input.reviewedBy || "").trim()` non-empty check — "reviewedBy is required." on fail

Added 9 mirror tests covering: valid input, UUID rejection, SQL injection rejection, all 6 statuses individually, unknown status, empty status, empty/whitespace reviewedBy, whitespace-trimming that passes.

### 2. Outreach queue empty state — silently skipped (GAP — CLOSED)

The `wa.me` link test had `if (count === 0) return` — never explicitly verified the empty-state message. Added 2 Playwright tests that assert: queue section always shows EITHER `wa.me` rows OR "No contacts queued for today" message, and "Today's send queue" panel title is always visible.

### 3. Contact detail activity timeline empty state (GAP — CLOSED)

"No interactions recorded yet." was tested in the outreach page context but not on the contact detail page. Added 1 test that covers both the events-present and events-absent paths on `/cockpit/contacts/c/[id]`.

### 4. Kalpataru Owners tab real data count (GAP — CLOSED)

The existing "clicking Owners tab" test only checked `count() > 0` on generic `h2/p/li`. Added 2 tests:
1. Tab renders without error or crash
2. "Owners & tenants" Overview stat tile is `> 0` for Kalpataru (which has 22 IGR-matched owner contacts via `registration_party_contact_matches`)

---

## Recommended Next QA Loop (Priority Order)

**1. `sanitiseQ` 101-char edge** — the truncation happens BEFORE NUL strip, so a 101-char string with a NUL byte at position 100 gets trimmed then NUL-stripped. One test to confirm order of operations (slice → NUL strip → trim).

**2. `recordOutreachActivity` `by` field validation** — `by` defaults to "director" and is capped to 100 chars. Currently: only OUTREACH_ACTIONS and UUID are tested. The `by` clamp is untested.

**3. Buildings workspace — Campaigns tab row count** — DLF has 10 channels. No test asserts the channels list is non-empty for DLF or that each channel shows a name.

**4. Buildings workspace — Website tab staging site URL** — `getWebsitePages` returns a staging URL for DLF. No test checks the URL is a valid `*.wixstudio.com` or similar link.

**5. Buildings workspace — RERA tab fact count** — For Imperial Heights, the RERA tab shows matched facts from migration 020. No test counts the RERA rows; only "RERA" heading visibility is checked.
