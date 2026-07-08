# Cockpit UI kit

Recreation of the internal operations cockpit from `Real Deal Housing OS/web/src/app/cockpit/`.

- `index.html` — interactive: sidebar switches Portfolio / Contacts (Audiences, Outreach, Media are intentionally stubbed — not recreated)
- `CockpitSidebar.jsx` — sidebar (building list with mode dots + blocker counts) and topbar (⌘K search, launch pill)
- `CockpitPortfolio.jsx` — launch-readiness strip, building cards with stat rows, Needs review / Agents / Blockers rails
- `CockpitContacts.jsx` — cleanup funnel, merge-candidate queue, review queues, import batches

Sample data mirrors the shapes in `web/src/lib/cockpit/` (values are representative, not real).
