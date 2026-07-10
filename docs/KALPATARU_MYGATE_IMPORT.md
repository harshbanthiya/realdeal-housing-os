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
- `scripts/dedupe_kalpataru_units.py` — one-shot unit merge, already committed. Safe to
  re-run (it will find 0 duplicate groups).

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
