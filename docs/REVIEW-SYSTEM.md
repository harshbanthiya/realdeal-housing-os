# REVIEW SYSTEM — how it works, and what still needs building

`/cockpit/review` is the human gate for everything the system produces. It is
the throttle on content, outreach and data quality by design: nothing outward-
facing ships without a person approving it.

Status 2026-07-24: **usable, not finished.** Read §4 before extending it.

---

## 1. How it works

The queues are cohort-shaped, not row-shaped — 886 Ekta registrations from one
IGR sweep, 3,530 disk-scanned files needing a type. Deciding those one card at a
time is not a workflow, so the engine groups each queue by its natural cohort
key and applies one decision to the whole group.

```
scripts/review_cohorts.py          ← THE ONLY WRITER. QUEUES registry at the top
   --list        all cohorts, JSON        is the single source of truth for
   --sample      20 rows for one cohort   what "pending" means per table and
   --apply-cohort --decision approve|reject   what a decision writes.
                 (dry-run unless --apply)

web/src/lib/cockpit/review-cohorts.ts   ← server actions, shell out to the script
web/src/app/cockpit/review/page.tsx     ← groups cohorts by queue
web/src/components/cockpit/cohort-card.tsx  ← Sample → dry-run → confirm → write
```

The page **reads through the same script** it writes through, so the UI can
never describe a decision differently from what actually happens. Every apply
does a dry-run first and shows the exact row count before the confirm step.

### Adding a queue

Add one entry to `QUEUES` in `review_cohorts.py`, then add the queue name to the
`QUEUES` set in `review-cohorts.ts`. Required keys:

| key | meaning |
|---|---|
| `label` | shown as the pill |
| `question` | **plain English: what is being asked, and what approve does** |
| `table`, `join`, `pending` | where the pending rows are |
| `cohort` | SQL expression — the natural grouping |
| `sample` | SQL expression — must name the **actual entities**, see §2 |
| `approve` / `reject` | SET clause bodies; `{by}` and `{note}` are substituted |

## 2. The rule that matters most: samples must show entities

The first version rendered a column value per row, so every sample line in a
cohort was identical and told the operator nothing:

```
'Review: inventory_match_review'          ← useless, 1,595 times
'matching normalized phone; review before merge'
```

A sample must answer "what am I deciding?" without leaving the page:

```
MOUNI ROY · C-3405 · 9819973771 · from ekta_sheet_2026
MBM Broking And Real Estate Pvt.Ltd  ==  Mr Bal Krishan Mittal  [+919324705054]
registry: Rajkumar Tripathi == ours: MR. RAJKUMAR TRIPATHI  [C-501 · sim 0.94]
```

That second line is why this matters: a company and a person share a phone.
The old sample would have let someone approve that merge blind.

**If you add a queue whose sample repeats the same string, the queue is not
finished.**

## 3. Queues today

| queue | pending | state |
|---|---|---|
| `media` | 5,896 | works; see §4.1 — approving `(untagged)` does not unblock Shorts |
| `unit_registration` | 3,647 | good — shows unit, doc type, date, price |
| `property_rels` | 2,442 | good — name, flat, phone, source. Approve ⇒ outreach-targetable |
| `drive_contacts` | 726 | good — sheet name → our contact + similarity |
| `contact_dupes` | 577 | good — both names + shared phone |
| `phonebook_rename` | 921 | good — current → proposed |
| `phonebook_to_db` | 801 | good; `low` = competing phones, never bulk-approve |
| `party_matches` | 137 | good — registry name vs ours, unit, similarity |
| `worker_findings` | 26 | fine |
| `contact_import` | 4,097 | **stubs with no content — see §4.2** |

## 4. What still needs work

### 4.1 Media approve does not tag — the biggest cohort is a near no-op
Approving `disk_scan · (untagged)` (3,530 files) sets `reviewed = TRUE` but
leaves `asset_type` NULL. `shorts_scout` requires `asset_type IS NOT NULL`, so
those files remain unusable for Shorts. **The single largest cohort does not
unblock the thing it appears to unblock.**

Options, in order of laziness:
1. Make the tagging grid at `/cockpit/media` handle bulk (it caps at 100 today).
2. Infer `asset_type` from `media_type` where unambiguous (video → `video`).
3. Let `photo_captioner` (Gemini vision) propose `asset_type` alongside alt-text
   and route that through a review cohort. Best quality, most work.

*(Fixed 2026-07-24 in passing: `reject` wrote `status='rejected'`, which is not
in `media_assets_status_check` — every "Reject all" on media errored. Now
`archived`.)*

### 4.2 `contact_import` is 4,097 content-free stubs
These Phase 5.4 rows have **no** `contact_import_row_id`,
`inventory_import_row_id` or `duplicate_candidate_id`, and a `title` that just
repeats their own `review_type`. There is nothing to judge.

The real data lives in `contact_property_hints` (1,598 `needs_review`) and
`inventory_import_rows` (1,595 `needs_review`) — with actual building, wing and
unit. **Wire those two as real queues, then close the stubs.** Until then the
queue is labelled honestly rather than pretending to be work.

### 4.3 No drill-in, no partial approval
A cohort is all-or-nothing. The sample caps at 20 rows with no pagination, and
there is no way to approve 80% of a cohort and hold back the rest. For cohorts
in the hundreds this is the main ergonomic gap. A "Drill in" view (paged rows,
per-row approve, "approve remaining") is the obvious next build.

### 4.4 No undo
Once a cohort is applied there is no reverse operation. `property_rels` approve
sets links `active`, which makes those contacts targetable for outreach — a
wrong bulk approve there has real-world consequences. Add an `undo-cohort` that
reverses the last apply by `reviewed_at` window, or record an apply batch id.

### 4.5 Queues deliberately excluded — do not "fix" by adding them
- **`zapkey_transactions` (3,058)** — needs unit/tower **linking logic**, not a
  yes/no. Flipping to `linked` without resolving `building_unit_id` records a
  link that does not exist.
- **`wa_number_queue` (355)** — approving means attach/create a contact via
  `update_wa_item.py`, not a status flip. It has a working UI already.

### 4.6 Smaller things
- Cohort counts are computed on every page load (one psql round trip for all
  queues). Fine at ~100 cohorts; revisit if it grows.
- `contact_dupes` has no guard against company-vs-person merges (see §2).
  A cheap heuristic on org-like tokens (Pvt, Ltd, LLP, Realty, Broking) would
  catch most, and could downgrade those to their own cohort.
- The building workspace Reviews tab still renders everything as "(preview)"
  because `getGlobalReviewQueue()` supplies no `reviewItemId`. Either point it
  at real queues or drop the tab and send people here.
- No keyboard flow. For hundreds of decisions, j/k + a/r would matter.

## 5. Principles to keep

- **Dry-run then confirm, always.** The operator sees the true row count before
  any write.
- **The engine is the single source of truth.** Do not let the page describe a
  decision in its own words — that is how a UI starts lying. (The component's
  hand-written effect map was deleted for this reason.)
- **A wrong link is worse than a missing one.** When confidence is low, say so
  in the cohort key so it cannot be bulk-approved by accident — as
  `phonebook_to_db · low · …` does for units claimed by competing phones.
- **Never invent content to fill a sample.** If a queue has nothing to show,
  that is a finding about the data, not a formatting problem.
