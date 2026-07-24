# Next-session handoff — written 2026-07-24 (session 76b1967 → cohort review)

## Prompt to paste into Claude

> Read docs/NEXT-SESSION.md. Last session shipped the cohort review system
> (/cockpit/review + scripts/review_cohorts.py): the ~21k pending human-review
> rows are now grouped into 80 cohorts, each approvable in one dry-run →
> confirm step. PostHog is live (US cloud, key in web/.env.local). The
> WhatsApp Groups panel finally has the building dropdown. Check the
> human-steps section for what the operator burned down, then pick up from
> "Where to go next".

## What shipped this session

- **`/cockpit/review`** — the missing operator surface. 7 live queues grouped
  by natural cohort (batch/source/type), each with a Sample button, a dry-run
  that reports the exact row count, and a confirm step that writes. Sidebar
  link added between Inbox and Contacts.
- **`scripts/review_cohorts.py`** — the only writer. `--list`, `--sample`,
  `--apply-cohort` (dry-run unless `--apply`). The QUEUES registry at the top
  is the single source of truth for what "pending" means and what a decision
  writes; the web page reads through the same script so the two cannot drift.
- **Merge-candidate card unlocked.** It was hardcoded `apply: false` with the
  comment "the actual apply path stays intentionally unwired" — now a
  two-step Preview → Confirm that really writes.
- **WhatsApp Groups building dropdown** — shows only for tenant_group /
  community_ours, amber until set. `update_wa_item.py --building-id` always
  worked; the UI simply never exposed it.
- **PostHog fixed and live.** Project is **US** cloud but the snippet was
  hardcoded to `eu.i.posthog.com` — every event would have failed silently.
  Now `NEXT_PUBLIC_POSTHOG_HOST` with a US default. Key + host verified
  present in the built client bundle.

## Steps for the human

1. **Vercel env**: add `NEXT_PUBLIC_POSTHOG_KEY` (the `phc_m8DJ…` value in
   `web/.env.local`) to the Vercel project → redeploy. Local is already live;
   production is still blind until this is done.
2. **Burn the review cohorts** at `/cockpit/review`. Suggested order —
   biggest and safest first:
   - `media · disk_scan · video` (2,060) and `disk_scan · (untagged)` (3,530)
     — these are file-tagging decisions, low risk.
   - `unit_registration · Ekta/IH registration_record_review` — sample shows
     real unit, doc type, date and price now.
   - ⚠ `property_rels` approve sets links **ACTIVE**, which makes those
     contacts targetable for outreach. Sample before approving 1,061 at once.
3. **WhatsApp**: set the building on the 5 tenant/community groups (dropdown
   is there now) → unblocks the 565-phone roster enrichment.
4. **YouTube Studio (3 min)**: channel title trailing space; try claiming
   @RealDealHousing (current: @realdealhousing01).
5. **A-2803 lease expires ~Aug 26** — decide if Padmini contacts the owner.
6. Optional: confirm the Ekta penthouse ₹16 Cr ask for Saturday's copy.

## Where to go next (Claude, pick with operator)

- **Zapkey (3,058 pending_review)** — deliberately excluded from the cohort
  engine: these need unit/tower **linking logic**, not a human yes/no.
  Flipping them to 'linked' without resolving building_unit_id would record a
  link that does not exist. Write the linker (trust unit number, not
  floor/tower — see zapkey memory) and the 66 `zapkey_link_confirm` rows
  become the review surface.
- **Brokers are not in the DB at all** — 0 contacts typed broker, but disk has
  ~16k rows across 10 sheets (largest: `All over Brokers.csv` 7,077,
  `Brokers List ENTIRE - Brokers.csv` 5,793, `BROKERS ONLY.csv` 3,147). Copies
  staged at `~/Desktop/RDH Broker Sheets`. 10 broker WhatsApp groups are
  already classified and ingesting — matching those senders to a real broker
  contact table is the obvious next intelligence layer.
- **WhatsApp §9B** (docs/BEEPER-ASSISTANT-PLAN.md): offer-vs-requirement split,
  buyer_requirements extraction, roster enrichment once buildings are set.
- **Two more Shorts** for the next free slots — Export library has unused cuts
  (IH C-804, Kalpataru C-311, IH B-2101 4BHK).
- **Attribution funnel dashboard** once PostHog has production traffic.

## Dead scaffolding — deliberately left alone

~450 pending rows across `wix_*`, `launch_n8n_*`, `fable_*`,
`launch_readiness_checks` etc. all froze between 2026-06-09 and 06-12, i.e.
before the pivot off Wix to the Next.js build. Operator's call was to leave
them; the cohort engine simply does not include those tables, so they no
longer compete for attention. Note this still inflates the *portfolio home*
counters, which read `launch_readiness_checks` directly.

## Gotchas

- `getGlobalReviewQueue()` (data.ts) only reads launch_readiness_checks +
  rera_project_profiles, and those rows carry no `reviewItemId` — so the
  building workspace Reviews tab renders every item as "(preview)" even though
  its write path is real. Point it at real queues or leave /cockpit/review as
  the approval surface.
- IGR eRegistration Index II comes back in ENGLISH ("Doc No. :", "Leave and
  License Months:NN") — parse_igr_index2_ekta.py has both branches.
- workers/_lib.q() splits psql output on `|` — sanitize EVERY selected text
  column. review_cohorts.py sidesteps this entirely by emitting one JSON blob.
- Remotion Root.tsx needs calculateMetadata — durationInFrames from
  defaultProps silently crops end cards on longer scene lists.
- YouTube channel branding updates: strip the `image` block before
  channels.update; title changes are gated (trailing space stuck).
- Cockpit auth cookie is `cockpit_auth` (value = COCKPIT_AUTH_TOKEN) — needed
  to curl any /cockpit route.
