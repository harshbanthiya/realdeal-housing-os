# PHONEBOOK PLAN — make the sales phone uniform, enriched, and reversible

Goal: every contact in the sales phone that we know something about carries a
consistent name, the role and apartment from our DB, and the previous saved
name kept in the notes. Personal contacts are never touched. Nothing is
destructive and everything is reversible.

Status: **plan only, nothing executed.** Written 2026-07-24.

---

## 1. What is actually wrong (measured, not guessed)

From her own export (`~/Downloads/contacts.vcf`, 7,623 cards):

| Finding | Count |
|---|---|
| Cards total | 7,623 |
| Cards with no usable mobile | 456 |
| Numbers appearing on 2+ cards (true duplicates) | 343 |
| Duplicate name strings | 442 |
| Cards with 2+ different mobiles | 0 |

Overlap with our data (7,654 distinct mobiles across all her exports):

| Match | Count |
|---|---|
| Matches a contact in our DB | 2,326 |
| …of which we know an actual wing + unit | **929** |
| Appears in her WhatsApp chats | 388 |
| Role known: owner / landlord / tenant | 926 / 16 / 9 |

**929 is the real target** — the contacts we can genuinely enrich with a unit.
Not 7,623. Everything else is either personal (leave alone) or known only as a
name and number (rename at most, nothing to add).

> Caution on the "4,406 in community_roster" figure from the broker work: those
> sheets were largely exported from this same phonebook years ago, so that
> overlap is partly circular. Do not treat it as independent confirmation.

## 2. She already has a system — we are standardising it, not replacing it

Her naming encodes exactly the right things, in five inconsistent dialects:

```
(IMHO)  OD 2802 IH          → Imperial Heights owner, D wing, 2802
(OEsq) Sagar Shah B 1103    → Oberoi Esquire owner, B 1103
OKR C 72 Sagar Shah         → Kalpataru Radiance owner, C 72
TKR - 1                     → Kalpataru Radiance tenant
ETO MANISH KUMAR / 2 BHK    → Ekta Tripolis owner
Extra 934                   → placeholder junk
```

Role + building + wing + unit + name. **Do not invent a new scheme** — she
would have to relearn her own phone. Pick one spelling of hers and apply it
everywhere.

### Proposed canonical form

```
{ROLE}{BLDG} {WING}{UNIT} {Name}

OIH  A203   Abhijeet Anpat
TKR  C1104  Sunil Gangwal
OET  B2803  Smriti Singh
BRK  Andheri  Rishi Arya          ← brokers have no unit
```

- **Role**: `O` owner · `T` tenant · `L` landlord · `BRK` broker · `LD` lead · `V` vendor
- **Building**: `IH` Imperial Heights · `KR` Kalpataru Radiance · `ET` Ekta Tripolis ·
  `DW` DLF Westpark · `OE` Oberoi Esquire · `WG` Windsor Grande
- Single space between fields, no double spaces, no brackets, no trailing junk.

Sorting consequence — worth a deliberate choice (see §7): role-first groups all
owners together; building-first would group each tower together instead.

### Multi-property people

`Sagar Shah` owns in **both** Oberoi Esquire and Kalpataru Radiance. The name
line can only carry one unit, so:

- Name carries the **primary** unit (most recent registration).
- **Every** other unit goes in the notes.
- The dedupe **must not** drop the second property. This is the single most
  important correctness rule in this plan.

## 3. What each card carries after the pass

| vCard field | Content |
|---|---|
| `FN` / `N` | the canonical name from §2 |
| `ORG` | building name in full |
| `TITLE` | role + primary unit |
| `NOTE` | structured block (below) |

```
— RDH —
Was saved as: (IMHO)  OD 2802 IH
Role: Owner · Imperial Heights D-2802
Also owns: Kalpataru Radiance C-72
Last registration: 2019-03-04 · Agreement for Sale · ₹2.35 Cr
Source: IGR + MyGate roster
RDH id: 3f2a… · updated 2026-07-24
```

**No PAN, no ID numbers in the phone.** If the handset is lost or backed up to
a personal cloud, that becomes a data-protection problem. Those stay in the DB.

## 3A. This is a two-way sync, not a push

Her phone is a **source of truth we do not have**, not just a target. Her saved
names encode role + building + wing + unit — `(IMHO) OD 2802 IH` is a statement
that D-2802 in Imperial Heights belongs to that number. Where our registry has
no phone for that unit, **her phone is the answer.**

| Direction | Trigger | Result |
|---|---|---|
| **Phone → DB** | Her name parses to a unit we hold, but we have no phone for it | Propose a contact↔unit link, review-gated |
| **Phone → DB** | Her name gives a role we don't have (tenant vs owner) | Propose a role, review-gated |
| **Phone → DB** | Number is unknown to us entirely but parses to one of our buildings | Propose a new contact |
| **DB → Phone** | We know role/unit/registration she doesn't show | Enrich the card's name + notes |
| **DB → Phone** | We know a *better* name (registry party name) | Propose rename, keep hers in notes |

Neither direction writes automatically. Both land in `/cockpit/review` as
cohorts, because a wrong unit link is worse than a missing one.

The same parser is reused on the drive sheets and her WhatsApp saved names —
those carry the same encoding (BEEPER plan §9), so one parser serves all three
sources.

## 4. Scope guard — what we will not touch

We only write to a card whose mobile is in an explicit allowlist, built from:
our DB contacts, the drive sheets, or her WhatsApp chats. Everything else —
family, doctor, plumber — is never read into a worklist and never written.

The allowlist is stored, so "did we touch this card?" is always answerable.

## 5. The iPhone problem, and the only safe way round it

**RESOLVED 2026-07-24: contacts are in iCloud, and the exports are unusable
for writing.**

Every one of her 10 `.vcf` exports contains **zero UID properties** — Apple
strips the UID on share-sheet export. Verified across all files (9 are
`VERSION:3.0` from Apple iOS/macOS, `contacts.vcf` is `VERSION:2.1`). Without a
UID there is no way to map an exported card back to the card on the server, so:

- The exports are **read-only source material**. They were the right input for
  the snapshot and the proposals, and nothing more.
- Re-importing an enriched `.vcf` would create a **second copy of every
  contact** — doubling the mess we are trying to fix.

**The write path is iCloud CardDAV** (`scripts/icloud_contacts.py`): pull the
live cards with their `href`/`etag`/`UID`, modify only `FN`/`N`/`NOTE`, and
`PUT` back with `If-Match`. Every other property (phone, email, photo, groups)
is preserved untouched, and the pre-write body is stored in
`icloud_cards.original_vcard` so `--rollback` restores exactly.

Needs one credential: an **app-specific password** from appleid.apple.com
(Sign-In and Security → App-Specific Passwords), stored in `secrets/icloud.env`
(gitignored). Her normal Apple ID password will not work and should not be used.

**Never** the delete-and-reimport route. One bad batch and her working tool is
gone.

## 6. Phases

**Phase 0 — Answer the account question (§5).** Blocks only Phase 4.

**Phase 1 — Backup and baseline.** *Zero risk, do first.*
Archive every current `.vcf` to `backups/phonebook/2026-07-24/`, and load a
`phonebook_snapshot` table: phone, original saved name, source file, captured
at. This is both the rollback point and the "last saved name" we promised to
keep. It also feeds saved-name parsing (BEEPER plan §9) — her names encode role
and building, which is data we do not otherwise have.

**Phase 2 — Match and propose.** *No writes to the phone.*
Join each allowlisted number to role, building, wing, unit, and last
registration. Generate the canonical name and the note block. Flag conflicts
(two buildings, role disagreement, name mismatch) rather than guessing.

**Phase 3 — Review.** A `phonebook_rename` cohort at `/cockpit/review`, grouped
by building + role, showing **old → new** with a sample. She approves a batch at
a time. Duplicate-merge proposals are a separate cohort, each showing every unit
that must survive the merge.

**Phase 4 — Apply, one batch at a time.**
Start with a single small batch — Imperial Heights A-wing owners (~190) — then
**stop and check her phone** before continuing. Record `applied_at` per card.

**Phase 5 — Keep it clean.**
A worker proposes names for newly matched contacts; she approves periodically.
Her own future saved names get parsed back into our DB, so the phone and the DB
improve each other instead of drifting.

## 7. The one decision that is hers

Sort order is a daily-use ergonomic choice, not a technical one:

- **Role-first** (`OIH A203 Name`) — all owners cluster, then by building.
- **Building-first** (`IH-O A203 Name`) — each tower clusters, roles mixed within.

Whichever she picks, we apply everywhere.

## 8. Risks and guards

| Risk | Guard |
|---|---|
| Duplicate cards created by re-import | Update in place only (§5); never import over existing cards |
| A merge destroys a second property | Merges list every unit; the note keeps them all |
| We rename a personal contact | Explicit allowlist; unmatched numbers never enter a worklist |
| Bad batch reaches the phone | One small batch first, verify, then continue |
| Sensitive data on a lost handset | No PAN or ID numbers in any card |
| Cannot undo | `phonebook_snapshot` holds every original name; restore is a rerun |

## 9. What this is worth

Beyond tidiness: 929 contacts become instantly legible to the salesperson —
she sees role and apartment before she picks up. It feeds Loop 4 (Serve &
remember) directly, and her saved names flowing back into the DB improve
matching for every future import.
