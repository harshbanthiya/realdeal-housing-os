import React from "react";
import { PlaceholderFrame } from "../marketing/PlaceholderFrame.jsx";

/** Listing card — 4/3 image well with type badge, teal title, meta line, bold price. */
export function ListingCard({ title, location, config, sqft, price, type = "sale", src }) {
  return (
    <div
      style={{
        display: "flex", flexDirection: "column", height: "100%",
        borderRadius: 16, border: "1px solid var(--mist-deep)", background: "#fff",
        padding: 20, fontFamily: "var(--font-sans)", boxSizing: "border-box",
      }}
    >
      <PlaceholderFrame ratio="4/3" radius={8} src={src}>
        <span
          style={{
            position: "absolute", left: 12, top: 12, borderRadius: 9999,
            background: "var(--teal)", color: "#fff", padding: "4px 10px",
            fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
            textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap",
          }}
        >
          {type === "rent" ? "For rent" : "For sale"}
        </span>
      </PlaceholderFrame>
      <h3 style={{ margin: "16px 0 0", fontSize: 16, fontWeight: 600, lineHeight: 1.375, color: "var(--teal)" }}>{title}</h3>
      <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--ink-50)" }}>
        {location} · {config}{sqft && sqft !== "—" ? ` · ${sqft} sqft` : ""}
      </p>
      <p style={{ margin: "12px 0 0", fontSize: 18, fontWeight: 700, color: "var(--teal)" }}>{price}</p>
    </div>
  );
}
