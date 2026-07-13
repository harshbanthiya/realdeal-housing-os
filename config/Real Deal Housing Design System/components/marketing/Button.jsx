import React from "react";

const VARIANTS = {
  primary: {
    background: "var(--teal)", color: "#fff", border: "1px solid var(--teal)",
  },
  outline: {
    background: "transparent", color: "var(--teal)", border: "1px solid var(--mist-deep)",
  },
  warm: {
    background: "var(--warm)", color: "#fff", border: "1px solid var(--warm)",
  },
};

/** Pill CTA — the recurring link-button pattern from the site source. */
export function Button({ variant = "primary", size = "md", href = "#", onClick, children, style }) {
  const pad = size === "sm" ? "8px 16px" : "14px 24px";
  const font = size === "sm" ? 12 : 14;
  const v = VARIANTS[variant];
  return (
    <a
      href={href}
      onClick={onClick}
      onMouseEnter={(e) => {
        if (variant === "outline") e.currentTarget.style.background = "var(--mist)";
        else e.currentTarget.style.opacity = "0.9";
      }}
      onMouseLeave={(e) => {
        if (variant === "outline") e.currentTarget.style.background = "transparent";
        else e.currentTarget.style.opacity = "1";
      }}
      style={{
        display: "inline-flex", alignItems: "center", gap: 10, whiteSpace: "nowrap",
        borderRadius: 9999, padding: pad, textDecoration: "none",
        fontFamily: "var(--font-sans)", fontSize: font, fontWeight: 600,
        transition: "opacity .15s, background .15s", cursor: "pointer",
        ...v, ...style,
      }}
    >
      {children}
    </a>
  );
}
