import React from "react";

/** Numbered section eyebrow — mono warm numeral, 32px hairline, tracked uppercase label. */
export function Eyebrow({ n, label, onDark = false }) {
  return (
    <p
      style={{
        margin: "0 0 20px", display: "flex", alignItems: "center", gap: 12,
        fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600,
        textTransform: "uppercase", letterSpacing: "0.18em",
        color: onDark ? "var(--on-teal-45)" : "var(--ink-45)",
      }}
    >
      {n && <span style={{ fontFamily: "var(--font-mono)", color: "var(--warm)" }}>{n}</span>}
      <span style={{ height: 1, width: 32, background: onDark ? "rgba(255,255,255,.25)" : "var(--mist-deep)" }} />
      {label}
    </p>
  );
}
