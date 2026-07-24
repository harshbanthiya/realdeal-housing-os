# NORTH STAR — what we are building, and how every day's work must serve it

This is the document every other plan answers to. Read it before proposing
work. If a task does not move one of the loops in §3, it is either a §7
day-to-day fire (handle it, log it, move on) or it should not be done.

Written 2026-07-24. Amend it deliberately; do not let it rot.

---

## 1. The business in one paragraph

A genuine buyer or renter in Mumbai is hunting for a specific building —
"Kalpataru Radiance", "Ekta Tripolis", "Imperial Heights Goregaon West". They
search Google, YouTube, Instagram. **They must find us.** When they do, they
must land on a page that tells them the truth — real footage, real registration
history, real prices — get their first few questions answered immediately, and
then be handed to a human who can actually serve them. The AI never sells. The
AI makes sure the human is never late, never without context, and never guessing.

Everything we build is upstream or downstream of that sentence.

## 2. The philosophy — being great is the benchmark

**Take a smaller chunk and do it exceptionally, then spread organically.**

We are not trying to cover Mumbai. We are trying to be, without qualification,
the best source of truth on the internet for four buildings. When someone
searching "Ekta Tripolis" finds a page with every registration since 2015, real
footage of the actual tower, and a person who replies — we have won that
building. Then we take the fifth.

Concretely this means:
- **Depth before breadth.** One building fully known beats ten buildings
  sketched. Refuse work that widens before the current chunk is genuinely good.
- **Nothing ships at 70%.** A half-right price on a page is worse than no page.
- **Measured or it didn't happen.** Every loop in §3 has a number. If we can't
  measure it, we build the measurement before we build the feature.
- **Compounding beats bursts.** A worker that improves 1% daily and never
  regresses beats a heroic weekend. This is why every expert (§5) owns an eval
  set: so improvement is provable and regression is caught.
- **Human in the loop, always, on anything outward-facing.** Not as a
  bottleneck — as the quality gate that lets us move fast everywhere else.

### The ds4 lesson (philosophy adopted, software rejected)

antirez's ds4 is built on *deliberate narrowness*: it refuses to be a general
model runner, specializes in a few best-in-class models, integrates loading /
prompting / tool-calling / serving as one tested system, and drops models the
moment something better exists. Specialization over generality.

**We adopt that stance and reject the software.** ds4 targets 96GB+ RAM —
"128 GB laptops and 512 GB workstations". Our machine is an **M1 MacBook Air,
8GB RAM, 8 cores**. ds4 is not a near-miss here; it is off by an order of
magnitude. Anyone who proposes it again should be pointed at this paragraph.

What we take instead: be narrow on purpose, integrate vertically, and pick the
smallest thing that is genuinely good at exactly our job.

## 3. The four loops (everything is one of these)

Each loop has an owner metric. If the number isn't moving, the loop is broken.

| # | Loop | What it does | Metric |
|---|------|--------------|--------|
| 1 | **Know** | Turn drive + IGR + WhatsApp into verified facts per building/unit | % units with a complete registration + price history |
| 2 | **Be found** | Shorts, blogs, building pages, schema, AI-search citations | impressions + clicks per building slug (GSC), YouTube views |
| 3 | **Convert** | Site answers the first questions, then hands to a human fast | wa.me clicks / enquiries per 100 sessions (PostHog) |
| 4 | **Serve & remember** | Every contact has full history; the human is never without context | % contacts with activity timeline; time-to-first-reply |

Loop 1 is the moat — nobody else has it. Loop 2 is the only growth channel we
control for free. Loop 3 is where the money is lost today. Loop 4 is what makes
a repeat client.

**Current honest state:** Loop 1 is strong and getting stronger. Loop 2 has
machinery but starves on unreviewed media. Loop 3 is *unmeasured until PostHog
has production traffic* — fix this first, we are flying blind. Loop 4 barely
exists beyond WhatsApp ingest.

## 4. What we already have (do not rebuild these)

- **Facts**: 44,572 drive files catalogued (`drive_files`, DRIVE-MAP.md);
  IGR registrations for Kalpataru / Ekta / Imperial Heights; DLF unit→floor-plan
  mapping; MyGate rosters; 3,500+ contacts; PAN fragments for enrichment.
- **Pipes**: Postgres as the single source of truth; guarded Python writers;
  read-only cockpit; worker harness (`workers/_lib.py`) with run logging and a
  findings inbox; n8n container; Remotion video template; YouTube upload with
  scheduling; Resend email; Beeper/WhatsApp read-only ingest + search.
- **Review**: `/cockpit/review` — cohort approval across 8 queues, dry-run then
  confirm. This is the human-in-the-loop gate. It is the throttle on everything.
- **Local model**: Ollama + `qwen3:4b` (2.5GB). Gemini free tier as the
  escalation tier. Both wired through `workers/_llm_tiers.py`.

## 5. Contact intelligence and the expert layer — how we actually get there

The ask: correlate WhatsApp conversation with contacts, know every interaction
regardless of role, and route requests to specialised experts that keep getting
better.

### 5.1 The hard constraint shapes the design

On 8GB, with Docker + Postgres + Next.js already resident, we can hold **one
small model in memory at a time**. So:

> **Experts are prompts, tools, and eval sets — not separate models.**

An "expert" here = a named system prompt + the exact tools it may call + a
golden eval set + a recorded score. One model (`qwen3:4b`) wears many hats,
loaded once, serialised. This is ds4's narrowness applied honestly to our
hardware.

### 5.2 Routing is deterministic, not a model

Do **not** build an LLM router. It doubles latency, burns the memory budget,
and is unpredictable. Route on facts we already have:

```
inbound thing (message / task / row)
  → classify by CHEAP signals first:
      chat kind (broker_group / tenant_group / client) — already in wa_chats
      regex intent (price? availability? requirement? complaint?)
      entity hits (building alias, unit pattern, phone in contacts)
  → deterministic table maps (kind × intent) → expert
  → expert runs with ONLY the context it needs
  → output is review-gated, scored, logged
```

An LLM is used **inside** an expert, never to decide which expert runs.

### 5.3 The experts we actually need (in build order)

1. **Activity retrieval** — "everything we know about this contact": WhatsApp
   timeline, registrations, units, outreach, notes. *Mostly SQL, no LLM.* Build
   this first: every other expert consumes it, and it is the Loop-4 metric.
2. **Classification** — role (owner/tenant/broker/lead), intent, building.
   Cheap local model + regex tiers. Feeds routing itself.
3. **Context/brief** — compress a contact's history into the 5 lines a
   salesperson needs before calling. Highest human value per token spent.
4. **Content** — Shorts copy, blog drafts, building-page facts (`shorts_scout`
   is the first one and already exists).
5. **Email/outreach** — sequence drafting, always human-sent.

Each ships with `evals/<expert>.jsonl`: 20–50 real cases with expected output.
An expert may not be changed without re-running its evals. **A score that drops
is a blocked change.** That is the compounding mechanism — not vibes.

### 5.4 Groundwork required before any of this pays off

In strict order. Skipping ahead wastes the model budget on bad context.

1. **Identity resolution must be solid.** One person = one contact row, phone-
   keyed. `contact_reconcile` + the dedupe cohorts are exactly this work. An
   expert reasoning over a fragmented contact graph produces confident nonsense.
2. **An event spine.** One append-only `contact_activity_events`-shaped view of
   *everything* — WhatsApp message, site visit, enquiry, call, outreach, doc
   signed — with `occurred_at`, `contact_id`, `kind`, `payload`. Loop 4 is
   impossible without it; the expert layer becomes easy with it.
3. **Text extraction.** ~2,400 PDFs and ~2,800 docs are opaque today
   (DRIVE-MAP.md §when to upgrade). `pdftotext` → Postgres FTS answers most
   content questions without embeddings. Do this before anyone says "RAG".
4. **Eval harness.** A tiny runner: feed cases, diff against expected, record
   score in a table. ~100 lines. Without it "the model got better" is a feeling.
5. **Only then** embeddings/pgvector, and only where FTS measurably fails.

### 5.5 Where n8n fits

n8n is the **glue for external systems on a schedule** (webhooks, Resend,
inbound leads, cross-service handoffs) — not the place to put intelligence.
Business logic lives in guarded Python where it is testable and reviewable.
Rule of thumb: if it needs an eval, it is not an n8n node.

## 6. What "measured" means

Nothing counts until it appears in one of these:

- **PostHog** — sessions, source attribution (`utm_campaign=<building-slug>`),
  wa.me click rate. *Blocked on the production key — highest-priority unblock.*
- **Google Search Console** — impressions/clicks per building slug (`gsc_report.py`).
- **YouTube** — views/retention per Short, tagged by building.
- **Postgres** — coverage counts (`vw_drive_building_coverage`,
  `vw_contact_reconcile_progress`), review burndown, worker run history.
- **Reply latency** — time from enquiry to human reply. The one number a
  customer actually feels.

Weekly: one line per loop, per building. If a number didn't move, say why.

## 7. Day-to-day fires — how they get handled without derailing us

Real businesses have real interruptions. The rule is: **do them properly, log
them, and return to the loops.** They must not become architecture.

Protocol:
1. Solve it with the smallest thing that works (usually a script in `scripts/`).
2. Write down what was learned in the relevant doc — never only in chat.
3. If the same fire recurs twice, *then* consider a worker for it.
4. Never let a fire silently rewrite the roadmap.

### Live example: broker WhatsApp Community

**Goal:** every broker we know is in one Community, so one message reaches all
of them without blocks or bans (~5,000 member ceiling).

**What is NOT automatable** — accept this and stop looking: WhatsApp has no
bulk-add API. A person must be in the sales phone's address book, and joining
is by tapping an invite link. `build_broker_channel_invites.py` already
documents this.

**What IS automatable, and is our job:**
- Consolidate every broker across the 10 drive sheets (~16k rows; `BROKERS ONLY.csv`
  3,147, `Brokers List ENTIRE - Brokers.csv` 5,793, `All over Brokers.csv` 7,077)
  plus the 10 classified broker WhatsApp groups → dedupe by phone.
  *Note: the `contacts` table currently holds **zero** brokers — this is a real gap.*
- Emit a **vCard (.vcf) batch** to import into the sales phone in one action,
  named consistently (e.g. `RDH Broker · <Name> · <Area>`) so the phonebook
  stays sane and future saved-name parsing works.
- Mint per-broker tracked invite links (already built) so we learn who joined.
- Track membership state in Postgres so we never re-invite or double-add, and
  can measure reach honestly.

That is a contained job that also *feeds Loop 1 and Loop 4* — which is what a
well-handled fire looks like.

## 8. Guardrails for whoever works on this next (human or Claude)

- **Read this file, then `docs/NEXT-SESSION.md`.** Do not re-derive state from
  the code; the docs and the DB are the state.
- **Query, don't crawl.** The drive is catalogued (`drive_files`). Running
  `find` over 45k files on a slow exFAT volume is a dead end by definition.
- **Postgres is the truth.** Web reads are read-only; every write goes through a
  guarded script that is dry-run by default. Do not add a second write path.
- **Never widen scope to look productive.** Four buildings, done properly.
- **Leave the check behind.** Non-trivial logic ships with one runnable check
  (`--selfcheck`, a test, an eval). The drive classifier's selfcheck caught a
  real misclassification within minutes of being written — that is the standard.
- **Say what is blocked and why.** A blocked item named plainly is progress; a
  blocked item quietly worked around is debt.
- **Correct the premise when it is wrong.** ds4 on an 8GB Air is the worked
  example. Building on a false premise wastes more than saying so costs.

## 9. The 3 things that matter right now

Everything else waits behind these.

1. **PostHog key into Vercel** → Loop 3 becomes measurable. Minutes of work,
   unblocks all attribution.
2. **Burn the review cohorts** at `/cockpit/review` → unblocks media for Shorts
   (Loop 2), unblocks contacts for outreach (Loop 4). The system is throttled on
   human review by design; this is the throttle.
3. **Event spine + activity-retrieval expert** → the foundation the whole
   intelligence layer stands on, and the first thing that makes a salesperson's
   day visibly better.
