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
