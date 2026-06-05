# Real Deal Housing OS Architecture

Real Deal Housing OS is a local-first operations stack for a Mumbai real estate company. The first phase runs from an external hard disk on a MacBook Air and keeps private client, owner, lead, inventory, and media data off public systems unless an admin explicitly approves publishing.

## Phase 1 Services

| Service | Container | Local URL | Purpose |
| --- | --- | --- | --- |
| Postgres | `realdeal-postgres` | `127.0.0.1:5432` | Main database for contacts, buildings, inventory, interactions, tasks, media records, and content workflow records. |
| n8n | `realdeal-n8n` | `http://localhost:5678` | Local automation builder for imports, cleanup workflows, content drafting, approval routing, and future API integrations. |
| NocoDB | `realdeal-nocodb` | `http://localhost:8080` | Airtable-like UI for viewing and editing Postgres data. Use it as the operational database interface for admin users. |
| Adminer | `realdeal-adminer` | `http://localhost:8081` | Emergency database viewer for technical troubleshooting. Do not use it as the normal business UI. |

All public-facing ports are bound to `127.0.0.1`, so the services are reachable only from the Mac running Docker. The stack is not designed to expose client data on the internet.

## Data Layout

| Folder | Use |
| --- | --- |
| `docker/` | Docker Compose configuration and local environment template. |
| `data/` | Persistent container data for Postgres, n8n, and NocoDB. This is private and ignored by Git. |
| `imports/` | Incoming CSV/XLSX files for contacts, buildings, and inventory. Private import files are ignored by Git. |
| `exports/` | Generated outputs and reports. Ignored by Git. |
| `media/` | Raw, edited, and thumbnail property media. Private media is ignored by Git. |
| `secrets/` | Local-only keys, passwords, and API tokens. Ignored by Git. |
| `schemas/` | SQL schema files applied to a fresh Postgres data directory. |
| `workflows/n8n/` | Exported n8n workflows. Credential exports should not be committed. |
| `docs/` | Architecture and setup notes. |
| `prompts/` | AI prompt templates and operating instructions. |

## Databases

The Postgres container creates three local databases:

| Database | Purpose |
| --- | --- |
| `POSTGRES_DB` | Main Real Deal Housing OS application database. Defaults to `realdeal_os`. |
| `N8N_DB` | n8n internal workflow database. Defaults to `realdeal_n8n`. |
| `NOCODB_DB` | NocoDB metadata database. Defaults to `realdeal_nocodb`. |

The initial application schema is defined in `schemas/001_initial_schema.sql`. It creates the first operational tables:

- `contacts`
- `buildings`
- `inventory`
- `media_assets`
- `content_items`
- `interactions`
- `tasks`

## Security Model

- Keep `docker/.env` private and never commit it.
- Keep all real API keys, tokens, passwords, contact lists, and private media out of Git.
- Use only local URLs during the MVP phase.
- Publish website, social, WhatsApp, and email content only after an explicit admin approval step.
- Treat n8n workflow exports carefully because they can contain credential references.
- Use Adminer only for technical troubleshooting.

## MVP Workflow

1. Import contacts, buildings, and inventory into Postgres.
2. Use NocoDB for admin-friendly cleanup and review.
3. Use n8n for repeatable workflows such as deduplication, lead follow-up reminders, media processing, and draft content generation.
4. Store generated content in `content_items` with a `draft`, `review`, `approved`, or `published` status.
5. Add API publishing only after the approval workflow is reliable.

## Future Integrations

Future phases can add Plane, Twenty CRM, Mautic, Wix CMS publishing, Google Search Console, WhatsApp providers, social APIs, SEO monitoring, and dashboarding. Those integrations should read from Postgres and write back status records instead of bypassing the local operational database.

