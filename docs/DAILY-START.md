# DAILY START — the prompt to paste when you open Claude

Copy the block in §1 verbatim, then add one line saying what today is about.
It works whether today is "continue what we built" or "here's a new problem".

---

## 1. The prompt (copy this)

```
Read docs/NORTH-STAR.md, then run `python3 scripts/daily_brief.py` and read the
output. That is the real state — trust it over anything a doc or your memory
says. Then read docs/NEXT-SESSION.md for detail on where the last session stopped.

Before proposing anything, tell me in 5 lines:
  1. which of the four loops today's work serves (or that it's a §7 fire)
  2. what the brief says is currently blocking that loop
  3. what you propose to do, smallest version first
  4. how we'll know it worked (the number, not a feeling)
  5. anything you think I'm wrong about

Rules: Postgres is the truth; writes go through guarded dry-run-first scripts;
query drive_files instead of crawling the drive; leave one runnable check behind;
never widen scope to look productive; say plainly what's blocked rather than
working around it silently.

Today: <ONE LINE — see §2 for how to phrase it>
```

## 2. How to phrase the "Today:" line

The rest of the prompt is identical every day. Only this line changes, and its
shape tells Claude how to behave.

### A. Continuing / extending what exists
> Today: continue the review burndown — start with the media cohorts so Shorts
> get unblocked.

> Today: extend contact_reconcile to also read the broker sheets, and get the
> review queue converging.

Claude should: pick up existing machinery, not rebuild it; check the relevant
doc section first; make the smallest change that moves the metric.

### B. A new daily requirement / business fire
> Today: I need every broker we know saved into the sales phone and invited to
> the Community. Fire — handle it properly, then back to the loops.

Claude should: apply NORTH-STAR §7 — smallest thing that works, usually a
script in `scripts/`; write down what was learned; only build a worker if this
is the second occurrence. **It must not turn a fire into architecture.**

### C. Brainstorming / direction
> Today: brainstorm how we get Loop 3 conversion up. No code yet — argue it out
> with me first.

Claude should: not write code; ground every claim in the brief's numbers; say
what it would measure; flag where the premise is shaky.

### D. Something is broken
> Today: the 30-min loop hasn't run since yesterday — find out why.

Claude should: check `worker_runs` and `~/Library/Logs/rdh-media-enrichment.log`
first; reproduce before fixing; leave a check behind so it's caught next time.

## 3. When to end the day

Ask for this before you stop:

```
Wrap up: update docs/NEXT-SESSION.md with what changed and what's blocked,
commit with a message that explains WHY, and tell me the one thing you'd do
first next session.
```

## 4. What the brief covers (so you can spot a stale answer)

`scripts/daily_brief.py` reads live from Postgres:

- **Review backlog** per queue — the throttle on everything
- **Contact reconciliation** — is every drive contact accounted for
- **Content shelf** — Shorts and blog drafts waiting for approval
- **Scheduled/posted** — what goes out next
- **Worker health** — last run and summary per worker
- **Open findings** — `action` severity first
- **Building coverage** — drive files, units, registrations, reviewed media
- **Known blockers** — the short list that needs a human

If Claude tells you something that contradicts the brief, the brief wins.

## 5. Standing context worth repeating occasionally

Claude re-reads NORTH-STAR each session, but these are the ones most often
worth restating because they change how work gets scoped:

- The machine is an **8GB M1 Air**. Anything needing a big local model is out.
  One resident `qwen3:4b` via Ollama, Gemini free tier as escalation.
- **Four buildings, done properly** beats broad coverage. Depth first.
- The **human is the quality gate**, not a bottleneck to engineer around.
- **Nothing outward-facing ships without review** — no auto-post, no auto-send.
