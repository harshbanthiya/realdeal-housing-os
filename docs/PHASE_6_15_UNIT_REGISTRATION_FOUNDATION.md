# Phase 6.15 — Building structure + IGR unit-registration foundation

Extends the MahaRERA verification layer (Phases 6.8–6.14) toward the goal of a **per-unit
ownership / rental picture** for the (<10) buildings we actively work: for a building, know its
towers/floors/units, then line up every registration (sale / lease / leave-and-license / gift /
mortgage …) done on each unit, with the **names of the parties**, and later match those names to
our contacts.

> **Schema + fake workflow ONLY.** Nothing in this phase scrapes IGR/MahaRERA, calls an external
> API, browses the web, solves a CAPTCHA, auto-creates a contact relationship, merges
> buildings/units, or publishes anything. This builds the destination schema and the human-review
> workflow *before* any collection — exactly as Phase 6.8 did for the verification layer.

> **Legal/privacy note:** IGR Index II party names come from a **public register**, but they are
> still personal data and the data is **not a legal document**. Default dashboards are
> **counts-only**; views that expose names are explicitly suffixed `_operator`.

## Why this is a new layer (not already covered)

The existing RERA layer verifies the **project** (registration number, promoter, status, official
carpet areas). It does **not** model the **per-unit transaction history**. In Maharashtra/Mumbai:

- **MahaRERA** is building/project-name searchable → gives project facts + clues to land identifiers.
- **IGR eSearch** is the actual registration (Index II) source, but it is **property-number first**
  (year × district × village × CTS/survey/plot no. + CAPTCHA), **not** building-name first.
- The join key is usually the **CTS / city-survey number**, sourced from MahaRERA filings and the
  Mumbai property card / Mahabhumi.

So the practical chain is: **building → MahaRERA → CTS/survey/village → IGR eSearch → Index II →
parties → match to contacts.** Phase 6.15 adds the schema for the second half of that chain.

## What migration `047_unit_registration_foundation.sql` adds

| Table | Role |
| ----- | ---- |
| `building_tower_structure` | Towers/wings → floors → units-per-floor / total units (review-gated). |
| `building_property_identifiers` | CTS / survey / plot / milkat / gat / village / SRO — the **IGR bridge keys**; `is_igr_search_key` marks the one used to query IGR. |
| `igr_registration_search_jobs` | Planned IGR eSearch queries (year × district × village × property-no). `captcha_required` defaults true; `external_call_made` stays **false** (no calls this phase). |
| `unit_registration_records` | Index II transactions: doc#, date, SRO, document type, consideration, raw flat/wing text; `building_unit_id` set only after a `unit_link_review`. |
| `unit_registration_parties` | Party names per record (buyer/seller/lessor/lessee/…), with normalized name for matching. |
| `registration_party_contact_matches` | Party → contact match candidates; on accept can propose a `contact_property_relationships` row. |
| `unit_registration_review_items` | Human review queue (one `review_type` per step). |

### Dashboards (9 views)

**SAFE (counts only, no names):** `vw_building_structure_dashboard`,
`vw_building_property_identifier_dashboard`, `vw_igr_search_job_queue`,
`vw_unit_registration_dashboard` (party_count / matched_party_count only),
`vw_unit_registration_review_queue`, `vw_imperial_heights_registration_readiness`.

**OPERATOR (public-register party names, internal use):**
`vw_unit_registration_parties_operator`, `vw_unit_ownership_timeline_operator` (the per-unit
ownership/rental chain), `vw_registration_party_contact_match_queue_operator`.

### Real gates (`vw_imperial_heights_registration_readiness`, all hard-false today)

- `ready_for_igr_search` — true only when a **verified, search-key** property identifier exists.
- `ready_for_party_matching` — true only when ≥1 **verified** registration record exists.
- `ready_for_relationship_creation` — true only when ≥1 **accepted** party→contact match exists.
- `external_call_count` surfaces whether any IGR call was ever recorded (0 today).

## Fake workflow (this phase)

`scripts/seed_fake_unit_registration.py` (dry-run default; `--apply --fake-ok`) seeds a
**clearly-fake, self-contained** set — one fake building `ZZ_FAKE IGR Registration Tower
(Phase 6.15)` (deliberately **not** matching "Imperial Heights"), 1 fake contact, 1 tower
structure, 2 property identifiers (one CTS search key), 1 IGR search job, 2 registration records
(a sale + a leave-and-license), 4 parties, 1 party→contact match candidate, and 6 review items —
all tagged `fake_batch='FAKE_PHASE_6_15_UNIT_REGISTRATION'`.
`scripts/cleanup_fake_unit_registration.py --apply` removes **only** those tagged rows (FK-safe,
including the fake building + contact). `scripts/unit_registration_summary.py` is read-only counts
(never prints names).

```bash
python3 scripts/seed_fake_unit_registration.py                 # dry-run
python3 scripts/seed_fake_unit_registration.py --apply --fake-ok
python3 scripts/unit_registration_summary.py
python3 scripts/cleanup_fake_unit_registration.py             # dry-run
python3 scripts/cleanup_fake_unit_registration.py --apply
```

## Safety posture (verified via fake test)

- Fake seed created exactly **1 / 1 / 1 / 2 / 1 / 2 / 4 / 1 / 6** rows; cleanup returned all to **0**.
- Operator timeline correctly showed the per-unit ownership chain with party names; the SAFE
  dashboard showed **counts only** (no names). Match candidate stayed `candidate` (not accepted).
- **No real building/contact changed** — buildings `6`, contacts unchanged after seed + cleanup.
- Imperial Heights readiness stayed **all hard-false** (`no_verified_search_key_yet`) throughout.
- **No IGR/MahaRERA/external call, no scraping, no browsing, no CAPTCHA, no auto-relationship.**

## Phase 6.16 — per-unit accounting from RERA + ownership/tenancy timelines

Migration `048_unit_ownership_tenancy_timeline.sql` makes three requirements first-class:

1. **Every unit accounted for from RERA.** `vw_building_unit_accounting` reconciles, per building,
   `rera_expected_units` (sum of `rera_carpet_area_records.apartment_count` for a RERA profile
   **linked** to the building) vs. `enumerated_units` (active `building_units`) vs.
   `units_with_registration`, and surfaces `units_not_yet_enumerated`. On real data today, the
   canonical **Imperial Heights** anchor shows **213 expected / 52 enumerated / 161 to account for**.
   (Expected stays 0 until the RERA profile is building-linked — review-first.)

2. **Each unit's timeline shows ownership AND active tenancy.** `document_type` is classified by
   `registration_category()` into `ownership` / `tenancy` / `encumbrance` / `other` (overridable via
   `unit_registration_records.transaction_category`). New tenancy columns
   (`tenancy_start_date` / `tenancy_end_date` / `tenancy_monthly_rent` / `tenancy_deposit`) capture
   lease terms. Views:
   - `vw_unit_ownership_timeline_operator` — ownership chain only (sellers/purchasers per event).
   - `vw_unit_tenancy_timeline_operator` — tenancy events with an `is_active` flag (live end-date).
   - `vw_unit_full_timeline_operator` — unified chronological events, each tagged by category.
   - `vw_unit_current_status_operator` — **one row per unit**: current owner (latest ownership
     event's purchaser) **and** active tenant (most recent live tenancy) together, driven from
     `building_units` so every enumerated unit appears even with no registrations.

3. **Extract whatever names/details exist.** The record + party model already stores every party
   name/role/type, consideration, market value, dates, SRO, and area; tenancy rent/deposit/term are
   now captured too. The (later) IGR Index II parser populates these from real snapshots.

Verified via the enriched fake workflow: a unit with a two-sale ownership chain (2018 A→B, 2022
B→C) plus a live leave-and-license (C→D) correctly resolved to **current owner = C**, **active
tenant = D** (rent ₹55,000), unified timeline tagged each event, and accounting showed
**80 expected / 1 enumerated / 79 to account for** — then cleanup returned everything to 0 with real
data untouched (buildings 6, contacts 1313).

## Next recommendation

For the first **real** pass (Imperial Heights):
1. **Structure + identifiers**: record towers/floors/units and the CTS/survey/village from the
   MahaRERA filing + property card → human-verify via `vw_unit_registration_review_queue`.
2. Build the guarded, **operator-assisted** IGR capture script (headed Playwright, **human CAPTCHA**,
   git-ignored raw snapshots under `exports/`) — the IGR analogue of the 6.10–6.12 MahaRERA capture.
3. Review-gated **Index II parser** → `unit_registration_records` + `unit_registration_parties`.
4. **Party → contact matching** (normalized-name candidates) → on accept, propose
   `contact_property_relationships` rows.
