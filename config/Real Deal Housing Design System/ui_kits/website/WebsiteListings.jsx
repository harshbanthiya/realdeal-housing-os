import React, { useState } from "react";
import { Reveal } from "../../components/marketing/Reveal.jsx";
import { ListingCard } from "../../components/cards/ListingCard.jsx";
import { RDH_LISTINGS } from "./WebsiteHome.jsx";

/** Buy/Rent listings screen with an interactive type toggle. */
export function WebsiteListings() {
  const [type, setType] = useState("sale");
  const items = RDH_LISTINGS.filter((l) => l.type === type);
  const seg = (t, label) => (
    <button
      onClick={() => setType(t)}
      style={{
        borderRadius: 9999, border: type === t ? "1px solid var(--teal)" : "1px solid var(--mist-deep)",
        background: type === t ? "var(--teal)" : "transparent",
        color: type === t ? "#fff" : "var(--teal)",
        padding: "8px 18px", fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 600,
        cursor: "pointer", transition: "background .15s",
      }}
    >
      {label}
    </button>
  );
  return (
    <div style={{ margin: "0 auto", maxWidth: 1152, padding: "72px 24px 96px", boxSizing: "border-box", fontFamily: "var(--font-sans)" }}>
      <Reveal>
        <p style={{ margin: "0 0 24px", display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: "var(--ink-50)" }}>
          <span style={{ height: 8, width: 8, borderRadius: 9999, background: "var(--warm)" }} />
          {items.length} listings · Goregaon · Andheri · Malad
        </p>
        <h1 style={{ margin: 0, fontSize: 52, fontWeight: 800, lineHeight: 1.05, letterSpacing: "-0.025em", color: "var(--teal)" }}>
          {type === "sale" ? "Apartments for sale" : "Apartments for rent"}
        </h1>
        <div style={{ marginTop: 28, display: "flex", gap: 10 }}>
          {seg("sale", "For sale")}
          {seg("rent", "For rent")}
        </div>
      </Reveal>
      <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
        {items.map((l, i) => (
          <Reveal key={l.title + i} delay={(i % 3) * 0.05} style={{ height: "100%" }}>
            <ListingCard {...l} />
          </Reveal>
        ))}
      </div>
    </div>
  );
}
