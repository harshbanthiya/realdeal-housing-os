import React from "react";
import { Card } from "../../components/core/Card.jsx";
import { Pill } from "../../components/core/Pill.jsx";
import { Mono } from "../../components/core/Mono.jsx";
import { PanelTitle } from "../../components/core/PanelTitle.jsx";

const QUEUES = [
  { label: "Merge candidates", approved: 4, pending: 7 },
  { label: "Duplicates", approved: 12, pending: 2 },
  { label: "Property hints", approved: 3, pending: 5 },
  { label: "Inventory matches", approved: 9, pending: 0 },
  { label: "Lead requirements", approved: 1, pending: 3 },
];

const BATCHES = [
  { label: "Imperial Heights unit data", real: true, rows: 214, pending: 7, approved: 41 },
  { label: "Kalpataru Radiance owners", real: true, rows: 148, pending: 4, approved: 96 },
  { label: "Oberoi Esquire data", real: false, rows: 62, pending: 0, approved: 0 },
];

const MERGES = [
  { id: "RVW-2211", a: "Rakesh Sharma · +91 98200 11223", b: "R. Sharma · rakesh.s@gmail.com", building: "Imperial Heights", confidence: "0.92" },
  { id: "RVW-2214", a: "Meena Kapoor · +91 98333 40911", b: "Meena K · +91 98333 40911", building: "Kalpataru Radiance", confidence: "0.88" },
];

function Stage({ n, label, tone, sub }) {
  return (
    <div style={{ borderRadius: 8, border: "1px solid var(--mist-deep)", padding: 12, textAlign: "center" }}>
      <div style={{ fontSize: 22, fontWeight: 600, color: "var(--teal)" }}>{n}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: "var(--ink-65)" }}>{label}</div>
      <div style={{ marginTop: 6 }}><Pill tone={tone}>{sub || "—"}</Pill></div>
    </div>
  );
}

export function CockpitContacts() {
  return (
    <div style={{ padding: "28px 24px", fontFamily: "var(--font-sans)" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: "-0.02em", color: "var(--teal)" }}>Contacts</h1>
        <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--ink-55)" }}>137 cleaned canonical · 17 awaiting review across 2 real import batches</p>
      </div>

      <Card padding={20} style={{ marginBottom: 28 }}>
        <PanelTitle hint="programmatic pipeline · review-gated">Cleanup funnel</PanelTitle>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <Stage n={424} label="Imported rows" tone="neutral" sub="lossless" />
          <Stage n={17} label="In review" tone="review" sub="needs your decision" />
          <Stage n={137} label="Approved" tone="active" sub="ready to merge" />
          <Stage n={137} label="Canonical" tone="ready" sub="cleaned contacts" />
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1.7fr 1fr", gap: 24 }}>
        <div>
          <PanelTitle hint="7 pending">Merge candidates</PanelTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {MERGES.map((m) => (
              <Card key={m.id} padding={16}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <Mono size={11} style={{ color: "var(--warm)" }}>{m.id}</Mono>
                  <Pill tone="review">confidence {m.confidence}</Pill>
                </div>
                <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 12 }}>
                  <div style={{ borderRadius: 8, background: "var(--mist)", padding: "10px 12px", fontSize: 13, color: "rgba(26,26,26,0.8)" }}>{m.a}</div>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-40)" }}>↔</span>
                  <div style={{ borderRadius: 8, background: "var(--mist)", padding: "10px 12px", fontSize: 13, color: "rgba(26,26,26,0.8)" }}>{m.b}</div>
                </div>
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 11, color: "var(--ink-45)" }}>{m.building}</span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button style={{ borderRadius: 9999, border: "1px solid var(--mist-deep)", background: "transparent", padding: "6px 14px", fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600, color: "var(--teal)", cursor: "pointer" }}>Skip</button>
                    <button style={{ borderRadius: 9999, border: "1px solid var(--teal)", background: "var(--teal)", padding: "6px 14px", fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600, color: "#fff", cursor: "pointer" }}>Preview approve</button>
                  </div>
                </div>
              </Card>
            ))}
            <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-40)" }}>
              "Preview approve" runs the guarded script in dry-run (no writes). Applying stays disabled until enabled.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <Card padding={20}>
            <PanelTitle hint="46 items">Review queues</PanelTitle>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
              {QUEUES.map((g, i) => (
                <li key={g.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: i < QUEUES.length - 1 ? "1px solid var(--mist)" : "none", paddingBottom: i < QUEUES.length - 1 ? 10 : 0 }}>
                  <span style={{ fontSize: 14, color: "rgba(26,26,26,0.75)" }}>{g.label}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {g.approved > 0 && <Pill tone="ready">{g.approved} ok</Pill>}
                    <Pill tone={g.pending > 0 ? "review" : "neutral"}>{g.pending} pending</Pill>
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card padding={20}>
            <PanelTitle hint="2 real">Import batches</PanelTitle>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 12 }}>
              {BATCHES.map((b) => (
                <li key={b.label} style={{ borderRadius: 8, border: "1px solid var(--mist-deep)", padding: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13, fontWeight: 500, color: "var(--teal)" }}>{b.label}</span>
                    {b.real ? <Pill tone="active">real</Pill> : <Pill tone="neutral">test</Pill>}
                  </div>
                  <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, textAlign: "center", fontSize: 11 }}>
                    <div><div style={{ fontWeight: 600, color: "var(--teal)" }}>{b.rows}</div><div style={{ color: "var(--ink-40)" }}>rows</div></div>
                    <div><div style={{ fontWeight: 600, color: "var(--amber)" }}>{b.pending}</div><div style={{ color: "var(--ink-40)" }}>pending</div></div>
                    <div><div style={{ fontWeight: 600, color: "var(--teal)" }}>{b.approved}</div><div style={{ color: "var(--ink-40)" }}>approved</div></div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
