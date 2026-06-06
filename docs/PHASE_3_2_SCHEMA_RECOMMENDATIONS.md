# Phase 3.2 Schema Recommendations

Do not apply these changes yet. This document captures future database design after archive profiling and multi-source normalization.

## contact_methods

Purpose: store every phone, email, WhatsApp number, website, and other contact method without losing secondary values.

Suggested fields:

- `id uuid primary key`
- `contact_id uuid references contacts(id)`
- `method_type text`
- `raw_value text`
- `normalized_value text`
- `label text`
- `source_file text`
- `is_primary boolean default false`
- `confidence numeric`
- `created_at timestamptz default now()`

## lead_requirements

Purpose: store portal, Meta/Facebook, website, and manually captured buyer/tenant requirements separately from contact identity.

Suggested fields:

- `id uuid primary key`
- `contact_id uuid references contacts(id)`
- `source text`
- `purpose text`
- `property_type text`
- `locality text`
- `city text`
- `budget_min numeric`
- `budget_max numeric`
- `visit_intent text`
- `raw_payload jsonb`
- `created_at timestamptz default now()`

## inventory_import_rows

Purpose: preserve property inventory rows before matching them to the main `inventory` table.

Suggested fields:

- `id uuid primary key`
- `source_file text`
- `building_name text`
- `wing text`
- `unit_number text`
- `typology text`
- `area text`
- `rent numeric`
- `sale_price numeric`
- `raw_payload jsonb`
- `matched_inventory_id uuid references inventory(id)`
- `created_at timestamptz default now()`

## source_files

Purpose: track source files, archives, hashes, detected formats, and processing state.

Suggested fields:

- `id uuid primary key`
- `archive_name text`
- `file_path text`
- `file_hash text`
- `detected_format text`
- `row_count integer`
- `processed_at timestamptz`
- `metadata jsonb`

## Notes

- Keep `contact_import_rows` as the audit table for raw rows.
- Use `contact_methods` to avoid forcing multiple phones/emails into one `contacts` row.
- Keep property inventory import separate from contact import.
- Keep source file tracking separate so archive re-processing can be idempotent.
