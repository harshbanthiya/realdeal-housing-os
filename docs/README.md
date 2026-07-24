# Real Deal Housing OS — docs map

**Start here: [NORTH-STAR.md](NORTH-STAR.md)** — what we are building, the four
loops everything must serve, and the guardrails. Read it before proposing work.


Human-operated, review-gated real-estate intelligence OS. Local Postgres is the
source of truth (62 migrations, `schemas/001–062`); `web/` is Next.js 16 + Wix
Headless with a cockpit at `/cockpit/*`; Python parsers in `scripts/`, daily
workers in `workers/`. Mumbai market, MahaRERA + IGR are the authoritative registries.

## Where things live — read only what the task needs
| Need | File |
|---|---|
| **Master plan, current state, next TODOs** | `ROADMAP.md` (§2 state, §5 architecture, §14C work order, **§17 resume/todos**) |
| **Website/Wix launch state + blockers/TODOs** | `LAUNCH_CONTEXT.md` |
| **What's been done (history, 1 line/phase + SHAs)** | `PHASE_LOG.md` |
| **YouTube channel: render → schedule → post (human-gated)** | `YOUTUBE-WORKFLOW.md` |
| **How a subsystem works** | `reference/` (schema, contacts/merge, relationships, RERA/IGR, review UIs, growth, media) |

TODOs live in the working docs (ROADMAP §17, LAUNCH_CONTEXT), not here — this file
is the stable map you keep open while editing those. Claude memory (`MEMORY.md`
index) mirrors `PHASE_LOG.md`; prefer whichever is already in context.

## Standing constraints (always apply)
- **realdealhousing.com serves the Next.js site from Vercel** (live 2026-07-14, indexed).
  The premium Wix site's **dashboard/CMS/media is the headless backend** (edit freely);
  its old editor PAGES and the editor-era `Amenities` collection stay untouched. The Wix
  "Test" site is a media archive — never delete it (live site hot-links its files).
- Review-gate everything: pipelines write `*_review_items` + `review_action_log`; no
  canonical writes without human approval. Masked views for PII.
- PAN never in web/Wix/LLM prompts unless the task needs it and it's access-logged.
- No bulk WhatsApp/email to non-consented numbers (DPDP + number-ban risk); Lane A human-send only.
- No portal bulk-scraping, no CAPTCHA bypass; manual/assisted capture with attribution.
- Follow the Gallery White design system in `web/`. Next free migration number: **066**.

## Prompt template (copy, fill the `<…>`)
```
RDH OS. Truth = local Postgres. Read docs/README.md for the map + standing constraints.
For plan/todos see ROADMAP §17; for site see LAUNCH_CONTEXT; for history see PHASE_LOG;
for how a subsystem works see docs/reference/. Read only what this task needs.

Goal: <what I want to achieve>
Context/where to look: <file, phase, or migration — or "find it">
Constraints: obey README standing constraints; <any extra>
Done when: <exit test — e.g. "tsc clean", "worker runs ok", "operator approves">
```
