import React, { useEffect, useRef, useState } from "react";
import { Button } from "../../components/marketing/Button.jsx";
import { Eyebrow } from "../../components/marketing/Eyebrow.jsx";
import { PendingChip } from "../../components/marketing/PendingChip.jsx";
import { PlaceholderFrame } from "../../components/marketing/PlaceholderFrame.jsx";
import { StickyCta } from "../../components/chrome/StickyCta.jsx";

/** Mobile (390px) view of the Westpark landing inside a phone frame, with the two-segment sticky CTA. */
export function WebsiteMobile() {
  const scrollRef = useRef(null);
  const enquiryRef = useRef(null);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const root = scrollRef.current, target = enquiryRef.current;
    if (!root || !target) return;
    const io = new IntersectionObserver(([e]) => setHidden(e.isIntersecting), { root, rootMargin: "0px 0px -40% 0px" });
    io.observe(target);
    return () => io.disconnect();
  }, []);

  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "56px 24px 96px", fontFamily: "var(--font-sans)" }}>
      <div style={{ width: 390, height: 760, borderRadius: 40, border: "1px solid var(--mist-deep)", boxShadow: "0 0 0 8px var(--ink)", background: "#fff", overflow: "hidden", position: "relative" }}>
        {/* status bar */}
        <div style={{ height: 44, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink)", borderBottom: "1px solid rgba(227,232,229,0.6)", background: "rgba(255,255,255,0.85)" }}>
          <span>9:41</span>
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ display: "flex", height: 20, width: 20, alignItems: "center", justifyContent: "center", borderRadius: 9999, background: "var(--teal)", color: "#fff", fontSize: 7, fontWeight: 700, fontFamily: "var(--font-sans)" }}>RDH</span>
          </span>
        </div>
        <div ref={scrollRef} style={{ height: 716, overflowY: "auto" }}>
          <div style={{ padding: "40px 20px 0" }}>
            <p style={{ margin: "0 0 16px", display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 500, color: "var(--ink-55)" }}>
              <span style={{ height: 8, width: 8, borderRadius: 9999, background: "var(--warm)" }} />
              DLF &amp; Trident Realty · Andheri West
            </p>
            <h1 style={{ margin: 0, fontSize: 44, fontWeight: 800, lineHeight: 1.03, letterSpacing: "-0.025em", color: "var(--teal)" }}>DLF Westpark</h1>
            <p style={{ margin: "16px 0 0", fontSize: 16, lineHeight: 1.625, color: "var(--ink-70)" }}>
              A calmer, verification-first preview of Andheri West's new launch.
            </p>
            <div style={{ margin: "20px 0 0", display: "flex", flexDirection: "column", gap: 8, fontSize: 14, color: "var(--ink-65)" }}>
              <span>Pricing <PendingChip token="PRICE_VERIFY" /></span>
              <span>RERA <PendingChip token="RERA_VERIFY" /></span>
            </div>
            <div style={{ margin: "28px 0 0" }}>
              <PlaceholderFrame ratio="16/9" radius={12} src="../../assets/imagery/westpark-exterior.jpg" alt="DLF Westpark exterior" />
            </div>
          </div>

          <div style={{ padding: "56px 20px 0" }}>
            <Eyebrow n="02" label="Project overview" />
            <p style={{ margin: 0, fontSize: 22, fontWeight: 500, lineHeight: 1.375, letterSpacing: "-0.01em", color: "var(--teal)" }}>
              Built by DLF — verified before it's published.
            </p>
          </div>

          <div style={{ margin: "48px 0 0", background: "var(--teal)", color: "#fff", padding: "48px 20px" }}>
            <Eyebrow n="05" label="Lifestyle & amenities" onDark />
            <h2 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em" }}>The everyday, considered.</h2>
            <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 1, borderRadius: 12, overflow: "hidden", background: "rgba(255,255,255,0.15)" }}>
              {["Clubhouse & gym", "Gardens & deck", "Kids & community"].map((n) => (
                <div key={n} style={{ background: "var(--teal)", padding: 20 }}>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{n}</div>
                  <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--on-teal-55)" }}>Details <PendingChip token="VERIFY" /></p>
                </div>
              ))}
            </div>
          </div>

          <div ref={enquiryRef} style={{ padding: "56px 20px 96px" }}>
            <Eyebrow n="09" label="Get in touch" />
            <h2 style={{ margin: 0, fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--teal)" }}>Request the full brief.</h2>
            <p style={{ margin: "12px 0 0", fontSize: 14, lineHeight: 1.625, color: "var(--ink-65)" }}>
              Price list, floor plans and brochure. No commitment, no lock-in.
            </p>
            <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
              <Button variant="warm" href="https://wa.me/918291293889">WhatsApp Padmini</Button>
              <Button variant="outline" href="#">Email instead →</Button>
            </div>
            <p style={{ margin: "20px 0 0", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-40)" }}>
              sticky CTA slides away while this form is in view ↓
            </p>
          </div>
        </div>
        <StickyCta hidden={hidden} whatsappHref="https://wa.me/918291293889" />
      </div>
    </div>
  );
}
