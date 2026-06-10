# NocoDB Human Dashboard Runbook

This runbook gets a human operator from a running stack to a usable, read-only
NocoDB dashboard over the live `realdeal_os` database, and explains what may and
may not be done from it right now.

> **NocoDB is an inspection surface first.** All state-changing actions still run
> through the guarded terminal scripts (see §13). Do not use NocoDB to edit, add,
> or delete rows in `realdeal_os` during this phase.

---

## 1. Open NocoDB

Start the stack from the project root, then open the UI:

```bash
./stop.sh
./start.sh
docker ps
./scripts/check_db.sh
```

Continue only if all four containers (`realdeal-postgres` healthy, `realdeal-nocodb`,
`realdeal-n8n`, `realdeal-adminer`) are up and `check_db.sh` passes. Then open:

```text
http://localhost:8080
```

Sign in with the NocoDB admin account. Those credentials live in `docker/.env`
(`NC_ADMIN_EMAIL` / `NC_ADMIN_PASSWORD`) — read them from that file; do not paste
them into chat, tickets, or screenshots. See §15 (Security note).

---

## 2. Connect the base to Postgres

The user already created an empty base named **Real Deal Housing OS**. Add the
live database to it as an external data source:

1. Open the **Real Deal Housing OS** base.
2. **Data Sources → New Data Source → PostgreSQL** (sometimes labelled
   "Connect external data").
3. Fill in the connection (see §3 for exact values).
4. **Test Connection**, then **Save**.

### Why `localhost` failed

When the user first tried host `localhost`, NocoDB showed:

```text
Connection to internal hosts is not allowed
```

Two separate things were happening:

- **`localhost` is the wrong host.** Inside the NocoDB container, `localhost`
  means the NocoDB container itself, not Postgres. The right host on the Docker
  network is the service name **`postgres`** (it resolves to a private Docker IP,
  e.g. `172.18.0.2`).
- **NocoDB's SSRF guard blocks private/internal hosts by default.** Even with the
  correct host `postgres`, NocoDB refuses connections to private/internal network
  addresses unless explicitly allowed. This is controlled by the environment
  variable **`NC_ALLOW_LOCAL_EXTERNAL_DBS`**.

This stack now sets `NC_ALLOW_LOCAL_EXTERNAL_DBS=true` on the `nocodb` service in
`docker/docker-compose.yml`, so connecting to host `postgres` is permitted. The
whole stack is bound to `127.0.0.1` only, so this flag does not widen any
externally reachable surface.

If you ever see the "internal hosts" error again, confirm the flag is live:

```bash
docker exec realdeal-nocodb printenv NC_ALLOW_LOCAL_EXTERNAL_DBS   # expect: true
```

If it is empty, the container predates the config change — recreate it:

```bash
cd docker && docker compose up -d nocodb
```

---

## 3. Which base / source / database to use

Use these exact values in the data-source form:

| Field      | Value                                            |
| ---------- | ------------------------------------------------ |
| Host       | `postgres`  (the Docker service name)            |
| Port       | `5432`                                           |
| Database   | `realdeal_os`                                    |
| Schema     | `public`                                         |
| Username   | `POSTGRES_USER` value from `docker/.env`         |
| Password   | `POSTGRES_PASSWORD` value from `docker/.env`     |
| SSL        | off / not required (local Docker network)        |

Read the username/password from `docker/.env`; never type them into chat. After
saving, NocoDB lists the `public` schema's tables and `vw_*` views.

> The `realdeal_os` database is **separate** from NocoDB's own metadata database
> (`NOCODB_DB`). Connecting `realdeal_os` as an external source does not touch
> NocoDB's internals.

---

## 4. Which views to open first

Open the human-friendly views (prefix `vw_human_`) in this order. They are thin,
read-only projections of the audited Milestone 2B views.

1. **`vw_human_dashboard_home`** — one-row system overview.
2. **`vw_human_next_actions`** — the prioritized safe action queue.
3. **`vw_human_owner_relationships`** — the active owner relationships (masked).
4. **`vw_human_candidate_review_queue`** — the next owner/unit candidates.

Underlying audited views (open when you need full detail): `vw_milestone_2b_summary`,
`vw_owner_relationship_dashboard`, `vw_building_unit_owner_summary`,
`vw_contact_property_trace_full`, `vw_property_relationship_revert_readiness`,
`vw_owner_unit_candidate_queue`, `vw_duplicate_risk_dashboard`,
`vw_owner_relationship_revert_dashboard`.

**Growth pipeline (Phase 6.0):** the growth/SEO/lead engine has its own read-only
views — `vw_growth_pipeline_home`, `vw_seo_keyword_dashboard`,
`vw_content_pipeline_dashboard`, `vw_inbound_lead_review_queue`,
`vw_channel_permission_dashboard`, `vw_campaign_readiness_dashboard`,
`vw_ai_agent_task_dashboard`. These are inspection-only and contain no publishing or
outreach actions (campaigns have `send_enabled = false`). See
`docs/GROWTH_SEO_LEAD_PIPELINE.md`.

**Wix CMS readiness (Phase 6.2):** `vw_wix_cms_mapping_dashboard`,
`vw_content_review_dashboard`, `vw_publishing_readiness_dashboard`, and
`vw_imperial_heights_content_plan` show the field-mapping coverage, the content
review queue, and the pre-publish checklist. `ready_for_publish` stays false until
every check passes and the row is approved — nothing publishes from these views. See
`docs/PHASE_6_2_WIX_CMS_CONTENT_REVIEW_PLAN.md`.

**Content quality & AI planning (Phase 6.3):** `vw_content_quality_dashboard`,
`vw_content_source_requirements_dashboard`, `vw_ai_prompt_template_dashboard`,
`vw_ai_task_execution_plan_dashboard`, and `vw_imperial_heights_content_readiness`
show per-brief quality checks, the sources each brief still needs, the AI prompt
template catalogue (no full prompt text), the AI execution plans (all `manual`,
no external calls, human-review-required), and overall readiness. `ready_for_ai_draft`
and `ready_for_publish` are both false until checks pass and sources are collected.
See `docs/PHASE_6_3_CONTENT_QUALITY_AI_PLANNING.md`.

**Local content draft workspace (Phase 6.4):** `vw_content_draft_artifact_dashboard`
(metadata/flags only, no body), `vw_content_draft_review_queue`,
`vw_content_source_gap_dashboard`, and `vw_imperial_heights_draft_workspace` show the
internal draft artifacts, their review queue, the open source gaps, and per-brief
readiness. All artifacts are `internal_only=true` / `public_ready=false`; nothing here
is public or published. Internal drafts may also be exported (with an
"INTERNAL DRAFT — NOT FOR PUBLISHING" header) to the git-ignored `exports/content/`.
See `docs/PHASE_6_4_LOCAL_CONTENT_DRAFT_WORKSPACE.md`.

**Source-gap resolution workflow (Phase 6.5):** `vw_source_gap_resolution_dashboard`
(per-gap tasks/evidence/reviews with a `recommended_next_action`),
`vw_internal_source_evidence_dashboard` (safe count-only internal evidence),
`vw_source_gap_review_queue` (the human accept/resolve/waive queue), and
`vw_imperial_heights_source_gap_status` (per-brief readiness; `ready_for_publish` is
hard-coded false). Work the review queue to confirm each gap's classification, accept
or reject the internal evidence, and resolve/waive gaps **only** with verified, citable
sources. No gap is auto-resolved; `external_calls_allowed=false`; nothing is published
or sent. See `docs/PHASE_6_5_SOURCE_GAP_RESOLUTION_WORKFLOW.md`.

**Internal evidence acceptance (Phase 6.6):** `vw_internal_evidence_acceptance_dashboard`
(per-evidence `evidence_status` + linked `review_status` + `recommended_next_action`) and
`vw_imperial_heights_evidence_readiness` (per-profile rollup of candidate/accepted/
needs_review/rejected evidence and gap counts; `ready_for_publish` hard-coded false).
Accept only purely-internal, non-personal evidence via
`scripts/review_internal_source_evidence.py` (dry-run default); reverse with
`scripts/revert_internal_source_evidence_review.py`. Accepting evidence never resolves a
gap — gaps stay open, content stays not-ready for AI/public drafting, and nothing is
published or sent. See `docs/PHASE_6_6_INTERNAL_EVIDENCE_ACCEPTANCE.md`.

**Building-anchor dedupe planning (Phase 6.7):** `vw_imperial_heights_building_anchor_summary`
(one row per Imperial-Heights-like building with alias/unit/relationship/profile/brief
counts and a `recommended_role`), `vw_building_dedupe_dashboard` (canonical-vs-duplicate
counts + review status), and `vw_building_dedupe_review_queue` (the human review queue).
Approve a `duplicate_building_review` only when confident the two anchors are the same
building. Planning is review-gated and **never merges/moves/deletes** anything — buildings,
relationships, and SEO/content rows are untouched; nothing is published or sent. See
`docs/PHASE_6_7_BUILDING_DEDUPE_PLANNING.md`.

---

## 5. What each view means

| View | Meaning |
| ---- | ------- |
| `vw_human_dashboard_home` | One row: canonical contacts, active owner relationships, pending/safe candidate counts, duplicate-risk count, revert-ready count, communications sent, building/unit totals. The "is the system where I expect it?" glance. |
| `vw_human_next_actions` | One row per actionable item across the whole system, with `action_type`, `priority` (lower = act sooner), the `related_view`/`related_table`, an `entity_id`, a `safe_summary`, a `recommended_action`, and `status`. No raw contact values. |
| `vw_human_owner_relationships` | The current active owner relationships, with a masked owner hint, building, unit, status, revert readiness, and a "source trace present" flag. |
| `vw_human_candidate_review_queue` | Owner/unit import rows not yet linked to a canonical contact, with safe signal flags (has contact method, has property/building/unit hint, duplicate involved), the recommended next action, and a review priority. |
| `vw_milestone_2b_summary` | The full one-row system snapshot the home view summarizes. |
| `vw_owner_relationship_dashboard` | Full per-relationship detail (building, unit, alias status, source file/row, review status). |
| `vw_building_unit_owner_summary` | One row per building unit with owner counts. |
| `vw_contact_property_trace_full` | End-to-end source trace: canonical contact → relationship → building/unit → source batch/file/row → review/merge status. |
| `vw_property_relationship_revert_readiness` | Per active relationship: can it be safely reverted, and if not, why. |
| `vw_owner_unit_candidate_queue` | The detailed candidate queue the human review queue summarizes. |
| `vw_duplicate_risk_dashboard` | Duplicate-candidate groups with a type-only `reason` (e.g. "matching normalized phone") — never raw values. |
| `vw_owner_relationship_revert_dashboard` | Active owner relationships with full revert-readiness reasoning. |

---

## 6. Inspect active owner relationships

Open **`vw_human_owner_relationships`**.

- Expect **2 active owner relationships** right now (both for *Imperial Heights*,
  Wing A units **-102** and **-203**).
- `owner_hint` is masked (first initial + `[MASKED]`) — by design.
- `relationship_status = active` and `review_status = approved` mean the
  relationship is live and was approved.
- `revert_ready = true` means the relationship can currently be reverted safely
  (still approved, no communication sent, no downstream activity).
- `source_trace_present = true` means a source row resolves in
  `vw_contact_property_trace_full` (see §7).

---

## 7. Inspect source traceability

Open **`vw_contact_property_trace_full`** and filter by the `relationship_id` you
saw in §6.

You should see, for each relationship, the chain: masked contact hint →
relationship → building/unit → `source_batch_label` / `source_file` /
`source_row_number` → `canonical_merge_label` / `canonical_merge_status` →
`property_review_status`. This is how you prove *where a relationship came from*
without exposing raw personal data.

---

## 8. Inspect revert readiness

Open **`vw_property_relationship_revert_readiness`** (or
`vw_owner_relationship_revert_dashboard` for the owner-only view).

- `revert_allowed = true` → the approval can be reverted with the guarded script
  (§13) if needed.
- `revert_allowed = false` → read `reason_if_not_allowed`
  (`relationship_not_active`, `review_not_approved`, `communication_sent`, or
  `downstream_activity`). A relationship with communications sent or downstream
  activity is intentionally **not** trivially revertible.

---

## 9. Inspect the next candidate queue

Open **`vw_human_candidate_review_queue`** (detail in
`vw_owner_unit_candidate_queue`).

- Expect **56 rows** (owner/unit import rows not yet linked to a canonical
  contact), of which **~50 are "safe"** (have a contact method, no duplicate
  involvement) and **~6 are duplicate-involved**.
- Sort by `review_priority` ascending to see the cleanest candidates first.
- `recommended_action` tells you the next safe step
  (`ready_to_merge`, `approve_then_merge`, `duplicate_review_first`,
  `needs_contact_method`, `needs_more_info`).

> Inspecting the queue is allowed. **Acting** on it (merging) is a guarded
> terminal action and is paused in this phase — see §11/§12.

---

## 10. Inspect duplicate risks

Open **`vw_duplicate_risk_dashboard`**.

- Expect **15 duplicate-candidate rows**; **6** of them overlap the owner/unit
  candidate queue (the "duplicate-involved" candidates).
- The `reason` / `safe_summary` columns describe the match **type** only
  (e.g. "matching normalized phone/email", `strength=…, status=…`) — never the
  raw phone or email.
- `recommended_action` indicates whether a candidate should be reviewed before any
  merge (`review_before_merge`), etc.

---

## 11. What actions ARE allowed right now

- Browsing, filtering, sorting, and grouping any `vw_*` view in NocoDB.
- Reading the source trace and revert-readiness reasoning.
- Running the read-only helpers from the terminal:
  - `python3 scripts/human_dashboard_summary.py`
  - `python3 scripts/milestone_2b_summary.py`
- Building **read-only** NocoDB grid/gallery layouts over the `vw_*` views for
  easier inspection.

---

## 12. What actions are NOT allowed right now

- **No outreach** — no WhatsApp / SMS / email / calls to any contact.
- **No bulk import** — do not import new real contact/owner data.
- **No bulk approval** — do not mass-approve review items or candidates.
- **No raw data export** — do not export contact names, phones, emails,
  websites, or addresses out of the system.
- **No editing `realdeal_os` rows in NocoDB** — the dashboard is read-only for
  business data. State changes go through the guarded scripts in §13, one at a
  time, with review.

---

## 13. Which terminal scripts correspond to human actions

When an action *is* authorized (in a later, un-paused phase), it runs through one
of these guarded scripts from the project root — **not** through NocoDB:

| Action | Script |
| ------ | ------ |
| Set a review item's status (approve / reject / needs more info) | `scripts/update_review_item.py` |
| Apply a canonical contact merge | `scripts/apply_canonical_merge.py` |
| Roll back a canonical contact merge | `scripts/rollback_canonical_merge.py` |
| Stage real property-relationship candidates | `scripts/apply_real_property_relationship_candidates.py` |
| Approve a property-relationship candidate | `scripts/approve_property_relationship_candidate.py` |
| Revert a property-relationship approval | `scripts/revert_property_relationship_approval.py` |

The `entity_id` / `related_table` columns in `vw_human_next_actions` tell you
which record a given script should target.

---

## 14. NocoDB is for review/inspection first

For now, treat NocoDB strictly as a **read-only review and inspection** layer.
The terminal scripts remain the **guarded action layer**: every state change is
explicit, reviewable, and reversible where the revert-readiness views say so.
Do not collapse these layers by editing data directly in NocoDB.

---

## 15. Security note — exposed credential

A database password appeared in a local screenshot / chat context while diagnosing
the connection. Treat it as compromised for operational purposes:

- **Rotate the local Postgres / NocoDB credentials before any serious operational
  use** (`POSTGRES_PASSWORD`, and the NocoDB data-source password that mirrors it,
  plus `NC_ADMIN_PASSWORD` if it was visible). Rotation is **not** performed in
  this phase — do it explicitly when ready.
- **Do not paste secrets into chat**, tickets, or screenshots. Read connection
  values from `docker/.env` directly.
- **`docker/.env` stays git-ignored** and must never be committed. Only
  `docker/.env.example` (placeholder values) is tracked.
- **Do not commit secrets** in any form (compose files, docs, scripts, fixtures).
