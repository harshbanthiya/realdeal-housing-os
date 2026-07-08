import React from "react";

/** Honest image placeholder — dashed mist frame with mono label; or a real image with fixed ratio. */
export function PlaceholderFrame({ ratio = "4/3", label, src, alt = "", radius = 12, style, children }) {
  if (src) {
    return (
      <div style={{ aspectRatio: ratio, borderRadius: radius, overflow: "hidden", position: "relative", ...style }}>
        <img src={src} alt={alt} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        {children}
      </div>
    );
  }
  return (
    <div
      style={{
        aspectRatio: ratio, borderRadius: radius,
        border: "1px dashed var(--mist-deep)", background: "rgba(238,241,239,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        textAlign: "center", position: "relative",
        fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-40)",
        ...style,
      }}
    >
      {label}
      {children}
    </div>
  );
}
