# Real Deal Housing OS

Local-first operations stack for Real Deal Housing OS.

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
