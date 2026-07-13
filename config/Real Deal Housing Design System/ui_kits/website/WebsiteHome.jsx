import React from "react";
import { Reveal } from "../../components/marketing/Reveal.jsx";
import { Button } from "../../components/marketing/Button.jsx";
import { ProjectCard } from "../../components/cards/ProjectCard.jsx";
import { ListingCard } from "../../components/cards/ListingCard.jsx";

export const RDH_PROJECTS = [
  { slug: "imperial-heights", name: "Imperial Heights", location: "Goregaon West", meta: "44-storey tower · 2–4.5 BHK", src: "../../assets/imagery/westpark-exterior.jpg" },
  { slug: "kalpataru-radiance", name: "Kalpataru Radiance", location: "Goregaon West", meta: "4 towers · 4.2 acres · 2–4 BHK", src: "../../assets/imagery/westpark-gardens.jpg" },
  { slug: "ekta-tripolis", name: "Ekta Tripolis", location: "Goregaon West", meta: "36 storeys · Skypolis · Caliopolis · Theopolis" },
  { slug: "bharat-auravistas", name: "Bharat Auravistas", location: "Oshiwara, Andheri West", meta: "36-storey · 3 BHK · Luxe & Grande" },
];

export const RDH_LISTINGS = [
  { title: "Bharat Auravistas — Luxe 3 BHK", location: "Andheri West", config: "3 BHK", sqft: "1140", price: "₹4,59,00,000", type: "sale" },
  { title: "Exclusive 3.5 BHK — Imperial Heights", location: "Goregaon West", config: "3.5 BHK", sqft: "1409", price: "₹5,25,00,000", type: "sale" },
  { title: "Imperial Heights — 3.5 BHK", location: "Goregaon West", config: "3.5 BHK", sqft: "1445", price: "₹4,50,00,000", type: "sale" },
  { title: "Kalpataru Radiance — 3 BHK", location: "Goregaon West", config: "3 BHK", sqft: "1033", price: "₹3,75,00,000", type: "sale" },
  { title: "Ekta Tripolis — 2.5 BHK", location: "Goregaon West", config: "2.5 BHK", sqft: "—", price: "On request", type: "sale" },
  { title: "Kalpataru Radiance — 2 BHK", location: "Goregaon West", config: "2 BHK", sqft: "—", price: "On request", type: "sale" },
  { title: "Imperial Heights — 4.5 BHK Fully Furnished", location: "Goregaon West", config: "4.5 BHK", sqft: "1893", price: "₹2,00,000 / mo", type: "rent" },
  { title: "Kalpataru Radiance — 3 BHK", location: "Goregaon West", config: "3 BHK", sqft: "1017", price: "₹1,10,000 / mo", type: "rent" },
  { title: "Ekta Tripolis — 2.5 BHK", location: "Goregaon West", config: "2.5 BHK", sqft: "908", price: "₹90,000 / mo", type: "rent" },
  { title: "Imperial Heights — 2 BHK Duplex", location: "Goregaon West", config: "2 BHK Duplex", sqft: "727", price: "₹85,000 / mo", type: "rent" },
];

const PILLARS = [
  { title: "Truly Modern Buildings", points: ["Handpicked for builder reputation and credibility", "Spacious apartments and common areas", "Prime locations and proximity", "Top-notch modern amenities"] },
  { title: "All Apartments on Offer", points: ["Our dedicated team continually finds apartments for rent or sale", "If it's on the market, we have it", "Maximum choices for better negotiation and ideal layouts"] },
  { title: "Best Deals for You", points: ["Negotiating the lowest prices and best layouts", "Maximum negotiation room across floors and layouts", "Relax and let us handle the documentation"] },
];

const wrap = { margin: "0 auto", maxWidth: 1152, padding: "0 24px", boxSizing: "border-box" };
const h2 = { margin: 0, fontSize: 34, fontWeight: 700, letterSpacing: "-0.025em", color: "var(--teal)" };
const seeAll = { fontSize: 14, fontWeight: 600, color: "var(--teal)", textDecoration: "none", textUnderlineOffset: 4 };

export function WebsiteHome({ go }) {
  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      {/* Hero */}
      <section style={{ ...wrap, padding: "96px 24px 80px" }}>
        <Reveal>
          <p style={{ margin: "0 0 24px", display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500, color: "var(--ink-50)" }}>
            <span style={{ height: 8, width: 8, borderRadius: 9999, background: "var(--warm)" }} />
            15 years · Mumbai Western Suburbs
          </p>
          <h1 style={{ margin: 0, maxWidth: 900, fontSize: "clamp(2.6rem,6.5vw,5.5rem)", fontWeight: 800, lineHeight: 1.02, letterSpacing: "-0.025em", color: "var(--teal)" }}>
            Your Future Home Is Right Here
          </h1>
          <p style={{ margin: "28px 0 0", maxWidth: 576, fontSize: 18, lineHeight: 1.625, color: "var(--ink-65)" }}>
            2, 3 &amp; 4 BHK apartments for sale and rent in Mumbai's most sought-after towers — Imperial Heights, Kalpataru Radiance, Ekta Tripolis and more across Goregaon, Andheri &amp; Malad.
          </p>
          <div style={{ marginTop: 40, display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Button onClick={(e) => { e.preventDefault(); go("buy"); }}>View listings →</Button>
            <Button variant="outline" onClick={(e) => { e.preventDefault(); go("westpark"); }}>New launch · DLF Westpark</Button>
          </div>
        </Reveal>
      </section>

      {/* New launch banner */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", borderBottom: "1px solid var(--mist-deep)", background: "var(--teal)", color: "#fff" }}>
        <div style={{ ...wrap, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "28px 24px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ borderRadius: 9999, background: "var(--warm)", padding: "4px 10px", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>New</span>
            <span style={{ fontSize: 18, fontWeight: 600 }}>DLF Westpark, Andheri West — now previewing</span>
          </div>
          <a href="#" onClick={(e) => { e.preventDefault(); go("westpark"); }} style={{ fontSize: 14, fontWeight: 600, color: "var(--on-teal-90)", textDecoration: "none", textUnderlineOffset: 4 }}
            onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
            onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}>
            Explore the launch →
          </a>
        </div>
      </section>

      {/* Featured projects */}
      <section style={{ ...wrap, padding: "80px 24px" }}>
        <Reveal>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
            <h2 style={h2}>Featured projects</h2>
            <a href="#" style={seeAll} onClick={(e) => e.preventDefault()}>All projects →</a>
          </div>
        </Reveal>
        <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {RDH_PROJECTS.map((p, i) => (
            <Reveal key={p.slug} delay={i * 0.06}>
              <ProjectCard name={p.name} location={p.location} meta={p.meta} src={p.src} href="#" />
            </Reveal>
          ))}
        </div>
      </section>

      {/* Featured properties */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "rgba(238,241,239,0.4)" }}>
        <div style={{ ...wrap, padding: "80px 24px" }}>
          <Reveal>
            <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
              <h2 style={h2}>Featured properties</h2>
              <a href="#" style={seeAll} onClick={(e) => { e.preventDefault(); go("buy"); }}>View all →</a>
            </div>
          </Reveal>
          <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
            {RDH_LISTINGS.filter((l) => l.type === "sale").slice(0, 4).map((l, i) => (
              <Reveal key={l.title} delay={i * 0.05} style={{ height: "100%" }}>
                <ListingCard {...l} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Why work with us */}
      <section style={{ ...wrap, padding: "80px 24px" }}>
        <Reveal><h2 style={h2}>Why work with us?</h2></Reveal>
        <div style={{ marginTop: 40, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32 }}>
          {PILLARS.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.07}>
              <div style={{ borderRadius: 16, border: "1px solid var(--mist-deep)", padding: 28 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--warm)" }}>0{i + 1}</div>
                <h3 style={{ margin: "12px 0 0", fontSize: 20, fontWeight: 700, color: "var(--teal)" }}>{p.title}</h3>
                <ul style={{ margin: "16px 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8, fontSize: 14, color: "var(--ink-65)" }}>
                  {p.points.map((pt) => (
                    <li key={pt} style={{ display: "flex", gap: 8 }}><span style={{ color: "var(--warm)" }}>·</span> {pt}</li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Testimonial */}
      <section style={{ borderTop: "1px solid var(--mist-deep)", background: "var(--teal)", color: "#fff" }}>
        <div style={{ margin: "0 auto", maxWidth: 896, padding: "96px 24px", textAlign: "center", boxSizing: "border-box" }}>
          <Reveal>
            <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.2em", color: "var(--on-teal-45)" }}>What our clients say</p>
            <blockquote style={{ margin: "24px auto 0", maxWidth: 768, fontSize: 28, fontWeight: 500, lineHeight: 1.375, letterSpacing: "-0.01em" }}>
              &ldquo;Ms. Padmini Jain came to the forefront in lining up various apartments to choose from and helped me at each step until I registered my own apartment.&rdquo;
            </blockquote>
            <div style={{ marginTop: 28, fontSize: 14, color: "var(--on-teal-75)" }}>
              <span style={{ fontWeight: 600, color: "#fff" }}>Dr. Gopal Kewalramani</span> · Physician — Andheri West
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  );
}
