# Next-session handoff — written 2026-07-22 (session a58e16f → 76b1967)

## Prompt to paste into Claude

> Read docs/NEXT-SESSION.md and docs/YOUTUBE-WORKFLOW.md. Last session (commits
> a58e16f..76b1967): Ekta Tripolis paid IGR loaded (776 registrations, 67 party
> matches, tenancy Index II parsed — 30/38 end dates, 3 leases in
> vw_tenancy_expiring_soon, A-2803 expires Aug 26); two Shorts scheduled
> (DLF Westpark hKZ6i0_yV9I Thu, Ekta penthouse PgezWBUDUP0 Sat — next free
> slots Tue 7/28, Thu 7/30); YouTube channel SEO pass done via API (full-scope
> token in secrets/youtube_token.json), all site links UTM-tagged
> (utm_campaign=<building-slug>); PostHog snippet shipped in
> web/src/instrumentation-client.ts (EU cloud, inert until key).
> Check the human-steps section below for what the operator finished, then
> pick up from "Where to go next".

## Steps for the human (do these before/with the next session)

1. **PostHog key (2 min, unlocks all attribution)**: sign up free at
   https://eu.posthog.com → create project → copy the `phc_...` key →
   paste into `web/.env.local` (`NEXT_PUBLIC_POSTHOG_KEY=phc_...`) AND into
   Vercel project env vars → redeploy. Until this, YouTube clicks are invisible.
2. **YouTube Studio (3 min)**: fix channel title trailing space
   ("Real Deal Housing " → "Real Deal Housing"); try claiming the cleaner
   handle @RealDealHousing (current: @realdealhousing01).
3. **Watch the two scheduled Shorts** before they auto-publish:
   DLF Thu 7:30pm IST (youtube.com/watch?v=hKZ6i0_yV9I),
   Ekta penthouse Sat 7:30pm IST (youtube.com/watch?v=PgezWBUDUP0).
4. **A-2803 lease expires in ~35 days** (vw_tenancy_expiring_soon) — decide if
   Padmini reaches out to the owner (contact matched in unit registry).
5. Optional: confirm the Ekta penthouse asking price (footage says ₹16 Cr,
   unverified) — if current, we add it to Saturday's title/description.

## Where to go next (Claude, pick with operator)

- **Attribution live-check**: once the PostHog key is in, verify events flow,
  then build the funnel dashboard (youtube → building page → wa.me click).
- **Two more Shorts for Tue 7/28 + Thu 7/30** — Export library has unused
  cuts (IH C-804, Kalpataru C-311, IH B-2101 4BHK); template now supports
  still-image scenes (Ken Burns) and duration follows props (82670aa).
- **Ekta tenancy follow-through**: 8 Devanagari Index II docs have no end
  dates (format omits tenure) — Regular-registration recapture or accept;
  2 tenancy records still unit-unlinked.
- **WhatsApp intelligence §9** (docs/BEEPER-ASSISTANT-PLAN.md): operator group
  classify + LLM layer — was the standing next-up before this session.
- **wa.me prefilled-text attribution** per building in video descriptions
  (operator liked the idea, not yet applied).

## Gotchas rediscovered this session

- IGR eRegistration Index II comes back in ENGLISH ("Doc No. :", "Leave and
  License Months:NN") — parse_igr_index2_ekta.py has both branches.
- workers/_lib.q() splits psql output on `|` — sanitize EVERY selected text
  column, not just body_text.
- Remotion Root.tsx needed calculateMetadata — durationInFrames from
  defaultProps silently cropped end cards on longer scene lists.
- YouTube channel branding updates: strip the `image` block before
  channels.update; title changes are gated (trailing space stuck).
