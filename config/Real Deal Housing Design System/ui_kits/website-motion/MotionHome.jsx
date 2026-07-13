import React, { useEffect, useState } from "react";
import { RevealLines } from "../../components/motion/RevealLines.jsx";
import { RevealImage } from "../../components/motion/RevealImage.jsx";
import { CountUp } from "../../components/motion/CountUp.jsx";
import { Ticker } from "../../components/motion/Ticker.jsx";
import { Parallax } from "../../components/motion/Parallax.jsx";
import { Reveal } from "../../components/marketing/Reveal.jsx";
import { Button } from "../../components/marketing/Button.jsx";
import { Eyebrow } from "../../components/marketing/Eyebrow.jsx";

const wrap = { margin: "0 auto", maxWidth: 1152, padding: "0 24px", boxSizing: "border-box" };

const SLIDES = [
  { src: "../../assets/imagery/westpark-exterior.jpg", label: "DLF Westpark · Andheri West" },
  { src: "../../assets/imagery/westpark-gardens.jpg", label: "Gardens & amenity deck" },
];

/* ——— Hero: full-bleed slider, slow ken-burns, numbered pagination (luxury-places style) ——— */
function MotionHero() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % SLIDES.length), 5200);
    return () => clearInterval(t);
  }, []);
  return (
    <section style={{ position: "relative", height: "86vh", minHeight: 560, overflow: "hidden", background: "var(--teal)" }}>
      <style>{`@keyframes rdh-kenburns { from { transform: scale(1.0); } to { transform: scale(1.1); } }
        @media (prefers-reduced-motion: reduce) { [data-kb] { animation: none !important; } }`}</style>
      {SLIDES.map((s, idx) => (
        <div key={s.src} style={{ position: "absolute", inset: 0, opacity: idx === i ? 1 : 0, transition: "opacity 1.2s var(--ease-expo)" }}>
          <img data-kb src={s.src} alt={s.label}
            style={{ width: "100%", height: "100%", objectFit: "cover", animation: idx === i ? "rdh-kenburns 7s var(--ease-expo) forwards" : "none" }} />
        </div>
      ))}
      {/* teal scrim — flat, no gradients */}
      <div style={{ position: "absolute", inset: 0, background: "rgba(31,61,77,0.6)" }} />
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
        <div style={{ ...wrap, width: "100%", paddingBottom: 64 }}>
          <p style={{ margin: "0 0 20px", display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: "rgba(255,255,255,0.75)" }}>
            <span style={{ height: 8, width: 8, borderRadius: 9999, background: "var(--warm)" }} />
            15 years · Mumbai Western Suburbs
          </p>
          <RevealLines as="h1" delay={0.15}
            lines={["Your Future Home", "Is Right Here"]}
            style={{ fontSize: "clamp(3rem,7vw,6rem)", fontWeight: 800, lineHeight: 1.02, letterSpacing: "-0.025em", color: "#fff" }} />
          <div style={{ marginTop: 36, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
            <p style={{ margin: 0, maxWidth: 480, fontSize: 17, lineHeight: 1.625, color: "rgba(255,255,255,0.75)" }}>
              Premium limited buildings across Goregaon, Andheri &amp; Malad — every fact verified before it's published.
            </p>
            {/* numbered pagination */}
            <div style={{ display: "flex", gap: 20 }}>
              {SLIDES.map((s, idx) => (
                <button key={idx} onClick={() => setI(idx)}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: idx === i ? "#fff" : "rgba(255,255,255,0.45)" }}>0{idx + 1}</span>
                  <span style={{ display: "block", marginTop: 8, height: 2, width: 56, background: "rgba(255,255,255,0.25)", position: "relative", overflow: "hidden" }}>
                    <span style={{ position: "absolute", inset: 0, background: "#fff", transform: idx === i ? "scaleX(1)" : "scaleX(0)", transformOrigin: "left", transition: idx === i ? "transform 5.2s linear" : "none" }} />
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ——— Stats band with count-up (Halston achievements) — real numbers only ——— */
function MotionStats() {
  const stats = [
    { v: 15, s: "", l: "years in the market" },
    { v: 4, s: "", l: "signature projects" },
    { v: 10, s: "", l: "live listings" },
    { v: 3, s: "", l: "western suburbs" },
  ];
  return (
    <section style={{ borderBottom: "1px solid var(--mist-deep)" }}>
      <div style={{ ...wrap, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24, padding: "56px 24px" }}>
        {stats.map((st, i) => (
          <Reveal key={st.l} delay={i * 0.06}>
            <CountUp value={st.v} suffix={st.s} style={{ fontSize: 56, fontWeight: 800, letterSpacing: "-0.025em", color: "var(--teal)" }} />
            <div style={{ marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--ink-45)" }}>{st.l}</div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ——— Projects: hover rows with swapping preview image (Halston services list) ——— */
const ROWS = [
  { name: "Imperial Heights", location: "Goregaon West", meta: "44 storeys · 2–4.5 BHK", src: "../../assets/imagery/westpark-exterior.jpg" },
  { name: "Kalpataru Radiance", location: "Goregaon West", meta: "4 towers · 4.2 acres", src: "../../assets/imagery/westpark-gardens.jpg" },
  { name: "Ekta Tripolis", location: "Goregaon West", meta: "36 storeys · trilogy", src: "../../assets/imagery/westpark-masterlayout.png" },
  { name: "DLF Westpark", location: "Andheri West", meta: "New launch · Phase 2", src: "../../assets/imagery/westpark-location.png" },
];

function MotionProjects({ go }) {
  const [active, setActive] = useState(0);
  return (
    <section style={{ ...wrap, padding: "96px 24px" }}>
      <Reveal><Eyebrow n="02" label="Signature buildings" /></Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 48, alignItems: "start" }}>
        <div style={{ borderTop: "1px solid var(--mist-deep)" }}>
          {ROWS.map((r, i) => (
            <a key={r.name} href="#" onClick={(e) => { e.preventDefault(); if (r.name === "DLF Westpark") go("westpark"); }}
              onMouseEnter={() => setActive(i)}
              style={{
                display: "grid", gridTemplateColumns: "auto 1fr auto", alignItems: "baseline", gap: 20,
                padding: "26px 4px", borderBottom: "1px solid var(--mist-deep)", textDecoration: "none",
                background: active === i ? "rgba(238,241,239,0.4)" : "transparent", transition: "background .3s",
              }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: active === i ? "var(--warm)" : "var(--ink-40)" }}>0{i + 1}</span>
              <span>
                <span style={{ display: "block", fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--teal)" }}>{r.name}</span>
                <span style={{ display: "block", marginTop: 2, fontSize: 13, color: "var(--ink-50)" }}>{r.location} · {r.meta}</span>
              </span>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--teal)", opacity: active === i ? 1 : 0.35, transition: "opacity .3s" }}>View →</span>
            </a>
          ))}
        </div>
        <div className="rdh-zoom" style={{ position: "sticky", top: 96, aspectRatio: "4/3", borderRadius: 16, overflow: "hidden" }}>
          {ROWS.map((r, i) => (
            <img key={r.src} src={r.src} alt={r.name}
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: active === i ? 1 : 0, transform: active === i ? "scale(1)" : "scale(1.06)", transition: "opacity .6s var(--ease-expo), transform 1.2s var(--ease-expo)" }} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* ——— Editorial statement + parallax feature ——— */
function MotionStatement({ go }) {
  return (
    <>
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.4)" }}>
        <div style={{ ...wrap, padding: "112px 24px" }}>
          <Reveal><Eyebrow n="03" label="Our promise" /></Reveal>
          <RevealLines as="p"
            lines={["A calmer, verification-first way", "to evaluate premium Mumbai", "residences."]}
            style={{ fontSize: "clamp(1.8rem,3.4vw,2.6rem)", fontWeight: 500, lineHeight: 1.25, letterSpacing: "-0.02em", color: "var(--teal)", maxWidth: 860 }} />
          <Reveal delay={0.3}>
            <p style={{ margin: "28px 0 0", maxWidth: 520, fontSize: 16, lineHeight: 1.625, color: "var(--ink-65)" }}>
              Every claim is shown with its verification status. Pending facts stay honest placeholders — we never invent a value to fill a frame.
            </p>
          </Reveal>
        </div>
      </section>
      <section style={{ position: "relative" }}>
        <Parallax speed={0.1} style={{ height: "70vh", minHeight: 440 }}>
          <img src="../../assets/imagery/westpark-gardens.jpg" alt="DLF Westpark gardens" style={{ width: "100%", height: "118%", objectFit: "cover", display: "block" }} />
        </Parallax>
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 48 }}>
          <div style={{ ...wrap }}>
            <Reveal>
              <div style={{ display: "inline-block", borderRadius: 16, background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)", padding: "28px 32px", maxWidth: 420 }}>
                <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--warm)" }}>New launch</p>
                <h3 style={{ margin: "10px 0 0", fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--teal)" }}>DLF Westpark, Andheri West</h3>
                <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.6, color: "var(--ink-65)" }}>Now previewing — pricing and RERA shown as pending until verified.</p>
                <div style={{ marginTop: 18 }}>
                  <Button size="sm" onClick={(e) => { e.preventDefault(); go("westpark"); }}>Explore the launch →</Button>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>
    </>
  );
}

/* ——— Ticker + dark CTA chapter ——— */
function MotionCta() {
  return (
    <>
      <section style={{ borderTop: "1px solid var(--mist-deep)", borderBottom: "1px solid var(--mist-deep)", padding: "36px 0", background: "#fff" }}>
        <Ticker items={["Imperial Heights", "Kalpataru Radiance", "Ekta Tripolis", "Bharat Auravistas", "DLF Westpark"]}
          itemStyle={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.025em", color: "var(--teal)" }} />
      </section>
      <section style={{ background: "var(--teal)", color: "#fff" }}>
        <div style={{ ...wrap, padding: "128px 24px", textAlign: "center" }}>
          <RevealLines as="h2"
            lines={["Request the full brief.", "No lock-in, no pressure."]}
            style={{ fontSize: "clamp(2.2rem,4.5vw,3.6rem)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-0.025em", color: "#fff" }} />
          <Reveal delay={0.25}>
            <div style={{ marginTop: 40, display: "flex", justifyContent: "center", gap: 16 }}>
              <Button variant="warm" href="https://wa.me/918291293889">WhatsApp Padmini</Button>
              <Button variant="outline" href="tel:+918291293889" style={{ borderColor: "rgba(255,255,255,0.3)", color: "#fff" }}>+91 829 129 3889</Button>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function MotionHome({ go = () => {} }) {
  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      <MotionHero />
      <MotionStats />
      <MotionProjects go={go} />
      <MotionStatement go={go} />
      <MotionCta />
    </div>
  );
}
