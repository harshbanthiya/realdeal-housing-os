# Property Hint To Relationship Workflow (Phase 5.2)

Phase 5.2 turns source-aware property hints into reviewable building, unit, and
contact relationship candidates. This is still review-first and guarded: no real
owner sheet import, no canonical contact merge, and no outreach.

## What Property Hints Are

Property hints are non-canonical clues captured during source-aware imports. They
live in `contact_property_hints` or in parsed fields on source rows, such as:

- building name or building code
- wing
- unit number
- relationship type, such as owner, tenant, broker, buyer, or business lead
- source row and source file references

Hints are evidence, not facts. They preserve what the source appeared to say while
keeping the final building/unit/contact relationship behind review.

## How Hints Become Candidates

`scripts/plan_property_relationship_candidates.py` is the read-only planner. It
counts possible candidate rows from:

- `contact_property_hints`
- parsed building/unit fields from `contact_import_rows` that do not already have
  a `contact_property_hints` row
- `inventory_import_rows`
- `lead_requirements`

The planner prints counts only. It does not create buildings, aliases, units,
relationships, review items, contacts, messages, or tasks.

Candidate logic:

- A building name/code without a canonical building can become a building alias
  candidate.
- Wing/unit details can become a building unit candidate.
- A hint with a canonical/test contact and enough building/unit evidence can become
  a `contact_property_relationships` candidate.
- Every materialized relationship remains `pending_review` and gets a
  `property_relationship_review_items` queue item.

## Why A Canonical Contact Is Required

Real relationships must point to a reviewed canonical `contacts` row. Source rows
can contain duplicates, old values, partial names, or unrelated business records.
Creating real property relationships before canonical contact approval would make
the relationship graph hard to trust and hard to roll back.

For this reason, the planner skips rows with no canonical contact as
`skip:needs_canonical_contact`. The fake Phase 5.2 harness uses only a tagged
`is_test=true` contact so the path can be tested without touching real people.

## Building Alias Review

Imported building labels can be inconsistent. A source might use a code, short name,
spelling variant, sheet tab label, or map business name. Building alias candidates
go into `building_aliases` with `status = pending_review`.

Reviewers decide whether an alias should map to an existing canonical building, be
rejected, or lead to a later canonical building creation step. Aliases are not
auto-approved.

## Unit Matching

Unit candidates go into `building_units` with review-oriented status. Unit matching
uses building, wing, and unit number signals when available. The schema intentionally
allows non-unique `(building_id, wing, unit_number)` rows because imported sheets can
contain duplicates, stale unit labels, or uncertain building matches.

Review should confirm the building and unit before a relationship is treated as a
real owner/tenant fact.

## Stronger Evidence For Owner/Tenant Links

Owner, tenant, landlord, seller, buyer, broker, and agent relationships are higher
impact than generic lead interest. Phase 5.2 therefore requires stronger evidence,
especially unit-level evidence, before materializing owner/tenant-style candidates.

Rows with owner/tenant-style relationship types but no usable unit detail are skipped
as `skip:owner_tenant_needs_unit`. Business lead or interested buyer/tenant signals
may be building-level candidates when the source supports that weaker relationship.

## Fake Workflow Commands

All fake scripts are dry-run by default and print counts only.

```bash
# Read-only planning
python3 scripts/plan_property_relationship_candidates.py --fake-only

# Seed one fake source-aware property hint
python3 scripts/seed_fake_property_hints.py
python3 scripts/seed_fake_property_hints.py --apply --fake-ok

# Confirm the seeded hint plans as exactly one candidate path
python3 scripts/plan_property_relationship_candidates.py \
  --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS --fake-only

# Materialize one fake candidate chain
python3 scripts/apply_fake_property_relationship_candidates.py \
  --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS
python3 scripts/apply_fake_property_relationship_candidates.py \
  --batch-label FAKE_PHASE_5_2_PROPERTY_HINTS --apply --fake-ok

# Inspect counts only
python3 scripts/property_relationship_summary.py

# Clean up fake candidate rows, then fake seed rows
python3 scripts/cleanup_fake_property_relationship_candidates.py
python3 scripts/cleanup_fake_property_relationship_candidates.py --apply
python3 scripts/seed_fake_property_hints.py --cleanup
python3 scripts/seed_fake_property_hints.py --cleanup --apply
```

`apply_fake_property_relationship_candidates.py` refuses non-`FAKE_` source batches
and refuses hints that resolve to real (`is_test=false`) contacts.

## Future Real Workflow

Phase 5.4 added the first real source-aware owner/unit audit batch
(`REAL_PHASE_5_4_IMPERIAL_UNIT_AUDIT_001`) without creating relationships. A later
relationship workflow should be explicitly approved before use. It should:

- start from reviewed source-aware imports
- require canonical contact approval before real relationship creation
- plan counts before writes
- materialize candidates as `pending_review`, never auto-approved
- keep source file, source row, property hint, and inventory row traceability
- expose only masked/safe review views in NocoDB
- provide dry-run rollback before any destructive cleanup

Phase 5.5 plans the canonical-contact step needed before those relationship
candidates can be created. It selects safe owner/unit `merge_candidate` review items
but does not approve them or create contacts. See
`docs/PHASE_5_5_OWNER_UNIT_CANONICAL_CONTACT_PLAN.md`.

Phase 5.6 approves exactly two of those owner/unit `merge_candidate` review items
and prepares the canonical merge scripts for a later contact-only apply phase. It
still does not create canonical contacts, buildings, units, property relationships,
or outreach. See
`docs/PHASE_5_6_OWNER_UNIT_REVIEW_APPROVAL_AND_MERGE_PREP.md`.

Phase 5.7 creates exactly one canonical contact from the approved owner/unit review
set and updates the read-only relationship planner so property hints and inventory
rows can resolve that contact through the canonical merge audit trail. The post-merge
planner shows 2 relationship candidates, but Phase 5.7 does not apply them or create
building/unit/property relationship rows. See
`docs/PHASE_5_7_FIRST_OWNER_UNIT_CANONICAL_MERGE.md`.

## Warnings

- Do not import additional real owner/property sheets without an explicit phase.
- Do not create real owner/tenant relationships yet.
- Do not run canonical contact merges as part of Phase 5.2.
- Do not send WhatsApp, SMS, emails, or any outreach from this workflow.
- Do not print raw names, phone numbers, emails, websites, addresses, or private
  client/property data in reports.

## Phase 5.8: first real candidate apply (review-gated)

Phase 5.8 promotes the read-only plan into the first *real* relationship candidate
for one Phase 5.7 canonical contact, using
`scripts/apply_real_property_relationship_candidates.py` (dry-run default; writes
only with `--real-ok --apply`). It creates one building anchor, one `pending_review`
building alias, one `needs_review` building unit, one `pending_review` `owner`
`contact_property_relationship`, and one `pending` `property_relationship_review_item`,
then surfaces them in the five NocoDB review views. Nothing is approved/activated,
no outreach is sent, and `scripts/rollback_real_property_relationship_candidates.py`
(dry-run default) can remove the tagged candidate rows while refusing to delete any
already-approved/active relationship. See
`docs/PHASE_5_8_FIRST_REAL_RELATIONSHIP_CANDIDATE.md`.

## Phase 5.9: first real relationship approval

Phase 5.9 closes the loop by approving one Phase 5.8 candidate and activating one
owner relationship, using `scripts/approve_property_relationship_candidate.py`
(dry-run default; `--real-ok --apply` to write; one review item at a time). It
transitions the review item to `approved`, the relationship to `active`, the unit to
`active`, and the alias to `approved`, and logs the decision in
`property_relationship_action_log`. `scripts/revert_property_relationship_approval.py`
(dry-run default) restores the review state without deleting rows. Contacts,
contact_methods, and source-aware audit rows are never modified, and no outreach is
sent. See `docs/PHASE_5_9_FIRST_PROPERTY_RELATIONSHIP_APPROVAL.md`.

## Phase 5.10: owner/building/unit dashboard

Phase 5.10 adds masked read-only dashboard views and a counts-only summary script to
inspect, trace, and revert-check the resulting active owner relationship before
scaling — view/script polish only (no import, no new contacts/relationships, no
approvals, no outreach). See `docs/OWNER_BUILDING_UNIT_DASHBOARD.md`.

## Phase 5.11: second canonical contact + relationship candidate

Phase 5.11 ran the per-row flow a second time: one more owner/unit canonical contact
plus one review-gated relationship candidate
(`REAL_PHASE_5_11_PROPERTY_REL_CANDIDATE_002`, `pending_review`), created with the
same guarded `apply_real_property_relationship_candidates.py`. It was not approved or
activated, and no outreach was sent. See
`docs/PHASE_5_11_SECOND_OWNER_UNIT_CANONICAL_AND_REL_CANDIDATE.md`.

## Phase 5.12: second relationship approval

Phase 5.12 approved the Phase 5.11 candidate into a second active owner relationship,
using `approve_property_relationship_candidate.py` (now phase-agnostic — it keys on
the candidate `source` marker, so it handles `phase=5.11` candidates). One review item
at a time, no bulk approval, no outreach. See
`docs/PHASE_5_12_SECOND_PROPERTY_RELATIONSHIP_APPROVAL.md`.
