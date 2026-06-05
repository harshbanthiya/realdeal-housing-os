# Real Deal Housing OS Database

This document explains the Phase 2 business database schema in plain English.
It applies only to the `realdeal_os` database. It does not describe or modify the separate internal databases used by n8n and NocoDB.

## Database

- `realdeal_os`: main business database for contacts, buildings, inventory, media, content, interactions, tasks, and import tracking.
- `realdeal_n8n`: internal n8n database. Do not edit manually unless you are intentionally repairing n8n.
- `realdeal_nocodb`: internal NocoDB database. Do not edit manually unless you are intentionally repairing NocoDB.

## Tables

### import_batches

Tracks each import run, such as a contacts CSV, inventory spreadsheet, media list, or mixed cleanup batch.
Use this table to record where an import came from, who ran it, how many rows were processed, and whether it completed successfully.

Important fields:

- `source_name`: human-readable name for the import.
- `source_type`: simple category such as `contacts`, `inventory`, `media`, or `mixed`.
- `source_file_path`: local path to the original file, if safe to store.
- `status`: `planned`, `importing`, `completed`, `failed`, or `rolled_back`.
- `total_rows`, `processed_rows`, `error_rows`: import progress counts.

### contacts

Stores people and organizations: leads, clients, owners, buyers, tenants, agents, developers, and vendors.

Important fields:

- `full_name`: required display name.
- `contact_type`: lead/client/owner/etc.
- `phone_primary`, `phone_secondary`, `whatsapp_number`: searchable phone fields.
- `email`: searchable email field.
- `status`: active, inactive, do not contact, duplicate, archived, etc.
- `tags`: flexible labels for segmentation.
- `import_batch_id`: optional link back to the import that created the contact.

### buildings

Stores buildings, projects, societies, or developments.

Important fields:

- `name`: required building or project name.
- `developer`, `project_name`: project context.
- `area`, `locality`, `city`: Mumbai location fields for searching and filtering.
- `latitude`, `longitude`: optional map coordinates.
- `import_batch_id`: optional link back to the import that created the building.

### inventory

Stores individual sale/rent units or listings.

Important fields:

- `building_id`: links the unit to a building.
- `owner_contact_id`: links the unit to the owner contact.
- `unit_number`: flat, apartment, or office number.
- `listing_type`: sale, rent, lease, or sale/rent.
- `property_type`: apartment, villa, office, shop, commercial, plot, or other.
- `availability_status`: available, blocked, sold, rented, inactive, draft, or unknown.
- `asking_price`, `monthly_rent`, `deposit_amount`: price fields.
- `internal_notes`: private operational notes.
- `public_description`: approved listing-friendly description.

### media_assets

Stores references to local media files, not the media files themselves.
Raw photos and videos should stay in `media/`, which is ignored by Git.

Important fields:

- `inventory_id`: optional link to a specific unit.
- `building_id`: optional link to a building.
- `file_path`: local path to the asset.
- `media_type`: photo, video, floor plan, document, or other.
- `status`: raw, editing, ready, approved, published, or archived.
- `sha256_hash`: optional duplicate-detection hash.
- `metadata`: flexible JSON for camera, editing, or publishing details.

### content_items

Stores drafted, approved, scheduled, and published content for Wix, social media, email, WhatsApp, YouTube, SEO, and internal use.

Important fields:

- `content_type`: listing caption, Wix listing, social post, email, WhatsApp, YouTube description, blog, SEO meta, or other.
- `channel`: Wix, Instagram, Facebook, LinkedIn, YouTube, email, WhatsApp, internal, or other.
- `status`: draft, review, approved, scheduled, published, rejected, or archived.
- `approval_status`: pending, approved, rejected, changes requested, or not required.
- `building_id`, `inventory_id`, `media_asset_id`: optional links to related real estate records.
- `approved_by`, `approved_at`: approval tracking before publishing.
- `scheduled_for`, `published_at`, `published_url`: publishing workflow fields.

### interactions

Stores calls, WhatsApp messages, emails, meetings, site visits, and other contact history.

Important fields:

- `contact_id`: required relationship to the person or organization.
- `inventory_id`: optional relationship to a listing discussed.
- `channel`: phone, WhatsApp, email, meeting, site visit, social, Wix, NocoDB, n8n, or other.
- `direction`: inbound, outbound, or internal.
- `occurred_at`: when the interaction happened.
- `summary`: required note about what happened.
- `next_follow_up_at`: date/time for the next follow-up.

### tasks

Stores operational work items for follow-ups, site visits, content approvals, imports, and admin tasks.

Important fields:

- `contact_id`, `building_id`, `inventory_id`, `content_item_id`: optional links to related work.
- `title`: required task title.
- `task_type`: follow-up, site visit, content, import, admin, or other.
- `assigned_to`: person responsible.
- `status`: open, in progress, waiting, completed, or cancelled.
- `priority`: low, normal, high, or urgent.
- `due_at`, `follow_up_at`: date fields used for dashboards and reminders.

## Relationships

- `inventory.building_id` points to `buildings.id`.
- `inventory.owner_contact_id` points to `contacts.id`.
- `media_assets.inventory_id` points to `inventory.id`.
- `media_assets.building_id` points to `buildings.id`.
- `content_items.building_id` points to `buildings.id`.
- `content_items.inventory_id` points to `inventory.id`.
- `content_items.media_asset_id` points to `media_assets.id`.
- `interactions.contact_id` points to `contacts.id`.
- `interactions.inventory_id` points to `inventory.id`.
- `tasks.contact_id` points to `contacts.id`.
- `tasks.building_id` points to `buildings.id`.
- `tasks.inventory_id` points to `inventory.id`.
- `tasks.content_item_id` points to `content_items.id`.
- Importable tables can optionally point to `import_batches.id`.

## Safety Notes

- Keep private contact files, photos, videos, and database dumps outside Git.
- Store credentials only in `docker/.env` or local-only secret files.
- Use `content_items.approval_status` and `status` before any website or social publishing workflow.
- NocoDB is a user interface over the database; it does not replace approval checks.
