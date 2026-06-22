# Cockpit UI Audit
**Date:** 2026-06-21  
**Branch:** qa/full-stack-test-hardening  
**Method:** source reading + live Playwright + curl probes

---

## Legend
| Symbol | Meaning |
|---|---|
| ✅ | Fully wired — renders real data, actions work end-to-end |
| ⚠️ | Partially wired — renders but some sub-elements are stubs |
| 🚧 | Stub / placeholder — UI exists, no real logic behind it |
| ❌ | Broken or missing entirely |

---

## /cockpit (home dashboard)

| Element | Status | Notes |
|---|---|---|
| Buildings list | ✅ | Reads `launch_projects` + `buildings` from DB |
| Building card → workspace link | ✅ | Routes to `/cockpit/buildings/[slug]` |
| "Needs review" panel | ✅ | Reads `launch_readiness_checks` + `rera_project_profiles` |
| "Blockers" panel | ✅ | Reads `launch_readiness_checks` where severity=blocker |
| "Agents" panel | ✅ | **FIXED Loop 13** — `getAgentActivity()` queries `ai_agent_tasks` (task_type, status, prompt_summary, raw_input JSONB); `agentLabel()`, `buildingFromRaw()`, `taskTone()` helpers. Falls back to fallback row when no tasks exist. |
| Launch readiness STREAMS | ✅ | **FIXED Loop 9** — `getStreamReadiness()` queries `launch_readiness_checks`, classifies by keyword into 4 streams, computes tone live. |
| Any clickable action | ❌ | Home page is fully read-only — no buttons at all |

---

## /cockpit/contacts (cleanup funnel)

| Element | Status | Notes |
|---|---|---|
| Cleanup funnel stats | ✅ | Reads real import_batches + review queue counts |
| Import batch list | ✅ | Real data |
| Review queue type counts | ✅ | Real data |
| MergeCandidateCard "Preview approve" | ✅ | Calls `updateReviewItem({ apply: false })` — dry-run script, shows result |
| MergeCandidateCard "Skip" | ✅ | Client-side state only, no write — correct |
| MergeCandidateCard real apply | 🚧 | `apply: false` hardcoded in component (`merge-candidate-card.tsx:29`) — apply path intentionally disabled |
| Sub-nav (Pipeline / Sheet / Contacts) | ✅ | Links work |

---

## /cockpit/contacts/pipeline (kanban)

| Element | Status | Notes |
|---|---|---|
| Kanban columns render | ✅ | 4 columns: unreviewed / reviewed / attached / canonical |
| Card count + totals | ✅ | Real data |
| Drag-and-drop cards | ❌ | No DnD library, no drag handles, cards are static divs — **by design** per footer note: "A card moves right as you approve and merge it." |
| Card click action | ✅ | **FIXED Loop 7** — canonical + attached stage cards are `<Link>` to contact detail; in_review/approved remain non-clickable (no contact UUID) |
| "+N more" overflow | ✅ | Shows count of hidden cards |

---

## /cockpit/contacts/sheet (table)

| Element | Status | Notes |
|---|---|---|
| Contact rows | ✅ | Masked canonical contacts from DB |
| Sort column headers | ✅ | URL-based sort (name/type/created/status) |
| Sort direction toggle | ✅ | asc/desc via URL param |
| Pagination prev/next | ✅ | URL-based, `page=N` |
| Row click → contact detail | ✅ | Links to `/cockpit/contacts/c/[id]` |
| Search / filter | ❌ | **Missing entirely** — no search input on sheet page |

---

## /cockpit/contacts/c/[id] (contact detail)

| Element | Status | Notes |
|---|---|---|
| Contact header (name, role, status) | ✅ | Real data, masked |
| Outreach tier pill | ✅ | hot/warm/cold/untouched/opted_out from DB |
| "do not spam" badge | ✅ | Reads from outreach activity |
| Outreach stats (sent/opens/replies) | ✅ | Real counts from DB |
| "+ Add to outreach" button | ✅ | Calls `enqueueContact({ apply: true })` — real write via script |
| "In outreach · status (step N)" badge | ✅ | Shows when contact is already in queue |
| Group select dropdown | ✅ | **Loop 21 verified** — shows groups from DB (4 in DB: Test group, Test 1, Windsor Grande, Ekta Tripolis); hidden when no groups. Tested both select visible and Add to group button co-presence. |
| "Add to group" button | ✅ | Calls `addContactsToGroup({ apply: true })` — real write |
| Contact methods list | ✅ | Masked phone/email/other |
| Building relationships | ✅ | Real unit/wing/role/status |
| Activity timeline | ✅ | Shows events if any; empty state message if none |
| "Add note" / manual activity log | ✅ | **FIXED Loop 6** — `ContactNoteForm` inside Activity timeline card; textarea with 500-char counter; ⌘↵ shortcut; `logContactNote()` server action → `add_contact_note.py`; `router.refresh()` reloads timeline on success |
| Remove from outreach | ✅ | **FIXED Loop 8** — "Remove" button alongside "In outreach" badge; calls `clearQueueRow({ queueId, apply: true })`; `router.refresh()` updates badge on success |

---

## /cockpit/buildings/[slug] (workspace)

| Element | Status | Notes |
|---|---|---|
| Building header | ✅ | Name, location, mode, launch countdown |
| Mode pill display | ✅ | Reads from DB |
| **Mode switcher buttons** | ✅ | **FIXED Loop 4 + Loop 11** — Loop 4: interactive buttons with local state; Loop 11: persists to `launch_projects.mode` via `updateBuildingMode` server action + `update_building_mode.py`; legacy buildings (no launch_project row) switch locally only |
| Tab bar (11 tabs) | ✅ | Client-side state, all tabs switch correctly |
| **Overview tab** | ✅ | Stats render — per-building counts fixed Loop 18 |
| Launch kanban (overview) | ✅ | Reads `launch_kanban_tasks` from DB; DLF shows columns + tasks; non-launch shows steady-state prose |
| Campaign calendar | ✅ | **FIXED Loop 15** — `getLaunchCalendar(slug?)` now filters by `lp.launch_key = slug` via JOIN when slug provided; falls back to global query or static items |
| **Owners tab** | ✅ | Masked owner/tenant list with unit |
| **Units tab** | ✅ | Full unit grid renders |
| Unit tower selector | ✅ | Client-side filter |
| Unit cell click → detail panel | ✅ | Opens side panel with registration/tenancy detail |
| Unit cell action buttons | ✅ | **FIXED Loop 7 + Loop 12 + Loop 19** — Loop 7: relationship-based owner contact link; Loop 12: IGR-parsed owners also link when match exists; Loop 19: "+ Add to outreach" button now in unit detail panel when ownerContactId is present (UnitOutreachButton component added to unit-registry.tsx) |
| **Leads tab** | ✅ | **FIXED Loop 20** — `stats.leads`/`warm` wired to real `inbound_leads` table via GROUP BY + leadsMap (same pattern as ownerMap). Empty-state message is mode-sensitive: launch → "Pre-launch interest list…"; active → "0 leads captured. Run a campaign…". DB has 0 leads → shows 0 correctly. |
| **Listings tab** | ✅ | **FIXED Loop 21** — `getListings()` returns `[]` for live DB (honest empty state: "No listings yet for this building."). Stat tile fixed: `data.listings.length` replaces hardcoded `s.listings=0` in workspace-tabs.tsx so tile auto-updates when listings are imported. |
| **SEO tab** | ✅ | **FIXED Loop 16** — `getKeywords(slug)` was ignoring slug and cross-contaminating all pages with IH keywords. Fixed: JOIN `buildings b ON b.id = k.building_id WHERE lower(regexp_replace(b.name,'[^a-z0-9]+','-','gi')) = $1`. DLF/Kalpataru now correctly show empty state. |
| **Campaigns tab** | ✅ | **FIXED Loop 15** — `getCampaigns(slug)` was silently broken (queried `channel_type` which doesn't exist; `.catch()` hid error → always empty). Fixed: correct column `channel`, JOIN `launch_projects` slug filter, `channelTone()` helper. Now renders 10 DLF channels. Create/edit actions not present (read-only display). |
| **RERA tab** | ✅ | **FIXED Loop 17** — `getReraFacts(slug)` queried LIMIT 1 with no ORDER BY/WHERE — returned arbitrary profile. Fixed: JOIN buildings WHERE slug=exact OR LIKE slug+'-%' (catches wing variants). Returns all matching profiles. |
| **Website tab** | ✅ | **FIXED Loop 14** — `getWebsitePages(slug)` queries `wix_staging_sites` (join via `launch_projects`) + `wix_cms_collections`; `stagingTone()` maps `staging_status` → Tone; landing page always included; "Production publish" always last. Falls back to hardcoded rows when DB not live. |
| **Reviews tab** | ✅ | **FIXED Loop 10 + Loop 17** — confirm gate (Loop 10); removed 4,097 `import_review_items` rows that had no building link and were flooding every building's Reviews tab (Loop 17) |
| **Agents tab** | ✅ | **FIXED Loop 13** — `getAgentTasks(slug)` queries `ai_agent_tasks` filtered by `raw_input->>'launch_key' = slug` or `slugify(raw_input->>'building_name') = slug`. Falls back to 4 planned stub rows when no tasks match. |

---

## /cockpit/outreach (WhatsApp assisted)

| Element | Status | Notes |
|---|---|---|
| Status strip (send mode, daily cap, ready owners) | ✅ | Real data from DB |
| "Preview" queue button | ✅ | Dry-run `buildOutreachQueue({ apply: false })`, shows banner "Build outreach queue…". **Loop 21 tested click → banner appears.** |
| "Build & queue" button | ✅ | Real write via script |
| Queue row "Open in WhatsApp" | ✅ | `wa.me/91XXXXXXXXXX?text=...` format |
| Queue row "Mark sent" | ✅ | Calls `recordOutreachActivity` with apply=true |
| Queue row "Replied" | ✅ | ✅ wired |
| Queue row "Enquired" | ✅ | ✅ wired |
| Queue row "Opted in" | ✅ | ✅ wired |
| Queue row "Opted out / STOP" | ✅ | ✅ wired |
| Queue row "Remove" | ✅ | Calls `clearQueueRow({ apply: true })` |
| "Clear queue" button | ✅ | Calls `clearOutreachQueue({ apply: true })` with window.confirm guard |
| Groups panel "Create group" | ✅ | Calls `createContactGroup({ apply: true })` |
| Groups panel "Build queue" (from group) | ✅ | Calls `buildOutreachQueue({ source: 'group', apply: true })` |
| WhatsApp Business API send | ❌ | Not connected — audiences page notes "Direct API state: not connected" |
| Message template editor | ❌ | **Missing** — no UI to edit/preview WA message templates |

---

## /cockpit/audiences (audience exports)

| Element | Status | Notes |
|---|---|---|
| Building filter select | ✅ | URL-based form |
| Role filter select | ✅ | URL-based form |
| "Update preview" submit | ✅ | GET form, updates URL params |
| Audience metrics (contacts/phones/emails/hashed rows) | ✅ | Real counts from DB |
| "Download Meta CSV" link | ✅ | Routes to `/cockpit/audiences/meta` which streams CSV. **Loop 22:** endpoint tested — returns 200, `text/csv` content-type, `email,phone` header line, `.csv` Content-Disposition filename. |
| WhatsApp send state | 🚧 | Shows "not connected" — static, no action |
| Email campaigns section | ❌ | **Missing entirely** |

---

## Summary Counts

| Status | Count |
|---|---|
| ✅ Fully working | 52 |
| ⚠️ Partial | 0 |
| 🚧 Stub/hardcoded | 5 |
| ❌ Missing/broken | 7 |

### New audit findings (Loop 24)
- `agentLabel()`, `buildingFromRaw()`, `taskTone()` — pure private helpers with zero unit tests. Exported all three and added 19 Vitest tests (5 agentLabel + 5 buildingFromRaw + 9 taskTone).
- Home dashboard panels (Buildings list, Needs review, Blockers, Agents) — zero Playwright tests. Added 11 tests covering: portfolio summary line, building card links, DLF card presence, Needs review heading + item, Blockers heading + BLK-xxx IDs, Agents heading + row count.
- Pre-existing flaky test hardened: "Leads tab on launch building" timeout 5000ms → 10000ms (new home dashboard tests add ~8s to pre-test run time, causing intermittent timeout).

### New audit findings (Loop 22)
- `e164Indian()` and `metaCsvFromRows()` — zero unit tests on the Meta audience CSV path. Added 21 Vitest tests (13 phone normalization + 8 CSV generation).
- Meta CSV route `GET /cockpit/audiences/meta` — link tested but response never verified. Added 3 Playwright tests confirming 200/text-csv/email-phone header.
- "Update preview" URL param assertion was weak (only checked `/cockpit/audiences`). Strengthened with explicit `role=` param check.

### New audit findings (Loop 23)
- `audienceScope()` — zero unit tests on CSV filename slug generation. Added 7 Vitest tests (no-filter, building-only, building+role, role-only, special chars, consecutive special chars, leading/trailing spaces).
- `parseAudienceFilters()` — zero unit tests on input sanitisation + role allowlist. Added 7 Vitest tests including the allowlist blocking `admin` role injection.
- Contact detail "Add to group" click — untested as interactive action. Added Playwright test: click → font-mono message appears (applies real write via script).
- Outreach "Build queue from group" click — untested as interactive action. Added Playwright test: click enabled button → message appears.

### New audit findings (Loop 20)
- `/cockpit/contacts` index page (cleanup funnel) had zero Playwright coverage — added 8 tests covering stage stats, sub-nav navigation, merge candidates, review queues, import batches, canonical count
- Sub-nav link labels: "Overview", "Pipeline", "All contacts" (NOT "Sheet")
- Leads tab empty-state message is mode-sensitive and correct; now wired to real DB query

## Top Gaps (by severity)

1. ~~**Mode switcher not functional**~~ ✅ **FIXED Loop 4** — now interactive buttons with local mode state
2. ~~**No search on contact sheet**~~ ✅ **FIXED Loop 5** — debounced client search bar + server-side ILIKE on `full_name`/`phone_primary`; q param preserved through sort/page links
3. ~~**No manual activity log on contact detail**~~ ✅ **FIXED Loop 6** — `ContactNoteForm` with char counter, ⌘↵ shortcut, dry-run script → real write
4. ~~**Unit cell has no actions**~~ ✅ **FIXED Loop 7 (partial)** — owner contact name is now a link; IGR-sourced owners still plain text
5. ~~**Agent runtime stub**~~ ✅ **FIXED Loop 13** — `getAgentActivity()` + `getAgentTasks()` query `ai_agent_tasks`
6. ~~**Home STREAMS hardcoded**~~ ✅ **FIXED Loop 9** — `getStreamReadiness()` queries `launch_readiness_checks` live
7. **Listings from seed** — `getListings()` returns `[]` when DB connected (no listings table); seed only in !live() path — honest empty state
8. ~~**Website tab shows seed data**~~ ✅ **FIXED Loop 14** — `getWebsitePages()` queries `wix_staging_sites` + `wix_cms_collections`
9. **No WhatsApp Business API** — no credentials, no template editor
10. **No email campaign page** — entirely missing
11. ~~**No remove-from-outreach on contact detail**~~ ✅ **FIXED Loop 8** — "Remove" button added; wired to `clearQueueRow` via `queueId` from `activity.queue`
