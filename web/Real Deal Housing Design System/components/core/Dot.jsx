import React from "react";

const TONES = {
  ready: "var(--teal)",
  blocked: "var(--warm)",
  review: "var(--amber)",
  active: "var(--accent)",
  neutral: "var(--ink-30)",
};

export function Dot({ tone = "neutral", style }) {
  return (
    <span
      style={{
        display: "inline-block", height: 8, width: 8,
        borderRadius: 9999, background: TONES[tone], ...style,
      }}
    />
  );
}
