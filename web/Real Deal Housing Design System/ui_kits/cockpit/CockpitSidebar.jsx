import React from "react";
import { Dot } from "../../components/core/Dot.jsx";
import { Pill } from "../../components/core/Pill.jsx";
import { Mono } from "../../components/core/Mono.jsx";

export const CP_BUILDINGS = [
  { slug: "dlf-westpark", name: "DLF Westpark", location: "Andheri West", mode: "launch", launchInDays: 58, stats: { owners: 4, tenants: 0, leads: 12, warm: 3, listings: 2, openReviews: 5, blockers: 3 }, seoRank: "n/a" },
  { slug: "imperial-heights", name: "Imperial Heights", location: "Goregaon West", mode: "active", stats: { owners: 212, tenants: 64, leads: 31, warm: 9, listings: 6, openReviews: 2, blockers: 0 }, seoRank: "#3" },
  { slug: "kalpataru-radiance", name: "Kalpataru Radiance", location: "Goregaon West", mode: "active", stats: { owners: 148, tenants: 41, leads: 18, warm: 4, listings: 4, openReviews: 0, blockers: 0 }, seoRank: "#5" },
  { slug: "ekta-tripolis", name: "Ekta Tripolis", location: "Goregaon West", mode: "prospecting", stats: { owners: 96, tenants: 22, leads: 7, warm: 1, listings: 2, openReviews: 1, blockers: 0 }, seoRank: "#8" },
];

const MODE_TONE = { launch: "blocked", active: "ready", prospecting: "review", post_launch: "neutral" };

export function CockpitSidebar({ screen, go }) {
  const item = (key, label) => (
    <a href="#" onClick={(e) => { e.preventDefault(); go(key); }}
      style={{
        display: "flex", alignItems: "center", gap: 8, borderRadius: 8, padding: "8px 12px",
        fontSize: 14, fontWeight: 500, textDecoration: "none", marginTop: 2,
        background: screen === key ? "#fff" : "transparent",
        boxShadow: screen === key ? "0 0 0 1px var(--mist-deep)" : "none",
        color: screen === key ? "var(--teal)" : "var(--ink-65)",
      }}>
      {label}
    </a>
  );
  return (
    <aside style={{ display: "flex", width: 240, flexShrink: 0, flexDirection: "column", borderRight: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.3)", fontFamily: "var(--font-sans)", height: "100%", boxSizing: "border-box" }}>
      <div style={{ display: "flex", height: 56, alignItems: "center", gap: 8, borderBottom: "1px solid var(--mist-deep)", padding: "0 20px" }}>
        <span style={{ display: "flex", height: 24, width: 24, alignItems: "center", justifyContent: "center", borderRadius: 6, background: "var(--teal)", color: "#fff", fontSize: 10, fontWeight: 700 }}>RDH</span>
        <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--teal)" }}>Operations cockpit</span>
      </div>
      <nav style={{ flex: 1, overflowY: "auto", padding: "16px 12px" }}>
        {item("portfolio", "Portfolio")}
        {item("contacts", "Contacts")}
        {item("audiences", "Audiences")}
        {item("outreach", "Outreach")}
        {item("media", "Media")}
        <div style={{ margin: "20px 0 8px", padding: "0 12px", fontFamily: "var(--font-mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--ink-40)" }}>
          Buildings · {CP_BUILDINGS.length}
        </div>
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 2 }}>
          {CP_BUILDINGS.map((b) => (
            <li key={b.slug}>
              <a href="#" onClick={(e) => e.preventDefault()}
                style={{ display: "flex", alignItems: "center", gap: 10, borderRadius: 8, padding: "8px 12px", fontSize: 14, color: "var(--ink-65)", textDecoration: "none" }}>
                <Dot tone={MODE_TONE[b.mode]} />
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.name}</span>
                {b.stats.blockers > 0 && <Mono size={10} style={{ color: "var(--warm)" }}>{b.stats.blockers}</Mono>}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <div style={{ borderTop: "1px solid var(--mist-deep)", padding: 12, fontSize: 14 }}>
        <a href="#" onClick={(e) => e.preventDefault()} style={{ display: "flex", alignItems: "center", gap: 8, borderRadius: 8, padding: "8px 12px", color: "var(--ink-55)", textDecoration: "none" }}>↗ Marketing site</a>
        <a href="#" onClick={(e) => e.preventDefault()} style={{ display: "flex", alignItems: "center", gap: 8, borderRadius: 8, padding: "8px 12px", color: "var(--ink-55)", textDecoration: "none" }}>⏻ Sign out</a>
      </div>
    </aside>
  );
}

export function CockpitTopbar() {
  return (
    <header style={{ display: "flex", height: 56, flexShrink: 0, alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--mist-deep)", padding: "0 24px", fontFamily: "var(--font-sans)", boxSizing: "border-box" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14, color: "var(--ink-50)" }}>
        <Mono size={12}>⌘K</Mono>
        <span>Search buildings, leads, reviews…</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 12, color: "var(--ink-50)" }}>DLF Westpark launch</span>
        <Pill tone="blocked">3 blockers · go-live locked</Pill>
      </div>
    </header>
  );
}
