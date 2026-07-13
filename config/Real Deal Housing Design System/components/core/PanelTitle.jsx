import React from "react";

export function PanelTitle({ children, hint }) {
  return (
    <div style={{ marginBottom: 16, display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
      <h2 style={{ margin: 0, fontFamily: "var(--font-sans)", fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--teal)" }}>
        {children}
      </h2>
      {hint && (
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-40)" }}>{hint}</span>
      )}
    </div>
  );
}
