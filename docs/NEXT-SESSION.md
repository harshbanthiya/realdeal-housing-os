# Next-session handoff — written 2026-07-24

## Prompt to paste into Claude

See **docs/DAILY-START.md** — copy the block there, it is the standing prompt.
Read **docs/NORTH-STAR.md** first, then run `python3 scripts/daily_brief.py`.

## What shipped 2026-07-24 (9e748f9 → 2bcf080)

- **`/cockpit/review`** — cohort approval across 10 queues (~19k pending rows in
  ~100 cohorts). Sample → dry-run → confirm → write. See docs/REVIEW-SYSTEM.md.
- **Drive catalog** — all 44,572 files in `drive_files` (migration 070) +
  generated docs/DRIVE-MAP.md. **Query it; never `find` the drive.**
- **`contact_reconcile`** worker (071) — every contact on the drive ends matched,
  created, in review, or explicitly skipped. Backlog-throttled so it converges.
- **`shorts_scout`** worker — keeps 3 Short drafts + blog companions ready, built
  only from reviewed media, flat-number guard on all copy.
- Both workers run in the 30-min launchd loop (start.sh loads, stop.sh unloads).
- **Phonebook two-way sync** (073/074) — snapshot of her 11,840 cards, parser for
  her five naming dialects, 921 renames + 801 unit links proposed, all
  review-gated. iCloud CardDAV writer built (`scripts/icloud_contacts.py`).
- **Broker Community roster** (072) — 8,135 brokers, tiered vCard worklists.
- **PostHog fixed** — project is US cloud, snippet was hardcoded to EU.
- **NORTH-STAR.md** — the doc every plan now answers to.

## Human steps still open

1. **Vercel**: add `NEXT_PUBLIC_POSTHOG_KEY` → redeploy. Production is blind
   until this. Local is verified working.
2. **Burn review cohorts** at `/cockpit/review`. Start with `party_matches`
   (137, two names + similarity — seconds each), then `property_rels`.
   ⚠ `property_rels` approve makes contacts outreach-targetable, and there is
   no undo (REVIEW-SYSTEM.md §4.4).
3. **iCloud app-specific password** → `secrets/icloud.env`, then
   `python3 scripts/icloud_contacts.py --verify`. Blocks the phonebook rename.
   The CardDAV path is **untested** against Apple's server.
4. **WhatsApp**: set building on the 5 tenant/community groups.
5. **Brokers**: import `~/Desktop/RDH Broker Sheets` ACTIVE_FIRST vcf (110), then
   `build_community_roster.py --mark-saved --apply`.

## Where to go next (Claude)

**Review system is the priority** — it is the throttle on everything else, and
docs/REVIEW-SYSTEM.md §4 lists exactly what is missing. In order:

1. **Wire the real import queues** (§4.2): `contact_property_hints` (1,598) and
   `inventory_import_rows` (1,595) are the actual decisions; the 4,097
   `import_review_items` are content-free stubs.
2. **Media tagging** (§4.1): approving the 3,530 `(untagged)` cohort does NOT
   make those files usable for Shorts — `asset_type` stays NULL and
   `shorts_scout` filters on it. The biggest cohort is currently a near no-op.
3. **Drill-in + partial approval** (§4.3) — cohorts are all-or-nothing today.
4. **Undo** (§4.4) — no reverse operation exists for an applied cohort.

Then, from NORTH-STAR §9: the event spine + activity-retrieval expert.

Other open threads:
- **Zapkey linker** (3,058 rows) — needs unit/tower logic, not review.
- **Brokers absent from `contacts`** — ~16k rows on the drive, 0 in the DB.
- **Notion inventory** (`RDH files/RDH Notion Inventory/`) has per-flat BHK,
  area, facing, parking, price, portal status — none of it ingested. Zero
  Imperial Heights units have `bhk` or area populated. This is why "is there a
  video of B-2501" could not be answered from SQL.

## Gotchas

- `getGlobalReviewQueue()` supplies no `reviewItemId`, so the building
  workspace Reviews tab shows every item as "(preview)".
- `%%` in a Python f-string is NOT the pg_trgm `%` operator.
- `contacts.canonical_status` only accepts active/test/archived/merged/inactive.
  `contact_methods.validation_status` has no 'pending' (use 'unverified').
  `media_assets.status` has no 'rejected' (use 'archived').
  `seo_content_drafts.kind` is blog_post|seo_brief only.
- xlsx files claim Excel's full 1,048,576-row extent — skip empty rows on load.
- Her .vcf exports contain **no UID** (Apple strips it), so they can only ever
  be read. Re-importing would duplicate every contact.
- Cockpit auth cookie is `cockpit_auth` (= COCKPIT_AUTH_TOKEN).
- IGR eRegistration Index II comes back in ENGLISH; parse_igr_index2_ekta.py
  has both branches.
- Remotion Root.tsx needs calculateMetadata or end cards get cropped.
