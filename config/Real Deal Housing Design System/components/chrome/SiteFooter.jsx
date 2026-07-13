import React from "react";

const COLS = {
  Explore: ["Buy", "Rent", "Sell", "Projects"],
  Company: ["About", "Blog", "FAQ", "Contact"],
};

/** Teal footer — brand blurb, contacts, link columns, mono compliance line. */
export function SiteFooter() {
  const linkStyle = { color: "var(--on-teal-75)", textDecoration: "none" };
  return (
    <footer style={{ borderTop: "1px solid var(--mist-deep)", background: "var(--teal)", color: "var(--on-teal-90)", fontFamily: "var(--font-sans)" }}>
      <div style={{ margin: "0 auto", maxWidth: 1152, padding: "56px 24px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 40, flexWrap: "wrap" }}>
          <div style={{ maxWidth: 384 }}>
            <div style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em" }}>Real Deal Housing</div>
            <p style={{ margin: "12px 0 0", fontSize: 14, lineHeight: 1.625, color: "var(--on-teal-65)" }}>
              15 years finding premium homes across Mumbai's Western Suburbs — Goregaon, Andheri &amp; Malad.
            </p>
            <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 4, fontSize: 14, color: "var(--on-teal-75)" }}>
              <div>Tel: <a href="tel:+918291293889" style={linkStyle}>+91 829 129 3889</a></div>
              <div>Email: <a href="mailto:support@realdealhousing.com" style={linkStyle}>support@realdealhousing.com</a></div>
              <div style={{ color: "var(--on-teal-55)" }}>Motilal Nagar, Goregaon West, Mumbai 400104</div>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40, fontSize: 14 }}>
            {Object.entries(COLS).map(([title, links]) => (
              <div key={title}>
                <div style={{ marginBottom: 12, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--on-teal-45)" }}>{title}</div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                  {links.map((l) => (
                    <li key={l}><a href="#" style={linkStyle}>{l}</a></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 48, display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", borderTop: "1px solid var(--on-teal-border)", paddingTop: 24, fontSize: 12, color: "var(--on-teal-45)" }}>
          <span>© Real Deal Housing Private Limited</span>
          <span style={{ fontFamily: "var(--font-mono)" }}>New project facts shown as pending placeholders until verified.</span>
        </div>
      </div>
    </footer>
  );
}
