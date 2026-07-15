# FABLE Real Estate Intelligence Roadmap

> Persistent context document. Any agent resuming work MUST read this first, then the
> "Resume here" section at the bottom. Last updated: 2026-07-08 (Fable 5).

## 1. Mission

Build Real Deal Housing OS into a low-cost, high-standard, human-operated, agentic
real-estate intelligence business: premium public website, headless Wix CMS/CDN,
AI concierge, persistent consumer journeys, deep building/apartment intelligence,
a scraper/parser swiss army knife, human approval cockpit, daily agent jobs,
SEO/AI-search dominance for priority buildings, salesperson field assistant,
market monitoring, and lawful consent-aware identity enrichment.

Product posture: **high-trust intelligence desk, not surveillance.** Every
sensitive or outward-facing action goes through a review queue first.

## 2. Current state (verified 2026-07-08)

- Local Postgres is the source of truth; **62 migrations (schemas/001–062)**, ~150 tables
  (061 = worker layer, 062 = zapkey transactions; the next free number is 063).
- `web/`: Next.js 16 + React 19 + Tailwind 4 + Wix SDK + pg + Resend; cockpit at
  `/cockpit/*` (outreach, media, contacts). Vitest + Playwright test setup.
- Docker stack: Postgres, NocoDB, Adminer, n8n (see `docker/`, `start.sh`).
- Real data already flowing: 1,310 canonical contacts (1,240 attached to 6 buildings),
  Kalpataru Radiance 1,627 staged IGR registrations, Imperial Heights RERA + IGR
  timelines, PAN KYC enrichment (migrations 052/054, IDfy interface, access-logged),
  media DAM (056), brochure extraction staging (057/058).
- Website: production deploy done, real listings catalogue + detail pages,
  Gallery White design system in `web/` (follow it). realdealhousing.com Wix
  editor site's PAGES are off-limits, but its dashboard/CMS/media is now the live
  headless backend (2026-07-14); Wix "Test" site is a media archive — never delete.
- Review-gated everything: `*_review_items` tables + `review_action_log` pattern
  is established across all pipelines.

## 3. Assumptions

- Single human operator (Harsh) approves everything; throughput of the review
  queue is the real bottleneck, not compute.
- Budget ≈ $0 infra beyond what's running; LLM spend must be tracked and batched.
- External APIs available-ish: Surepass/IDfy (PAN/mobile/email verify), Wix, Resend.
  WIX_CLIENT_ID was a known blocker for headless CMS reads (see LAUNCH_CONTEXT.md).
- India/Mumbai market; MahaRERA + IGR are the authoritative public registries;
  portal scraping (99acres/MagicBricks/Housing/NoBroker) has ToS risk — manual/
  assisted capture is the default, automation only where terms allow.
- DPDP Act 2023 applies to personal data: consent, purpose limitation, and
  deletion rights are legal requirements, not nice-to-haves.

## 4. Tool evaluation (prior shortlist + Kampouse stars crawl)

Crawled all 1,037 starred repos via GitHub API (2026-07-08, 12 pages). Full dump
was scanned by keyword buckets (scraping/parsing, agents/workflows, search,
analytics, comms, data tools). Findings below; stars counts are as of crawl date.

### Verdicts on prior CTO shortlist

| Repo | Use case | Impact | Effort | Priority | Verdict | Reason |
|---|---|---|---|---|---|---|
| **pgmq** (5.0k★, in stars) | Ingestion/job queue on Postgres | High | Low | P0 | **Adopt now** | Postgres-native SQS; zero new infra; exactly the "every agent writes to a queue" primitive |
| **Vercel AI SDK** (25.4k★, in stars) | AI concierge, streaming/tool-calls in Next.js | High | Low | P0 | **Adopt now** | Already on Next.js 16; the obvious concierge substrate |
| **Langfuse** (30.7k★, in stars) | LLM traces, cost, prompt versions | High | Low-Med | P0 | **Adopt now** | Self-host via docker-compose; token-budget principle is unenforceable without it |
| **PostHog** (35.4k★, in stars) | Product analytics, funnels, replay | High | Low | P0 | **Adopt now (cloud free tier)** | Self-host is heavy (ClickHouse+Kafka); free 1M events/mo cloud tier is the lazy correct answer |
| **Meilisearch** (58.5k★, in stars) | Search across buildings/units/docs/blog | Med-High | Low | P1 | **Adopt @60d** | Single binary, trivial ops; wait until content volume justifies it |
| **Meetily** (21.3k★, in stars) | Local call/meeting transcription | Med | Med | P1 | **Adopt @60d** | Privacy-first local Whisper/Parakeet + diarization; perfect for field assistant, but field assistant is 60d scope |
| **Prefect** (22.8k★, in stars) | Python pipeline orchestration | Med | Med | P2 | **Later** | cron + pgmq + n8n covers current job count; adopt when >5 pipelines need retries/observability |
| **Graphiti** (28.5k★, in stars) | Temporal knowledge graph | Med | High | P2 | **Later (60d pilot at most)** | Needs Neo4j/FalkorDB + LLM per episode = cost; migrations 047/048 already model ownership/tenancy timelines in SQL. Pilot only if temporal queries outgrow SQL. |
| **Trigger.dev** (15.6k★, in stars) | Background workflows | Low here | Med-High | P3 | **Skip** | Cloud-first, heavy self-host; n8n + cron + pgmq already cover the trigger surface |
| **Budibase** (28.1k★, in stars) | Operator cockpit | Low here | Med | P3 | **Skip** | Custom Next.js cockpit + NocoDB already exist and are better fitted |
| **Dokploy** (35.5k★, in stars) | Deployment | Med later | Low | P2 | **Later** | Adopt at the point web/ moves off current hosting; not a today problem |
| **Payload CMS** (43.5k★, in stars) | CMS fallback | Low | High | P3 | **Skip unless Wix fails** | Agreed with prior CTO: fallback only |
| **OpenBrowser** (9.5k★, in stars) | Autonomous browser agents | Low | Med | P3 | **Skip** | Playwright already installed + human-in-loop capture flow proven (RERA 6.10–6.12); autonomous browsing adds ToS risk |
| **agentic-qe** (408★, in stars) | AI QA fleet | Low | Med | P3 | **Skip** | Playwright e2e in web/ suffices; niche, coding-agent-oriented |
| **agentic-cal** (17★, in stars) | Scheduling/email hub | — | — | P3 | **Skip (immature)** | 17 stars, Cloudflare-Workers-specific. Use Cal.com self-host if scheduling ever needs a product |
| **Da7-Tech/mind** (10★) / **ByteRover** (4.9k★, in stars) | Agent memory | — | — | P3 | **Skip** | 10★ is not adoptable; Claude memory + this doc + phase docs already are the memory layer |
| **Semantica** (1.4k★, in stars) | Provenance/governance | Low | High | P3 | **Skip** | Provenance already implemented natively (source_files, internal_source_evidence, *_review_items, pan_access_log) |
| **Wix CMS/CDN** | Public content + media | High | In flight | P0 | **Adopt (continuing)** | Already the plan; Test-site CMS seeded (7 collections) |

### New finds from the stars crawl (not in prior shortlist)

| Repo | Use case | Impact | Effort | Priority | Verdict | Reason |
|---|---|---|---|---|---|---|
| **pgmq** (5.0k★) | (listed above — the single best find) | High | Low | P0 | Adopt now | |
| **lightpanda** (31.7k★) | Headless browser for AI/automation | Low-Med | Med | P3 | Skip for now | Zig, early; Playwright covers it |
| **refine** (35.2k★) | Admin panel framework | Low | Med | P3 | Skip | Cockpit is already custom-built |
| **useplunk/plunk** (5.3k★) | OSS email platform | Low | Med | P3 | Skip | Resend + react-email already integrated |
| **RamiAwar/dataline** (1.6k★) | Chat-with-your-DB for operator | Med | Low | P2 | Later (nice-to-have) | Could let operator query Postgres in English; low risk if read-only creds |
| **electric-sql/pglite** (15.5k★) | Embedded Postgres | Low | — | P3 | Skip | No offline/embedded need yet |
| **supermemory** (28.3k★) | Memory engine | Low | Med | P3 | Skip | Same reason as mind/ByteRover |
| **scira** (11.8k★) | AI search engine | Low | Med | P3 | Skip | Not the product |
| **faiss** (40.5k★) | Vector similarity | Low | Med | P3 | Skip → use pgvector | Postgres-centric system; pgvector is the right shape |
| **cipher387/API-s-for-OSINT** (2.4k★) | OSINT API list | — | — | — | **Reject on posture** | Silent person-enrichment contradicts the high-trust desk principle |

### Gaps the stars list does NOT cover (my additions, from outside the list)

| Tool | Use case | Verdict | Reason |
|---|---|---|---|
| **docling** (IBM) or **marker+surya** | PDF/scanned-PDF/OCR → structured | **Adopt now** | The stars list has almost zero document-parsing tooling; this is RDH's core ingestion need. docling: MIT, local, tables+OCR+layout. Current pdftotext pipeline (6.20) keeps working; docling is the upgrade path for scanned docs & brochures. |
| **pgvector** | Embeddings for doc/unit/FAQ search + dedupe assist | Adopt @30–60d | One `CREATE EXTENSION`; powers concierge retrieval over building facts |
| **faster-whisper** | Local voice-note/call transcription | Adopt @60d | What Meetily wraps anyway; can be used standalone for salesperson voice notes |
| **Cal.com** (self-host) | Visit scheduling | Later | Only if visit coordination outgrows WhatsApp + manual |

**Overall judgment on the prior CTO list:** directionally right (Langfuse, PostHog,
Meilisearch, Vercel AI SDK, Meetily, "avoid giant agent OS" are all correct), but it
over-weighted new orchestration infra (Trigger.dev, Prefect, Graphiti now) and
under-weighted two facts: (1) the existing Postgres schema already implements
provenance + review-gating natively, and (2) the missing capability is **document
parsing**, which nothing on the list addressed. pgmq + docling are the two highest-
leverage adoptions.

## 5. Architecture decision: canonical objects

**Decision: do NOT build five new greenfield objects. Map them onto existing tables
and add only thin missing pieces.** The schema already encodes 6+ months of review-
gated workflow; parallel new objects would fork the truth.

| Canonical object | Already exists as | Missing (build this) |
|---|---|---|
| **ConsumerCase** | `inbound_leads`, `lead_requirements`, `interactions`, `contact_activity_events`, `whatsapp_assisted_queue`, `email_drip_state` | A `consumer_cases` spine table (id, contact_id nullable, source_campaign, consent_stage, requirement_id, status, next_best_action) + `consumer_case_events` unified timeline view over the existing event tables. One migration. |
| **BuildingIntelligenceProfile** | `buildings`, `building_aliases`, `building_tower_structure`, `building_property_identifiers`, `building_web_profiles`, `rera_project_profiles`, `rera_carpet_area_records`, `media_assets` | A `building_intelligence_view` (read model joining the above) + `building_facts` table: (building_id, fact_type, value, source_file_id, confidence, contradicts_fact_id, review_status). Contradiction tracking is the only genuinely new concept. |
| **ApartmentIntelligenceProfile** | `building_units`, `unit_registration_records`, `unit_registration_parties`, ownership/tenancy timelines (047/048) | `unit_facts` (same shape as building_facts: floorplan, facing, view, area variants) + listing-readiness check view. |
| **EntityProfile** | `contacts` + canonical merge machinery, `contact_methods`, `idfy_pan_results`, `pan_access_log`, `registration_party_contact_matches` | Essentially done. Add `consent_records` (contact_id, purpose, channel, granted_at, evidence, revoked_at) — today consent lives scattered in `channel_permissions`/launch tables. |
| **SourceArtifact** | `source_files`, `internal_source_evidence`, `brochure_extractions`, `rera_snapshot_captures`, `media_assets` | Unify under `source_files` as the one registry: add columns (artifact_kind, sha256, parse_status, parser, confidence) so screenshots/API responses/XLS all register there. Every `*_facts` row FKs to it. |

### System diagram

```
                          ┌────────────────────────────────────────────┐
                          │            PUBLIC SURFACE                  │
                          │  web/ (Next.js 16, Gallery White)          │
                          │  listings · building pages · blog(Wix CMS) │
                          │  AI concierge (Vercel AI SDK)              │
                          │  PostHog (analytics) · Wix CDN (media)     │
                          └───────────────┬────────────────────────────┘
                                          │ leads / questions / consent
                                          ▼
┌──────────────┐   files    ┌────────────────────────────────────────────┐
│ INGESTION    │──────────▶ │        POSTGRES (source of truth)          │
│ PDFs XLS     │  pgmq      │ source_files → staging → *_review_items   │
│ screenshots  │  queues    │ → canonical: buildings/units/contacts      │
│ IGR/RERA     │            │ + facts tables (confidence, provenance)    │
│ brochures    │            │ + consumer_cases · consent_records         │
│ portal data  │            │ + pan_access_log (audited identity)        │
└──────────────┘            └───────┬───────────────────┬────────────────┘
       ▲                            │                    │
       │ parsers (docling,          ▼                    ▼
       │ pdftotext, xlrd,   ┌───────────────┐   ┌──────────────────────┐
       │ vision LLM)        │ COCKPIT       │   │ DAILY AGENTS (cron/  │
       └────────────────────│ /cockpit/*    │   │ n8n → pgmq → queue)  │
                            │ + NocoDB      │   │ all output = review  │
                            │ HUMAN APPROVES│◀──│ items, never direct  │
                            └───────────────┘   └──────────────────────┘
                                    │                    │
                                    ▼                    ▼
                            publish: Wix CMS/blog · listings · WhatsApp
                            (Langfuse traces every LLM call end-to-end)
```

## 6. Scraper/parser swiss army knife

Principle: **one registry (`source_files`), one queue (pgmq), many narrow parsers,
every extraction lands in a staging table with confidence + provenance, human
approves promotion to canonical.** This is already the proven pattern (6.13, 6.19,
6.20, 6.22, brochure staging 057) — generalize it, don't reinvent it.

| Source type | Parser approach | Output/staging | Confidence | Dedupe | Safety |
|---|---|---|---|---|---|
| Digital PDF (Index II, RERA) | pdftotext (proven, incl. Devanagari fix 6.20) → regex/structured | `unit_registration_*`, `rera_*` staging | High for known layouts | doc-number uniqueness (migration 060) | Auto-parse, human-promote |
| Scanned PDF / brochures | **docling** (layout+OCR+tables) → LLM cleanup pass | `brochure_*` staging (057/058) | Med; per-field scores | building_id + fact_type | Auto-parse, human-promote |
| XLS/XLSX/CSV (IGR exports) | existing xls bulk parser (6.22, PRIMARY loader) | `import_*` rows → staging | High | reg-number + CTS | Auto-parse, human-promote |
| Screenshots (WhatsApp/MyGate/portal) | Claude vision → JSON schema per screenshot type | new `screenshot_extractions` staging | Med-Low; always review | phash on image + extracted keys | **Always human review**; MyGate/WhatsApp contain third-party personal data → consent/purpose check before promotion |
| Website pages / portal listings | Manual save or assisted Playwright capture (RERA 6.11/6.12 pattern: human solves CAPTCHA, no bypass) → snapshot table → parser | `*_snapshot_captures` pattern | Med | URL + content hash | Rate-limited, robots-aware, no CAPTCHA bypass ever |
| Images/videos | Media DAM (056) + vision captioning → `media_assets` metadata | exists | Med | sha256 | Auto-tag, human-approve for publishing |
| API responses (IDfy/Surepass/Wix) | Typed clients, raw response stored | `idfy_*` pattern (054) | High | request hash | Purpose + access log mandatory (pan_access_log pattern) |
| Emails / call transcripts / voice notes | faster-whisper local → LLM summary → action extraction | new `interaction_transcripts` → `interactions` | Med | interaction id | Consent required for recording; store consent flag on transcript |
| Manual notes | Cockpit forms | `interactions`, operator notes | High (human) | — | None needed |

Build order: (1) generalize `source_files` registry + pgmq intake queue,
(2) screenshot vision parser (biggest untapped data: WhatsApp/MyGate archives),
(3) docling for scanned brochures, (4) transcripts at 60d.

## 7. Market monitoring

No blind scraping. Per-portal approach, in order of preference:
1. **Official/permitted:** MahaRERA (human-assisted capture proven), IGR eSearch
   (proven), portal RSS/sitemaps where published, developer press pages.
2. **Manual upload fallback:** operator saves portal pages/screenshots → screenshot
   parser → staging. Zero ToS risk, works today.
3. **Assisted browser capture:** operator-initiated Playwright session (6.11 gates:
   CAPTCHA and external warnings stop the run), rate-limited, attributed.

Jobs (all write to review queues, never auto-canonical):
- Weekly: per priority building — new/changed/removed listings vs last snapshot →
  `market_observations` staging (new table, same facts shape).
- Weekly: price-per-sqft trend per building from observations + own registrations.
- Monthly: RERA status re-check for tracked projects (`rera_project_status_checks` exists).
- Alerts: repeated broker inventory, supply spikes, price cuts → operator task.

## 8. SEO / AI-search content engine

Assets exist: seo_keywords, content_briefs, content_items, quality checks, source
requirements, publishing queue, gap-resolution workflow (014–016). The engine is
mostly *operationalizing* what's built:

- **Weekly Content Scout job:** questions people ask about priority buildings
  (People-Also-Ask, portal Q&A, own concierge logs once live) → `content_briefs`.
- **Per building:** fact page (RERA + registry-backed), FAQ (schema.org FAQPage),
  comparison pages (X vs Y in locality), locality page. All facts must FK to
  `source_files` — the existing source-requirement checks (014) enforce this.
- **AI-search (AEO):** structured data (schema.org Residence/Place/FAQPage/
  RealEstateListing), llms.txt, stable fact-dense pages with cited sources —
  RDH's registry-backed facts are exactly what LLMs can't get elsewhere; that is
  the moat. Original prose only; no scraped/copied content; no unverifiable
  price/legal claims (quality checks already encode this).
- **Stale detection:** content_items.updated_at vs building facts changed-at → refresh queue.
- **Rank tracking:** manual weekly check on 10–20 target queries in a sheet first;
  a tool only if that becomes painful.
- Publishing always through `content_publishing_queue` + human approval.

## 9. Listing generation (approval-based)

Flow: unit passes listing-readiness view (facts + ≥N approved media + price source)
→ Listing Draft Agent composes title/description/highlights from `unit_facts` +
`building_facts` ONLY (no invention; missing fields listed, not filled) → risky-claim
check (reuses content_quality_checks) → operator approves in cockpit → export to
web/ listing + Wix CMS + WhatsApp card + social draft. Price/rent shown only when
source-backed (registration record, owner instruction, or comparable set).

## 10. Salesperson field assistant

Mobile-friendly cockpit routes (`/cockpit/field/*`), not a new app:
- **Before call:** lead brief = consumer_case + building facts + prior interactions, one screen.
- **During call:** recording ONLY with stated consent; local transcription (faster-whisper/Meetily).
- **After call:** LLM summary → requirements/objections/next action → draft to review, one-tap accept into consumer_case.
- **Before visit:** visit brief (unit facts, open questions, documents to request).
- **During visit:** voice note + photo upload → ingestion queue.
- **After visit:** follow-up WhatsApp draft → whatsapp_assisted_queue (Lane A human-send, Phase 8.0 pattern).
- **Manager view:** pipeline board over consumer_cases.

60-day scope; the only new infra is faster-whisper + the routes.

## 11. Daily agent ecosystem

Rule: narrow agents, cron/n8n triggered, pgmq for work items, **output = review
items only**. Langfuse tags per agent enforce daily token budgets; on failure, log
+ skip + surface in daily digest (never retry-storm).

| Agent | Trigger | Inputs → Outputs | Approval point | Risk | Budget/day |
|---|---|---|---|---|---|
| 1. Content Scout | weekly cron | keywords, PAA, concierge logs → content_briefs | brief approval | Low | ~50k tok |
| 2. Building Librarian | on new source_file | staged facts w/ confidence → building/unit_facts staging | fact promotion | Low | ~100k |
| 3. Registry Timeline | on new registrations | ownership/tenancy timeline diffs → review items | timeline change | Med | ~30k |
| 4. Lead Triage | on inbound lead | lead → scored consumer_case + suggested reply draft | reply send | Med | ~20k |
| 5. Visit Coordinator | on visit request | availability → proposed slots draft | msg send | Med | ~10k |
| 6. Listing Draft | unit reaches ready | facts+media → listing draft | publish | Med | ~30k |
| 7. Market Monitor | weekly | snapshots → market_observations + alerts | observation accept | Low | ~50k |
| 8. SEO Refresh | weekly | stale content vs changed facts → refresh drafts | publish | Low | ~50k |
| 9. QA | daily | broken links, missing images, failed checks → operator tasks | n/a (read-only) | None | ~10k |
| 10. Relationship | weekly | party↔contact match candidates (6.26 pattern) → review items | merge/link | **High** | ~30k |
| 11. Data Quality | daily | dupes, orphans, stale review queues → digest | n/a (read-only) | None | ~10k |
| 12. API Verification | on operator request ONLY | PAN/mobile/email verify via IDfy/Surepass | **pre-approval required + purpose logged** | **High** | per-request |
| 13. Sales Assistant | on call/visit events | transcripts → summaries/next actions | case update accept | Med | ~30k |

Start with 4 agents (Librarian, Lead Triage, QA, Data Quality); add the rest as
their surface comes online.

## 12. Human approval / control model

Non-negotiable human gates (all already have table patterns): publishing,
external outreach/bulk messaging (whatsapp_assisted_queue Lane A), identity
enrichment (pan_access_log + purpose), legal/RERA claims, entity merges
(canonical_merge_*), destructive cleanup, pricing claims, final listings.

Additions to build: a **unified review inbox** in cockpit (one queue view across
all `*_review_items` tables, oldest-first, with counts) — operator throughput is
the bottleneck, and today reviews are scattered across many tables/views.

## 13. Compliance & risk notes

- **DPDP Act 2023:** consent_records table = consent artifact; purpose limitation
  enforced via pan_access_log pattern extended to all sensitive reads; retention
  policy per artifact_kind (define: e.g., raw screenshots with third-party personal
  data reviewed-or-deleted within N days); deletion honoring on request.
- **PAN data:** already masked in review views; keep PAN out of LLM prompts unless
  the task requires it and it's logged; never in web/ or Wix.
- **WhatsApp/MyGate screenshots contain third parties' data** — extraction is for
  internal intelligence only, never publication; review gate checks purpose.
- **Portal ToS:** no bulk scraping, no CAPTCHA bypass (established line, 6.11);
  manual/assisted capture with attribution.
- **Content:** original prose, source-backed facts, no price/legal claims without
  provenance (content_quality_checks enforce).
- **Recordings:** consent stated on-call before recording; store the consent flag.
- Known hygiene debt: n8n credential rotation still pending (see memory
  credential-hygiene-docker-env).

## 14. 30/60/90 roadmap

### Days 1–30 (spine + first loop)
1. Migration 061: `consumer_cases` + `consumer_case_events` view + `consent_records`.
2. Migration 062: `building_facts` + `unit_facts` + source_files registry columns; backfill IH + Kalpataru facts from existing staged data.
3. Install pgmq; wire one ingestion queue (file drop → parse → staging).
4. Langfuse self-host (docker-compose into existing stack); wrap all LLM call sites.
5. PostHog snippet on web/ (cloud free tier).
6. Screenshot vision parser v1 (WhatsApp/MyGate → staging → review).
7. AI concierge v1 (Vercel AI SDK) for ONE building (Imperial Heights or Kalpataru Radiance), answering from building_facts only, logging questions to consumer_cases.
8. Unified review inbox in cockpit.
9. Listing draft approval flow for ready units.
10. Resolve WIX_CLIENT_ID blocker; blog publishing path via Wix CMS.

### Days 31–60 (breadth + field ops)
1. docling for scanned brochures; finish brochure→facts pipeline.
2. Meilisearch over buildings/units/content; pgvector for concierge retrieval.
3. Agents 1/2/9/11 live on cron with Langfuse budgets.
4. Market Monitor v1 (manual-upload driven) + market_observations.
5. Field assistant v1 (/cockpit/field): lead brief, post-call summary, follow-up drafts; faster-whisper for voice notes.
6. SEO: building fact pages + FAQs + schema markup for 2 priority buildings; llms.txt.
7. Graphiti pilot decision point: only if a concrete temporal query is painful in SQL — otherwise skip permanently.

### Days 61–90 (scale + intelligence)
1. Expand to 5–15 priority buildings (facts, pages, concierge coverage).
2. Remaining agents (Registry Timeline, Relationship, SEO Refresh, Listing Draft, Sales Assistant) online.
3. Entity resolution hardening (registration parties ↔ contacts at scale).
4. API Verification workflow with full consent/purpose UI.
5. Content/social pipeline: OG images, reel/carousel scripts, comparison pages.
6. Rank/AI-citation tracking routine; monthly intelligence report per building.
7. Retention-policy enforcement job + audit review.

## 14A. MVP Experience Definition — human + worker, end state

What the MVP is when the 30-day scope is done: **one operator, a fleet of daily
workers, and a website that turns strangers into structured cases — where the
operator only ever does judgment work, and everything else happens on its own.**

### The three actors

1. **Consumer** — anonymous visitor → concierge user → WhatsApp lead → visit → client.
2. **Operator (Harsh)** — approves, calls, negotiates, decides. Target: ≤60 min/day of system work.
3. **Worker fleet** — deterministic + LLM workers running daily regardless of Claude usage.

### Consumer experience (what a visitor can do)

- Land on the Wix marketing site or a Next.js building page from Google/reels/WhatsApp forwards; pages are fast, fact-dense, source-backed (RERA/registry provenance is visible as trust signals).
- Open the AI concierge on a priority building; ask anything ("Is Wing C ready?", "What do 3BHKs go for?"). Answers come ONLY from approved building_facts, with "needs human confirmation" for price/availability/legal; every question is logged to a consumer_case.
- Progressive value gates: save a shortlist / "send this to my WhatsApp" → consent captured in consent_records → case gets a contact.
- Continue on WhatsApp without repeating themselves (operator sends from the case brief; Lane A human-send).
- Book/plan a visit, receive a follow-up that references what they actually said.

### Operator daily routine (~45–60 min)

**Morning (15–20 min) — the inbox is the whole job:**
1. Open `/cockpit/inbox`. Workers ran at 07:30; findings ranked action → warn → info.
2. Act on `action` items: approve listing drafts that hit readiness 5/5; approve content drafts; confirm/answer concierge escalations; okay parsed market files for promotion.
3. Triage new leads: each inbound already has a case card (source, requirement extracted, suggested reply draft) — edit and send via WhatsApp queue, or discard.

**Midday (opportunistic, 10–20 min):**
4. Drop anything collected into `imports/market_inbox/` — portal screenshots, brochures, IGR exports, WhatsApp screenshots. That's the entire ingestion effort: drag files into a folder.
5. Make the 1–3 phone calls the system queued (near-ready listings missing one field, owner price confirmations, visit coordination).

**Evening (10–15 min):**
6. Review facts staged by parsers (approve/reject in cockpit/NocoDB — masked views for PII).
7. Voice-note or type call/visit outcomes into the case (transcription at 60d; typing at MVP).
8. Glance at worker pulse + PostHog snapshot (visitors, concierge questions, leads).

**Weekly (~1 hr):** approve SEO briefs/refreshes for the content calendar; review market observations digest; approve entity merges and relationship candidates; check token spend in Langfuse.

**The operator NEVER:** formats listings, remembers follow-ups, hunts for documents, re-asks known requirements, writes first drafts, checks sites for changes, or wonders "what needs my attention" — all of that is worker output waiting in one inbox.

### Worker load (what runs without anyone touching it)

Daily 07:30 (deterministic, run even with zero LLM budget):
- market_watch: register new inbox files, dedupe, queue for parsing.
- data_quality: 6+ structural checks; new problems become findings.
- listing_readiness: rescore inventory; "1 field away" actions.
- seo_freshness: stale/stuck/uncovered content findings.
- review_inbox: snapshot all queues; stale-queue alarms; powers the inbox page.

Daily, LLM-assisted (once ANTHROPIC_API_KEY provisioned; skip gracefully without):
- parse stage: XLS→IGR parser, PDF→pdftotext/docling, screenshots→vision extract; all land in staging with confidence + provenance.
- lead triage: inbound → requirement extraction → case card + suggested reply draft.
- content scout: draft briefs/refreshes for uncovered/stale buildings.
- listing drafts: compose title/description/highlights from approved facts only.
- All traced in Langfuse with per-worker daily budgets.

Continuous (event-driven):
- Concierge answers visitors from approved facts, logs questions, escalates the high-risk ones, captures consent, creates cases.
- PostHog records every funnel step.

### What human + workers achieve together (MVP success criteria)

1. **No lead starts cold:** every inquiry reaches the operator as a structured case with source, requirement, and a draft reply. Response time minutes, not hours.
2. **Intelligence compounds daily:** every file dropped becomes provenance-backed facts within a day; contradictions get flagged, not buried.
3. **Listings ship themselves to 90%:** operator's only listing work is one phone call for a missing field + one approval click.
4. **SEO never goes stale silently:** every priority building has fact pages/FAQs; staleness is a finding, not a discovery.
5. **The 5,981-item backlog trends to zero** via bulk triage + daily stale-queue pressure.
6. **Nothing sensitive moves without approval:** consent, PAN, publishing, outreach, merges — all gated, all logged.
7. **The system runs on a dead-Claude day:** deterministic workers + cockpit + WhatsApp queue are fully functional with zero LLM availability.

### Explicitly OUT of MVP

Autonomous outreach/publishing; automated portal scraping; negotiation/pricing advice
beyond source-backed comparables; call recording/transcription (60d); Graphiti;
multi-operator roles; payments/contracts; consumer accounts/portal.



## 14B. Go-to-market readiness plan (2026-07-08)

Reality check: website not live/finalized; `inventory` empty; the 1,310 contacts
are registry-derived, NOT opted-in (Phase 7.9: 0 channel_permissions allowed);
no inbound lead source is on. Software without these is layers, not value.

**Human-only decisions (this week):** launch building; dedicated WhatsApp
Business number; final domain routing (Wix public vs where Next.js pages live);
portal broker subscription budget (99acres/MagicBricks — the standard Mumbai
buyer-lead source); provision ANTHROPIC_API_KEY + WIX_CLIENT_ID; claim Google
Business Profile.

**Claude-buildable to "plugged in" (1–2 weeks):** finalize site for ONE launch
building (fact page, listings, forms→inbound_leads, click-to-WhatsApp with
source attribution, PostHog, schema/OG/sitemap); migration 062
(consumer_cases/consent_records); cockpit Lead Desk (case cards + reply
drafts); bulk triage for the 5,981 backlog; inventory bootstrap queue from
unit registry (owner-confirmation call list); verify Resend domain + drip.

**Lead sources ranked (beyond contacts already in the system):**
1. Owner outreach Lane A — registry→owners of the launch building, 10–20/day
   human calls/WhatsApp, legitimate broker purpose, consent captured on reply.
   Converts the dead contact DB into inventory + permissions. Fastest real value.
2. Google Business Profile + reviews from past clients — biggest free local inbound.
3. Portal listings for confirmed inventory — paid, standard, immediate buyer leads.
4. SEO building pages + AI-search citations — compounding, 2–6 months.
5. Reels/social from existing media assets, 2–3/week, click-to-WhatsApp deep
   links with source attribution (workers draft scripts/captions).
6. Referral asks to historical clients from the old sheets.
7. Google Ads — only after the funnel converts organically.

**Compliance line for scraped contacts:** a human broker calling an owner about
their own building = normal practice; NO bulk WhatsApp/email to non-consented
numbers (number-ban + DPDP risk). Lane A human-send only, low daily volume,
opt-out honored, consent logged in consent_records on positive response.

**"MVP can start" checklist:** form→inbox case card→WhatsApp reply <15 min
end-to-end; file drop→parsed facts within a day; ≥10 confirmed inventory units;
≥1 lead source flowing; GBP live; every LLM call traced; /cockpit/inbox is the
single morning surface.

## 14C. EXECUTION PLAN — operator work order 2026-07-08 (the active plan)

Operator's priority sequence, verbatim intent: finish + finalize the site design →
live on realdealhousing.com → full Playwright e2e QA of every click/motion/flow →
Google Ads + Search Console → socials connected, funnels receive from everywhere →
PAN↔email/mobile verification API prod-tested → 99acres lead-email parsing →
WhatsApp capture/qualify interface for Padmini → Resend ramps reusable →
copywriting/research engine publishing SEO blogs continuously.

Tracked as harness tasks #1–#10 (same numbering). Order + who does what:

| # | Task | Claude does | Human does | Exit test |
|---|---|---|---|---|
| 1 | Design changes + finalize | Apply changes, polish per Gallery White | **List the specific design changes wanted**; sign off | Operator says "final" |
| 2 | Playwright e2e everything | Full suite: flows, clicks, animations, forms, mobile, reduced-motion; daily QA worker | — | Suite green locally |
| 3 | Live on realdealhousing.com | Deploy config, env, prod-safety (cockpit off) | **Domain routing decision** (Wix vs Next split), DNS access | Site live, form works |
| 4 | Search Console + Ads + PostHog | Verification tags, sitemap submit, snippet, UTM convention | Create/link Google Ads acct, GSC ownership | GSC verified, events flowing |
| 5 | Socials → funnels | sameAs schema, UTM deep links, per-source click-to-WhatsApp, single intake into inbound_leads | Update profile bios/links; GBP claim | Test lead from each channel attributes correctly |
| 6 | Verification API prod (PAN↔email/mobile) | Fix/test enrich_pan_idfy.py + surepass script (both dirty in git), both directions, access-logged, approval-gated | Prod credentials; approve first real batch | 1 real verified round-trip logged |
| 7 | 99acres email parser | .eml intake via market_inbox + parser worker → inbound_leads | **Provide 2–3 sample lead emails**; set up forwarding | Sample email → case card in inbox |
| 8 | WhatsApp capture (Padmini) | Migration 062 whatsapp_discussions + guarded capture script + /cockpit/whatsapp page (mark in-discussion, paste chat, qualify, auto-match contact) | Padmini uses it daily; feedback loop | Real conversation captured + qualified |
| 9 | Resend ramps generalized | Decouple DLF ramp sender for on-demand approved sends w/ suppression+consent | Approve sends | Non-DLF email sent to consented contact |
| 10 | Copy/research/intelligence → blogs | Facts (brochure+RERA+human-confirmed) → web research → SEO draft → review queue → Wix publish; daily worker, Langfuse | ANTHROPIC_API_KEY + WIX_CLIENT_ID; approve posts | First blog live via pipeline |

Build order rationale: 8 and 7 are revenue-adjacent and independent of the site —
they proceed in parallel with 1–3. 6 unblocks trust/verification for qualifying.
10 starts as soon as keys exist; it compounds and shouldn't wait for the site.

**Operator inputs needed to unblock (ask-list):** design-change list (#1), domain
routing + DNS (#3), Google account access (#4), profile bio updates (#5), IDfy/
Surepass prod creds (#6), 3 sample 99acres emails (#7), API keys (#10).

## 15. Blockers

- WIX_CLIENT_ID / headless CMS auth (pre-existing; see LAUNCH_CONTEXT.md).
- Surepass/IDfy production credentials + signed purpose policy before any real API verification.
- n8n credential rotation (hygiene debt).
- Operator review bandwidth — mitigated by unified inbox, but real.

## 15A. Always-on worker layer — BUILT 2026-07-08

**Operator directive (2026-07-08):** the OS must be *active* — full-time daily
workers that live and work even when Claude usage limits are exhausted; use the
architecture already built; make the cockpit actually serve the operator; small
compounding daily jobs (website/SEO/market watch/intelligence). Public site stays
on Wix; cockpit self-hosted. The long-form first-principles vision (30 agent use
cases, ConsumerCase-centric dual-mode website, consent ladder, cross-channel
continuity) was recorded by the operator in chat this date — treat it as the
north star; the worker layer below is its always-on execution substrate.

**How "works when usage is down" is solved:** workers are deterministic-first
(pure SQL via `scripts/_db.py` docker-exec psql — zero LLM, zero external deps,
run free forever). LLM steps are optional via `workers/_llm.py`, which calls the
Anthropic API directly (separate billing from Claude Code session limits) and
returns None → worker skips gracefully when no key. Key: `ANTHROPIC_API_KEY` env
or `secrets/anthropic_api_key` file (not yet provisioned).

**Built and verified live:**
- Migration `schemas/061_worker_layer.sql` (APPLIED): `worker_runs`, `worker_findings`
  (deduped operator queue; severity info/warn/action; status pending/acked/resolved).
- `workers/`: `_lib.py` (harness: log_run + finding upsert), `_llm.py`,
  `review_inbox.py` (dynamic snapshot of all 23 `*_review_items` + candidate queues,
  stale-queue findings), `data_quality.py` (6 structural checks, drift-tolerant),
  `listing_readiness.py` (5-point completeness score on `inventory`, action findings
  for ready/near-ready), `seo_freshness.py` (stale published / approved-unscheduled /
  stuck drafts / uncovered buildings), `market_watch.py` (intake: files dropped in
  `imports/market_inbox/` → sha256-dedupe → `source_files` + action finding),
  `run_all.py`, `run_if_due.sh`, `install_schedule.sh`.
- Scheduling: launchd `com.rdh.workers` daily 07:30 (installed; log
  `~/Library/Logs/rdh-workers.log`) **+ fallback**: `start.sh` now calls
  `workers/run_if_due.sh` (runs once per day on any stack start — TCC-free).
  **KNOWN ISSUE:** launchd-spawned python gets `Operation not permitted` on the
  external volume until the operator grants Full Disk Access to `/usr/bin/python3`
  (or `/bin/bash`) in System Settings → Privacy & Security. Fallback works regardless.
- Cockpit: `/cockpit/inbox` (sidebar "Inbox") — pending findings ranked by severity,
  review-queue snapshot table, worker pulse. Read-only per web/db.ts convention;
  ack/resolve via NocoDB or a future guarded script. `tsc --noEmit` clean.

**First live run results (2026-07-08):** 5,981 pending items across 22 review
queues (import_review_items alone: 4,097 stale >14d); 5,919 media assets
unreviewed; 939 units without source provenance; 7 buildings with zero content;
`inventory` table has 0 active rows (the listing pipeline has no inventory to
score — itself a key insight).

**Repo leverage status (per operator: "use all the git repos"):**
- pgmq: NOT available in the current postgres image (`pg_available_extensions` = 0).
  `worker_findings` covers the queue need today; swap to a pgmq-enabled image only
  when async multi-consumer queues are actually needed.
- docling: the designated parse path for scanned PDFs/brochures landing in
  market_inbox (next step, not yet installed).
- Langfuse: add as docker service when the first `_llm.py`-using worker goes live.
- Vercel AI SDK: concierge (30d item), unchanged.
- PostHog: still pending snippet on web/.

## 16. Tests run this session

- Migration 061 applied cleanly; all 5 workers ran `ok` against live DB (twice:
  direct + via start.sh-style guard). `run_if_due.sh` skip-path verified.
- `web/`: `npx tsc --noEmit` clean after inbox page + sidebar change.
- launchd trigger verified failing with TCC error (documented above); fallback verified.

## 17. Resume here

**State (2026-07-15):** Launch blockers CLEARED (www live on Vercel, 29 old-Wix 301s,
pushed; see PHASE_LOG 2026-07-15). Live lead capture: /api/enquiry → Wix
EnquiriesPreview + email to operator; /contact + /sell forms real. 3D maps, corrected
pins (Ekta PIN_VERIFY pending operator eyeball), favicon, own-archive media on IH/Ekta.
Deploys are MANUAL: `cd web && npx vercel --prod` (repo not connected to Vercel).

**Next task (in order):**
1. **SEO LLM worker (content_scout) on ₹0 stack** — operator chose local/open-source over
   API. Plan: (a) Ollama + qwen3:4b (~2.5GB, JSON-schema output via /v1 endpoint) for
   mechanical tiers — review-backlog triage, extraction, dedupe hints; (b) Gemini free
   tier (key in web/.env.local) for long-form SEO briefs + vision; (c) SKIP Langfuse for
   now (v3 needs ClickHouse; 8GB M1 can't) — instead `llm_runs` trace table in local
   Postgres + cockpit view. All outputs review-gated as usual. Extension: an
   answers-engine worker drafting Reddit/Quora answers that reference our pages —
   DRAFT-ONLY into a review queue, operator posts by hand from their own accounts
   (platform ToS + authenticity; same Lane A discipline as WhatsApp).
2. Listing detail pages: per-listing photo galleries (listings have more photos than the
   single card image — source from per-flat folders in RDH ALL Footage via media_assets,
   review-gated selection in /cockpit/media).
3. Image privacy for owner-entrusted photos: right-click/drag/longpress suppression +
   watermarking + low-res zoom tiles. (Screenshots CANNOT be technically blocked on the
   web — document the honest limit; watermark + resolution-capping is the real control.)
4. Media slots as "real estate": rotate hero/gallery footage by time/season/campaign —
   slot schema (slot id → asset pool + schedule) instead of hardcoded paths; ties into
   media_assets + /cockpit/media approvals.
5. Operator: grant Full Disk Access to /usr/bin/python3 so the 07:30 launchd run works unattended; drop first real files into `imports/market_inbox/`.
6. Burn down the 5,981-item review backlog with the Ollama triage tier from (1) — guarded bulk script + NocoDB view, review-gated.
7. Migration 064: `consumer_cases` + `consent_records` + `building_facts`/`unit_facts` per §5
   (063 is now media_social_funnel — listing_content/subscribers/email_suppression, 2026-07-14).
8. market_watch parse stage: XLS → existing IGR bulk parser; PDF → pdftotext/docling; screenshots → local vision model per (1).
9. Inventory bootstrap: `inventory` has 0 rows — feed it from unit registry + owner outreach so listing_readiness has something to score.

**Unresolved questions for operator:**
- Provision ANTHROPIC_API_KEY for daily LLM workers (API billing ≠ Claude Code limits)?
- PostHog cloud (free tier, data leaves machine) vs self-host (heavy)? Doc assumes cloud.
- Which building first for concierge v1: Imperial Heights or Kalpataru Radiance?
- Confirm retention window for raw WhatsApp/MyGate screenshots (proposal: review-or-delete in 30 days).

**Conventions to preserve:** review-gate everything via `*_review_items` +
action logs; masked views for PII; no writes to canonical without approval;
realdealhousing.com Wix editor site untouched; Gallery White design system in web/.
