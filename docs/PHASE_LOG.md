# Phase Log — achieved history

Terse, one line per phase. Full prose for any phase is in git history (the old
`docs/PHASE_*.md` files, removed 2026-07-13). Newest work is at the bottom.
For current state + what's next, read `ROADMAP.md` §2 + §17, not this file.

Convention throughout: **review-gated** — pipelines write to `*_review_items`
staging + `review_action_log`; nothing hits canonical without human approval.
Masked views for PII. `schemas/NNN` = migration number.

## Phase 3–4 — schema + first canonical contact merges
- **3.2** Schema recommendations (source-aware design baseline).
- **4** First real canonical contact merge (a651f82).
- **4.1** Canonical review dashboard: masked NocoDB views, migration 007 (682f469).
- **4.2** Second real canonical merge.

## Phase 5 — property relationship pipeline
- **5.1** Relationship schema: building/unit/contact, migration 008.
- **5.3–5.7** Real owner source dry-run → Imperial unit audit import → owner/unit
  canonical-contact plan → review/merge prep → first owner/unit canonical merge.
- **5.8** First review-gated owner/unit relationship candidate (Imperial Heights).
- **5.9** Approved 5.8 → first active owner relationship.
- **5.10** Owner/building/unit masked dashboard, migration 009.
- **5.11** Second owner/unit canonical + second relationship candidate.
- **5.12** Approved 5.11 → two active owner relationships.
- **5.13 / Milestone 2B** Data-quality dashboard, migration 010; 50 safe / 6 dup-risk candidates.
- **5.13A** NocoDB human dashboard: SSRF fix + migration 011 + runbook.

## Phase 6 — RERA / IGR / content / unit registration
- **6.0** Growth/SEO/lead foundation, migration 012 (no publishing yet).
- **6.1** First real SEO plan (Imperial Heights anchor 0e72db71).
- **6.2** Wix CMS content-review prep, migration 013.
- **6.3** Content quality + AI planning, migration 014.
- **6.4** Local content draft workspace, migration 015 (internal-only).
- **6.5** Source-gap resolution workflow, migration 016 (17 gaps → tasks).
- **6.6** Internal evidence acceptance, migration 017 (3 building_alias evidences).
- **6.7** Building dedupe planning: IH duplicate anchor found (0e72db71 vs f05bbd01), no merge.
- **6.8** MahaRERA verification foundation, migration 019 (schema + fake workflow only).
- **6.9** Manual RERA Imperial Heights: real rows from operator PDF (P51800003270, Wing C/D).
- **6.10** Playwright RERA fetch feasibility: async SPA needs networkidle wait.
- **6.11** RERA headed-capture gates: CAPTCHA / external-warning stop the run, no bypass.
- **6.12** RERA post-CAPTCHA capture SUCCEEDED (human solved CAPTCHA, full detail captured).
- **6.13** RERA snapshot parser, migration 020 (review-gated, no canonical writes).
- **6.14** RERA parser review; gotcha: boolean::text is `true`/`false` not `t`/`f`.
- **6.15+6.16** Per-unit registration foundation + ownership/tenancy timelines,
  migrations 047+048 (31ed03c). IH: 213 expected / 52 enumerated / 161 to-account.
- **6.17** Imperial Heights structure from RERA PDF; IGR village = Borivali NOT Andheri.
- **6.18** First end-to-end per-unit flow (real CTS 260/5A), migration 049.
- **6.19** IGR list parser: 70 regs on CTS 260/5A → 12 Wing A-Ora staged.
- **6.20** IGR Index II PDF parser adds PRICE layer; pdftotext Devanagari scramble fixed.
- **6.21** Consolidated onto real "Kalpataru Radiance" (f63d75ab), migration 050; rich Unit Registry UI.
- **6.22** IGR .xls bulk parser (PRIMARY loader): staged 1,627 Kalpataru registrations.
- **6.23** Kalpataru building merge: 3 variants → 1 canonical (74d36fa).
- **6.24** B-Wing tenancy Index II queue: 21 L&L shortlist.
- **6.25** PAN KYC enrichment MVP, migration 052; 36 party PANs, format-only.
- **6.26** Contact↔unit name match: 55 contacts linked via registration party names, 33 pending.
- **6.31** Master directory cross-ref + Truecaller enrichment workflow (8d186d1).

## Phase 7 — DLF Westpark launch → website architecture pivot
DLF launch command center; most 7.x planning docs are **superseded by the
website-architecture pivot** (Next.js `web/` + Wix Headless, see ROADMAP §5).
- **7.0** DLF launch command center, migration 021 (name guard: "DLF Westend" internal).
- **7.1** Launch funnel workspace, migration 022 (all draft/pending).
- **7.2** DLF contact segmentation + permission review.
- **7.3–7.5** Lead intake/attribution plan → n8n workflow blueprint → DLF operator cockpit.
- **7.6** Launch blocker triage; "DLF Westpark" name confirmed (663924e).
- **7.7** Campaign copy + consent-language review (6ec9324).
- **7.8** Consent/suppression/privacy readiness, migration 029 (consent_ready never passed).
- **7.9** Contact permission evidence: **0 channel_permissions allowed** → all outreach safe_blocked.
- **7.10** Controlled test lead intake.
- **7.11–7.13** DLF n8n build package → review → manual import verification (inactive workflows).
- **7.14** DLF Wix landing + lead-form build package.
- **7.15** Wix UX/SEO/integration masterplan.
- **7.16** Fable UI/UX handoff package for DLF Westpark.
- **7.17** Fable "Gallery White" + Gemini output review, migration 037 (not ready for build).
- **7.18** Gallery White APPROVED design direction, ready_for_wix_design_build=true (f38367a).
- **7.19** Wix staging/preview-site plan, migration 038.
- **7.20** Manual Wix staging build tracking, migration 039 (no-site path, API deferred).
- **7.21** Wix API permission → capability map, migration 040 (no key yet).
- **7.22** Manual Wix staging site recorded, ready_for_staging_qa=true.
- **7.23–7.25** Wix AI build execution plan → route review → Git/CLI availability check.
- **7.26** Wix Test site: 7 native CMS collections seeded + editor handoff. **realdealhousing.com OFF-LIMITS.**
- **PIVOT** Off Wix editor → Next.js (`web/`) + Wix Headless + local Postgres as truth;
  Gallery White DLF landing built (98fb41b).

## Phase 8 — outreach + multi-user
- **8.0** WhatsApp assisted outreach (Lane A human-in-loop) + `/cockpit/outreach`, migration 045 (8c8b55b).
- **8.1** Contact groups + outreach panel, migration 046 (9dbe0a5).
- **8.3** Cockpit shared-password login gate + multi-user access (0812010).

## 2026-07 — always-on layer + transaction index (post-phase)
- **Website live** on Vercel (7c6298b): CMS adapter → real Test-site Wix schemas,
  SEO plumbing, 5 heroes on Wix CDN. robots=noindex pending domain decision. See LAUNCH_CONTEXT.
- **Worker layer** BUILT + live (a5ece2f): migration 061; 5 deterministic daily
  workers (review_inbox, data_quality, listing_readiness, seo_freshness, market_watch)
  + `/cockpit/inbox`. launchd 07:30 + start.sh fallback. First run: 5,981 pending
  review items, `inventory` table empty. See ROADMAP §15A.
- **Contact consolidation** (098041a): 1,310 canonical contacts, 1,240 attached to 6 buildings.
- **Kalpataru MyGate import**: 1,475 contacts / 1,543 pending_review rels; idempotent.
- **Tower D MyGate load**: 107 screenshots + WhatsApp xlsx → 518 pending rels; 26 wing-D units created.
- **Zapkey transaction index** (migration 062): apiv2.zapkey.com/listing (Cloudflare,
  browser-only); covers 63 flats IGR has no doc for. Trust unit number, not floor/tower.
