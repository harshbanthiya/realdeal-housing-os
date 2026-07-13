# Master Contact Directory × Truecaller — enrichment workflow (Phase 6.31)

## What the master directory is
`Kalpataru_Master_Contact_Directory.xlsx` = **196 phone numbers** scraped from community
WhatsApp-group screenshots (181 India, rest international). It has **numbers + region only — no
names, flats, or emails.**

## What the cross-reference found
`scripts/cross_ref_master_directory.py` matched every master number against (a) our flat-tagged
rental call list and (b) the DB `contact_methods`:

| Bucket | Count |
|---|---|
| Already known **with a flat** | 3 |
| Known as a contact (no flat) | 2 |
| **NEW / unknown to us** | ~190 |

So the directory is almost entirely **new community numbers we have no name for** — that's the gap
Truecaller can close. Outputs (git-ignored `exports/master_directory/`, PII):
`master_directory_crossref.csv` and `truecaller_worklist.csv` (177 Indian unknowns, blank
`truecaller_name` / `email` / `flat_if_known` columns to fill).

## How Truecaller can (and can't) be used
**There is no consumer bulk lookup API.** Truecaller Premium removes the daily search cap and shows
more detail, but lookup is still **one number at a time in the app**. Truecaller-for-Business / the
SDK is for verifying *your own* users (login/OTP), not bulk reverse-lookup of third parties — and
automating bulk reverse lookup would violate Truecaller's ToS.

What you realistically get per number: **a name** (usually), sometimes a city/tags, **rarely an
email** (only if that person added it to their own Truecaller profile). Don't expect emails at scale.

## The workflow
1. **Open `truecaller_worklist.csv`.** 177 Indian numbers, prioritised (you can stop anytime).
2. **Look each up in the Truecaller app**, type the name into `truecaller_name`, an `email` only if
   shown, and a `flat_if_known` if the name/tag reveals it.
3. **Ingest back:** `python3 scripts/cross_ref_master_directory.py --ingest <filled.csv>` (dry-run;
   the writer is stubbed until we confirm the contact-upsert target). It will create/enrich contacts
   + `contact_methods` (phone) + email where present.
4. **Auto-attach to flats:** re-run the name→flat matcher (`match_contacts_to_units_by_name.py`) so
   any newly-named contact whose name matches an IGR registration party gets linked to its apartment.

## Guardrails (DPDP / TRAI)
- Reverse-looking-up strangers to build profiles is **personal-data processing** — keep it to a
  defined purpose (community/contact directory), not covert profiling.
- A Truecaller-verified name/email is **KYC/identification, NOT marketing consent.** Do not WhatsApp/
  SMS/call for marketing off the back of it without a consent or other lawful basis (same rule as the
  PAN enrichment in Phase 6.25). Keep enrichment status separate from outreach permission.
