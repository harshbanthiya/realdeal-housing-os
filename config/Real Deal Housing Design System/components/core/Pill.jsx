import React from "react";

export const TONE_STYLES = {
  ready:   { background: "var(--tone-ready-bg)",   color: "var(--tone-ready-fg)" },
  blocked: { background: "var(--tone-blocked-bg)", color: "var(--tone-blocked-fg)" },
  review:  { background: "var(--tone-review-bg)",  color: "var(--tone-review-fg)" },
  active:  { background: "var(--tone-active-bg)",  color: "var(--tone-active-fg)" },
  neutral: { background: "var(--tone-neutral-bg)", color: "var(--tone-neutral-fg)" },
};

export function Pill({ tone = "neutral", children, style }) {
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, whiteSpace: "nowrap",
        borderRadius: 9999, padding: "2px 10px",
        fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 500,
        ...TONE_STYLES[tone], ...style,
      }}
    >
      {children}
    </span>
  );
}
