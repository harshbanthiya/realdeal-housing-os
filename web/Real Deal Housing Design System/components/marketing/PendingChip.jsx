import React from "react";

/** Honest "pending verification" chip — mono, mist bg, warm tick. Never fabricate a value. */
export function PendingChip({ token }) {
  return (
    <span
      title="Pending verification — not yet confirmed"
      style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        borderRadius: 4, background: "var(--mist)", padding: "2px 6px",
        fontFamily: "var(--font-mono)", fontSize: "0.78em", fontWeight: 500,
        letterSpacing: "-0.01em", color: "rgba(31,61,77,0.8)", verticalAlign: "baseline",
      }}
    >
      <span aria-hidden style={{ display: "inline-block", height: 6, width: 6, borderRadius: 9999, background: "rgba(194,73,61,0.7)" }} />
      {token}
    </span>
  );
}
