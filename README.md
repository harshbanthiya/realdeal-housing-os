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

## Phase 6.9 Manual MahaRERA Verification (Imperial Heights Wing C & D)

Phase 6.9 enters **real but review-gated** MahaRERA verification rows for Imperial Heights,
transcribed by a human from a manually-supplied official MahaRERA PDF snapshot (project
`P51800003270`, [view/6231](https://maharerait.maharashtra.gov.in/public/project/view/6231))
— **no scraping, no API, no browsing**. `scripts/apply_manual_rera_verification.py`
(dry-run default) creates 1 RERA profile (`needs_human_review`), 2 building-match
candidates (`candidate`, not accepted), 26 carpet-area records (`needs_human_review`, 213
apartments), 13 status/risk/document checks (litigation/complaint/non-compliance as
**counts only — no personal names**), and 6 pending review items (incl. a high-priority
`rera_address_review`). Per the operator note, **RERA street/boundary/lat/long are NOT
stored as trusted address** — `district/taluka/locality/pincode` left NULL, address left
for operator review; **no building merged, no internal address changed, no gap resolved,
nothing verified/accepted/published/sent.** Reversible via
`scripts/cleanup_manual_rera_verification.py`. The PDF is **not committed**.

```bash
python3 scripts/apply_manual_rera_verification.py --building-id 0e72db71-8b93-4ecd-879c-17d8d8f2b206 \
  --profile-slug imperial-heights-goregaon-west --rera-registration-number P51800003270 \
  --official-project-url https://maharerait.maharashtra.gov.in/public/project/view/6231 \
  --project-name "Imperial Heights Wing C and D" --real-ok [--apply]
python3 scripts/cleanup_manual_rera_verification.py            # dry-run
```

See `docs/PHASE_6_9_MANUAL_RERA_IMPERIAL_HEIGHTS.md`.

## Phase 6.10 Playwright MahaRERA Fetch Feasibility

Phase 6.10 is **setup + feasibility only** for opening JavaScript-rendered MahaRERA pages
with a headless browser and saving **raw, untrusted** snapshots — **no bulk scraping, no
DB writes, no CAPTCHA/auth bypass**. Playwright is an optional dev dependency
(`requirements-rera-fetch.txt`; `python3 -m playwright install chromium` — browser binaries
go to the per-user cache, never the repo). `scripts/fetch_rera_page_playwright.py` opens
**exactly one** allow-listed MahaRERA URL and saves `screenshot.png` / `page.html` /
`visible_text.txt` / `network_summary.json` / `metadata.json`
(`trusted_for_db=false`) under the **git-ignored** `exports/rera_snapshots/`.
`scripts/parse_rera_snapshot_placeholder.py` is a non-DB, counts-only prototype.
Feasibility test on `view/6231`: page opened (HTTP 200, no block, 37 network events) but
the SPA renders project data asynchronously, so a future capture must wait for
network-idle/selector. **No DB/RERA/building/content row changed; nothing published or
sent.** Snapshots are never committed.

```bash
python3 -m pip install -r requirements-rera-fetch.txt && python3 -m playwright install chromium
python3 scripts/fetch_rera_page_playwright.py --url "<one MahaRERA URL>" --output-label <label> --apply
python3 scripts/parse_rera_snapshot_placeholder.py --snapshot-folder exports/rera_snapshots/<folder>
```

See `docs/RERA_PLAYWRIGHT_FETCH_FEASIBILITY.md`.

## Phase 6.11 MahaRERA Headed Capture — External-Warning + CAPTCHA Gates

Phase 6.11 taught the single-URL capture script (`scripts/fetch_rera_page_playwright.py`) to
**detect** the two gates an operator observed on MahaRERA and to handle them safely — **no
bulk scraping, no DB writes, no CAPTCHA bypass/OCR/solver, no auto-submit**. (1) An
**external-site confirmation modal** is detected; YES is clicked **only** with
`--accept-external-warning` (allowlisted single URL), else the run stops with
`status=external_warning_required`. (2) A **CAPTCHA** is detected; **without
`--human-captcha-mode` the run stops** with `status=captcha_required`. With
`--human-captcha-mode` (headed), the script pauses and a **human** solves the CAPTCHA in the
visible browser themselves; only then does it capture `screenshot_after_human.png` + HTML +
visible text + network summary (counts-only; cookies/auth/tokens/queries redacted). The
script **never** reads, OCRs, solves, auto-submits, or services the CAPTCHA, and never prints
its text. Tests on `view/6231`: headless → `captcha_required` (safe stop, no DB writes);
headed with no human present → honest `captcha_still_present`, **no bypass**.
`scripts/parse_rera_snapshot_placeholder.py` (counts/booleans only) confirms a gated snapshot
is unparseable until a human clears the CAPTCHA. **No RERA match accepted, no profile
verified, no building merged, no source gap resolved, nothing published or sent.**

```bash
# Headless — stops safely at whichever gate appears (no human, no DB writes):
python3 scripts/fetch_rera_page_playwright.py --url "<one MahaRERA URL>" \
  --output-label <label> --save-screenshot --save-visible-text --save-html \
  --save-network-summary --apply

# Headed human-in-the-loop — operator solves the CAPTCHA, then presses Enter:
python3 scripts/fetch_rera_page_playwright.py --url "<one MahaRERA URL>" \
  --output-label <label> --headful --human-captcha-mode --pause-for-human \
  --save-screenshot --save-visible-text --save-html --save-network-summary --apply
```

See `docs/RERA_PLAYWRIGHT_FETCH_FEASIBILITY.md`.

## Phase 6.12 Operator-Assisted MahaRERA Post-CAPTCHA Capture

Phase 6.12 ran **one** operator-assisted capture on `project/view/6231`: the headed
`--human-captcha-mode --pause-for-human` flow opened a visible browser, a **real human
manually solved and submitted the CAPTCHA**, and the script then captured the rendered page
(`status=captured`, `captcha_solved_by_human=true`, `screenshot_after_human.png`). The
post-CAPTCHA snapshot holds the real project detail — `visible_text.txt` ~164 B → **~9.8 KB**,
`page.html` ~32 KB → **~315 KB**, network 37 → **116 requests / 75 JSON-like / 47 candidate
endpoints** — and the counts-only parser found **all eight** expected sections present
(Registration Number, Project Name, Project Status, Promoter, Building, Apartment/Unit
summary, Complaint, Litigation), so the snapshot is **suitable for a future review-gated
parser**. It stays **raw and untrusted** until human review. **No CAPTCHA bypass/OCR/solver,
no DB writes, no RERA match accepted, no profile verified, no building merged, no source gap
resolved, nothing published or sent.** Snapshots remain git-ignored under
`exports/rera_snapshots/` and are never committed. See
`docs/RERA_PLAYWRIGHT_FETCH_FEASIBILITY.md`.

## Phase 6.13 Review-Gated MahaRERA Snapshot Parser

Phase 6.13 parses the Phase 6.12 post-CAPTCHA snapshot into **untrusted, review-gated candidate
facts** and compares them to the Phase 6.9 manual rows — **no canonical writes, no personal
names stored**. Migration `schemas/020_rera_snapshot_parser_staging.sql` adds 4 staging tables
(`rera_snapshot_captures`, `rera_parsed_fact_candidates`, `rera_snapshot_compare_results`,
`rera_snapshot_review_items`) + 5 dashboards, incl.
`vw_imperial_heights_rera_parser_readiness` (`ready_to_update_rera_profile` /
`ready_for_content_fact_use` are **hard false**).
`scripts/parse_rera_snapshot_to_candidates.py` (dry-run default; `--real-ok` to read snapshot,
`--apply` to write; refuses unless the folder is under git-ignored `exports/rera_snapshots/`
and the profile/reg resolve) extracted **17 candidate facts** + **10 compare results
(6 matched / 0 mismatch / 4 pending_review)** in one transaction tagged `phase=6.13`. The
snapshot **corroborates** the manual data (reg `P51800003270`, status `Completed`, carpet 26,
apartments 213 all matched). Complaint/litigation/appeal/non-compliance are stored as
**counts only** (51 legal rows counted, **0 names stored**); the promoter **company** name is
an official public record. Canonical rows unchanged: profile `needs_human_review`, matches
`candidate`, carpet 26 / status 13 / review 6, buildings 2, gaps 17 open / 0 resolved,
`ready_for_publish=0`, nothing sent. `scripts/cleanup_rera_snapshot_parser_candidates.py`
(dry-run shown) removes only the tagged `phase=6.13` rows.

```bash
python3 scripts/parse_rera_snapshot_to_candidates.py \
  --snapshot-folder exports/rera_snapshots/<ts>_imperial_heights_wing_cd_6231_post_captcha \
  --profile-slug imperial-heights-goregaon-west \
  --rera-registration-number P51800003270 --real-ok [--apply]
```

See `docs/PHASE_6_13_RERA_SNAPSHOT_PARSER.md`. Next: **human review** of the parser
candidates via `vw_rera_snapshot_review_queue`.

## Phase 6.14 Human Review of RERA Snapshot Parser Candidates

Phase 6.14 is the first **reversible** human-review pass over the Phase 6.13 parser staging
outputs — **staging-only, no canonical writes, no external calls**.
`scripts/review_rera_snapshot_parser_candidates.py` (dry-run default; `--real-ok` to read,
`--apply` to write; safe helpers `--approve-safe-matched` / `--approve-privacy-safety`, with
`--limit` and a refusal that blocks `--approve-safe-matched` from touching risk/legal-count
items) approved the **6** non-personal `parser_manual_match_review` items (promoting 5 mapped
facts to `matched_manual`: registration number, project status, registration date, carpet row
count, apartment total) and the **4** `privacy_safety_review` items (each confirming
`personal_data_excluded=true` / `safe_for_public_use=false` — names excluded). The **4**
`risk_count_compare` + **1** capture `parsed_fact_review` items were **left pending** (legal
counts need human context). After apply: parsed facts = 5 matched_manual / 8 candidate / 4
needs_human_review; reviews = 10 approved / 5 pending. Canonical/manual rows unchanged: profile
`needs_human_review`, matches `candidate`, carpet 26 / status 13 / review 6, buildings 2, gaps
17 open / 0 resolved, `ready_for_publish=0`, nothing sent;
`ready_to_update_rera_profile` / `ready_for_content_fact_use` stay **false**. Changes are
stamped `review_phase=6.14` and reversible via `scripts/revert_rera_snapshot_parser_review.py`
(dry-run shown only).

```bash
python3 scripts/review_rera_snapshot_parser_candidates.py \
  --profile-slug imperial-heights-goregaon-west \
  --approve-safe-matched --approve-privacy-safety \
  --reviewed-by operator --limit 10 --real-ok [--apply]
```

See `docs/PHASE_6_14_RERA_PARSER_REVIEW.md`. Next: **profile verification + match acceptance**
after the remaining legal-context review.

## Phase 7.0 DLF Launch Command Center Foundation

Phase 7.0 pivots to **launch-growth operations**: a project-scoped command center to prepare a
high-priority **DLF** launch (~**August**) across Wix / SEO / blog / Instagram / YouTube Shorts /
WhatsApp / email / phone / referral / listing portals, with **later** n8n automation.
**Foundation + a review-gated seed only — no sends, no publishing, no external calls.**
Migration `schemas/021_launch_command_center.sql` adds 6 tables (`launch_projects`,
`launch_channels`, `launch_campaign_calendar`, `launch_lead_segments`, `launch_operator_tasks`,
`launch_readiness_checks`) + 7 dashboards (incl. `vw_dlf_launch_priority_dashboard`, whose
`ready_for_launch_push` is a real gate — **false** this phase).

**Naming guard:** the user says **“DLF Westend”**; public sources may say **“DLF The Westpark /
Westpark Phase-I, Andheri West.”** These are **not** assumed equal — the seed records both, sets
`name_confirmation_required=true`, and adds a **blocker** check `project_name_confirmed=pending`.

`scripts/seed_dlf_launch_command_center.py` (dry-run default; `--real-ok` to read, `--apply` to
write; refuses duplicate `launch_key` without `--allow-existing`) seeded **1 launch_project · 10
channels · 6 lead segments (counts only) · 11 readiness checks (3 blocker) · 11 operator tasks ·
30 calendar placeholders · 4 campaign_drafts · 4 ai_agent_tasks** — all send/publish disabled,
`status=draft/planned/pending`, tagged `phase=7.0`. **No contacts selected (contacts still 4), no
inbound leads, nothing sent/published, no external calls.** DLF rollup:
`ready_for_launch_push=false`, `send_enabled_count=0`, `publish_enabled_count=0`, blocked on
project-name confirmation. `scripts/cleanup_dlf_launch_command_center.py` (dry-run shown; 77 rows)
removes only the tagged `phase=7.0` rows and refuses if any send/publish/sent flag is set.

```bash
python3 scripts/seed_dlf_launch_command_center.py \
  --launch-key dlf-westpark-andheri-west \
  --project-display-name "DLF Westend / The Westpark Andheri West" \
  --internal-alias "DLF Westend" --expected-launch-month "August" --real-ok [--apply]
```

See `docs/PHASE_7_0_DLF_LAUNCH_COMMAND_CENTER.md`. Next: confirm project name/RERA → landing-page
brief → campaign copy drafts → contact permission review → n8n lead-intake plan.

## Phase 7.1 DLF Launch Funnel & Campaign Draft Workspace

Phase 7.1 builds the full launch funnel on top of the 7.0 command center
(`Audience → Message → Landing Page → Lead Form → Qualification → Follow-up → Site Visit →
Booking Intent → Closed/Lost/Nurture`) — **schema + a review-gated draft seed only, no sends, no
publishing, no external calls.** Migration `schemas/022_launch_funnel_workspace.sql` adds 8 tables
(`launch_landing_page_specs`, `launch_lead_capture_forms`, `launch_utm_campaign_specs`,
`launch_content_pillars`, `launch_message_templates`, `launch_social_content_drafts`,
`launch_lead_scoring_rules`, `launch_draft_review_items`) + 9 dashboards (the message/social views
expose only `body_char_count` / `caption_char_count`, **never full copy**; the rollup
`vw_dlf_launch_funnel_readiness` keeps `ready_for_launch_push` a real gate — **false** this phase).

`scripts/seed_dlf_launch_funnel_workspace.py` (dry-run default; `--real-ok` to read, `--apply` to
write; refuses if launch project missing or rows already exist without `--allow-existing`) seeded
**1 landing-page spec · 1 lead-capture form · 8 UTM specs · 10 content pillars · 13 message
templates (7 WhatsApp / 4 email / 1 phone / 1 referral) · 15 social drafts · 10 lead-scoring rules
· 60 review items · 2 new readiness checks**, all `draft`/`pending`, `send_enabled=false`,
`publish_enabled=false`, `human_review_required=true`, tagged `phase=7.1`. Draft copy uses only
compliant placeholders (`[PROJECT_NAME_CONFIRM]`, `[RERA_VERIFY]`, `[PRICE_VERIFY]`,
`[BROCHURE_LINK_PENDING]`, `[WIX_PAGE_PENDING]`, `[VERIFY]`) with opt-out lines — no false
scarcity, guaranteed returns, unverified RERA, or exact price. **No contacts selected (contacts
still 4), no leads, nothing sent/published, no external calls.** Funnel rollup:
`ready_for_launch_push=false`, send/publish counts `0`, blocked on project-name + consent.
`scripts/cleanup_dlf_launch_funnel_workspace.py` (dry-run shown; 120 rows) removes only the tagged
`phase=7.1` rows and refuses if any send/publish/sent flag is set.

```bash
python3 scripts/seed_dlf_launch_funnel_workspace.py \
  --launch-key dlf-westpark-andheri-west --real-ok [--apply]
```

See `docs/PHASE_7_1_DLF_LAUNCH_FUNNEL_WORKSPACE.md`. Next: confirm project name → contact
permission review → Wix form/lead-intake plan → n8n workflow plan → approve first campaign copy.

## Phase 7.2 DLF Contact Segmentation And Permission Review

Phase 7.2 adds a masked, review-gated contact segmentation layer for the DLF launch.
Migration `schemas/023_launch_contact_segmentation.sql` adds candidate, permission-review, and
audit tables plus 4 dashboards. The planner created **5** segment candidates and **19** pending
permission review items: 2 active-owner candidates and 3 existing warm-contact candidates.

No candidates were approved, no campaign selection happened, `send_enabled=0`,
`communication_sent=0`, contacts stayed 4, and raw contact values are never exposed.

```bash
python3 scripts/plan_dlf_contact_segments.py \
  --launch-key dlf-westpark-andheri-west --limit 50 --real-ok [--apply]
python3 scripts/cleanup_dlf_contact_segments.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

See `docs/PHASE_7_2_DLF_CONTACT_SEGMENTATION_PERMISSION_REVIEW.md`. Next: human permission +
suppression review, or Wix/n8n lead intake planning.

## Phase 7.3 DLF Lead Intake And Attribution Plan

Phase 7.3 adds the review-gated lead-intake foundation for the DLF launch. Migration
`schemas/024_dlf_lead_intake_attribution.sql` adds 5 tables
(`launch_lead_intake_endpoints`, `launch_lead_field_mappings`,
`launch_lead_attribution_rules`, `launch_inbound_lead_review_items`,
`launch_operator_daily_metrics`) plus 6 dashboards, including
`vw_dlf_lead_intake_readiness`. The readiness view hard-blocks live capture:
`ready_for_live_lead_capture=false` and `external_call_allowed_count=0`.

`scripts/seed_dlf_lead_intake_plan.py` (dry-run default; `--real-ok`; `--apply` to write)
seeds **8 planned endpoints, 18 draft field mappings, attribution rules from the 8 Phase-7.1 UTM
specs, 30 zero-valued daily metric placeholders, and 5 pending readiness checks**. Endpoints
remain `planned`, field/rule rows remain `draft`, no inbound leads or contacts are created, no
external APIs are called, no live webhooks are created, and nothing is sent or published. Cleanup
is dry-run first via `scripts/cleanup_dlf_lead_intake_plan.py` and refuses if any endpoint became
active, any external call was allowed, or any lead/contact exists from the seed tag.

```bash
python3 scripts/seed_dlf_lead_intake_plan.py \
  --launch-key dlf-westpark-andheri-west --real-ok [--apply]
python3 scripts/cleanup_dlf_lead_intake_plan.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

See `docs/PHASE_7_3_DLF_LEAD_INTAKE_ATTRIBUTION_PLAN.md`. Next: n8n workflow dry-run planning,
operator dashboard polish, or a fully cleaned fake-lead round-trip.

## Phase 7.4 DLF n8n Workflow Blueprint

Phase 7.4 adds the review-gated n8n automation blueprint layer without creating anything in n8n.
Migration `schemas/025_n8n_launch_workflow_blueprint.sql` adds 5 tables
(`launch_n8n_workflow_blueprints`, `launch_n8n_workflow_nodes`,
`launch_n8n_payload_schemas`, `launch_n8n_test_cases`, `launch_n8n_review_items`) plus 6
dashboards, including `vw_dlf_n8n_readiness`. The readiness rollup keeps
`ready_to_build_in_n8n=false`, `ready_to_activate=false`, and `external_call_allowed_count=0`
until a later review phase.

`scripts/seed_dlf_n8n_workflow_blueprint.py` (dry-run default; `--real-ok`; `--apply` to write)
seeds **6 planned workflow blueprints, 20 planned nodes, 1 draft payload schema, 7 fake-only test
cases, and 18 pending review items**. No n8n API is called, no workflow or webhook is created, no
inbound lead/contact is created, and nothing is sent or published. Cleanup is dry-run first via
`scripts/cleanup_dlf_n8n_workflow_blueprint.py` and refuses if any workflow was built/activated,
any external call was allowed, any test case executed, or any inbound lead exists from the seed
tag.

```bash
python3 scripts/seed_dlf_n8n_workflow_blueprint.py \
  --launch-key dlf-westpark-andheri-west --real-ok [--apply]
python3 scripts/cleanup_dlf_n8n_workflow_blueprint.py \
  --launch-key dlf-westpark-andheri-west --real-ok
```

See `docs/PHASE_7_4_DLF_N8N_WORKFLOW_BLUEPRINT.md`. Next: human blueprint approval, then a
separate guarded build phase.

## Phase 7.5 DLF Operator Cockpit

Phase 7.5 adds a view-only human cockpit for daily DLF launch execution. Migration
`schemas/026_dlf_operator_cockpit.sql` adds 9 dashboard views:
`vw_dlf_operator_cockpit_home`, `vw_dlf_operator_today_tasks`,
`vw_dlf_operator_review_backlog`, `vw_dlf_operator_campaign_calendar_next_14_days`,
`vw_dlf_operator_audience_readiness`, `vw_dlf_operator_lead_intake_readiness`,
`vw_dlf_operator_n8n_readiness`, `vw_dlf_operator_content_readiness`, and
`vw_dlf_operator_safety_posture`. The cockpit combines blockers, today tasks, review backlog,
calendar placeholders, audience readiness, lead-intake readiness, n8n readiness, content
readiness, and safety posture without exposing raw contact values or full copy bodies.

`scripts/dlf_operator_cockpit_summary.py` prints the cockpit as counts only. The expected safety
posture remains `safe_blocked`: `send_enabled=0`, `publish_enabled=0`, external automation off,
no live lead capture, no campaign-approved contacts, no communications sent, and no publishing.

```bash
python3 scripts/dlf_operator_cockpit_summary.py \
  --launch-key dlf-westpark-andheri-west
```

See `docs/PHASE_7_5_DLF_OPERATOR_COCKPIT.md`. Next: work the blocker/review queues; activation
requires separate explicit approval.

## Phase 7.6 DLF Launch Blocker Triage & Project-Name Confirmation

Phase 7.6 adds safe blocker-triage views plus guarded tooling to confirm the public project name
**only when an operator explicitly supplies it**. Migration `schemas/027_dlf_launch_blocker_triage.sql`
adds 3 views (no new tables): `vw_dlf_launch_blocker_triage` (open blockers grouped by area —
project_identity / consent / suppression / copy_review / lead_capture / n8n / publishing / sending),
`vw_dlf_project_identity_status` (name-confirmation state; `public_name_ready_for_copy=false` until
confirmed), and `vw_dlf_launch_activation_guardrail` (the hard activation guardrail + `hard_stop_reason`).

Scripts (all dry-run by default; writes require `--real-ok` **and** `--apply`):

```bash
# Confirm the public name — ONLY with an operator-supplied confirmed name:
python3 scripts/confirm_dlf_project_identity.py \
  --launch-key dlf-westpark-andheri-west \
  --confirmed-project-display-name "<OPERATOR-SUPPLIED NAME>" \
  --confirmed-by "h b" --decision-notes "..." --real-ok --apply

# Review a non-activation readiness check:
python3 scripts/review_dlf_launch_readiness_check.py \
  --check-type consent_ready --status needs_review --reviewed-by "h b" --real-ok --apply

# Revert a Phase 7.6 confirmation:
python3 scripts/revert_dlf_project_identity_confirmation.py --real-ok --apply
```

In this phase the operator confirmed the public name **DLF Westpark** (slug
`dlf-westpark-andheri-west`), applied via the confirmation tool: `project_display_name` = `DLF
Westpark`, `project_name_confirmed=true` (readiness check **passed**, `verify_project_name` task
**done**), previous name `DLF Westend / The Westpark Andheri West` captured. This is an
operator-confirmed identity, **not** web-verified. The launch still stays `safe_blocked` —
`ready_for_launch_push=false` — because consent, suppression, copy, lead capture, and n8n are not
ready (hard-stop reason advanced to *3 blocker readiness checks outstanding*). The
confirmation/readiness scripts refuse to enable send/publish, activate n8n, or mark
`ready_for_launch_push`, with in-transaction guards that roll back if any activation flag would flip.
See `docs/PHASE_7_6_DLF_LAUNCH_BLOCKER_TRIAGE.md`.

## Phase 7.7 DLF Westpark Campaign Copy & Consent Review

Phase 7.7 is an internal review of the DLF launch campaign copy and consent/opt-out language. Script
`scripts/review_dlf_campaign_copy.py` (dry-run by default; writes need `--real-ok` + `--apply`)
replaces the confirmed-name placeholder `[PROJECT_NAME_CONFIRM]` → **DLF Westpark** in draft text
fields (templates / social / landing), then marks copy/consent `launch_draft_review_items`:
internally-clean copy → `approved`, copy that still carries a factual placeholder
(`[RERA_VERIFY]`/`[PRICE_VERIFY]`/`[BROCHURE_LINK_PENDING]`/`[WIX_PAGE_PENDING]`/`[VERIFY]`/
`[VISUAL_DIRECTION_PENDING]`) → `needs_more_info`. Result this phase: project-name placeholder count
**0**; **8 approved**, **21 needs_more_info**; factual placeholders preserved.

It writes only draft text + `raw_context` and the review marks. It never enables send/publish, never
passes any readiness check (so `whatsapp_template_approved` stays **pending** — provider approval is
out of scope), and never touches contacts/leads; an in-transaction guard rolls back if any activation
flag would flip. Launch stays `safe_blocked`, `ready_for_launch_push=false`, send/publish 0,
contacts 4, leads 0. Reversible via `scripts/revert_dlf_campaign_copy_review.py`. See
`docs/PHASE_7_7_DLF_CAMPAIGN_COPY_REVIEW.md`.

## Phase 7.8 DLF Consent, Suppression & Lead-Privacy Readiness

Phase 7.8 reviews the process-level consent/privacy posture. Migration
`schemas/029_dlf_consent_privacy_readiness.sql` adds 1 audit table
(`launch_consent_privacy_review_log`) and 4 views (`vw_dlf_consent_privacy_readiness`,
`vw_dlf_contact_permission_gap_dashboard`, `vw_dlf_lead_form_privacy_dashboard`,
`vw_dlf_suppression_readiness_dashboard`). Script `scripts/review_dlf_consent_privacy_readiness.py`
(dry-run by default; writes need `--real-ok` + `--apply`) logs the lead-form-consent /
privacy-field-mapping / suppression PROCESS as process_approved, marks **lead_privacy_reviewed
passed** (form has consent fields + PII mappings, no live capture), moves the 9 WhatsApp/email
permission reviews to **needs_more_info**, and sets **consent_ready needs_review** (never passed —
there are 0 `channel_permissions` allowed).

It never grants a channel permission, never approves a contact for campaign (`approved_for_segment`
stays 0), never passes `whatsapp_template_approved` (provider approval is external — stays pending),
and never passes `suppression_checked` (process approved ≠ executed). An in-transaction guard rolls
back if any of those — or any send/publish/n8n activation — would happen. Launch stays
`safe_blocked`, `ready_for_launch_push=false`, send/publish 0, contacts 4, leads 0. Reversible via
`scripts/revert_dlf_consent_privacy_readiness.py`. See `docs/PHASE_7_8_DLF_CONSENT_PRIVACY_READINESS.md`.

## Phase 7.9 DLF Contact Permission Evidence & Suppression Review

Phase 7.9 adds an evidence-based permission/suppression review. Migration
`schemas/030_dlf_contact_permission_evidence.sql` adds 3 tables
(`launch_contact_permission_evidence`, `launch_contact_suppression_checks`,
`launch_contact_permission_decision_log`) and 4 masked views
(`vw_dlf_contact_permission_evidence_dashboard`, `vw_dlf_contact_suppression_check_dashboard`,
`vw_dlf_contact_permission_decision_dashboard`, `vw_dlf_campaign_selection_guardrail`). Script
`scripts/review_dlf_contact_permission_evidence.py` (dry-run by default; writes need `--real-ok` +
`--apply`) created **10** evidence rows (5 candidates × whatsapp/email, all **needs_more_info** — 0
allowed, since 0 `channel_permissions` allowed), **5** suppression checks (all **clear**, no list
write), approved the 5 `suppression_review` items (suppression-list clear only, **not** consent), and
logged 30 audit rows.

`permission_decision='allowed'` is only ever derived from a real `channel_permissions` allowed row;
an in-transaction guard refuses any unbacked `allowed`/`suppressed`, any approved-for-segment
candidate, a granted permission, a passed `consent_ready`/`whatsapp_template_approved`, or any
send/publish/n8n activation. Candidates stay `needs_permission_review`, `approved_for_segment=0`,
`ready_for_campaign_selection=false`, `consent_ready` needs_review, launch `safe_blocked`, send/publish
0, contacts 4, leads 0. Reversible via `scripts/revert_dlf_contact_permission_evidence.py`. See
`docs/PHASE_7_9_DLF_CONTACT_PERMISSION_EVIDENCE.md`.

## Phase 7.10 DLF Controlled Test Lead Intake

Phase 7.10 proves the lead-intake validation path with **fake/test payloads only**. Migration
`schemas/031_dlf_test_lead_intake_harness.sql` adds 3 tables (`launch_test_lead_payloads`,
`launch_test_lead_validation_results`, `launch_test_lead_review_items`) and 4 views
(`vw_dlf_test_lead_payload_dashboard`, `vw_dlf_test_lead_validation_dashboard`,
`vw_dlf_test_lead_review_queue`, `vw_dlf_test_lead_readiness` — dashboards expose no fake
name/phone/email). Script `scripts/run_dlf_test_lead_intake.py` (dry-run by default; writes need
`--real-ok` + `--apply`) created **5** fake payloads (valid brochure, missing consent, missing
phone/email, high-budget, referral) → 3 validated / 2 failed, **40** validations (37 passed / 2 failed
/ 1 needs_review), **13** review items. All payloads `uses_fake_data=true`,
`creates_real_lead/contact=false`, `external_call_made=false`.

It never touches the real `inbound_leads`/`contacts` tables, calls no API/webhook, and an
in-transaction guard refuses any real/external test residue, send/publish, or a true
`ready_for_launch_push`/`ready_for_live_lead_capture`. `inbound_leads` stays 0, contacts 4,
`ready_for_live_lead_capture=false`, launch `safe_blocked`. Test rows are **retained** for dashboard QA
(clearly fake, tagged `phase=7.10`); remove with `scripts/cleanup_dlf_test_lead_intake.py`. See
`docs/PHASE_7_10_DLF_TEST_LEAD_INTAKE.md`.

## Phase 7.11 DLF Inactive n8n Workflow Build Package

Phase 7.11 prepares an importable but **inactive** n8n workflow template package for DLF lead intake.
Migration `schemas/032_dlf_n8n_build_package.sql` adds 3 tracking tables
(`launch_n8n_build_packages`, `launch_n8n_build_validation_results`,
`launch_n8n_build_review_items`) and 4 views (`vw_dlf_n8n_build_package_dashboard`,
`vw_dlf_n8n_build_validation_dashboard`, `vw_dlf_n8n_build_review_queue`,
`vw_dlf_n8n_build_readiness`). The generator `scripts/create_dlf_n8n_workflow_template.py` writes the
local artifact to ignored `exports/n8n_templates/dlf-westpark-lead-intake-inactive-template.json` and
records 1 validated build package, 7 passed validations, and 5 pending review items.

The package contains no credentials, no live webhook URL, no webhook secret, no active workflow flag,
and no executable send nodes. It does not call n8n, does not create/import/activate a workflow, does
not create a live webhook, and does not touch real leads or contacts. `workflow_created_in_n8n=0`,
`activation_requested=0`, `ready_for_manual_import=false`, `ready_to_activate=false`, inbound leads 0,
contacts 4, send/publish 0. Cleanup dry-run: `scripts/cleanup_dlf_n8n_build_package.py`. See
`docs/PHASE_7_11_DLF_N8N_BUILD_PACKAGE.md`.

## Phase 7.12 DLF n8n Build Package Review

Phase 7.12 reviews the inactive n8n package for **manual import readiness only**. Script
`scripts/review_dlf_n8n_build_package.py` (dry-run by default; writes need `--real-ok` + `--apply`)
approved the safe build-package, security, privacy, and manual-import review items, moved the
activation blocker to `needs_more_info`, and set the package to `approved_for_manual_import`.

This does not call n8n, import/create a workflow, create a webhook, or request activation.
`ready_for_manual_import=true`, but `ready_to_activate=false`, `workflow_created_in_n8n=0`,
`activation_requested=0`, and active workflows 0. `inbound_leads=0`, contacts 4, send/publish 0,
communications 0. Rollback dry-run: `scripts/revert_dlf_n8n_build_package_review.py`. See
`docs/PHASE_7_12_DLF_N8N_BUILD_PACKAGE_REVIEW.md`.

## Phase 7.13 DLF n8n Manual Import Verification

Phase 7.13 adds the human-only inactive manual-import verification layer. Migration
`schemas/033_dlf_n8n_manual_import_verification.sql` adds `launch_n8n_manual_import_checks` plus
`vw_dlf_n8n_manual_import_check_dashboard` and `vw_dlf_n8n_manual_import_readiness`.

No manual import happened in this phase, so `scripts/record_dlf_n8n_manual_import_check.py` recorded
one pending no-import check only. The package remains `approved_for_manual_import`,
`workflow_created_in_n8n=false`, `activation_requested=false`, all blueprints remain
`planned`/`not_created`, and `ready_to_activate=false`. Rollback dry-run:
`scripts/revert_dlf_n8n_manual_import_check.py`. See
`docs/PHASE_7_13_DLF_N8N_MANUAL_IMPORT_VERIFICATION.md`.

## Phase 7.14 DLF Wix Landing Page & Lead Form Build Package

Phase 7.14 prepares a safe, human-buildable Wix landing page + lead form package for DLF Westpark.
Migration `schemas/034_dlf_wix_landing_build_package.sql` adds `launch_wix_build_packages`,
`launch_wix_build_validation_results`, and `launch_wix_build_review_items` plus
`vw_dlf_wix_build_package_dashboard`, `vw_dlf_wix_build_validation_dashboard`,
`vw_dlf_wix_build_review_queue`, and `vw_dlf_wix_build_readiness`.

`scripts/create_dlf_wix_landing_build_package.py` (dry-run by default; `--real-ok --apply` to write)
generates one git-ignored Markdown artifact under `exports/wix_build_packages/` plus 1 `validated`
package, 8 passed validations, and 6 pending review items. It calls no Wix API, creates/publishes no
Wix page, and creates no live form/webhook. Unverified facts stay as placeholders (`RERA_VERIFY`,
`PRICE_VERIFY`, `BROCHURE_LINK_PENDING`, `WIX_PAGE_PENDING`, `VERIFY`, `VISUAL_DIRECTION_PENDING`).
`wix_page_created`/`wix_page_published`/`live_form_created` stay 0; `ready_to_publish`,
`ready_for_live_lead_capture`, and `ready_for_launch_push` stay false. Cleanup dry-run:
`scripts/cleanup_dlf_wix_landing_build_package.py`. See
`docs/PHASE_7_14_DLF_WIX_LANDING_BUILD_PACKAGE.md`.

## Phase 7.15 Wix Website UX, SEO & Integration Masterplan

Phase 7.15 upgrades from a single landing-page package to a unified Wix website experience plan.
Migration `schemas/035_wix_ux_integration_masterplan.sql` adds `wix_site_experience_blueprints`,
`wix_page_blueprints`, `wix_integration_readiness_items`, `wix_design_component_specs`,
`wix_ux_review_items` plus six views including `vw_dlf_wix_unified_experience_readiness`
(`ready_to_publish` hard-false).

`scripts/seed_dlf_wix_ux_integration_masterplan.py` (dry-run by default; `--real-ok --apply` to write)
seeds 1 site experience blueprint, 7 page blueprints, 11 integration readiness items, 11 design
component specs, and 31 pending review items for DLF Westpark. Planning only: no Wix/Meta/WhatsApp/
email/n8n/Google API call, no publishing, no live form/webhook, no sends. Every integration stays
`external_call_allowed=false`, every page `publish_enabled=false`; `ready_for_manual_wix_build`,
`ready_for_tracking_connection`, and `ready_to_publish` stay false. High-end Fable UI/UX design and
optional Three.js visuals are deferred to a future phase (`fable_handoff_future_phase=true`). Cleanup
dry-run: `scripts/cleanup_dlf_wix_ux_integration_masterplan.py`. See
`docs/PHASE_7_15_WIX_UX_INTEGRATION_MASTERPLAN.md`.

## Phase 7.16 Fable UI/UX Handoff Package

Phase 7.16 distills the approved Phase 7.15 masterplan into a privacy-safe Fable handoff package.
Migration `schemas/036_fable_uiux_handoff_package.sql` adds `fable_uiux_handoff_packages`,
`fable_uiux_handoff_sections`, `fable_uiux_handoff_validation_results`,
`fable_uiux_handoff_review_items` plus five views including `vw_dlf_fable_handoff_readiness`.

`scripts/create_dlf_fable_uiux_handoff_package.py` (dry-run by default; `--real-ok --apply` to write)
generates two git-ignored Markdown artifacts under `exports/fable_handoffs/` — a concise Fable prompt
(~2.2 KB) and a detailed design brief — plus 1 `generated` package, 12 sections, 9 passed
validations, and 7 pending reviews. Artifacts carry only public/business-safe design direction
(Apple-inspired luxury, mobile-first, SEO/Wix constraints, placeholder rules); a direct scan confirms
no contact data, secrets, or DB IDs. No Fable call and no Wix/Meta/WhatsApp/email/n8n call happen:
`fable_call_made_count`/`external_call_made_count` stay 0 and `ready_for_fable_use` stays false until
reviews are approved. The operator pastes the concise prompt into Fable manually. Cleanup dry-run:
`scripts/cleanup_dlf_fable_uiux_handoff_package.py`. See
`docs/PHASE_7_16_FABLE_UIUX_HANDOFF_PACKAGE.md`.

## Phase 7.17 Fable "Gallery White" + Gemini Output Review

Phase 7.17 captures the manually generated Fable design output (**"DLF Westpark — Gallery
White"**) and the Gemini second-opinion critique into review-gated rows, and records the
concrete design refinements extracted from that critique. Migration
`schemas/037_fable_design_output_review.sql` adds `fable_design_outputs`,
`design_second_opinion_reviews`, `design_refinement_actions`, `fable_design_review_items`
plus five views including the real gate `vw_dlf_design_output_readiness`.

`scripts/capture_dlf_fable_design_output.py` (dry-run by default; `--real-ok --apply` to
write) scans the raw artifacts for leakage (emails, phone-like strings, DB UUIDs, secrets —
all 0), then records 1 captured output, 1 captured Gemini review, 12 proposed refinement
actions, and 14 pending review items. The raw Fable/Gemini files stay git-ignored under
`exports/` — the database stores only paths plus business-safe summaries, never raw text.
No Fable/Gemini/Wix/Meta/WhatsApp/email/n8n call happens: `external_call_made_count` stays 0,
and `ready_for_wix_design_build` stays false until a human approves the output and at least
one refinement action. Cleanup dry-run:
`scripts/cleanup_dlf_fable_design_output_capture.py`. See
`docs/PHASE_7_17_FABLE_GEMINI_OUTPUT_REVIEW.md`.

## Phase 7.18 Gallery White Approved Design Direction

Phase 7.18 records the human review decision: **"Gallery White" is accepted as the DLF Westpark
public website design direction**, the Gemini critique is accepted as guidance, and all twelve
refinement actions are accepted. `scripts/review_dlf_gallery_white_design_direction.py` (dry-run
by default; `--real-ok --apply`, with required `--reviewed-by`/`--decision-notes`) sets the
captured output to `accepted_direction`, the Gemini review to `accepted_guidance`, the 12
`design_refinement_actions` to `accepted`, and approves all 14 `fable_design_review_items` — which
flips the computed `vw_dlf_design_output_readiness` to `ready_for_fable_followup = true` and
`ready_for_wix_design_build = true`.

No Fable/Gemini/Wix/Meta/WhatsApp/email/n8n call happens; no publishing, no live forms/webhooks, no
contact/lead/message changes. `external_call_made_count` stays 0 and `ready_for_launch_push` stays
false — `ready_for_wix_design_build` is a design-readiness signal, not a launch gate. An
in-transaction guard refuses on any contact-data/secret/external/send/publish/launch flag. Reversible
via `scripts/revert_dlf_gallery_white_design_review.py` (dry-run by default). The approved, refined
spec is in `docs/PHASE_7_18_GALLERY_WHITE_APPROVED_DESIGN_SPEC.md`.

## Phase 7.19 Wix Staging / Preview-Site Plan

Phase 7.19 plans a **safe Wix staging/preview site** so the Gallery White design can be built and
tested visually before touching the live domain. Migration
`schemas/038_dlf_wix_staging_site_plan.sql` adds `wix_staging_sites`,
`wix_staging_build_checklist_items`, `wix_staging_qa_checks`, `wix_staging_review_items` plus five
views including the real gate `vw_dlf_wix_staging_readiness`.

`scripts/seed_dlf_wix_staging_site_plan.py` (dry-run by default; `--real-ok --apply`) seeds 1
`planned` staging site, a 20-item Gallery White build checklist, 13 pre-publish QA checks, and 7
pending review items. Every staging live flag stays false: no real domain, no public indexing, no
Wix API call, no page created/published, no live form/webhook, no external tracking. The readiness
view shows `ready_for_manual_staging_build = true`, `ready_for_staging_qa = false` (until the manual
build exists), and `ready_for_production_publish = false` (always). No Wix/n8n/Meta/Google/WhatsApp/
email call; no publishing; no leads/contacts/messages changed. Cleanup dry-run:
`scripts/cleanup_dlf_wix_staging_site_plan.py`. See
`docs/PHASE_7_19_WIX_STAGING_PREVIEW_SITE_PLAN.md`.

## Phase 7.20 Manual Wix Staging Build Tracking

Phase 7.20 tracks the **human/manual** Wix staging build without calling any Wix API or reading any
Wix API key. Migration `schemas/039_dlf_wix_staging_build_tracking.sql` adds the append-only
`wix_staging_build_action_log` plus `vw_wix_staging_build_action_log_dashboard` and
`vw_dlf_wix_staging_build_progress`.

`scripts/record_dlf_wix_staging_build_progress.py` (dry-run by default; `--real-ok --apply`, with
required `--performed-by`/`--decision-notes`) records manual build progress: it moves selected
setup/safety checklist and absence-QA items forward, optionally records an operator-supplied staging
site name/URL (only with `--confirm-staging-site-created-manually` **and** real details — it never
fabricates a site), and logs that **Wix API permission/key usage is deferred** to a later
capability-map phase. `--mark-safety-checks-passed` requires all six `--confirm-*` safety flags.

In this phase no manual staging site was supplied, so build tracking was initialized only: the 2
setup checklist items moved to `in_progress` and the API-deferral was logged (3 audit rows). No Wix
API call, no API key read/stored, no real domain, no public indexing, no published page, no live
form/webhook, no external tracking; `ready_for_production_publish` and `ready_for_fake_lead_test`
stay false; no leads/contacts/messages changed. Reversible via
`scripts/revert_dlf_wix_staging_build_progress.py` (dry-run by default). See
`docs/PHASE_7_20_WIX_STAGING_BUILD_TRACKING.md`.

## Phase 7.21 Wix API Permission & Capability Map

Phase 7.21 builds a review-gated map of Wix API permissions → OS capabilities, defines **future**
API-key profiles, and queues human review **before any key is created or used** — storing **no
secrets and no API keys**. Migration `schemas/040_wix_api_permission_capability_map.sql` adds
`wix_api_permission_catalog`, `wix_api_integration_use_cases`, `wix_api_key_profiles`,
`wix_api_permission_review_items` plus five views including the real gate `vw_dlf_wix_api_readiness`.

`scripts/seed_wix_api_permission_capability_map.py` (dry-run by default; `--real-ok --apply`) seeds
46 permission catalog rows (6 `allow_staging_only`, 3 `read_only_preferred`, 14 `allow_later`, 3
`defer`, 20 `avoid`), 16 integration use cases, 4 planned key profiles (staging discovery / staging
build later / tracking later / production future — all `secret_value_stored=false`,
`external_call_allowed=false`), and 10 pending review items. No Wix API call, no API key
requested/read/stored, no `.env` Wix-secret inspection, no publish/send/leads/contacts. The readiness
view keeps `active_key_profiles`, `external_call_allowed_count`, `publish_permission_allowed_count`,
`send_permission_allowed_count` at 0 and `ready_for_api_call_test=false`. Cleanup dry-run:
`scripts/cleanup_wix_api_permission_capability_map.py`. See
`docs/PHASE_7_21_WIX_API_PERMISSION_CAPABILITY_MAP.md`.

## Phase 7.22 Manual Wix Staging Site Recorded

Phase 7.22 records the **manually created** Wix staging/preview site (built by the operator outside
the OS) and marks initial Gallery White build progress — reusing the Phase 7.20 tracking script, no
new migration. The staging site is now `created_manually` with its name and a `*.wixstudio.com`
preview URL stored in `wix_staging_sites` (DB only; the literal URL is not committed to the repo). The
Gallery White shell build moved hero/navigation/content sections to `in_progress` (12 checklist items
in progress), and the safety checklist + absence QA (`domain_not_connected`, `noindex`,
`webhook_disabled`, `tracking_disabled`) are passed (2 checklist + 5 QA).

Every live gate stays off: no real domain, no public indexing, no published page, no live
form/webhook, no external tracking, no Wix API call, no API key read/stored (deferral re-logged).
`ready_for_staging_qa` is now true; `ready_for_fake_lead_test` and `ready_for_production_publish` stay
false; no leads/contacts/messages changed. Reversible via
`scripts/revert_dlf_wix_staging_build_progress.py` (dry-run by default). See
`docs/PHASE_7_22_WIX_STAGING_SITE_RECORDED.md`.
