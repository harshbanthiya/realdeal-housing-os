# Kalpataru Radiance — MyGate directory import

Status: **DONE and idempotent** (2026-07-10). Re-running the loader is a no-op.

Building: `Kalpataru Radiance` = `f63d75ab-2ef9-48a9-afe2-cab3c4283283`

## Current committed state

| metric | value |
|---|---|
| building_units total | 665 |
| units created from MyGate | 426 |
| contacts with `mygate_ruid` | 1475 |
| pre-existing contacts linked by name match | 69 |
| mygate relationships (all `pending_review`) | 1543 |

Every relationship landed `pending_review` — none are approved. Operator review is
the next step; nothing here writes active relationships.

## Scripts

- `scripts/load_kalpataru_mygate.py` — the loader. `--dry-run` prints counts and rolls back.
- `scripts/audit_kalpataru_mygate.py` — unit-by-unit reconciliation of the JSON against the
  DB. **This is the regression check.** Exits non-zero if any flat is untouched.
- `scripts/dedupe_kalpataru_units.py` — one-shot unit merge, already committed. Safe to
  re-run (it will find 0 duplicate groups).
- `scripts/repair_kalpataru_duplicate_units.py` — one-shot, already committed. Restored 14
  flats the first (buggy) dedupe stranded.

## Reconciliation

```
python3 scripts/audit_kalpataru_mygate.py
```

Current result: **625/625 flats fully reconciled, 1571/1571 residents linked, 0 role
mismatches.** Every apartment in every wing has at least one contact with a role, and the
Unit Registry renders them (`mgRel` in `web/src/lib/cockpit/data.ts` keys on
`contacts.metadata->>'mygate_unit'`, which both the loader's insert and its name-match
update set).

## The grid: floors are looked up, not guessed

Kalpataru numbers flats `floor*10 + position` — verified against all 625 MyGate flats, no
exceptions, position 1–5 in wing A and 1–6 in B/C/D.

`deriveFloorPos()` in `data.ts` guessed floor from the flat number and tried the "standard"
scheme first, reading **`301` as floor 3 / unit 01**. Flat 301 then collided with flat 31 in
the grid's `byPos` map, one overwrote the other, and tower A's 30th floor rendered empty
while floors 1–3 looked overfull. Every `X01`–`X05` flat was misplaced.

MyGate knows the real floor, so `backfill_kalpataru_floors.py` writes it to
`building_units.floor` and `floorPos()` prefers it, falling back to the heuristic only for
the 24 IGR flats MyGate does not list. On a collision the known-floor unit wins its slot.

Current tally (`audit_kalpataru_mygate.py` checks this and fails on any collision):

| wing | floors | flats | boxes | empty | off-grid |
|---|---|---|---|---|---|
| A | 31 | 134 | 155 | 21 | 4 |
| B | 31 | 169 | 186 | 17 | 4 |
| C | 31 | 162 | 186 | 24 | 7 |
| D | 31 | 160 | 186 | 26 | 9 |

Zero collisions, and **every placed flat carries a contact name and role** on its tile
(owner if one is on record, else the first tenant).

The 88 empty boxes are not a bug: MyGate lists only occupied flats, and several floors
genuinely have 4 rather than 5–6 apartments. The grid draws `floors × units-per-floor`, so
slots with no flat stay blank. The off-grid count is IGR rows whose flat number does not fit
the scheme (`D-1160145068`, `A-832` from "83, Along with 2 Car Parking"); they keep a null
floor and are surfaced in the tower header rather than silently dropped.

## Flat numbering differs per building — never mix them

| building | scheme | floor 1 flat 1 | floor 10 flat 1 |
|---|---|---|---|
| Kalpataru Radiance | `floor*10 + position` | `11` | `101` |
| Imperial Heights | `floor*100 + position` | `101` | `1001` |

`101` therefore means **different apartments in the two buildings**. `floorPos()` in `data.ts`
tries both bases against the stored floor; they can never both be valid, because the two
candidates differ by `90*floor`, so for any floor ≥ 1 at most one lands in 1..12.

The IGR register also writes some Kalpataru flats in the `floor*100` form (`2703` = floor 27,
flat 3 = MyGate's `273`), which is exactly why `unit_text` alone cannot be trusted and
`floor_text` is required before any flat-number correction.

`audit_kalpataru_registrations.py` asserts no registration is linked to a unit of another
building, and fails if one ever is. Currently zero.

## Registrations ↔ apartments

The old `igr_xls_kalpataru` loader linked records by flat number and landed on the **wrong
wing** for 681 of them: doc 3950 stores `tower: B`, its Devanagari reads "विंग बी ब्रीलीयंस",
and it was linked to wing A flat 173. The record's own `raw_context.tower` and `wing_text`
agree with each other in 591 of 597 records, and on the 422 mislinked records whose Devanagari
names a wing inside a flat clause, the description backed the recovered wing 421 times and the
linked wing once.

`relink_kalpataru_registrations.py` moved 700 records onto the right apartment (old id kept in
`raw_context.relink_prev_unit_id`, so it is reversible; 59 party-contact matches followed).
`create_missing_kalpataru_units.py` first created 52 apartments that have registrations but no
MyGate resident — vacant flats MyGate never listed, which is why the grid had 88 empty boxes.

Result:

| verdict | before | after |
|---|---|---|
| correctly linked | 293 | **993** |
| mislinked | 704 | **4** |
| unlinked but resolvable | 169 | 169 |
| unclear | 127 | 127 |
| land / development-rights / OC deeds (no flat) | 224 | 224 |

The 4 remaining are genuinely ambiguous and left for a human: two flats with no active unit,
one 3-digit flat with no floor (`604` could be floor 60 or floor 6), and doc 6926 where
`wing_text` says A but the Devanagari says सी (C).

## Source-document QA (both buildings)

`scripts/qa_registration_sources.py` re-derives building, wing and flat for every linked
registration from the register itself, and never from the DB. Evidence tiers, strongest first:

1. **Index II text capture** — `exports/igr_index2_snapshots{,_imperial_heights}/…_docN_YYYY_r0.txt`
2. **SearchResult sheet** — `imports/igr Registrations/**/SearchResult*.xls` and `~/Downloads`
   (UTF-16 HTML; these are the search pages the doc numbers were harvested from)
3. **`property_description_raw`** — the same register text as stored at ingest

Verdicts: `confirmed`, `CONFLICT` (source contradicts the link), `needs_review` (source can't
prove it — includes every Devanagari-only description), `no evidence`.

| | Kalpataru | Imperial Heights |
|---|---|---|
| confirmed | 76 | 377 |
| CONFLICT | 194 | 5 |
| needs_review | 450 | 161 |
| no source document | 377 | 384 |
| **linked total** | **1097** | **927** |

All 1571 non-confirmed records are on the human review queue
(`unit_registration_review_items`, visible through `vw_unit_registration_review_queue`) as
`source_qa_conflict` / `source_qa_needs_review` / `source_qa_no_document`. Enqueue is
idempotent on `(record, review_type)`. Full detail: `exports/qa/registration_source_qa.csv`.

The biggest single finding: **175 Kalpataru registrations whose register text names
"द मिडोस" (The Meadows)**, not Kalpataru Radiance. Per the operator, only records explicitly
naming Kalpataru Radiance belong to it. They are queued, not deleted.

### Four traps this QA had to learn

- **Doc numbers are not unique.** They restart each year and repeat across SRO offices.
  `doc 8188/2024` exists in *both* snapshot directories as two different flats in two
  different buildings. Snapshots are keyed `(building, doc, year)`; sheets `(doc, year, SRO)`.
  Keying on the doc number alone matched an Ekta Tripolis row to a Kalpataru flat.
- **The SRO does not identify the building.** Any document may be registered at any SRO
  office. SRO is part of a document's identity, nothing more.
- **Party addresses are not property addresses.** "कल्पतरू सिनर्जी" (Kalpataru Synergy) appears
  in `party_address` — it is the developer's registered office ("Office no. 101, Kalpataru
  Synergy"), not the flat's building. Only the property description's `Building Name` field
  is evidence.
- **The register runs fields together.** `Apartment/Flat No:A/204Shop No:Floor No:12.00Building
  Name:…` has no commas, and `Floor No:SECOND FLOOR` spells the floor. Parsing must stop at the
  next field label and understand ordinal words, or the flat token swallows the floor and the
  building name.

Two things the audit must keep getting right:

- A contact can hold **several relationships to one unit** — phase 6.26 added a `landlord`
  row alongside an existing `owner` row for the same person (C-84, Suryakant Sohoni).
  Collect a set of roles per contact, never overwrite, and treat `landlord` as satisfying
  MyGate's `owner`.
- The UI only renders units with `canonical_status='active'` and `offgrid` not true, so the
  audit filters the same way. A unit that exists but is flagged `duplicate` is invisible,
  which is a real gap, not a false positive.

Source data: `captures/mygate_directory/building_*.json` — committed to the repo, so the
import replays from a clean clone. 626 flats across wings A–D (all occupied), 1572 resident
records, plus a one-flat society office. Contains names, MyGate user ids, flat, floor and
owner/tenant role; no phone numbers.

`captures/mygate_flows/` is the raw HTTP capture the directory was pulled from. It is
**gitignored and must stay that way** — 132 of those files contain live MyGate auth JWTs.

## The idempotency bug, and what actually fixed it

Symptom: every re-run of the loader inserted ~17 new relationships and drifted the
contact count, even though contacts are keyed on the stable `mygate_ruid`.

Two independent causes, both now fixed. Neither was the one initially suspected.

### 1. Duplicate `building_units` (the smaller half)

IGR imports had created two rows for 17 flats — a clean one (`155`) and a messy twin
(`A -Ora/155,`, `D-295Shop No:`). The loader's canonical unit pick,
`DISTINCT ON (wing, flat_digits) … ORDER BY … created_at`, had identical `created_at`
values for both twins, so the winner was non-deterministic per run.

In every one of the 17 groups the clean row held all the relationships and the messy
twin held none, but 10 twins did hold `unit_registration_records`. So the fix was a
merge, not a delete: re-point those 10 registrations at the keeper, then drop the twin.
`dedupe_kalpataru_units.py` does this. Result: 682 → 665 units, 0 duplicate groups.

An `id` tie-breaker was also added to the `ORDER BY` as a guard against future
duplicates reappearing from IGR loads.

**The first version of that merge picked the wrong keeper.** It ranked on relationship
count alone, but in 14 of the 17 pairs the messy row carried the relationships while the
clean row was the one phase 6.24 had marked `canonical_status='active'`. So the merge kept
the row flagged `duplicate`, deleted the active one, and those 14 flats dropped out of the
Unit Registry with 36 relationships stranded on invisible rows. `dedupe_kalpataru_units.py`
now ranks `active` first and re-points relationships (not just registrations) at the keeper;
`repair_kalpataru_duplicate_units.py` restored the 14.

Twelve rows remain `canonical_status='duplicate'`, correctly:
- 8 (A-603, A-902, C-601, D-803, …) have no relationships and no MyGate flat.
- 4 are the phase 6.24 merges `A-604 → A-64`, `C-801 → C-81`, `C-804 → C-84`, `D-701 → D-71`.
  These are **correct**: `604` is floor 6 position 04 under the IGR register's `floor*100`
  scheme, which is the same apartment MyGate calls `64`. (An earlier revision of this doc
  called them a bug that "stripped a digit". That was wrong.)

### 2. `name_to_contact()` fed on its own output (the real cause)

This is the one that mattered, and deduping units alone did not fix it.

`name_to_contact()` builds a "unique normalized name → contact_id" map from all
contacts linked to a Kalpataru unit, keeping only names that resolve to exactly one
contact. But after the first commit, the map also saw the 1,475 contacts the loader
itself had just created. So each run the map changed shape:

- a name with one pre-existing contact plus a new MyGate namesake now resolved to two
  contacts, dropped out of the map, and its resident became "unmatched";
- a name with no pre-existing contact but one MyGate contact newly *entered* the map.

Residents therefore re-pointed at different contacts run over run. Their `mygate_ruid`
got stamped onto a different contact, the relationship join followed the ruid, and ~17
fresh relationships appeared each time.

Fix: scope the map to pre-existing contacts with `c.source <> 'mygate'`.

The subtlety worth remembering — there are two wrong filters here and only one right one:

- filtering on `mygate_ruid IS NULL` drops the **name-match winners** (pre-existing
  contacts that we deliberately stamp a ruid onto), flipping them back to unmatched on
  the next run. This was tried and it made things worse.
- filtering on nothing at all lets the loader's own contacts into the map. This was the
  original bug.
- `source <> 'mygate'` keeps the winners and excludes the loader-created rows. Correct.

## Verification

```
python3 scripts/load_kalpataru_mygate.py --dry-run
```
Must print `INSERT 0 0` for both the contacts and relationships inserts, and counts
matching the table above. Anything else means idempotency has regressed.
