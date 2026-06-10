# Phase 6.9 — Manual MahaRERA Verification: Imperial Heights Wing C & D

Real but **review-gated** MahaRERA verification rows for Imperial Heights, transcribed by
a human from a **manually-supplied official MahaRERA PDF snapshot** — **no scraping, no
API calls, no browsing** from scripts. Nothing is verified/accepted, no building is
merged, no source gap is resolved, no internal building address is changed, and nothing is
published or sent.

## Source

- **Official project URL (user-supplied):**
  `https://maharerait.maharashtra.gov.in/public/project/view/6231`
- **Source PDF snapshot (user-supplied):** `Maharashtra Real Estate Regulatory Authority.pdf`
  — recorded as `source_label='official_maharera_pdf_snapshot_user_supplied'` in
  `raw_context`. The PDF itself is **not copied into the repo and not committed**; only its
  filename and generation timestamp are stored as metadata.
- **RERA registration number:** `P51800003270`

## Project facts entered (`rera_project_profiles`, 1 row, `needs_human_review`)

- Official project name: **Imperial Heights Wing C and D**
- Promoter (company): **EPITOME RESIDENCY PRIVATE LIMITED** (`promoter_type=Company`)
- Project type: Residential / Group Housing · Project status: **Completed**
- Registration date 2017-08-05 · Completion date 2021-06-30 (revised; original 2019-06-30)
- `verification_status='needs_human_review'`, `confidence_score=0.85`,
  `registration_status='registered_or_completed_needs_review'`
- Linked to building `0e72db71…` and the `imperial-heights-goregaon-west` web profile.

## Land / area facts entered (in `raw_context`)

Total land area (approved layout) 10084.49 sqm · land area for registration 10084.49 sqm ·
permissible built-up 66750.15 sqm · sanctioned built-up 64062.15 sqm · recreational open
space 7081.93 sqm · final plot/CTS/survey "1 part" · planning authority "Others" ·
financial encumbrance "No" · investor other than promoter "No".

## Building / wing facts (in `raw_context.rera_building_wing_records`)

Imperial Heights **Wing C** (NA, 51 sanctioned floors) and **Wing D** (NA, 51 sanctioned
floors); also recorded as a `building_wing_details_present` status check.

## Carpet-area records entered (`rera_carpet_area_records`, 26 rows, `needs_human_review`)

26 apartment/carpet-area rows totaling **213 apartments**. `carpet_area_sqft` is computed
as `carpet_area_sqm × 10.76391041671` (rounded to 2 dp). `booked_count` is left NULL — **no
availability is inferred** from these rows.

## Status / risk / document checks entered (`rera_project_status_checks`, 13 rows)

`info`: project_completed, certificate_available, land_area_details_present,
carpet_area_records_present, appeal_present, financial_encumbrance (clear),
technical_documents_present, promoter_documents_present,
occupation_certificate_documents_present, building_wing_details_present.
**`warning`:** litigation_present (8 rows), complaint_present (29 rows),
non_compliance_present (5 rows). No `blocker`-severity check.

## Address / geolocation intentionally NOT trusted from RERA

Per the operator note, MahaRERA often uses registration/administrative address details
rather than the practical building address used by brokers. So **RERA
street/boundary/latitude/longitude are NOT stored as trusted building address data**:
- `rera_project_profiles` `district` / `taluka` / `locality` / `pincode` are left **NULL**.
- `raw_context` carries `address_verification_status='needs_operator_review'`,
  `do_not_use_rera_address_for_public_listing=true`, `rera_address_fields_skipped=true`.
- **No internal `buildings` address/geolocation was updated** (verified: 0 changes).
- A dedicated **`rera_address_review`** review item (priority `high`) is queued so an
  operator can later confirm the usable building address.

## Personal data handling

Personal names from **director / complainant / allottee / respondent / grievance / appeal
/ non-compliance** sections are **intentionally NOT stored**. Litigation/complaint/appeal
/non-compliance are recorded as **counts only** with safe summaries; the only person/entity
name stored is the official **promoter company**.

## What remains `needs_human_review`

The profile (`needs_human_review`), both building matches (`candidate`, **not accepted**),
all 26 carpet records (`needs_human_review`), and all 6 review items (`pending`):
`rera_project_match_review` ×2, `rera_fact_review`, `rera_carpet_area_review`,
`rera_status_risk_review` (high), `rera_address_review` (high).

## Readiness (unchanged gates)

`vw_imperial_heights_rera_readiness`: `ready_for_building_dedupe=false`
(`blocked_reason=rera_match_not_accepted`), `ready_for_content_fact_use=false` (profile not
verified). Neither is set true in this phase.

## Cleanup (dry-run) command

```bash
# Dry-run (default): shows the tagged 6.9 rows that would be deleted.
python3 scripts/cleanup_manual_rera_verification.py

# Apply (deletes only phase='6.9'/source='manual_rera_verification_entry' rows; refuses if
# any profile verified / match accepted / mismatch corrected / content gap resolved):
python3 scripts/cleanup_manual_rera_verification.py --apply --real-ok
```

## Commands

```bash
python3 scripts/apply_manual_rera_verification.py \
  --building-id 0e72db71-8b93-4ecd-879c-17d8d8f2b206 \
  --profile-slug imperial-heights-goregaon-west \
  --rera-registration-number P51800003270 \
  --official-project-url https://maharerait.maharashtra.gov.in/public/project/view/6231 \
  --project-name "Imperial Heights Wing C and D" \
  --source-label official_maharera_pdf_snapshot_user_supplied --real-ok [--apply]
```

## Safety posture (verified after apply)

- **No scraping/API/browsing** — facts transcribed from the user-supplied PDF only.
- **No building merge, no address/geolocation update** — buildings 2, anchors 2, building
  address changes 0; `building_duplicate_candidates` still 1 pending.
- **No source gaps resolved** — gaps `open=17 / resolved=0`.
- **Not verified / not accepted** — profile `needs_human_review`, matches `candidate`.
- **No publishing, no outreach** — `ready_for_publish=0`, `communication_sent=0`.

## Next review step

A human reviews the `vw_rera_verification_review_queue`, confirms the RERA project facts,
and **accepts** the RERA match (`rera_project_match_review`) — only then does
`ready_for_building_dedupe` become true, unlocking the Phase 6.7 building dedupe. Verifying
the profile (with no blocker risk) is what later enables `ready_for_content_fact_use`. The
`rera_address_review` must be worked separately before any address is trusted publicly.
