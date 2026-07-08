import React from "react";

/** Continuous marquee strip — building names with warm mid-dot separators. */
export function Ticker({ items = [], speed = 28, style, itemStyle }) {
  const row = (key, hidden) => (
    <div key={key} aria-hidden={hidden || undefined} style={{ display: "flex", flexShrink: 0, alignItems: "center", animation: `rdh-ticker ${speed}s linear infinite` }}>
      {items.map((it, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center", whiteSpace: "nowrap" }}>
          <span style={itemStyle}>{it}</span>
          <span style={{ margin: "0 28px", color: "var(--warm)" }}>·</span>
        </span>
      ))}
    </div>
  );
  return (
    <div style={{ display: "flex", overflow: "hidden", ...style }}>
      <style>{`@keyframes rdh-ticker { from { transform: translateX(0); } to { transform: translateX(-100%); } }
        @media (prefers-reduced-motion: reduce) { [data-rdh-ticker] > div { animation: none !important; } }`}</style>
      <div data-rdh-ticker style={{ display: "flex" }}>
        {row("a", false)}
        {row("b", true)}
      </div>
    </div>
  );
}
