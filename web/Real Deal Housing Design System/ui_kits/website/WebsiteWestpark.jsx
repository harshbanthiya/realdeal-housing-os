import React, { useState } from "react";
import { Reveal } from "../../components/marketing/Reveal.jsx";
import { Button } from "../../components/marketing/Button.jsx";
import { Eyebrow } from "../../components/marketing/Eyebrow.jsx";
import { PendingChip } from "../../components/marketing/PendingChip.jsx";
import { StatusBadge } from "../../components/marketing/StatusBadge.jsx";
import { PlaceholderFrame } from "../../components/marketing/PlaceholderFrame.jsx";

const wrap = { margin: "0 auto", maxWidth: 1152, padding: "0 24px", boxSizing: "border-box" };
const h2 = { margin: 0, fontSize: 34, fontWeight: 700, letterSpacing: "-0.025em", color: "var(--teal)" };

const AMENITIES = [
  { category: "Wellness", name: "Clubhouse & gym", description: "Full amenity schedule VERIFY." },
  { category: "Outdoors", name: "Gardens & deck", description: "Landscape particulars VERIFY." },
  { category: "Family", name: "Kids & community", description: "Facility list VERIFY." },
];

const RESIDENCES = [
  { config: "3 BHK — Towers 6 & 7", carpetArea: "AREA_VERIFY", price: "PRICE_VERIFY" },
  { config: "4 BHK — Towers 6 & 7", carpetArea: "AREA_VERIFY", price: "PRICE_VERIFY" },
];

const FACTS = [
  { key: "developer", label: "Developer", value: "DLF & Trident Realty", status: "operator_confirmed" },
  { key: "location", label: "Micro-market", value: "Andheri West · D.N. Nagar / Link Road", status: "operator_confirmed" },
  { key: "rera", label: "RERA registration", value: "RERA_VERIFY", status: "pending_review" },
  { key: "pricing", label: "Pricing", value: "PRICE_VERIFY", status: "pending" },
  { key: "brochure", label: "Brochure", value: "BROCHURE_VERIFY", status: "pending" },
];

const FAQS = [
  { q: "Where is DLF Westpark located?", a: "Andheri West, in the D.N. Nagar / Link Road micro-market. Exact addressing stays pending until verified." },
  { q: "What configurations are offered?", a: "3 and 4 BHK residences in Towers 6 & 7 (Phase 2). Carpet areas are shown once verified." },
  { q: "Is the pricing final?", a: "Pricing is shown as a pending placeholder until we can verify it — we never invent a value." },
];

const MAP_STATES = ["Transit", "Schools", "Retail"];

export function WebsiteWestpark() {
  const [mapState, setMapState] = useState("Transit");
  return (
    <article style={{ fontFamily: "var(--font-sans)" }}>
      {/* 01 — Hero */}
      <section style={{ ...wrap, padding: "80px 24px" }}>
        <Reveal>
          <p style={{ margin: "0 0 24px", display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: "var(--ink-55)" }}>
            <span style={{ height: 8, width: 8, borderRadius: 9999, background: "var(--warm)" }} />
            DLF &amp; Trident Realty · Andheri West
          </p>
          <h1 style={{ margin: 0, maxWidth: 900, fontSize: "clamp(2.5rem,6.5vw,5.25rem)", fontWeight: 800, lineHeight: 1.03, letterSpacing: "-0.025em", color: "var(--teal)" }}>
            DLF Westpark
          </h1>
          <p style={{ margin: "28px 0 0", maxWidth: 672, fontSize: 20, lineHeight: 1.625, color: "var(--ink-70)" }}>
            A calmer, verification-first preview of Andheri West's new launch — every fact shown with its status.
          </p>
          <div style={{ margin: "32px 0 0", display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap", fontSize: 14, color: "var(--ink-65)" }}>
            <span>Pricing <PendingChip token="PRICE_VERIFY" /></span>
            <span>RERA <PendingChip token="RERA_VERIFY" /></span>
            <span>Micro-market · D.N. Nagar / Link Road</span>
          </div>
          <div style={{ marginTop: 40, display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Button href="#enquiry">Request details</Button>
            <Button variant="outline" href="#facts">See verified facts</Button>
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <div style={{ marginTop: 56 }}>
            <PlaceholderFrame ratio="21/9" radius={16} src="../../assets/imagery/westpark-exterior.jpg" alt="DLF Westpark exterior" />
          </div>
        </Reveal>
      </section>

      {/* 02 — Overview */}
      <section style={{ ...wrap, padding: "80px 24px" }}>
        <Reveal>
          <Eyebrow n="02" label="Project overview" />
          <p style={{ margin: 0, maxWidth: 768, fontSize: 30, fontWeight: 500, lineHeight: 1.375, letterSpacing: "-0.01em", color: "var(--teal)" }}>
            Built by DLF — verified before it's published. Full particulars remain under review; every pending marker is replaced with a sourced fact before anything goes live.
          </p>
        </Reveal>
      </section>

      {/* 04 — Location + map card */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.4)" }}>
        <div style={{ ...wrap, padding: "80px 24px" }}>
          <Reveal>
            <Eyebrow n="04" label="Location" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>
              <div>
                <h2 style={h2}>Andheri West · D.N. Nagar / Link Road</h2>
                <p style={{ margin: "20px 0 0", fontSize: 16, lineHeight: 1.625, color: "var(--ink-65)" }}>
                  Positioned in one of Mumbai's most established western micro-markets. Exact addressing, distances and connectivity times stay <PendingChip token="VERIFY" /> until confirmed.
                </p>
                <ul style={{ margin: "24px 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8, fontSize: 14, color: "var(--ink-60, var(--ink-65))" }}>
                  <li>· Commute &amp; metro access — <PendingChip token="VERIFY" /></li>
                  <li>· Schools &amp; institutions — <PendingChip token="VERIFY" /></li>
                  <li>· Retail &amp; lifestyle — <PendingChip token="VERIFY" /></li>
                </ul>
              </div>
              <div>
                <PlaceholderFrame ratio="1/1" radius={16} src="../../assets/imagery/westpark-location.png" alt="Location map">
                  <div style={{ position: "absolute", left: 12, bottom: 12, display: "flex", gap: 6 }}>
                    {MAP_STATES.map((s) => (
                      <button key={s} onClick={() => setMapState(s)}
                        style={{
                          borderRadius: 9999, border: "none", cursor: "pointer",
                          padding: "6px 14px", fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600,
                          background: mapState === s ? "var(--teal)" : "rgba(255,255,255,0.9)",
                          color: mapState === s ? "#fff" : "var(--teal)",
                        }}>
                        {s}
                      </button>
                    ))}
                  </div>
                  <span style={{ position: "absolute", right: 12, top: 12, borderRadius: 4, background: "rgba(255,255,255,0.9)", padding: "4px 8px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ink-55)" }}>
                    {mapState} · static card — live embed deferred
                  </span>
                </PlaceholderFrame>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* 05 — Amenities (dark chapter) */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "var(--teal)", color: "#fff" }}>
        <div style={{ ...wrap, padding: "96px 24px" }}>
          <Reveal>
            <Eyebrow n="05" label="Lifestyle & amenities" onDark />
            <h2 style={{ ...h2, color: "#fff", maxWidth: 512 }}>The everyday, considered.</h2>
          </Reveal>
          <div style={{ marginTop: 48, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, overflow: "hidden", borderRadius: 16, background: "rgba(255,255,255,0.15)" }}>
            {AMENITIES.map((a, i) => (
              <Reveal key={a.name} delay={i * 0.05} style={{ height: "100%" }}>
                <div style={{ height: "100%", background: "var(--teal)", padding: 28, boxSizing: "border-box" }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--warm)" }}>{a.category}</div>
                  <div style={{ marginTop: 12, fontSize: 18, fontWeight: 600 }}>{a.name}</div>
                  <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.625, color: "var(--on-teal-55)" }}>
                    {a.description.split("VERIFY")[0]}<PendingChip token="VERIFY" />
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 06 — Residences */}
      <section style={{ ...wrap, padding: "96px 24px" }}>
        <Reveal>
          <Eyebrow n="06" label="Residences" />
          <h2 style={h2}>Configurations</h2>
        </Reveal>
        <div style={{ marginTop: 40, borderTop: "1px solid var(--mist-deep)", borderBottom: "1px solid var(--mist-deep)" }}>
          {RESIDENCES.map((r, i) => (
            <Reveal key={r.config} delay={i * 0.05}>
              <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr auto", alignItems: "center", gap: 16, padding: "24px 0", borderBottom: i === 0 ? "1px solid var(--mist-deep)" : "none" }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: "var(--teal)" }}>{r.config}</div>
                <div style={{ fontSize: 14, color: "var(--ink-65)" }}>Carpet area · <PendingChip token={r.carpetArea} /></div>
                <div style={{ fontSize: 14, color: "var(--ink-65)" }}>Price · <PendingChip token={r.price} /></div>
                <Button size="sm" variant="outline" href="#enquiry">Request details</Button>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* 07 — Gallery */}
      <section style={{ ...wrap, padding: "0 24px 96px" }}>
        <Reveal><Eyebrow n="07" label="Gallery" /></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <Reveal delay={0}><PlaceholderFrame ratio="4/3" src="../../assets/imagery/westpark-gardens.jpg" alt="Gardens" /></Reveal>
          <Reveal delay={0.04}><PlaceholderFrame ratio="4/3" src="../../assets/imagery/westpark-masterlayout.png" alt="Master layout" /></Reveal>
          <Reveal delay={0.08}><PlaceholderFrame ratio="4/3" label={<span>Walkthrough video<br />VISUAL_DIRECTION_PENDING</span>} /></Reveal>
        </div>
      </section>

      {/* 08 — Verified facts ledger */}
      <section id="facts" style={{ borderTop: "1px solid var(--mist-deep)", borderBottom: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.4)" }}>
        <div style={{ ...wrap, padding: "96px 24px" }}>
          <Reveal>
            <Eyebrow n="08" label="Verified facts ledger" />
            <h2 style={{ ...h2, maxWidth: 512 }}>Every claim, with its verification status.</h2>
          </Reveal>
          <div style={{ marginTop: 40, overflow: "hidden", borderRadius: 16, border: "1px solid var(--mist-deep)", background: "#fff" }}>
            {FACTS.map((f, i) => (
              <Reveal key={f.key} delay={i * 0.03}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr auto", alignItems: "center", gap: 12, padding: "16px 24px", borderBottom: i < FACTS.length - 1 ? "1px solid var(--mist)" : "none" }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--teal)" }}>{f.label}</div>
                  <div style={{ fontSize: 14, color: "var(--ink-70)" }}>
                    {f.value.endsWith("_VERIFY") || f.value === "VERIFY" ? <PendingChip token={f.value} /> : f.value}
                  </div>
                  <StatusBadge status={f.status} />
                </div>
              </Reveal>
            ))}
          </div>
          <p style={{ margin: "16px 0 0", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-45)" }}>
            Source of truth: local Postgres OS · website snapshot only · no value published until verified.
          </p>
        </div>
      </section>

      {/* 09 — Enquiry */}
      <section id="enquiry" style={{ ...wrap, padding: "96px 24px" }}>
        <Reveal>
          <Eyebrow n="09" label="Get in touch" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: 48 }}>
            <div>
              <h2 style={h2}>Request the full brief.</h2>
              <p style={{ margin: "20px 0 0", maxWidth: 448, fontSize: 16, lineHeight: 1.625, color: "var(--ink-65)" }}>
                Price list, floor plans and brochure — and a private presentation if you'd like to go deeper. No commitment, no lock-in.
              </p>
              <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
                <Button variant="warm" href="https://wa.me/918291293889">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.117.549 4.107 1.51 5.84L.057 23.428a.5.5 0 0 0 .614.614l5.588-1.453A11.95 11.95 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.885 0-3.65-.52-5.16-1.426l-.37-.22-3.818.993.993-3.818-.22-.37A9.956 9.956 0 0 1 2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/></svg>
                  WhatsApp Padmini
                </Button>
                <Button variant="outline" href="mailto:PadminiJain1@gmail.com">Email instead →</Button>
              </div>
              <p style={{ margin: "24px 0 0", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-40)" }}>
                +91 82912 93889 · Director, Real Deal Housing
              </p>
            </div>
            <div style={{ borderRadius: 16, border: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.3)", padding: 32 }}>
              <p style={{ margin: "0 0 20px", fontFamily: "var(--font-mono)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--ink-40)" }}>What to expect</p>
              <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 16, fontSize: 14, color: "var(--ink-65)" }}>
                {["Price list and carpet area schedule for 3 & 4 BHK", "Floor plans for Towers 6 & 7 (Phase 2)", "Full brochure — DLF & Trident Realty", "Private presentation if you want to go deeper", "No lock-in, no brokerage pressure"].map((item) => (
                  <li key={item} style={{ display: "flex", gap: 12 }}>
                    <span style={{ color: "var(--warm)", fontWeight: 700 }}>—</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      </section>

      {/* 10 — FAQ */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.3)" }}>
        <div style={{ margin: "0 auto", maxWidth: 768, padding: "96px 24px", boxSizing: "border-box" }}>
          <Reveal>
            <Eyebrow n="10" label="FAQ" />
            <h2 style={h2}>Questions, answered honestly.</h2>
          </Reveal>
          <div style={{ marginTop: 40, borderTop: "1px solid var(--mist-deep)", borderBottom: "1px solid var(--mist-deep)" }}>
            {FAQS.map((f, i) => (
              <details key={f.q} style={{ padding: "20px 0", borderBottom: i < FAQS.length - 1 ? "1px solid var(--mist-deep)" : "none" }}>
                <summary style={{ display: "flex", cursor: "pointer", alignItems: "center", justifyContent: "space-between", gap: 16, fontSize: 18, fontWeight: 600, color: "var(--teal)", listStyle: "none" }}>
                  {f.q}
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--ink-40)" }}>+</span>
                </summary>
                <p style={{ margin: "12px 0 0", fontSize: 16, lineHeight: 1.625, color: "var(--ink-65)" }}>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </article>
  );
}
