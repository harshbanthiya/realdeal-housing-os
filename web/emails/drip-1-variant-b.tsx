/**
 * Email 1 — Variant B: "The Launch Bulletin"
 * Newspaper/editorial bold. SOLD OUT in 7 days as the entire hook.
 * White, black, amber — hard contrast, news urgency, data-driven.
 * REDESIGN v2 — bold typographic impact, tabloid-editorial energy.
 */
import {
  Body, Button, Container, Head, Hr, Html, Img,
  Preview, Section, Text, Link, Row, Column,
} from "@react-email/components";
import * as React from "react";

// ponytail: swap CDN paths once images uploaded to Wix Media Manager
const IMG_EXTERIOR = "https://static.wixstatic.com/media/dlf-westpark-exterior.jpg"; // brochure pg2 render
const IMG_POOL     = "https://static.wixstatic.com/media/dlf-westpark-pool.jpg";     // brochure pg3 render

interface Props {
  firstName?: string;
  ctaUrl?: string;
  waUrl?: string;
  unsubUrl?: string;
}

export default function DripOneB({
  firstName = "Investor",
  ctaUrl = "https://realdealhousing.com/dlf-westpark-andheri-west",
  waUrl = "https://wa.me/918291293889",
  unsubUrl = "#",
}: Props) {
  return (
    <Html lang="en" dir="ltr">
      <Head />
      <Preview>DLF Westpark Phase 1: SOLD OUT in 7 days. Towers 6 & 7 now open for EOI.</Preview>
      <Body style={body}>

        <Container style={container}>

          {/* ── Masthead ── */}
          <Section style={masthead}>
            <Row>
              <Column style={{ width: "50%", textAlign: "left" as const }}>
                <Text style={mastheadBrand}>REAL DEAL HOUSING</Text>
              </Column>
              <Column style={{ width: "50%", textAlign: "right" as const }}>
                <Text style={mastheadDate}>June 2026 · Mumbai</Text>
              </Column>
            </Row>
            <Hr style={mastheadRule} />
          </Section>

          {/* ── Banner headline ── */}
          <Section style={bannerSection}>
            <Text style={bannerKicker}>BREAKING · DLF WESTPARK PHASE 2</Text>
            <Text style={bannerHeadline}>
              Phase 1:<br />
              SOLD OUT<br />
              in 7 days.
            </Text>
            <Text style={bannerDeck}>
              Four towers. One week. Now Towers 6 &amp; 7 open for EOI —
              with pre-launch pricing still live and no lock-in.
            </Text>
          </Section>

          {/* ── Exterior image ── */}
          <Section style={{ padding: 0 }}>
            <Img
              src={IMG_EXTERIOR}
              width="600"
              alt="DLF The Westpark — Andheri West exterior"
              style={fullImg}
            />
            <Text style={imgCaption}>Artist&rsquo;s impression · DLF The Westpark · Andheri West</Text>
          </Section>

          {/* ── Numbers that matter ── */}
          <Section style={numbersSection}>
            <Text style={numbersTitle}>THE NUMBERS THAT MATTER</Text>
            <Row>
              <Column style={numCol}>
                <Text style={numBig}>18</Text>
                <Text style={numUnit}>acres</Text>
                <Text style={numDesc}>landmark scale</Text>
              </Column>
              <Column style={numCol}>
                <Text style={numBig}>8</Text>
                <Text style={numUnit}>towers</Text>
                <Text style={numDesc}>40 storeys each</Text>
              </Column>
              <Column style={numCol}>
                <Text style={numBig}>60k+</Text>
                <Text style={numUnit}>sq ft</Text>
                <Text style={numDesc}>amenities, 3 levels</Text>
              </Column>
              <Column style={numCol}>
                <Text style={numBig}>7</Text>
                <Text style={numUnit}>days</Text>
                <Text style={numDesc}>Phase 1 sold out</Text>
              </Column>
            </Row>
          </Section>

          {/* ── Two-column: why DLF + why now ── */}
          <Section style={twoColSection}>
            <Row>
              <Column style={twoColLeft}>
                <Text style={colLabel}>WHY DLF</Text>
                <Text style={colBody}>
                  India&rsquo;s largest listed real estate company.
                  57 years. NSE/BSE listed. Early investors across
                  DLF projects have seen 10–15× returns. They
                  chose Mumbai for their first project — this is
                  a city-entry statement, not just another launch.
                </Text>
              </Column>
              <Column style={twoColRight}>
                <Text style={colLabel}>WHY NOW</Text>
                <Text style={colBody}>
                  Pre-launch pricing. No lock-in period. Lifetime
                  maintenance by DLF — not a third-party society.
                  EOI secures your position in the allotment queue
                  before public pricing is released.
                </Text>
              </Column>
            </Row>
          </Section>

          {/* ── Pool / lifestyle image ── */}
          <Section style={{ padding: 0 }}>
            <Img
              src={IMG_POOL}
              width="600"
              alt="DLF The Westpark — landscaped pool and gardens"
              style={fullImg}
            />
            <Text style={imgCaption}>Artist&rsquo;s impression · curved pool · Japanese garden landscape</Text>
          </Section>

          {/* ── What's included ── */}
          <Section style={includesSection}>
            <Text style={includesTitle}>ULTRA LUXURY 4BHK · WHAT&rsquo;S INCLUDED</Text>
            <Row>
              <Column style={incCol}>
                {[
                  "Fine Dining Restaurant",
                  "Café",
                  "25m Swimming Pool",
                  "Jacuzzi + Kids Pool",
                  "Sky Lounge",
                ].map((i, idx) => (
                  <Text key={idx} style={incItem}>
                    <span style={{ color: "#b6862c" }}>›</span> {i}
                  </Text>
                ))}
              </Column>
              <Column style={incCol}>
                {[
                  "Spa + Treatment Rooms",
                  "Gym · TRX · Yoga Studio",
                  "Cricket Pitch · Pickleball",
                  "Bowling + Arcade + VR",
                  "Proposed Metro Station adjacent",
                ].map((i, idx) => (
                  <Text key={idx} style={incItem}>
                    <span style={{ color: "#b6862c" }}>›</span> {i}
                  </Text>
                ))}
              </Column>
            </Row>
          </Section>

          {/* ── Standout box ── */}
          <Section style={standoutBox}>
            <Text style={standoutText}>
              &ldquo;Phase 1: 4 towers SOLD OUT within ONE WEEK of launch.
              EOI for Phase 2 (Towers 6 &amp; 7) is open now.
              Limited inventory.&rdquo;
            </Text>
          </Section>

          {/* ── CTA ── */}
          <Section style={ctaSection}>
            <Row>
              <Column style={{ width: "60%", paddingRight: "20px" }}>
                <Text style={ctaLeft}>
                  Request the EOI form, price list, floor plans,
                  and brochure. Private presentation available
                  for serious buyers.
                </Text>
              </Column>
              <Column style={{ width: "40%", textAlign: "center" as const }}>
                <Button href={ctaUrl} style={ctaBtn}>
                  Get the brief →
                </Button>
                <Text style={ctaOr}>or</Text>
                <Button href={waUrl} style={waBtn}>
                  WhatsApp →
                </Button>
              </Column>
            </Row>
          </Section>

          {/* ── From ── */}
          <Section style={fromSection}>
            <Hr style={fromHr} />
            <Text style={fromName}>Padmini Jain</Text>
            <Text style={fromTitle2}>Director · Real Deal Housing · +91 82912 93889</Text>
          </Section>

          {/* ── Footer ── */}
          <Section style={footer}>
            <Hr style={footerHr} />
            <Text style={footerText}>
              Real Deal Housing Pvt. Ltd. · Mumbai, Maharashtra
            </Text>
            <Text style={footerText}>
              MahaRERA: PR1181012500079 · valid 30/06/2032 · maharera.maharashtra.gov.in
            </Text>
            <Text style={footerText}>
              Receiving this as a client of Real Deal Housing.{" "}
              <Link href={unsubUrl} style={footerLink}>Unsubscribe</Link>
            </Text>
            <Text style={disclaimer}>
              Not financial advice. Artist&rsquo;s impressions used where indicated.
              Return figures are historical references from public DLF project data.
              Past performance does not guarantee future returns.
            </Text>
          </Section>

        </Container>
      </Body>
    </Html>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const body: React.CSSProperties = {
  backgroundColor: "#f0efea",
  margin: 0,
  padding: 0,
  fontFamily: "Arial, Helvetica, sans-serif",
};
const container: React.CSSProperties = {
  maxWidth: "600px",
  margin: "0 auto",
  backgroundColor: "#ffffff",
};

const masthead: React.CSSProperties = { padding: "16px 32px 0" };
const mastheadBrand: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "2px",
  color: "#1a1a1a",
  margin: 0,
};
const mastheadDate: React.CSSProperties = {
  fontSize: "10px",
  color: "#999",
  margin: 0,
  letterSpacing: "0.5px",
};
const mastheadRule: React.CSSProperties = { borderColor: "#1a1a1a", borderWidth: "2px", margin: "12px 0 0" };

const bannerSection: React.CSSProperties = { padding: "28px 32px 24px", backgroundColor: "#ffffff" };
const bannerKicker: React.CSSProperties = {
  fontSize: "10px",
  fontWeight: "700",
  letterSpacing: "3px",
  color: "#b6862c",
  margin: "0 0 10px",
};
const bannerHeadline: React.CSSProperties = {
  fontSize: "58px",
  fontWeight: "900",
  lineHeight: "0.95",
  color: "#0c1a23",
  margin: "0 0 16px",
  fontFamily: "Arial Black, Arial, sans-serif",
  letterSpacing: "-1px",
};
const bannerDeck: React.CSSProperties = {
  fontSize: "15px",
  lineHeight: "1.6",
  color: "#555",
  margin: "0",
  borderLeft: "3px solid #b6862c",
  paddingLeft: "14px",
};

const fullImg: React.CSSProperties = {
  width: "600px",
  maxWidth: "100%",
  display: "block",
  height: "300px",
  objectFit: "cover",
  objectPosition: "center",
};
const imgCaption: React.CSSProperties = {
  fontSize: "10px",
  color: "#aaa",
  fontStyle: "italic",
  padding: "6px 32px",
  margin: 0,
  backgroundColor: "#f8f8f6",
};

const numbersSection: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  padding: "28px 20px",
};
const numbersTitle: React.CSSProperties = {
  fontSize: "9px",
  fontWeight: "700",
  letterSpacing: "3px",
  color: "rgba(255,255,255,0.4)",
  textAlign: "center",
  margin: "0 0 20px",
};
const numCol: React.CSSProperties = { textAlign: "center", width: "25%" };
const numBig: React.CSSProperties = {
  fontSize: "30px",
  fontWeight: "900",
  color: "#b6862c",
  margin: "0 0 2px",
  lineHeight: "1",
};
const numUnit: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: "700",
  color: "#ffffff",
  margin: "0 0 3px",
  letterSpacing: "1px",
};
const numDesc: React.CSSProperties = {
  fontSize: "9px",
  color: "rgba(255,255,255,0.45)",
  margin: 0,
  lineHeight: "1.3",
};

const twoColSection: React.CSSProperties = { padding: "28px 0" };
const twoColLeft: React.CSSProperties = {
  width: "50%",
  padding: "0 20px 0 32px",
  borderRight: "1px solid #eee",
  verticalAlign: "top",
};
const twoColRight: React.CSSProperties = {
  width: "50%",
  padding: "0 32px 0 20px",
  verticalAlign: "top",
};
const colLabel: React.CSSProperties = {
  fontSize: "9px",
  fontWeight: "700",
  letterSpacing: "3px",
  color: "#b6862c",
  margin: "0 0 10px",
};
const colBody: React.CSSProperties = {
  fontSize: "13px",
  lineHeight: "1.7",
  color: "#444",
  margin: 0,
};

const includesSection: React.CSSProperties = { padding: "20px 32px 24px", backgroundColor: "#f8f8f6" };
const includesTitle: React.CSSProperties = {
  fontSize: "9px",
  fontWeight: "700",
  letterSpacing: "3px",
  color: "#0c1a23",
  margin: "0 0 16px",
};
const incCol: React.CSSProperties = { width: "50%", verticalAlign: "top" };
const incItem: React.CSSProperties = {
  fontSize: "12px",
  color: "#444",
  margin: "0 0 7px",
  lineHeight: "1.4",
};

const standoutBox: React.CSSProperties = {
  backgroundColor: "#b6862c",
  padding: "24px 32px",
};
const standoutText: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: "1.6",
  color: "#ffffff",
  fontStyle: "italic",
  fontFamily: "Georgia, serif",
  margin: 0,
  textAlign: "center",
};

const ctaSection: React.CSSProperties = { padding: "28px 32px", borderTop: "1px solid #eee" };
const ctaLeft: React.CSSProperties = {
  fontSize: "13px",
  lineHeight: "1.7",
  color: "#444",
  margin: 0,
};
const ctaBtn: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  color: "#ffffff",
  padding: "12px 20px",
  fontSize: "12px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  borderRadius: "2px",
  textDecoration: "none",
  display: "inline-block",
  marginBottom: "8px",
};
const ctaOr: React.CSSProperties = {
  fontSize: "10px",
  color: "#ccc",
  margin: "4px 0",
  textAlign: "center",
};
const waBtn: React.CSSProperties = {
  backgroundColor: "transparent",
  color: "#b6862c",
  padding: "10px 20px",
  fontSize: "12px",
  fontWeight: "700",
  border: "1px solid #b6862c",
  borderRadius: "2px",
  textDecoration: "none",
  display: "inline-block",
};

const fromSection: React.CSSProperties = { padding: "16px 32px 20px" };
const fromHr: React.CSSProperties = { borderColor: "#eee", margin: "0 0 14px" };
const fromName: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: "700",
  color: "#1a1a1a",
  margin: "0 0 2px",
};
const fromTitle2: React.CSSProperties = {
  fontSize: "11px",
  color: "#999",
  margin: 0,
};

const footer: React.CSSProperties = { padding: "0 32px 32px" };
const footerHr: React.CSSProperties = { borderColor: "#eee", margin: "0 0 14px" };
const footerText: React.CSSProperties = {
  fontSize: "10px",
  color: "#bbb",
  textAlign: "center",
  margin: "0 0 3px",
  lineHeight: "1.5",
};
const footerLink: React.CSSProperties = { color: "#bbb", textDecoration: "underline" };
const disclaimer: React.CSSProperties = {
  fontSize: "10px",
  color: "#ccc",
  textAlign: "center",
  fontStyle: "italic",
  margin: "12px 0 0",
  lineHeight: "1.5",
};
