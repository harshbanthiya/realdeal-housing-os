# YouTube channel workflow — end to end, human in the middle

Channel: https://www.youtube.com/@RealDealHousing · Goal: building-name SEO
(low-competition queries like "Ekta Tripolis", "Imperial Heights Goregaon
West") → traffic to realdealhousing.com → WhatsApp Padmini.

## Pipeline (all review-gated; nothing posts without an operator command)

```
draft row (social_post_drafts)          ← AI (video_scout) or manual insert
   │  operator approves in /cockpit/seo (status → 'approved')
   ▼
scripts/render_short.py --draft-id X --apply     ← renders edit_spec (Remotion
   │  props) via video/ template; sets output_path, status='rendered'.
   │  Pre-made videos (see Export library) skip this: set output_path directly.
   ▼
scripts/upload_youtube.py --draft-id X --publish-at <ISO> --apply
      uploads private; YouTube auto-publishes at the scheduled hour.
      Sets status='posted', posted_url, scheduled_for. Logs to review_action_log.
```

Dry-run is the default for both scripts — omit `--apply` to preview.

## One-time operator setup — DONE 2026-07-17 (token cached in secrets/)
Steps were: Cloud project + YouTube Data API v3 → Desktop OAuth client JSON
→ `secrets/youtube_client_secret.json` → pip install google-api-python-client
google-auth-oauthlib → first `--apply` browser sign-in.
Gotcha hit: "Error 403 access_denied / has not completed verification" =
the signing-in gmail wasn't under OAuth consent screen → **Test users**.
Add the channel gmail there; "Testing" mode is fine permanently.
First post: youtube.com/watch?v=zv223NRCZw8 (Ekta, draft 3375f706).

## Posting schedule (growth cadence)
- **3×/week: Tue / Thu / Sat, published 7:30 PM IST** (= `--publish-at` in UTC:
  `14:00:00Z`). Evening IST is peak for Mumbai property browsing; consistency
  matters more than the exact hour.
- Upload can happen any time — `--publish-at` makes YouTube flip it public on
  schedule. Batch-upload a week on Monday, stay hands-off the rest of the week.
- Quota: one upload = 1600 of 10k daily units → max ~6 uploads/day. Fine.

## Content sources
1. **Remotion Shorts** (this repo, `video/`): per-listing 30s editorial cuts.
   Props shape = `video/props/*.json`. Approved examples: Ekta Tripolis 3BHK,
   Imperial Heights 3.5BHK (2026-07-17).
2. **Export library** (`/Volumes/RDH 5TB/RDH DATA 2024/RDH/Export`, ~39 files):
   pre-edited videos (e.g. "IH A 2105 YT Final HQ.mov", Ekta reels/penthouse).
   Register: INSERT social_post_drafts with title/description/tags,
   status='approved', output_path=absolute path → straight to upload step.
   ⚠ Filenames leak flat numbers ("IH A 2105") — titles/descriptions must NOT
   (configuration only, e.g. "3.5 BHK"); render_short.py and the Remotion
   template both enforce this for shorts, but Export uploads rely on the
   copy check below.

## Copy rules (per /copywriting pass, 2026-07-17)
- **Title**: building name first (it IS the keyword), then specifics:
  "Inside Ekta Tripolis, Goregaon West — a vacant 3 BHK at ₹4.10 Cr"
- **Description**: hook line naming building + area → price line →
  wa.me/918291293889 (Padmini) → realdealhousing.com → socials →
  **music credit (required by the No-Copyright licences: Declan DP, Hotham,
  etc.)** → hashtags (#BuildingName #GoregaonWest #MumbaiRealEstate).
- Never a flat number, never brochure language. "Specific facts. Real
  footage." is the brand line — copy must be able to survive it.

## Weekly operator loop (~20 min, Monday)
1. `/cockpit/seo` — approve/edit the week's 3 drafts (copy + edit_spec).
2. `python3 scripts/render_short.py --draft-id <id> --apply` per short;
   watch each rendered mp4 before upload. (Export files: skim once.)
3. `python3 scripts/upload_youtube.py --draft-id <id> --apply \
      --publish-at 2026-07-21T14:00:00Z` (Tue), `…-23…` (Thu), `…-25…` (Sat).
4. Done. Check posted_url rows next Monday; note view counts in decision_notes
   if anything over/under-performs (feeds video_scout's learning loop).

## Status legend (social_post_drafts)
draft → approved (operator, /cockpit/seo) → rendered (render_short.py)
→ posted (upload_youtube.py; posted_url + scheduled_for set).
