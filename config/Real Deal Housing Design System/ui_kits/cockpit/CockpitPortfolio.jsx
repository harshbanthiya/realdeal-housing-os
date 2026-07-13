import React from "react";
import { Card } from "../../components/core/Card.jsx";
import { Pill } from "../../components/core/Pill.jsx";
import { Dot } from "../../components/core/Dot.jsx";
import { Mono } from "../../components/core/Mono.jsx";
import { PanelTitle } from "../../components/core/PanelTitle.jsx";
import { CP_BUILDINGS } from "./CockpitSidebar.jsx";

const MODE_LABEL = { launch: "Launch", active: "Active", prospecting: "Prospecting", post_launch: "Post-launch" };
const MODE_TONE = { launch: "blocked", active: "ready", prospecting: "review", post_launch: "neutral" };

const STREAMS = [
  { label: "Contacts & permissions", tone: "ready", state: "ready", passed: 6, total: 6 },
  { label: "Campaign copy", tone: "review", state: "in review", passed: 3, total: 5 },
  { label: "Wix landing build", tone: "active", state: "building", passed: 4, total: 9 },
  { label: "Tracking & consent", tone: "blocked", state: "blocked", passed: 0, total: 3 },
];

const REVIEWS = [
  { title: "Merge candidate — R. Sharma ↔ Rakesh S.", building: "Imperial Heights", domain: "contacts", age: "2h", tone: "review" },
  { title: "RERA snapshot parse — Tower 6", building: "DLF Westpark", domain: "facts", age: "5h", tone: "blocked" },
  { title: "Unit audit rows 41–58", building: "Kalpataru Radiance", domain: "inventory", age: "1d", tone: "review" },
];

const AGENTS = [
  { action: "Normalized 214 contact rows", agent: "normalize_contact_file", building: "Ekta Tripolis", status: "ready" },
  { action: "Drafted drip-1 email variant B", agent: "content_draft", building: "DLF Westpark", status: "active" },
  { action: "Profiled Archive_2 workbook", agent: "profile_archive", building: "Imperial Heights", status: "neutral" },
];

const BLOCKERS = [
  { id: "BLK-071", statement: "Consent evidence missing for 2 contact segments", building: "DLF Westpark", openFor: "3d" },
  { id: "BLK-074", statement: "RERA registration number unverified", building: "DLF Westpark", openFor: "6d" },
];

function Stat({ n, label, sub, tone = "neutral" }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 18, fontWeight: 600, color: tone === "review" ? "var(--amber)" : "var(--teal)" }}>{n}</div>
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--ink-40)" }}>{label}</div>
      {sub && <div style={{ fontSize: 10, color: "rgba(31,61,77,0.6)" }}>{sub}</div>}
    </div>
  );
}

export function CockpitPortfolio() {
  return (
    <div style={{ padding: "28px 24px", fontFamily: "var(--font-sans)" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: "-0.02em", color: "var(--teal)" }}>Portfolio</h1>
        <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--ink-55)" }}>{CP_BUILDINGS.length} buildings · 1 in launch · {REVIEWS.length} items awaiting review</p>
      </div>

      <Card padding={20} style={{ marginBottom: 28 }}>
        <PanelTitle hint="DLF Westpark · T-58d">Launch readiness</PanelTitle>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {STREAMS.map((s) => (
            <div key={s.label} style={{ borderRadius: 8, border: "1px solid var(--mist-deep)", padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "var(--ink-65)" }}>{s.label}</span>
                <Dot tone={s.tone} />
              </div>
              <div style={{ marginTop: 8, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Pill tone={s.tone}>{s.state}</Pill>
                <span style={{ fontSize: 10, color: "var(--ink-40)" }}>{s.passed}/{s.total}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr", gap: 24 }}>
        <div>
          <PanelTitle hint="click to open workspace">Buildings</PanelTitle>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {CP_BUILDINGS.map((b) => (
              <Card key={b.slug} padding={20} style={{ height: "100%", boxSizing: "border-box", cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "var(--teal)" }}>{b.name}</div>
                    <div style={{ marginTop: 2, fontSize: 12, color: "var(--ink-50)" }}>{b.location}</div>
                  </div>
                  <Pill tone={MODE_TONE[b.mode]}>{MODE_LABEL[b.mode]}</Pill>
                </div>
                {b.launchInDays && <div style={{ marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--warm)" }}>launch in {b.launchInDays}d</div>}
                <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, borderTop: "1px solid var(--mist)", paddingTop: 12 }}>
                  <Stat n={b.stats.owners + b.stats.tenants} label="people" />
                  <Stat n={b.stats.leads} label="leads" sub={`${b.stats.warm} warm`} />
                  <Stat n={b.stats.listings} label="listings" />
                  <Stat n={b.stats.openReviews} label="reviews" tone={b.stats.openReviews > 0 ? "review" : "neutral"} />
                </div>
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <Mono size={11}>SEO {b.seoRank}</Mono>
                  {b.stats.blockers > 0 ? <Pill tone="blocked">{b.stats.blockers} blockers</Pill> : <Pill tone="ready">clear</Pill>}
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <Card padding={20}>
            <PanelTitle hint={`${REVIEWS.length}`}>Needs review</PanelTitle>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 12 }}>
              {REVIEWS.map((r, i) => (
                <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <Dot tone={r.tone} style={{ marginTop: 4 }} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 14, color: "rgba(26,26,26,0.8)" }}>{r.title}</div>
                    <div style={{ marginTop: 2, fontSize: 11, color: "var(--ink-45)" }}>{r.building} · <Mono size={11}>{r.domain}</Mono> · {r.age}</div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card padding={20}>
            <PanelTitle hint="last 24h">Agents</PanelTitle>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 12 }}>
              {AGENTS.map((a, i) => (
                <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <Dot tone={a.status} style={{ marginTop: 4 }} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 14, color: "rgba(26,26,26,0.8)" }}>{a.action}</div>
                    <div style={{ marginTop: 2, fontSize: 11, color: "var(--ink-45)" }}><Mono size={11}>{a.agent}</Mono> · {a.building}</div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card padding={20}>
            <PanelTitle hint={`${BLOCKERS.length} open`}>Blockers</PanelTitle>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 12 }}>
              {BLOCKERS.map((b) => (
                <li key={b.id} style={{ borderRadius: 8, border: "1px solid var(--mist-deep)", padding: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Mono size={11} style={{ color: "var(--warm)" }}>{b.id}</Mono>
                    <span style={{ fontSize: 11, color: "var(--ink-45)" }}>open {b.openFor}</span>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 14, color: "rgba(26,26,26,0.8)" }}>{b.statement}</div>
                  <div style={{ marginTop: 2, fontSize: 11, color: "var(--ink-45)" }}>{b.building}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
