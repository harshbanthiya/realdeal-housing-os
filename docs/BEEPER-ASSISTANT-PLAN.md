# Beeper WhatsApp Ingest → AI Co-worker Plan

> Persistent context. If a session dies mid-build, resume from "Build state" at the
> bottom. Companion to ROADMAP.md §10. Created 2026-07-21.

## 0. Decisions locked

- **Ingest: Beeper Desktop API** (localhost:23373, read-only OAuth token in
  `secrets/beeper_access_token`, re-mint via `scripts/beeper_get_token.py`).
  Salesperson's WhatsApp (+91 82912 93889) linked as Beeper companion device.
  Beeper Cloud buffers while Mac sleeps; worker catches up on wake.
- **Send: NEVER via API.** Cockpit renders `wa.me/<E164>?text=<urlencoded>` deep
  links; human taps send in official WhatsApp app/web. Zero ban surface.
- **MCP**: `beeper` MCP server registered in Claude user config for interactive work.
- Privacy: chats transit Beeper (Automattic) cloud — operator accepted.
  Personal chats excluded via per-chat `ingest_enabled=false` (operator toggles
  in cockpit; default ON, personal ones flipped off in first review).

## 1. Verified API shape (2026-07-21, Beeper 4.2.985)

- `GET /v1/chats/search?limit=N` → chats: id (`!x:beeper.local`), title, type
  single|group, network, unreadCount, lastActivity, participants{items:
  id, phoneNumber (+E164), fullName (= HER phone-book saved name, or raw number
  if unsaved), isAdmin, isSelf}, total. Radiance Ladies Group = 565 members.
- `GET /v1/chats/{urlencoded-id}/messages?limit=N` → id, chatID, senderID,
  senderName, timestamp, sortKey (cursor!), type TEXT|FILE|VIDEO|…, text (HTML),
  attachments[{srcURL mxc://, mimeType, fileName, fileSize, isVoiceNote}],
  isSender, isDeleted, mentions.
- **Group gotcha**: group senderID = `@whatsapp_lid-<n>:beeper.local` (WhatsApp
  privacy LID, not a phone). Resolve LID→phone via that chat's participants
  list. Fallback: senderName is often the raw "+91…" string. Store all three.
- 1:1 chats: participant id = `@whatsapp_<phone>:beeper.local` — phone direct.
- `/v1/messages/search?limit=50` → 400 (limit cap); use per-chat pagination.
- Media download: `POST /v1/assets/download` with srcURL.
- Bonus endpoints: `POST /v1/chats/{id}/reminders` (native Beeper reminder —
  a safe non-WhatsApp write), contacts per account.

## 2. Schema (migration `schemas/066_beeper_whatsapp_ingest.sql`)

Existing tables reused: `interactions` (0 rows — extend, don't duplicate),
`tasks` (0 rows — has due_at/task_type/follow_up_at already), `contacts` (3,239;
phone_primary/whatsapp_number/phone_secondary), `contact_methods` (4,475
normalized_value). Convention: review-gate via status columns + guarded scripts.

New:
- `wa_chats`: beeper_chat_id PK, title, chat_type, kind
  (unclassified|client|broker|broker_group|tenant_group|community_ours|
  personal|other), ingest_enabled bool default true, contact_id FK nullable
  (1:1 chats → canonical contact), building_id FK nullable (tenant groups →
  building), member_count, last_activity, notes.
- `wa_chat_members`: (beeper_chat_id, lid) PK, phone, display_name, is_admin,
  contact_id FK nullable (resolved match), last_seen_at.
- `wa_ingest_state`: beeper_chat_id PK, last_sort_key, last_run_at, msg_count.
- `wa_number_queue` (confirm queue): phone PK, first_seen_chat, wa_name
  (her saved name / pushname), seen_count, proposed_contact_id (fuzzy match
  candidate), status pending|attached|created|ignored, reviewed_at.
- `interactions` ADD COLUMNS: beeper_message_id text UNIQUE, beeper_chat_id,
  sender_phone, sender_lid, sender_display_name, is_group_msg bool,
  message_type, body_text (HTML stripped), body_html, media jsonb,
  rdh_code text (parsed ⌂-code), source text default 'beeper'.
- Views: `vw_wa_contact_timeline` (interactions+notes per contact, newest
  first), `vw_wa_today` (tasks due today/overdue + gone-quiet clients (client
  chats idle >7d) + today's activity counts), `vw_wa_confirm_queue`,
  `vw_wa_group_directory` (groups + kind + match coverage %),
  `vw_wa_roster_matches` (group members ↔ contacts by phone; the Radiance-565
  enrichment surface).

## 3. Worker `workers/beeper_ingest.py`

Cursor sweep: list chats → for each ingest_enabled chat, page messages since
last_sort_key → upsert interactions (ON CONFLICT beeper_message_id DO NOTHING)
→ resolve sender (1:1 = chat contact; group = LID→roster→phone) → refresh
wa_chat_members → match phone vs contacts (phone_primary/whatsapp_number/
phone_secondary/contact_methods.normalized_value, last-10-digit match) →
unmatched phones upsert wa_number_queue (seen_count++).
HTML→text strip. Media: store metadata only (download deferred).
Runs in existing roster (workers/run_all.py) + on-demand.

### ⌂-codes (outbound uniformity → machine-readable inbound)
Cockpit prefixes drafted messages with a tail sigil line; worker parses ANY
message (esp. isSender=true and the "Note to self" chat) matching
`⌂<letter> …`:
- `⌂V <when> <where>` → viewing: creates tasks row (task_type='viewing', due_at
  parsed) linked to the chat's contact.
- `⌂F <when>` → follow-up task.
- `⌂N <text>` → note onto that contact's timeline (summary interaction).
- `⌂N @<name> <text>` in Note-to-self → fuzzy-match name → note on that contact.
- `⌂L <listing-slug>` → records listing-shared event (ties to listing_content).
Unparsed codes land rdh_code raw for review. Date parsing: dd/mm hh[:mm]
[am|pm] + 'today/tomorrow/mon..sun'; on failure create task with due_at NULL +
title carrying raw text (never lose the intent).
Her phone = command channel: she texts her own WhatsApp (Message Yourself) —
ingested as Note-to-self chat, codes work from her phone anywhere.

### Event triggers (timestamp-driven)
- tasks.due_at powers vw_wa_today (overdue + due-today buckets).
- launchd roster already runs every 30 min → beeper_ingest each cycle; morning
  cycle (07:30) emails operator a digest (Resend, existing plumbing) — LATER.
- Optional native pings: POST /v1/chats/{id}/reminders so a reminder fires in
  Beeper app itself — safe write, no WhatsApp message. LATER.

## 4. Guarded writer `scripts/update_wa_item.py`

Dry-run default, --apply to write. Ops: `classify-chat` (kind, ingest_enabled,
building_id), `confirm-number` (attach phone→contact_id | create contact from
wa_name | ignore), `complete-task`, `link-chat-contact`. Labeled key: value
output (cockpit actions.ts parses this).

## 5. Cockpit (web/, read-only pool + server actions → guarded script)

- `web/src/lib/cockpit/whatsapp.ts` — reads from the views.
- `/cockpit/whatsapp` page: tabs Today | Activity | Groups | Confirm numbers.
  - Today: due/overdue tasks (✓ complete), gone-quiet clients w/ wa.me nudge link.
  - Activity: latest interactions (client+broker chats first, group noise
    collapsible), each row links to contact.
  - Groups: directory + kind selector + ingest toggle + match coverage.
  - Confirm: wa_number_queue with proposed matches → attach/create/ignore.
- Contact detail page: WhatsApp timeline panel (vw_wa_contact_timeline) +
  "Draft WhatsApp" button → wa.me link with ⌂-code templates (viewing/follow-up/
  listing share) — THE hybrid loop: cockpit drafts w/ code → official WhatsApp
  sends → Beeper ingests → code parsed → task/timeline updates itself.
- Nav: add WhatsApp entry to cockpit layout.

## 6. Contact enrichment catalog (all sources now possible)

| Source | Yield | Mechanism |
|---|---|---|
| Her phone-book names via WA (fullName) | role+building hints: "Ajay yadav EBD Tenant", "Neha C Wing Kalpataru" | name-pattern parse → contact_property_hints (review-gated) |
| Group rosters (wa_chat_members) | 565 phones in Radiance Ladies alone; per-building resident lists | phone↔contacts match view; unmatched → provisional contacts tagged w/ building |
| vCards shared in chats (.vcf attachments) | clean name+phone cards | parse on ingest (LATER) |
| Broker group listing posts | live inventory + broker specialization map | LLM extraction → listing candidates (LATER, §7) |
| Message frequency/recency | engagement scoring, gone-quiet detection | vw already; feeds vw_contact_engagement_score |
| Group membership overlap | who is broker vs tenant vs both; which buildings a broker works | wa_chat_members × kind |
| Zapkey/IGR cross-ref (existing) | owner↔unit truth | existing pipelines |
| ⌂N notes + call logs (manual) | ground truth from her | codes + note form |

## 7. AI co-worker layer (LATER — after ingest is stable)

On existing `workers/_llm_tiers.py` stack, all review-gated:
1. Conversation-burst classifier: buyer_requirement | owner_listing_lead |
   broker_inventory | scheduling | noise (skip ingest_enabled=false, skip
   personal kinds entirely).
2. buyer_requirements table → auto-match against unit registry/IGR prices →
   "line up these flats" panel per client.
3. Broker-group inventory extraction → market_watch-style comps + who-has-what.
4. Owner-lead detection ("want to sell/rent my flat") → listing_content draft.
5. Daily digest (07:30 email): new requirements, leads, due tasks, gone-quiet.
6. Auto-proposed follow-ups from message content ("call me Thursday").
Guard: LLM only ever writes *_review_items / draft rows. Flat-number privacy
rules apply to any outward surface.

## 8. Build state (update as you go)

- [x] Beeper installed, her WA linked, token minted, audit green
      (scripts/beeper_audit.py, scripts/beeper_get_token.py, commits 5e59b07,
      622dd77)
- [x] Migration 066 written + applied
- [x] workers/beeper_ingest.py first sweep DONE: 598 chats (35 groups), 6,483 msgs,
      363 auto-matched to contacts, 358 in confirm queue, 145 roster matches;
      registered in run_all.py roster
- [x] scripts/update_wa_item.py (classify-chat|confirm-number|complete-task)
- [x] web lib + /cockpit/whatsapp (Today|Confirm|Groups|Activity) + contact
      WA-timeline panel + ⌂-draft buttons + sidebar nav (tsc clean)
- [ ] Operator: classify groups, flip personal chats off, burn confirm queue
- [ ] LATER queue: media download, vCard parse, LLM layer (§7), digest email,
      Beeper native reminders, docs/YOUTUBE-WORKFLOW-style ops doc
- [x] 2026-07-21 PM: search (067: FTS 'simple' + pg_trgm over interactions;
      search bar w/ kind/direction/days filters on /cockpit/whatsapp) and
      broker market (068: wa_market_offers regex parser EN+Devanagari,
      workers/wa_offer_parser.py in roster; /cockpit/whatsapp/market —
      our-buildings box IH/Kalpataru/Ekta + rent/sale × BHK boxes; first
      parse: 311 offers, 165 our-building mentions). Commits 6c1d2a0, 700e5da.

## 9. REMAINING WORK (for next session — read §0–§8 above first, state is real)

Everything below is unbuilt. Ordered by value. Shipped so far: migrations
066/067/068 applied; workers beeper_ingest + wa_offer_parser in the 30-min
roster; /cockpit/whatsapp (search/today/confirm/groups) + /market + unit-
registry probable contacts + contact WA timelines all live and pushed.

### A. Operator manual steps (blocking some of B — nag until done)
- [ ] Classify the 35 groups in /cockpit/whatsapp Groups panel (kind selector);
      flip personal chats OFF (purges their stored msgs). Until then everything
      is 'unclassified' and tenant-group→building enrichment can't run.
- [ ] Set building_id on tenant groups (Radiance Ladies=Kalpataru etc.) —
      needs a small building dropdown ADDED to the Groups panel (only kind +
      ingest toggle wired now; update_wa_item.py --building-id already works).
- [ ] Burn the 358-row confirm-number queue (attach/create/ignore).
- [ ] Test one ⌂V / ⌂N from her phone end-to-end (parser is live but UNTESTED
      with real sent messages; also VERIFY her "Message Yourself" chat actually
      ingests — assumed, never observed).

### B. AI/enrichment layer (§7 detail, all review-gated, use workers/_llm_tiers.py)
- [ ] Offer-vs-REQUIREMENT split in wa_market_offers ("Required 2bhk" currently
      pollutes offer boxes). Cheap LLM classify or 'required|want|need' regex tier.
- [ ] buyer_requirements table + extraction from client chats → match against
      building_units/IGR prices → "line up flats" panel on contact page.
- [ ] Owner-lead detection ("selling my flat") → listing_content draft rows.
- [ ] Cross-group dedup of same-flat offers (same phone+bhk+price ≈ dupe).
- [ ] Price normalization (₹1.65 Cr / 55k / 1.2cr → numeric) for sorting/comps.
- [ ] Group-roster enrichment: after operator sets building_id on tenant groups,
      match wa_chat_members phones ↔ contacts per building; unmatched → provisional
      contacts tagged w/ building (Radiance Ladies = 565 phones waiting).
- [ ] Saved-name parsing → contact_property_hints ("Neha C Wing Kalpataru",
      "Ajay yadav EBD Tenant" — her phonebook encodes role+building).
- [ ] Broker specialization map (who posts what where — data already in
      wa_market_offers.sender_phone).

### C. Plumbing / robustness
- [ ] Health check: worker finding if 0 new interactions in 24h (= Beeper
      session dropped; re-link via QR). _lib.finding() exists for this.
- [ ] Media download: attachments store metadata only; wire POST /v1/assets/
      download for images/PDFs → media_assets pipeline. vCard (.vcf) parse.
- [ ] Voice notes → whisper.cpp transcription (video_transcriber pattern).
- [ ] wa_market_offers status actions (seen/archived) — schema has status,
      UI is read-only; add to update_wa_item.py + market page buttons.
- [ ] Morning digest 07:30 email via Resend (new offers, due tasks, gone-quiet,
      our-building mentions).
- [ ] Timeline pagination + media rendering on contact WA timeline (60-row cap now).
- [ ] MAX_PAGES_PER_CHAT=25 backfill cap: big groups still hold older history;
      loop worker runs (cursor resumes) if deeper backfill wanted.

### D. Known gotchas for the next Claude
- readQuery (web) returns rows[] directly, is READ ONLY; all writes via guarded
  scripts + server actions (wa-actions.ts pattern).
- run_psql = docker exec psql, ~100ms/call — BATCH multi-row VALUES always.
- Group senderID is LID; resolve via wa_chat_members (phone may be NULL for
  lid-only members; senderName often the raw +91… then).
- 'simple' FTS config on purpose (Hinglish); don't "fix" to 'english'.
- Beeper API: /v1/chats/search & per-chat /messages paginate via cursor=
  (oldestCursor, newest-first); limit param mostly ignored (~20/page).
- Ekta owner sheet loaded 2026-07-21 (scripts/load_ekta_owner_sheet.py,
  442 units, 345 pending_review owner rels, exports/ekta_owner_outreach_*.csv);
  unit-registry boxes now show ALL unit-linked rels w/ phones+WA (data.ts).
