import React from "react";

const NAV = ["Buy", "Rent", "Sell", "Projects", "Blog", "About", "FAQ", "Contact"];

/** Sticky marketing-site header — blur, hairline, monogram, teal phone pill. */
export function SiteHeader({ nav = NAV, phone = "+91 829 129 3889", active }) {
  return (
    <header
      style={{
        position: "sticky", top: 0, zIndex: 40,
        borderBottom: "1px solid rgba(227,232,229,0.6)",
        background: "rgba(255,255,255,0.85)", backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)", fontFamily: "var(--font-sans)",
      }}
    >
      <div style={{ margin: "0 auto", display: "flex", height: 64, maxWidth: 1152, alignItems: "center", justifyContent: "space-between", padding: "0 24px", boxSizing: "border-box" }}>
        <a href="#" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <span style={{ display: "flex", height: 28, width: 28, alignItems: "center", justifyContent: "center", borderRadius: 9999, background: "var(--teal)", color: "#fff", fontSize: 11, fontWeight: 700 }}>RDH</span>
          <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em", color: "var(--teal)" }}>Real Deal Housing</span>
        </a>
        <nav style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {nav.map((item) => (
            <a
              key={item}
              href="#"
              style={{
                fontSize: 13.5, fontWeight: 500, textDecoration: "none",
                color: item === active ? "var(--teal)" : "var(--ink-65)",
                transition: "color .15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--teal)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = item === active ? "var(--teal)" : "var(--ink-65)")}
            >
              {item}
            </a>
          ))}
        </nav>
        <a
          href="tel:+918291293889"
          style={{ borderRadius: 9999, background: "var(--teal)", padding: "8px 16px", fontSize: 13, fontWeight: 600, color: "#fff", textDecoration: "none", transition: "opacity .15s", whiteSpace: "nowrap" }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
        >
          {phone}
        </a>
      </div>
    </header>
  );
}
