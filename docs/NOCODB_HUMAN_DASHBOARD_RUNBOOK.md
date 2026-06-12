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

**MahaRERA verification (Phase 6.8 foundation):** `vw_rera_project_verification_dashboard`,
`vw_rera_building_match_dashboard`, `vw_rera_area_mismatch_dashboard`,
`vw_rera_status_risk_dashboard`, `vw_rera_verification_review_queue`, and
`vw_imperial_heights_rera_readiness` expose official RERA project verification, internal-
anchor matches, carpet-area mismatches, status/risk flags, and the review queue (no
personal contact data). `ready_for_building_dedupe` needs an accepted RERA match;
`ready_for_content_fact_use` needs a verified profile with no blocker risk. This phase is
schema + fake-workflow only — **no MahaRERA scraping/API calls**, nothing auto-corrected,
published, or sent. RERA is an internal verification aid, not legal advice. See
`docs/RERA_VERIFICATION_PIPELINE.md`.

**Manual MahaRERA verification — Imperial Heights (Phase 6.9):** real review-gated RERA
rows now exist for Imperial Heights Wing C & D (reg `P51800003270`) — work
`vw_rera_verification_review_queue` to confirm facts and **accept** the RERA match (two
`candidate` matches, one per duplicate anchor) before building dedupe, and work the
high-priority `rera_address_review` before trusting any address. The RERA
street/boundary/lat/long are **not** trusted building address data; litigation/complaint
counts carry **no personal names**. Nothing is verified/accepted/published here. See
`docs/PHASE_6_9_MANUAL_RERA_IMPERIAL_HEIGHTS.md`.

**RERA Playwright fetch feasibility (Phase 6.10):** a guarded single-URL Playwright
capture (`scripts/fetch_rera_page_playwright.py`) can save raw, untrusted MahaRERA page
snapshots under the git-ignored `exports/rera_snapshots/` — **no bulk scraping, no DB
writes, no CAPTCHA/auth bypass**. Snapshots are raw evidence (`trusted_for_db=false`,
`human_review_required=true`) and feed no dashboard until a future review-gated parser
exists. See `docs/RERA_PLAYWRIGHT_FETCH_FEASIBILITY.md`.

**RERA snapshot parser — review-gated candidates (Phases 6.12–6.13):** an operator-assisted
headed capture (Phase 6.12) produced a post-CAPTCHA snapshot, and Phase 6.13 parsed it into
**untrusted candidate facts**. Open `vw_rera_snapshot_review_queue` (the human queue),
`vw_rera_parsed_fact_candidate_dashboard` (parsed facts — counts/booleans, **no personal
names**), `vw_rera_snapshot_compare_dashboard` (parser-vs-Phase-6.9 comparison: 6 matched / 0
mismatch / 4 pending_review), and `vw_imperial_heights_rera_parser_readiness` (both
`ready_*` flags **hard false**). Legal-risk sections are **counts only**; the promoter
**company** name is an official record. Work the four `risk_count_compare` items and the
`privacy_safety_review` items; **nothing is verified/accepted/published** from parser output.
See `docs/PHASE_6_13_RERA_SNAPSHOT_PARSER.md`.

**RERA parser-candidate review (Phase 6.14):** a first reversible review pass approved the **6**
non-personal `parser_manual_match_review` items (5 facts → `matched_manual`) and the **4**
`privacy_safety_review` items (names confirmed excluded), and **left pending** the **4**
`risk_count_compare` + **1** capture review (legal counts need human context). In
`vw_rera_snapshot_review_queue` you'll now see 10 approved / 5 pending; canonical rows are
untouched and `ready_*` flags stay false. Approve via
`scripts/review_rera_snapshot_parser_candidates.py` (safe helpers `--approve-safe-matched` /
`--approve-privacy-safety`); undo via `scripts/revert_rera_snapshot_parser_review.py`. Still
**no verify / accept / merge / publish**. See `docs/PHASE_6_14_RERA_PARSER_REVIEW.md`.

**DLF launch command center (Phase 7.0):** the launch-growth workspace for the high-priority
DLF launch (~August). Open `vw_dlf_launch_priority_dashboard` first (read `blocked_reason` /
`ready_for_launch_push` — **false** this phase), then `vw_launch_command_center_home`,
`vw_launch_operator_task_dashboard` (11 pending tasks), `vw_launch_readiness_dashboard` (11
checks; 3 blockers — start with **`project_name_confirmed`**: confirm “DLF Westend” vs public
“DLF The Westpark / Westpark Phase-I”), `vw_launch_channel_dashboard` (10 channels, send/publish
off), `vw_launch_calendar_dashboard` (30 planned placeholders), and
`vw_launch_lead_segment_dashboard` (6 segments, **counts only — no raw contacts**). Everything is
**send/publish disabled**; nothing is sent or published. Undo the seed via
`scripts/cleanup_dlf_launch_command_center.py` (dry-run shown). See
`docs/PHASE_7_0_DLF_LAUNCH_COMMAND_CENTER.md`.

**DLF launch funnel workspace (Phase 7.1):** the full funnel draft workspace. Open
`vw_dlf_launch_funnel_readiness` first (`ready_for_launch_push` — **false**; `send_enabled_count`
/ `publish_enabled_count` **0**; blocked on project-name + consent), then
`vw_launch_draft_review_queue` (60 pending reviews), `vw_launch_landing_page_dashboard`,
`vw_launch_lead_capture_form_dashboard`, `vw_launch_utm_campaign_dashboard` (8 specs),
`vw_launch_content_pillar_dashboard` (10), `vw_launch_message_template_dashboard` (13 — shows
`body_char_count` only, **never full copy**), `vw_launch_social_content_dashboard` (15 —
`caption_char_count` only), and `vw_launch_lead_scoring_dashboard` (10 rules). Everything is
`draft`/`pending`, send/publish disabled, copy uses `[VERIFY]`-style placeholders with opt-out
lines. Undo via `scripts/cleanup_dlf_launch_funnel_workspace.py` (dry-run shown). See
`docs/PHASE_7_1_DLF_LAUNCH_FUNNEL_WORKSPACE.md`.

**DLF contact segmentation (Phase 7.2):** open
`vw_launch_contact_segment_candidate_dashboard`,
`vw_launch_contact_permission_review_queue`, `vw_dlf_contact_segment_readiness`, and
`vw_dlf_owner_audience_summary`. These views mask contact names and expose no phone numbers,
emails, websites, addresses, or raw payloads. Candidates remain unapproved until explicit human
permission and suppression review. See
`docs/PHASE_7_2_DLF_CONTACT_SEGMENTATION_PERMISSION_REVIEW.md`.

**DLF lead intake and attribution plan (Phase 7.3):** open `vw_dlf_lead_intake_readiness` first;
`ready_for_live_lead_capture` must be **false** and `external_call_allowed_count` must be **0**.
Then review `vw_launch_lead_intake_endpoint_dashboard`,
`vw_launch_lead_field_mapping_dashboard`, `vw_launch_lead_attribution_rule_dashboard`,
`vw_launch_inbound_lead_review_dashboard`, and `vw_launch_operator_daily_metrics_dashboard`.
These are planning views only: no live Wix/n8n endpoint, no inbound leads, no contacts, no sends,
and no publishing. See `docs/PHASE_7_3_DLF_LEAD_INTAKE_ATTRIBUTION_PLAN.md`.

**DLF n8n workflow blueprint (Phase 7.4):** open `vw_dlf_n8n_readiness` first;
`ready_to_build_in_n8n` and `ready_to_activate` must be **false**, and
`external_call_allowed_count` must be **0**. Then review
`vw_launch_n8n_workflow_blueprint_dashboard`, `vw_launch_n8n_node_dashboard`,
`vw_launch_n8n_payload_schema_dashboard`, `vw_launch_n8n_test_case_dashboard`, and
`vw_launch_n8n_review_queue`. These are blueprint/review views only: no n8n API calls, no live
workflows, no webhooks, no inbound leads, no contacts, no sends, and no publishing. See
`docs/PHASE_7_4_DLF_N8N_WORKFLOW_BLUEPRINT.md`.

**DLF operator cockpit (Phase 7.5):** open `vw_dlf_operator_cockpit_home` first, then
`vw_dlf_operator_safety_posture`, `vw_dlf_operator_today_tasks`,
`vw_dlf_operator_review_backlog`, `vw_dlf_operator_campaign_calendar_next_14_days`,
`vw_dlf_operator_audience_readiness`, `vw_dlf_operator_lead_intake_readiness`,
`vw_dlf_operator_n8n_readiness`, and `vw_dlf_operator_content_readiness`. These views are
count/status dashboards only and should continue to show the launch as blocked for send/publish.
See `docs/PHASE_7_5_DLF_OPERATOR_COCKPIT.md`.

**DLF launch blocker triage (Phase 7.6):** open `vw_dlf_launch_activation_guardrail` first
(`safety_status` must be **safe_blocked**, `ready_for_launch_push` **false**, all activation counts
**0**; read `hard_stop_reason` — now *3 blocker readiness checks outstanding*), then
`vw_dlf_project_identity_status` (`public_name_ready_for_copy` is now **true**: the operator
confirmed the public name **DLF Westpark**, slug `dlf-westpark-andheri-west`; previous working name
`DLF Westend / The Westpark Andheri West` is historical context only), then
`vw_dlf_launch_blocker_triage` to work the remaining open blockers by area (`recommended_action`,
`can_be_closed_by_operator`, `requires_external_action`). These are count/status views only — no
names, phones, emails, addresses, or raw copy. The name was confirmed with an operator-supplied
value via `scripts/confirm_dlf_project_identity.py --real-ok --apply` (reversible via
`revert_dlf_project_identity_confirmation.py`). See `docs/PHASE_7_6_DLF_LAUNCH_BLOCKER_TRIAGE.md`.

**DLF campaign copy review (Phase 7.7):** open `vw_launch_message_template_dashboard` and
`vw_launch_social_content_dashboard` (these expose only `*_char_count`, **never full copy**) and
`vw_launch_draft_review_queue` to see copy/consent review outcomes. After this phase the
`[PROJECT_NAME_CONFIRM]` placeholder is replaced by **DLF Westpark**; copy/consent review items are
**8 approved** (internal copy review only) / **21 needs_more_info** (copy still carries factual
placeholders RERA/price/brochure/Wix/`[VERIFY]`/visual-direction). Templates/social stay `draft` with
send/publish off; `whatsapp_template_approved` stays **pending** (provider approval is separate). The
review was done via `scripts/review_dlf_campaign_copy.py --real-ok --apply` (reversible via
`scripts/revert_dlf_campaign_copy_review.py`). See `docs/PHASE_7_7_DLF_CAMPAIGN_COPY_REVIEW.md`.

**DLF consent/privacy readiness (Phase 7.8):** open `vw_dlf_consent_privacy_readiness` first
(channel_permissions_allowed must be **0**; consent_ready / lead_privacy process status), then
`vw_dlf_contact_permission_gap_dashboard` (who is blocked by unknown consent — counts only, **no
names**), `vw_dlf_lead_form_privacy_dashboard` (consent + PII field counts, privacy review status),
and `vw_dlf_suppression_readiness_dashboard` (suppression rows / process status). After this phase
`lead_privacy_reviewed` is **passed** (process), `consent_ready` is **needs_review** (NOT passed — no
explicit consent basis), `whatsapp_template_approved` and `suppression_checked` stay **pending**, and
9 WhatsApp/email permission reviews are **needs_more_info**. No contact is approved for campaign and
no channel permission is granted. Done via `scripts/review_dlf_consent_privacy_readiness.py
--real-ok --apply` (reversible via `scripts/revert_dlf_consent_privacy_readiness.py`). See
`docs/PHASE_7_8_DLF_CONSENT_PRIVACY_READINESS.md`.

**DLF contact permission evidence (Phase 7.9):** open `vw_dlf_campaign_selection_guardrail` first
(`ready_for_campaign_selection` must be **false**; explicit_whatsapp/email_allowed must be **0**; read
`hard_stop_reason`), then `vw_dlf_contact_permission_decision_dashboard` (per-candidate posture, masked
names — **no phone/email**), `vw_dlf_contact_permission_evidence_dashboard` (evidence rows — 10, all
`needs_more_info`), and `vw_dlf_contact_suppression_check_dashboard` (5 suppression checks, all
`clear`). After this phase candidates stay `needs_permission_review`, suppression_status `clear`,
`suppression_review` items `approved` (list-clear only — **not** consent), but WhatsApp/email
permission stays `needs_more_info` and `approved_for_segment` stays **0**. No channel permission is
granted (a `permission_decision='allowed'` requires a real `channel_permissions` allowed row). Done via
`scripts/review_dlf_contact_permission_evidence.py --real-ok --apply` (reversible via
`scripts/revert_dlf_contact_permission_evidence.py`). See
`docs/PHASE_7_9_DLF_CONTACT_PERMISSION_EVIDENCE.md`.

**DLF controlled test lead intake (Phase 7.10):** open `vw_dlf_test_lead_readiness` first
(`ready_for_live_lead_capture` must be **false**; `fake_payloads_create_real_lead_count` /
`_real_contact_count` / `external_call_made_count` must all be **0**), then
`vw_dlf_test_lead_payload_dashboard` (5 fake payloads — status/type/flags only, **no fake
name/phone/email**), `vw_dlf_test_lead_validation_dashboard` (40 validations: 37 passed / 2 failed / 1
needs_review), and `vw_dlf_test_lead_review_queue` (13 pending review items). These are FAKE-only test
rows in dedicated `launch_test_lead_*` tables — the real `inbound_leads`/`contacts` tables are
untouched (still 0 / 4). Created via `scripts/run_dlf_test_lead_intake.py --real-ok --apply
--retain-test-rows`; remove via `scripts/cleanup_dlf_test_lead_intake.py`. See
`docs/PHASE_7_10_DLF_TEST_LEAD_INTAKE.md`.

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
| Plan DLF contact segment candidates | `scripts/plan_dlf_contact_segments.py` |
| Dry-run cleanup of DLF segment candidates | `scripts/cleanup_dlf_contact_segments.py` |
| Seed DLF lead-intake plan | `scripts/seed_dlf_lead_intake_plan.py` |
| Dry-run cleanup of DLF lead-intake plan | `scripts/cleanup_dlf_lead_intake_plan.py` |
| Seed DLF n8n workflow blueprint | `scripts/seed_dlf_n8n_workflow_blueprint.py` |
| Dry-run cleanup of DLF n8n workflow blueprint | `scripts/cleanup_dlf_n8n_workflow_blueprint.py` |
| Print DLF operator cockpit counts | `scripts/dlf_operator_cockpit_summary.py` |
| Create inactive DLF n8n build package | `scripts/create_dlf_n8n_workflow_template.py` |
| Dry-run cleanup of DLF n8n build package | `scripts/cleanup_dlf_n8n_build_package.py` |
| Review inactive DLF n8n build package | `scripts/review_dlf_n8n_build_package.py` |
| Revert DLF n8n build package review | `scripts/revert_dlf_n8n_build_package_review.py` |
| Record DLF inactive n8n manual import check | `scripts/record_dlf_n8n_manual_import_check.py` |
| Dry-run revert of DLF n8n manual import check | `scripts/revert_dlf_n8n_manual_import_check.py` |
| Create DLF Wix landing/form build package | `scripts/create_dlf_wix_landing_build_package.py` |
| Dry-run cleanup of DLF Wix build package | `scripts/cleanup_dlf_wix_landing_build_package.py` |
| Seed DLF Wix UX/SEO/integration masterplan | `scripts/seed_dlf_wix_ux_integration_masterplan.py` |
| Dry-run cleanup of DLF Wix UX masterplan | `scripts/cleanup_dlf_wix_ux_integration_masterplan.py` |
| Create DLF Fable UI/UX handoff package | `scripts/create_dlf_fable_uiux_handoff_package.py` |
| Dry-run cleanup of DLF Fable handoff package | `scripts/cleanup_dlf_fable_uiux_handoff_package.py` |
| Create DLF Wix AI build execution plan | `scripts/create_dlf_wix_ai_build_plan.py` |
| Dry-run cleanup of DLF Wix AI build plan | `scripts/cleanup_dlf_wix_ai_build_plan.py` |
| Review DLF Wix AI implementation route | `scripts/review_dlf_wix_ai_implementation_route.py` |
| Dry-run cleanup of DLF Wix AI route review | `scripts/cleanup_dlf_wix_ai_implementation_route_review.py` |

The `entity_id` / `related_table` columns in `vw_human_next_actions` tell you
which record a given script should target.

Phase 7.2 adds DLF launch contact segmentation views for read-only operator review:
`vw_launch_contact_segment_candidate_dashboard`,
`vw_launch_contact_permission_review_queue`, `vw_dlf_contact_segment_readiness`,
and `vw_dlf_owner_audience_summary`. These views mask contact names and expose no
phone numbers, emails, websites, addresses, or raw payloads. Candidates remain
unapproved until explicit human permission and suppression review.

Phase 7.3 adds DLF lead-intake planning views for read-only operator review:
`vw_launch_lead_intake_endpoint_dashboard`, `vw_launch_lead_field_mapping_dashboard`,
`vw_launch_lead_attribution_rule_dashboard`, `vw_launch_inbound_lead_review_dashboard`,
`vw_launch_operator_daily_metrics_dashboard`, and `vw_dlf_lead_intake_readiness`. These views
show endpoint/mapping/rule/status counts and keep live capture blocked.

Phase 7.4 adds DLF n8n blueprint views for read-only operator review:
`vw_launch_n8n_workflow_blueprint_dashboard`, `vw_launch_n8n_node_dashboard`,
`vw_launch_n8n_payload_schema_dashboard`, `vw_launch_n8n_test_case_dashboard`,
`vw_launch_n8n_review_queue`, and `vw_dlf_n8n_readiness`. These views show planned workflows,
planned nodes, schema/test metadata, and pending review gates while build/activation stay blocked.

Phase 7.5 adds DLF operator cockpit views for daily read-only execution:
`vw_dlf_operator_cockpit_home`, `vw_dlf_operator_today_tasks`,
`vw_dlf_operator_review_backlog`, `vw_dlf_operator_campaign_calendar_next_14_days`,
`vw_dlf_operator_audience_readiness`, `vw_dlf_operator_lead_intake_readiness`,
`vw_dlf_operator_n8n_readiness`, `vw_dlf_operator_content_readiness`, and
`vw_dlf_operator_safety_posture`.

Phase 7.11 adds DLF inactive n8n build-package views for read-only operator review:
`vw_dlf_n8n_build_package_dashboard`, `vw_dlf_n8n_build_validation_dashboard`,
`vw_dlf_n8n_build_review_queue`, and `vw_dlf_n8n_build_readiness`. These views show local package
status, validation checks, review gates, and activation blockers while n8n workflow creation and
activation remain 0/false.

Phase 7.12 reviews the inactive n8n build package for manual import readiness only. The safe package,
security, privacy, and manual-import review items are approved; the activation blocker remains
`needs_more_info`. `vw_dlf_n8n_build_readiness.ready_for_manual_import` may be true, but
`ready_to_activate` must remain false and n8n workflow creation/activation counts must remain 0.

Phase 7.13 adds DLF n8n manual-import verification views:
`vw_dlf_n8n_manual_import_check_dashboard` and `vw_dlf_n8n_manual_import_readiness`. The current
state is one pending no-import check: manual import has not happened, the package remains
`approved_for_manual_import`, workflow creation remains false, activation remains false, and
`ready_to_activate` must remain false.

Phase 7.14 adds DLF Wix landing/form build-package views for read-only operator review:
`vw_dlf_wix_build_package_dashboard`, `vw_dlf_wix_build_validation_dashboard`,
`vw_dlf_wix_build_review_queue`, and `vw_dlf_wix_build_readiness`. These views show local package
status, validation checks, and review gates for a human-buildable Wix landing page + lead form. The
package is `validated` with 8 passed validations and 6 pending reviews. No Wix API/page/publish/live
form happened: `wix_pages_created`/`wix_pages_published`/`live_forms_created` stay 0 and
`ready_to_publish` stays false.

Phase 7.15 adds DLF Wix UX/SEO/integration masterplan views for read-only operator review:
`vw_wix_site_experience_dashboard`, `vw_wix_page_blueprint_dashboard`,
`vw_wix_integration_readiness_dashboard`, `vw_wix_design_component_dashboard`,
`vw_wix_ux_review_queue`, and `vw_dlf_wix_unified_experience_readiness`. These show the planned site
experience, 7 page blueprints, 11 integration readiness items, 11 design components, and 31 pending
reviews. Planning only: every integration stays `external_call_allowed=false`, every page
`publish_enabled=false`, `integrations_active=0`, and `ready_to_publish` stays false. Connecting
Meta/WhatsApp/email/n8n/Google and publishing pages are separate, explicit, review-gated phases.

Phase 7.16 adds DLF Fable UI/UX handoff views for read-only operator review:
`vw_fable_uiux_handoff_package_dashboard`, `vw_fable_uiux_handoff_section_dashboard`,
`vw_fable_uiux_handoff_validation_dashboard`, `vw_fable_uiux_handoff_review_queue`, and
`vw_dlf_fable_handoff_readiness`. These show the privacy-safe Fable handoff package (1 generated, 12
sections, 9 passed validations, 7 pending reviews) distilled from the Phase 7.15 masterplan. The
artifacts (a concise prompt + detailed brief) live git-ignored under `exports/fable_handoffs/` and
carry no contact data, secrets, or DB IDs. No Fable/external call happened: `fable_call_made_count`
and `external_call_made_count` stay 0 and `ready_for_fable_use` stays false until reviews are
approved. The operator pastes the reviewed concise prompt into Fable manually.

Phase 7.17 adds DLF Fable/Gemini design-output review views for read-only operator review:
`vw_fable_design_output_dashboard`, `vw_design_second_opinion_dashboard`,
`vw_design_refinement_action_dashboard`, `vw_fable_design_review_queue`, and
`vw_dlf_design_output_readiness`. These show the captured Fable design output ("DLF Westpark —
Gallery White", 1 captured), the Gemini second-opinion critique (1 captured), 12 proposed refinement
actions, and 14 pending review items. The raw Fable/Gemini artifacts live git-ignored under
`exports/` and are never stored in the database (only paths + business-safe summaries); a leakage
scan found no contact data, secrets, or DB IDs. No Fable/Gemini/external call happened:
`external_call_made_count` stays 0 and `ready_for_wix_design_build` stays false until a human
approves the captured output and at least one refinement action.

Phase 7.18 records the approval decision over those same views: the operator runs
`scripts/review_dlf_gallery_white_design_direction.py` (terminal, dry-run by default), which sets
the captured output to `accepted_direction`, the Gemini review to `accepted_guidance`, the 12
refinement actions to `accepted`, and approves all 14 review items. Read-only in NocoDB,
`vw_dlf_design_output_readiness` then shows `ready_for_fable_followup` and
`ready_for_wix_design_build` as true (a design-readiness signal only — `ready_for_launch_push`
stays false, send/publish stay 0, and no Fable/Gemini/Wix/external call occurs). Reversible via
`scripts/revert_dlf_gallery_white_design_review.py`.

Phase 7.19 adds DLF Wix staging/preview-site views for read-only operator review:
`vw_wix_staging_site_dashboard`, `vw_wix_staging_build_checklist_dashboard`,
`vw_wix_staging_qa_dashboard`, `vw_wix_staging_review_queue`, and `vw_dlf_wix_staging_readiness`.
These track a manually-created Wix staging site (1 `planned`), a 20-item Gallery White build
checklist, 13 pre-publish QA checks, and 7 pending review items — seeded via the terminal script
`scripts/seed_dlf_wix_staging_site_plan.py`. Every staging live flag stays false (no real domain,
no public indexing, no Wix API call, no page published, no live form/webhook, no tracking);
`ready_for_manual_staging_build` is true while `ready_for_staging_qa` and
`ready_for_production_publish` stay false. NocoDB is read-only here — the manual Wix build and QA
happen in Wix, recorded back through the guarded terminal scripts.

Phase 7.20 adds the manual Wix staging build-tracking views for read-only operator review:
`vw_wix_staging_build_action_log_dashboard` (append-only audit log of manual build progress) and
`vw_dlf_wix_staging_build_progress` (staging_status, checklist_started/passed, qa_passed,
`api_permission_review_deferred_count`, `safety_flags_clean`, `ready_for_staging_qa`,
`ready_for_fake_lead_test`). Build progress is recorded via the terminal script
`scripts/record_dlf_wix_staging_build_progress.py`, which never calls a Wix API or reads a Wix API
key. In this phase tracking was initialized only (no operator staging site supplied): 2 setup items
`in_progress`, 1 `api_permission_review_deferred` audit row; `safety_flags_clean=true`,
`ready_for_fake_lead_test=false`, `ready_for_production_publish=false`. Wix API permission/key usage
is explicitly deferred to a later capability-map phase.

Phase 7.21 adds the Wix API permission/capability-map views for read-only operator review:
`vw_wix_api_permission_catalog_dashboard`, `vw_wix_api_integration_use_case_dashboard`,
`vw_wix_api_key_profile_dashboard`, `vw_wix_api_permission_review_queue`, and
`vw_dlf_wix_api_readiness`. These map 46 Wix permissions (6 staging / 3 read-only / 14 later / 3
defer / 20 avoid) to 16 OS use cases and 4 **planned** key profiles (staging discovery, staging build
later, tracking later, production future). No secret or API key is ever stored — `secret_value_stored`
and `external_call_allowed` stay false, and `ready_for_api_key_creation`/`ready_for_api_call_test`
stay false. **Never paste a Wix API key into NocoDB, Claude, Codex, or any chat**; keys live only in a
git-ignored `.env`, Keychain, 1Password, or the n8n credential vault when eventually created
externally.

Phase 7.22 records the operator's manually created Wix staging/preview site. In the staging views
(`vw_dlf_wix_staging_build_progress`, `vw_wix_staging_build_action_log_dashboard`) the staging site
now reads `created_manually` with its name + `*.wixstudio.com` preview URL; 12 build checklist items
are `in_progress` and the safety checklist + absence QA (`domain_not_connected`/`noindex`/
`webhook_disabled`/`tracking_disabled`) are passed. `safety_flags_clean=true`,
`ready_for_staging_qa=true`, `ready_for_fake_lead_test=false`, `ready_for_production_publish=false`.
No Wix API call/key, no real domain, no indexing, no publish, no live form/webhook/tracking — all
recorded via the terminal script (NocoDB stays read-only).

Phase 7.23 adds Wix AI build execution views for read-only operator review:
`vw_wix_ai_build_execution_plan_dashboard`, `vw_wix_ai_build_artifact_dashboard`,
`vw_wix_ai_build_step_dashboard`, `vw_wix_ai_build_validation_dashboard`,
`vw_wix_ai_build_review_queue`, and `vw_dlf_wix_ai_build_readiness`. These show the generated local
Gallery White implementation package, the preferred Wix Git Integration + Wix CLI route, the fallback
Custom Element + Velo route, 13 validation results, and 9 review gates. Artifacts stay ignored under
`exports/wix_ai_builds/`. Code review/operator setup can be ready, but Wix implementation, fake lead
testing, publishing, live forms/webhooks/tracking, and API usage remain blocked until later phases.

Phase 7.24 adds Wix AI implementation route-review views for read-only operator review:
`vw_wix_ai_implementation_route_decision_dashboard`, `vw_wix_ai_artifact_review_dashboard`,
`vw_wix_ai_operator_setup_task_dashboard`, `vw_wix_ai_execution_package_step_dashboard`,
`vw_wix_ai_implementation_review_queue`, and `vw_dlf_wix_ai_implementation_readiness`. These show
the selected `wix_git_cli` route, `wix_custom_element_velo` fallback, 11 passed artifact reviews,
7 pending minimum operator setup tasks, 3 planned AI execution steps, and 8 pending review gates.
`ready_for_operator_setup` may be true, but AI execution/code paste, fake lead testing, and production
publish remain blocked until review and setup clear. This is not a manual drag/drop build.

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
