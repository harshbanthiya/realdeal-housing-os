# Real Deal Housing OS

Local-first operations stack for Real Deal Housing OS.

## Before Every Phase

Start Docker Desktop manually if needed, then run this from the project root:

```bash
./stop.sh
./start.sh
docker ps
./scripts/check_db.sh
```

Continue only if:

- `realdeal-postgres` is running.
- `realdeal-n8n` is running.
- `realdeal-nocodb` is running.
- `realdeal-adminer` is running.
- `./scripts/check_db.sh` passes.

At the end of every phase, run:

```bash
./scripts/check_db.sh
git status --short
```

Do not diagnose Postgres issues until Docker Desktop and the containers have been restarted and `./scripts/check_db.sh` has been run.

## What `start.sh` does

`start.sh` is hardened for the external **exFAT** drive this project runs from:

1. Creates `docker/.env` from `docker/.env.example` on first run (then asks you to fill it in).
2. **Preflight cleanup:** deletes macOS metadata junk (`.DS_Store` and AppleDouble `._*`,
   files only) from the project tree via `scripts/clean_appledouble_junk.sh --apply`, and
   prints the count before/after.
3. **Hard guard:** if any junk remains under `data/postgres` after cleanup, it aborts
   *before* `docker compose up` with a clear error (Postgres would otherwise fail).
4. **Staged startup:** brings up Postgres first and waits for it to be healthy
   (`docker compose up -d --wait postgres`), retrying up to 3 times — each retry recreates
   Postgres from a stopped state and re-cleans — then launches the rest of the stack.

## AppleDouble / exFAT Troubleshooting

This project runs from an **exFAT** external volume (`noowners`). macOS stores extended
attributes on exFAT as AppleDouble `._*` sidecar files (one per real file), and Docker's
bind mount can re-materialise thousands of them under `data/postgres` during a
container bring-up. The Postgres entrypoint's permission (`chown`) pass fails on these
files, so the container exits and the stack reports `dependency ... is unhealthy`.

`start.sh` handles this automatically (preflight clean + guard + staged retry). To inspect
or clean manually, dry-run first (this prints **counts only**, never file paths):

```bash
./scripts/clean_appledouble_junk.sh          # dry run: shows how many junk files exist
./scripts/clean_appledouble_junk.sh --apply  # delete them (files only, never directories)
```

This only removes macOS metadata junk files. It does **not** repair database corruption.

Notes and durable options:

- Spotlight indexing was disabled on the volume (`mdutil -i off`, `mdutil -E`, plus a
  `.metadata_never_index` marker at the volume root). This reduces, but does not fully
  eliminate, `._*` regeneration during Docker bring-up — hence the retry loop in `start.sh`.
- The container itself cannot delete `._*` files (Docker's exFAT file sharing returns
  "Operation not permitted"), so cleanup must happen host-side before/between start attempts.
- The most robust long-term fix is to move the Postgres data off exFAT (e.g. a Docker named
  volume on the Docker Desktop VM, or an APFS/HFS+ location), which removes AppleDouble
  entirely. This requires a data migration and is not done yet.

## Credentials and `docker/.env`

- `docker/.env` holds local secrets and is **ignored by Git — never commit it**.
- `docker/.env.example` contains placeholders only (`change_me_*`); keep real secrets out of it.
- Do not store plaintext logins/passwords in comments inside `docker/.env`.
- If a plaintext credential was ever present in `docker/.env` (it has since been removed),
  **rotate that password/secret** as a precaution.

## Phase 3 Contact Import MVP

The contact import flow is lossless and review-first:

```bash
python3 scripts/profile_contact_file.py imports/contacts/test_simple_phonebook.csv
python3 scripts/normalize_contact_file.py imports/contacts/test_simple_phonebook.csv
python3 scripts/clean_contacts.py exports/contacts/<normalized_file>
python3 scripts/contact_dedupe_report.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
```

Database import is dry-run by default. Apply mode is not implemented yet.

Real input files belong in `imports/contacts/`. Generated outputs belong in `exports/contacts/`. Both folders are ignored by Git.

## Phase 3.2 Archive Workflow

For large archives, profile first and only normalize selected files:

```bash
python3 scripts/profile_archive.py imports/contacts/raw_archives/Archive.zip
python3 scripts/profile_contact_file.py exports/archive_profiles/<archive>/extracted/<file>
python3 scripts/normalize_contact_file.py exports/archive_profiles/<archive>/extracted/<file>
python3 scripts/clean_contacts.py exports/contacts/<normalized_file>
python3 scripts/contact_dedupe_report.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
python3 scripts/contact_import_summary.py exports/contacts/<cleaned_file>
```

The importer remains dry-run by default. Do not use `--apply` until the import policy and review screens are ready.

Warnings:

- Some `.csv` files are actually UTF-16 tab-delimited Meta/Facebook exports.
- VCF and Google Contacts files can contain multiple phones/emails; preserve all values.
- PDFs may be text-extractable or scanned/image-only. OCR is not implemented.
- Property inventory sheets should feed a future inventory import path, not only contact import.
- Archive 2 adds building/member workbook patterns and image-only screenshot folders. PNG/JPG files are marked `image_only_needs_ocr`; scanned PDFs remain profile-only.
- XLSX profiling scans the first 10 rows for likely table headers because some workbooks contain title/merged rows before the real table.

## Phase 3.3 Source-Aware Import Schema

Phase 3.3 adds source-aware database tables for review before canonical merge:

- `source_files`
- `contact_methods`
- `lead_requirements`
- `inventory_import_rows`
- `import_review_items`

It also adds review views for NocoDB and a safe planning script:

```bash
python3 scripts/plan_source_aware_import.py exports/contacts/<cleaned_file>
python3 scripts/import_contacts_to_db.py exports/contacts/<cleaned_file>
```

Both commands are dry-run only. `--apply` is intentionally disabled for source-aware imports.

Apply/check the schema with:

```bash
./scripts/apply_schema.sh
./scripts/check_db.sh
```

See `docs/SOURCE_AWARE_SCHEMA.md` for the review flow.

## Phase 3.4 Fake Source-Aware Apply Test

Phase 3.4 adds the first guarded write path for fake `.example` data only. It writes into source-aware import/audit tables and does not create or merge canonical contacts.

Example fake workflow:

```bash
python3 scripts/profile_contact_file.py imports/contacts/sample_simple_phonebook.csv.example
python3 scripts/normalize_contact_file.py imports/contacts/sample_simple_phonebook.csv.example --output-dir exports/contacts/phase_3_4_fake
python3 scripts/clean_contacts.py exports/contacts/phase_3_4_fake/<normalized_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/contact_dedupe_report.py exports/contacts/phase_3_4_fake/<cleaned_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/plan_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --output-dir exports/contacts/phase_3_4_fake
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file>
python3 scripts/apply_fake_source_aware_import.py exports/contacts/phase_3_4_fake/<cleaned_file> --apply --fake-ok
```

Cleanup is also guarded:

```bash
python3 scripts/cleanup_fake_import_batch.py
python3 scripts/cleanup_fake_import_batch.py --apply
```

Real imports remain disabled. Never use this fake apply script with raw samples, raw archives, or real client files.

## Phase 3.5 Real Source-Aware Audit Import

Phase 3.5 allows one controlled real cleaned CSV to be written into source-aware audit/import tables only. Canonical contacts are still protected.

```bash
python3 scripts/profile_contact_file.py imports/contacts/raw_samples/<small_real_file>
python3 scripts/normalize_contact_file.py imports/contacts/raw_samples/<small_real_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/clean_contacts.py exports/contacts/phase_3_5_real/<normalized_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/contact_dedupe_report.py exports/contacts/phase_3_5_real/<cleaned_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/plan_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --output-dir exports/contacts/phase_3_5_real
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/apply_real_source_aware_import.py exports/contacts/phase_3_5_real/<cleaned_file> --apply --real-ok --batch-label REAL_PHASE_3_5_TEST_001
```

Rollback is dry-run first:

```bash
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/cleanup_real_import_batch.py --batch-label REAL_PHASE_3_5_TEST_001 --apply
```

Real source-aware imports are tagged with `source_aware_only=true` and `canonical_merge_done=false`. Do not merge canonical contacts until a later reviewed workflow exists.

## Phase 3.6 NocoDB Review Workflow

Phase 3.6 adds masked NocoDB review views for the first real source-aware audit batch:

```text
REAL_PHASE_3_5_TEST_001
```

Open NocoDB at:

```text
http://localhost:8080
```

Start with these views:

```text
vw_review_dashboard_summary
vw_review_batch_sources
vw_review_business_leads
vw_review_contact_methods
vw_review_duplicate_candidates
vw_review_queue
```

Safe count-only helpers:

```bash
python3 scripts/review_batch_summary.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/list_review_views.py
```

Reviewing does not merge into canonical contacts. Do not send messages, WhatsApp, or email from this system yet.

## Phase 3.7 Review Actions

Phase 3.7 adds status-only review action tools. They update review tables and write `review_action_log`; they do not merge canonical contacts.

```bash
python3 scripts/review_queue_summary.py --batch-label REAL_PHASE_3_5_TEST_001
python3 scripts/update_review_item.py --review-item-id <id> --status needs_more_info --reviewed-by admin
python3 scripts/bulk_update_review_items.py --batch-label REAL_PHASE_3_5_TEST_001 --review-type lead_requirement_review --from-status pending --to-status needs_more_info --reviewed-by admin --limit 2
python3 scripts/update_duplicate_candidate.py --candidate-id <id> --status needs_more_info --reviewed-by admin
```

All update scripts are dry-run by default and require `--apply` for writes. See `docs/REVIEW_ACTIONS.md`.

## Phase 3.8 Fake Canonical Merge Workflow

Phase 3.8 tests a review-to-canonical merge path with fake `.example` data only. Real canonical merge is still disabled.

```bash
python3 scripts/plan_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --limit 2
python3 scripts/apply_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --limit 2
python3 scripts/apply_canonical_merge.py --batch-label FAKE_PHASE_3_8_MERGE_TEST --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --limit 2 --apply --test-ok
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE
python3 scripts/rollback_canonical_merge.py --merge-label FAKE_PHASE_3_8_CANONICAL_MERGE --apply
```

The apply script refuses real batches and requires fake labels. Rollback is dry-run by default. See `docs/CANONICAL_MERGE_WORKFLOW.md`.

## Phase 4 First Real Canonical Merge

Phase 4 (2026-06-08) promotes **one** approved `merge_candidate` review item from
the real audit batch `REAL_PHASE_3_5_TEST_001` into a single canonical contact,
behind `--real-ok` plus a strict guard matrix. Counts only are printed; no raw
personal data is shown and **no outreach (WhatsApp / SMS / email / message) is sent.**

```bash
# Plan (read-only)
python3 scripts/plan_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 --approved-only
# Dry-run apply (no writes): omit --apply
python3 scripts/apply_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 --real-ok
# Real apply (creates exactly 1 canonical contact): add --apply
python3 scripts/apply_canonical_merge.py --batch-label REAL_PHASE_3_5_TEST_001 \
  --review-item-id 0da30fd3-84a8-450a-b759-1d71a18db0f9 \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 --real-ok --apply
# Rollback dry-run (default; add --apply only when explicitly approved)
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_001 --real-ok --confirm-real-rollback
```

Real merge is enabled for only one approved review item at a time — no bulk merge,
no duplicate merge. See `docs/PHASE_4_FIRST_REAL_CANONICAL_MERGE.md`.

## Phase 4.1 Canonical Contact Review

Phase 4.1 adds a safe, masked review layer so the real canonical contact can be
inspected and traced to its import source without exposing raw personal values.
Migration `schemas/007_canonical_review_dashboard.sql` adds five NocoDB views:
`vw_canonical_contacts_review`, `vw_canonical_contact_methods_review`,
`vw_canonical_source_trace`, `vw_canonical_lead_requirements_review`,
`vw_canonical_merge_audit` (names masked to an initial, phones/emails masked).

```bash
# Counts-only summary (no DB writes)
python3 scripts/canonical_contact_summary.py --merge-label REAL_PHASE_4_CANONICAL_MERGE_001
```

No outreach is sent in this phase. See `docs/CANONICAL_CONTACT_REVIEW.md`.

## Phase 4.2 Second Real Canonical Merge

Phase 4.2 (2026-06-08) created a **second** real canonical contact from one more
approved `merge_candidate` review item (`14bc4ad4-013e-43bf-b32f-0d3310de7623`,
`google_maps_business_csv`) in `REAL_PHASE_3_5_TEST_001`, under merge label
`REAL_PHASE_4_CANONICAL_MERGE_002` — 1 contact, 3 methods, 1 lead requirement,
5 merge links. Same guardrails as Phase 4 (one approved item at a time, no bulk
merge, no duplicate merge, no outreach). Canonical contacts: 1 → 2; review statuses:
40 pending / 4 approved / 1 needs_more_info.

```bash
# Rollback dry-run (does not run destructively)
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_4_CANONICAL_MERGE_002 --real-ok --confirm-real-rollback
```

See `docs/PHASE_4_2_SECOND_REAL_CANONICAL_MERGE.md`.

## Phase 5.1 Property Relationship Pipeline

Phase 5.1 (Milestone 2) adds the schema foundation for linking canonical contacts to
buildings/units with reviewed relationship types (owner / tenant / broker / buyer /
lead …). Migration `schemas/008_property_relationship_pipeline.sql` adds 5 tables
(`building_aliases`, `building_units`, `contact_property_relationships`,
`property_relationship_review_items`, `property_relationship_action_log`) and 5 masked
NocoDB views. **Schema + fake test only** — no real owner/property sheets are imported
and no outreach is sent.

```bash
# Fake test workflow (counts only; dry-run by default)
python3 scripts/apply_fake_property_relationships.py --apply --fake-ok
python3 scripts/property_relationship_summary.py
python3 scripts/cleanup_fake_property_relationships.py --apply
```

See `docs/PROPERTY_RELATIONSHIP_PIPELINE.md`.

## Phase 5.2 Property Hint To Relationship Candidates

Phase 5.2 adds a guarded fake-only workflow for turning source-aware property hints
into reviewable relationship candidates. The planner is read-only and counts-only;
the fake apply path refuses non-`FAKE_` batches and real contacts. No real owner
sheets are imported, no canonical merge runs, and no outreach is sent.

```bash
python3 scripts/plan_property_relationship_candidates.py --fake-only
python3 scripts/seed_fake_property_hints.py --apply --fake-ok
python3 scripts/apply_fake_property_relationship_candidates.py \
  --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS --apply --fake-ok
python3 scripts/cleanup_fake_property_relationship_candidates.py --apply
python3 scripts/seed_fake_property_hints.py --cleanup --apply
```

See `docs/PROPERTY_HINT_TO_RELATIONSHIP_WORKFLOW.md`.

## Phase 5.4 Imperial Unit Audit Import

Phase 5.4 applied one small real unit-resident source into source-aware audit/import
tables only under batch `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`: 58 contact import
rows, 116 contact methods, 58 property hints, 58 inventory import rows, 14 duplicate
candidates, and 188 pending review items. It did not create canonical contacts,
buildings, units, or property relationships, and no outreach was sent.

Rollback remains dry-run by default:

```bash
python3 scripts/cleanup_real_import_batch.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001
```

See `docs/PHASE_5_4_IMPERIAL_UNIT_AUDIT_IMPORT.md`.

## Phase 5.5 Owner/Unit Canonical Contact Plan

Phase 5.5 analyzes `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` for future canonical
contact creation without changing review statuses or creating contacts. The first
candidate pass found 52 safe rows and 6 duplicate-involved rows; two safe
`merge_candidate` review items were selected for a later approval phase.

```bash
python3 scripts/owner_unit_candidate_summary.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --limit 2 \
  --source-format unit_resident_workbook
```

See `docs/PHASE_5_5_OWNER_UNIT_CANONICAL_CONTACT_PLAN.md`.

## Phase 5.6 Owner/Unit Review Approval And Merge Prep

Phase 5.6 approved exactly two owner/unit `merge_candidate` review items from
`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001` and updated canonical merge planning/apply
guardrails for a later contact-only owner/unit merge phase. No canonical merge apply
was run, no canonical contacts/buildings/units/relationships were created, and no
outreach was sent.

```bash
python3 scripts/plan_canonical_merge.py \
  --batch-label REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001 \
  --review-item-id <approved_owner_unit_merge_candidate_id> \
  --approved-only
```

Future owner/unit canonical contact creation requires an explicit later approval to
run `scripts/apply_canonical_merge.py --apply --real-ok`. See
`docs/PHASE_5_6_OWNER_UNIT_REVIEW_APPROVAL_AND_MERGE_PREP.md`.

## Phase 5.7 First Owner/Unit Canonical Merge

Phase 5.7 created exactly one canonical contact from one approved owner/unit
`merge_candidate` review item in `REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`, under
merge label `REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001`. It linked 2 contact
methods and recorded property/inventory trace counts. Canonical contacts increased
from 2 to 3. No buildings, units, property relationships, relationship review
items, or outreach were created.

```bash
python3 scripts/rollback_canonical_merge.py \
  --merge-label REAL_PHASE_5_7_OWNER_UNIT_CANONICAL_MERGE_001 \
  --real-ok \
  --confirm-real-rollback
```

See `docs/PHASE_5_7_FIRST_OWNER_UNIT_CANONICAL_MERGE.md`.

## Phase 5.8 First Real Relationship Candidate

Phase 5.8 created the first real, review-gated owner/unit relationship candidate
from the Phase 5.7 canonical contact: building anchor → `pending_review` alias →
`needs_review` unit → `pending_review` `owner` relationship → `pending` review item
(one each). Nothing is approved/active; no outreach.

```bash
# Dry-run, then apply (needs --real-ok --apply); rollback is dry-run by default
python3 scripts/apply_real_property_relationship_candidates.py \
  --contact-id <canonical_contact_id> --review-item-id <import_review_item_id> --apply --real-ok
python3 scripts/rollback_real_property_relationship_candidates.py --rel-label REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001
```

See `docs/PHASE_5_8_FIRST_REAL_RELATIONSHIP_CANDIDATE.md`.

## Phase 5.9 First Real Relationship Approval

Phase 5.9 approved one Phase 5.8 candidate and activated one owner relationship:
review item → approved, relationship → active, building unit → active, building
alias → approved, plus one action-log row. One at a time (no bulk approval), no
contacts/source rows changed, no outreach.

```bash
# Dry-run, then apply (--real-ok --apply); revert is dry-run by default
python3 scripts/approve_property_relationship_candidate.py \
  --review-item-id <REVIEW_ITEM_ID> --reviewed-by "h b" --decision-notes "..." --real-ok --apply
python3 scripts/revert_property_relationship_approval.py \
  --review-item-id <REVIEW_ITEM_ID> --reviewed-by "h b" --decision-notes "..." --real-ok
```

See `docs/PHASE_5_9_FIRST_PROPERTY_RELATIONSHIP_APPROVAL.md`.

## Phase 5.10 Owner/Building/Unit Dashboard

Phase 5.10 adds masked read-only dashboard views over the first active owner
relationship (view/script polish only — no import, no new contacts/relationships, no
approvals, no outreach). Migration `schemas/009_owner_building_unit_dashboard.sql`
adds `vw_owner_relationship_dashboard`, `vw_building_unit_owner_summary`,
`vw_contact_property_trace_full`, and `vw_property_relationship_revert_readiness`.

```bash
# Counts-only summary (no DB writes)
python3 scripts/owner_relationship_dashboard_summary.py
```

See `docs/OWNER_BUILDING_UNIT_DASHBOARD.md`.

## Phase 5.11 Second Owner/Unit Canonical Contact + Relationship Candidate

Phase 5.11 merged the second approved owner/unit review item
(`75bb7bad-…`) into a new canonical contact (`REAL_PHASE_5_11_OWNER_UNIT_CANONICAL_MERGE_002`;
canonical contacts 3 → 4) and created one review-gated relationship **candidate**
(`REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002`, unit "Wing A -203"). The candidate is
`pending_review` — not approved/active (active owner relationships stay 1) — and no
outreach was sent. Both rollback dry-runs verified. See
`docs/PHASE_5_11_SECOND_OWNER_UNIT_CANONICAL_AND_REL_CANDIDATE.md`.

## Phase 5.12 Second Property Relationship Approval

Phase 5.12 approved the Phase 5.11 candidate and activated a second owner
relationship: review item → approved, relationship → active, unit → active, alias →
approved, +1 action-log row. Active owner relationships **1 → 2**; pending candidates
→ 0; canonical contacts stay 4; no contacts/source rows changed; no outreach. The
approve/revert scripts are now phase-agnostic (keyed on the candidate source marker).
See `docs/PHASE_5_12_SECOND_PROPERTY_RELATIONSHIP_APPROVAL.md`.

## Phase 5.13 Milestone 2B Checkpoint + Data-Quality Dashboard

Phase 5.13 is a read-only milestone checkpoint before scaling. Migration
`schemas/010_milestone_2b_data_quality_dashboard.sql` adds five masked views
(`vw_milestone_2b_summary`, `vw_owner_unit_batch_quality`, `vw_owner_unit_candidate_queue`,
`vw_owner_relationship_revert_dashboard`, `vw_duplicate_risk_dashboard`) and
`scripts/milestone_2b_summary.py`. No import, no new contacts/relationships, no status
changes, no outreach.

```bash
python3 scripts/milestone_2b_summary.py   # counts only
```

Recommendation: **Phase 5.14 Option A** (merge more safe owner/unit candidates — 50
queued, 6 duplicate-involved deferred). See `docs/MILESTONE_2B_CHECKPOINT.md`.

## Phase 5.13A NocoDB Human Dashboard Setup

Phase 5.13A made NocoDB usable for a human operator. The fix:
`NC_ALLOW_LOCAL_EXTERNAL_DBS: "true"` on the `nocodb` service (NocoDB blocks
internal/private DB hosts by default), and connecting the base to host `postgres`
(not `localhost`), db `realdeal_os`, schema `public`. Migration
`schemas/011_human_dashboard_ops_views.sql` adds four masked human views and
`scripts/human_dashboard_summary.py`. See `docs/NOCODB_HUMAN_DASHBOARD_RUNBOOK.md`.

## Phase 6.0 Growth, SEO, Content & Lead Pipeline Foundation

Phase 6.0 lays the foundation for the growth engine: building SEO pages, keyword
targeting, content briefs, a publishing queue, inbound lead capture, attribution,
consent/channel permissions, suppression, campaign drafts, and an AI agent task
queue. Migration `schemas/012_growth_seo_lead_pipeline.sql` adds 11 tables and 7
read-only masked views (`vw_growth_pipeline_home`, `vw_seo_keyword_dashboard`,
`vw_content_pipeline_dashboard`, `vw_inbound_lead_review_queue`,
`vw_channel_permission_dashboard`, `vw_campaign_readiness_dashboard`,
`vw_ai_agent_task_dashboard`).

**Foundation only — no publishing and no outreach.** `campaign_drafts.send_enabled`
defaults `false`, `ai_agent_tasks.human_review_required` defaults `true`, and no
external API is called. The fake end-to-end workflow is fully reversible:

```bash
python3 scripts/seed_fake_growth_pipeline.py                 # dry-run (default)
python3 scripts/seed_fake_growth_pipeline.py --apply --fake-ok
python3 scripts/growth_pipeline_summary.py                   # counts only
python3 scripts/cleanup_fake_growth_pipeline.py --apply      # removes only fake rows
```

See `docs/GROWTH_SEO_LEAD_PIPELINE.md`.

## Phase 6.1 First Real Building SEO/Content Plan

Phase 6.1 creates the first **real, review-gated** SEO/content plan for a building
(Imperial Heights, Goregaon West) on the Phase 6.0 schema: 1 `building_web_profile`,
10 low-competition `seo_keywords`, 3 `content_briefs`, 3 **draft**
`content_publishing_queue` rows, and 5 **queued** `ai_agent_tasks`
(`human_review_required=true`). **No external calls, no publishing, no outreach.**
The chosen anchor is the earliest-created of the two duplicate "Imperial Heights"
buildings; building dedupe stays future work.

```bash
# Dry-run (default); real data requires --real-ok; writing requires --apply:
python3 scripts/apply_real_building_seo_plan.py \
  --building-id <BUILDING_ID> --building-name "Imperial Heights" \
  --area "Goregaon West" --city "Mumbai" \
  --profile-slug "imperial-heights-goregaon-west" --real-ok [--apply]

# Reversible cleanup (dry-run default; --apply --real-ok to delete planning rows only):
python3 scripts/cleanup_real_building_seo_plan.py \
  --building-id <BUILDING_ID> --profile-slug "imperial-heights-goregaon-west"
```

See `docs/PHASE_6_1_IMPERIAL_HEIGHTS_SEO_PLAN.md`.

## Phase 6.2 Wix CMS Mapping & Content Review

Phase 6.2 prepares the Imperial Heights plan for **future** Wix publishing without
publishing anything. Migration `schemas/013_wix_cms_content_readiness.sql` adds 4
tables (`wix_cms_collections`, `wix_cms_field_mappings`, `content_review_items`,
`publishing_readiness_checks`) and 4 views (`vw_wix_cms_mapping_dashboard`,
`vw_content_review_dashboard`, `vw_publishing_readiness_dashboard`,
`vw_imperial_heights_content_plan`). The prep script seeds 2 planned Wix
collections, 12 draft field mappings, 3 pending content reviews, and a 24-row
pending readiness checklist. **No Wix/external calls, no publishing, no outreach;
`ready_for_publish` stays false.**

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/prepare_wix_content_review.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
# Reversible cleanup (dry-run default; --apply --real-ok deletes only 6.2 rows):
python3 scripts/cleanup_wix_content_review.py --profile-slug imperial-heights-goregaon-west
```

See `docs/PHASE_6_2_WIX_CMS_CONTENT_REVIEW_PLAN.md`.

## Phase 6.3 Content Quality & AI Task Execution Planning

Phase 6.3 makes the Imperial Heights plan reviewable and ready for **future**
AI-assisted drafting, staying local and non-publishing. Migration
`schemas/014_content_quality_and_ai_planning.sql` adds 4 tables
(`content_quality_checks`, `content_source_requirements`, `ai_prompt_templates`,
`ai_task_execution_plans`) and 5 views (incl. `vw_imperial_heights_content_readiness`).
The prep script seeds 24 pending quality checks, 20 needed source requirements, 4
draft prompt templates (with safety rules), and 5 execution plans
(`manual`, `external_calls_allowed=false`, `requires_human_review=true`). **No AI
execution, no external calls, no publishing, no outreach; `ready_for_ai_draft` and
`ready_for_publish` both stay false.**

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/prepare_content_quality_plan.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
# Reversible cleanup (dry-run default; --apply --real-ok deletes only 6.3 rows):
python3 scripts/cleanup_content_quality_plan.py --profile-slug imperial-heights-goregaon-west
```

See `docs/PHASE_6_3_CONTENT_QUALITY_AI_PLANNING.md`.

## Phase 6.4 Local Content Draft Workspace

Phase 6.4 stores **internal, non-final** draft artifacts for the Imperial Heights
briefs — local only, no publishing. Migration
`schemas/015_content_draft_workspace.sql` adds 3 tables
(`content_draft_artifacts`, `content_draft_reviews`, `content_source_gap_items`)
and 4 views (incl. `vw_imperial_heights_draft_workspace`). The script seeds 7 draft
artifacts (3 outlines + 3 internal notes + 1 meta draft; all `internal_only=true`,
`public_ready=false`), 7 pending draft reviews, and 17 open source-gap items. Bodies
are outlines/placeholders with `[SOURCE NEEDED]` markers and an
"INTERNAL DRAFT — NOT FOR PUBLISHING" header — no contact data, no invented facts.
**No AI execution, no external calls, no publishing, no outreach.** An optional
exporter writes drafts under the git-ignored `exports/content/`.

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/create_local_content_draft_artifacts.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
python3 scripts/export_content_draft_artifacts.py --profile-slug imperial-heights-goregaon-west [--apply]
python3 scripts/cleanup_local_content_draft_artifacts.py --profile-slug imperial-heights-goregaon-west
```

See `docs/PHASE_6_4_LOCAL_CONTENT_DRAFT_WORKSPACE.md`.

## Phase 6.5 Source-Gap Resolution Workflow

Phase 6.5 turns the 17 open source-gap items into **review-gated** resolution tasks
and records **safe, count-only** internal evidence. Migration
`schemas/016_source_gap_resolution_workflow.sql` adds 3 tables
(`source_gap_resolution_tasks`, `internal_source_evidence`, `source_gap_review_items`)
and 4 views (incl. `vw_imperial_heights_source_gap_status`, whose `ready_for_publish`
is a hard-coded `false`). The planner classifies each open gap into an internal /
human / future-external task and seeds 17 resolution tasks (all `pending`), 15 internal
evidence rows (counts only — units, owner relationships, aliases, source batches), and
23 pending review items. **Nothing is auto-resolved** (gaps stay `open`),
`external_calls_allowed=0`, `external_calls_required=7` is a future-work flag only, and
there is **no AI execution, no external/web calls, no publishing, no outreach.**

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/plan_source_gap_resolution.py \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
python3 scripts/cleanup_source_gap_resolution.py --profile-slug imperial-heights-goregaon-west
```

See `docs/PHASE_6_5_SOURCE_GAP_RESOLUTION_WORKFLOW.md`.

## Phase 6.6 Internal Evidence Acceptance

Phase 6.6 lets a human accept the **purely-internal, non-personal** evidence candidates
from Phase 6.5 so the system records which internal facts can be trusted for *future*
drafting. `scripts/review_internal_source_evidence.py` (dry-run default) sets
`internal_source_evidence.evidence_status` and moves the linked `internal_evidence_review`
`pending -> approved/rejected/needs_more_info`, tagging each change in `raw_context`
(`evidence_review_phase=6.6`) for a clean revert via
`scripts/revert_internal_source_evidence_review.py`. Guards refuse non-candidate rows,
out-of-profile evidence, any phone/email-like `safe_summary`, and batches over `--limit`.
Migration `schemas/017_internal_evidence_acceptance_dashboard.sql` adds 2 views
(`vw_internal_evidence_acceptance_dashboard`, `vw_imperial_heights_evidence_readiness`;
`ready_for_publish` hard-coded false). First batch accepted the **3 `building_alias`** rows
(→ 3 reviews approved); `active_owner_relationship_count` is deferred for building dedupe,
`inventory_hint` needs human review. **No gaps resolved** (still 17 open), `ready_for_ai_draft=0`,
`ready_for_publish=0`, **no AI execution, no external calls, no publishing, no outreach.**

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/review_internal_source_evidence.py --profile-slug imperial-heights-goregaon-west \
  --evidence-id <uuid[,uuid...]> --status accepted --reviewed-by <name> --real-ok [--apply]
python3 scripts/revert_internal_source_evidence_review.py --profile-slug imperial-heights-goregaon-west
```

See `docs/PHASE_6_6_INTERNAL_EVIDENCE_ACCEPTANCE.md`.

## Phase 6.7 Building-Anchor Dedupe Planning

Phase 6.7 plans (does **not** execute) the consolidation of two duplicate "Imperial
Heights" building anchors that split the active owner relationships and understated the
SEO profile's evidence counts. Migration
`schemas/018_building_dedupe_review_workflow.sql` adds 3 tables
(`building_duplicate_candidates`, `building_dedupe_review_items`,
`building_dedupe_action_log`) and 3 views (incl.
`vw_imperial_heights_building_anchor_summary`). `scripts/plan_building_dedupe.py`
(dry-run default) proposes canonical anchor `0e72db71` (it holds the web profile + 3
briefs) over duplicate `f05bbd01`, seeding **1** `pending_review` candidate (strength
`strong`) and **1** pending review item. `scripts/plan_building_dedupe_consolidation.py`
is **dry-run only** (no `--apply`) and previews what a future merge would move (1 alias /
1 unit / 1 relationship). **No building merged/deleted, no relationship moved, no SEO/
content changed, no gaps resolved**, and **no AI execution, no external calls, no
publishing, no outreach.** Reversible via `scripts/cleanup_building_dedupe_plan.py`.

```bash
# Dry-run default; real data needs --real-ok; writing needs --apply:
python3 scripts/plan_building_dedupe.py --building-name "Imperial Heights" \
  --profile-slug imperial-heights-goregaon-west --real-ok [--apply]
python3 scripts/plan_building_dedupe_consolidation.py --candidate-id <uuid>   # dry-run only
python3 scripts/cleanup_building_dedupe_plan.py --building-name "Imperial Heights"
```

See `docs/PHASE_6_7_BUILDING_DEDUPE_PLANNING.md`.

## Phase 6.8 MahaRERA Verification Foundation

Phase 6.8 lays the **schema + fake-workflow** foundation for future official
[MahaRERA](https://maharera.maharashtra.gov.in/) building verification — **no scraping,
no API calls, no browsing** from scripts. Migration
`schemas/019_rera_verification_foundation.sql` adds 6 tables (`rera_project_profiles`,
`rera_building_match_candidates`, `rera_carpet_area_records`, `rera_project_status_checks`,
`rera_area_mismatch_candidates`, `rera_verification_review_items`) and 6 views (incl.
`vw_imperial_heights_rera_readiness`, whose `ready_for_building_dedupe` needs an accepted
RERA match and `ready_for_content_fact_use` needs a verified profile with no blocker risk).
`scripts/seed_fake_rera_verification.py` seeds a clearly-fake, fully-removable test set
(1 fake building + RERA profile/match/areas/checks/mismatch/reviews);
`scripts/cleanup_fake_rera_verification.py` removes only those tagged rows;
`scripts/rera_verification_summary.py` is read-only counts. **No real building/SEO/content
changed, no MahaRERA/external call, no publishing, no outreach** — verified by seeding then
fully cleaning the fake batch. RERA is an **internal verification aid, not legal advice.**

```bash
python3 scripts/seed_fake_rera_verification.py [--apply --fake-ok]
python3 scripts/rera_verification_summary.py
python3 scripts/cleanup_fake_rera_verification.py [--apply]
```

See `docs/RERA_VERIFICATION_PIPELINE.md`.
