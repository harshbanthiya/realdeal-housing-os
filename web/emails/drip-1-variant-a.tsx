/**
 * Email 1 — Variant A: "The Private Invite"
 * Ultra-luxury, near-black design. Personal from Padmini.
 * Lead angle: Phase 1 sold out in one week. Phase 2 now open.
 * REDESIGN v2 — dark prestige aesthetic, minimal copy, full hero visual.
 */
import {
  Body, Button, Container, Head, Hr, Html, Img,
  Preview, Section, Text, Link, Row, Column,
} from "@react-email/components";
import * as React from "react";

// ponytail: swap CDN paths once images uploaded to Wix Media Manager
const IMG_HERO   = "https://static.wixstatic.com/media/dlf-westpark-garden.jpg"; // brochure pg1 render
const IMG_LIVING = "https://static.wixstatic.com/media/dlf-westpark-living.jpg"; // IMG_1166 HEIC converted

interface Props {
  firstName?: string;
  ctaUrl?: string;
  waUrl?: string;
  unsubUrl?: string;
}

export default function DripOneA({
  firstName = "there",
  ctaUrl = "https://realdealhousing.com/dlf-westpark-andheri-west",
  waUrl = "https://wa.me/918291293889",
  unsubUrl = "#",
}: Props) {
  return (
    <Html lang="en" dir="ltr">
      <Head />
      <Preview>Phase 1: sold out in 7 days. Phase 2 is open — and you should be first.</Preview>
      <Body style={body}>

        {/* ── Top label bar ── */}
        <Section style={labelBar}>
          <Text style={labelText}>REAL DEAL HOUSING &nbsp;·&nbsp; PRIVATE CLIENT NOTE</Text>
        </Section>

        <Container style={container}>

          {/* ── Hero image — full bleed ── */}
          <Section style={{ padding: 0, margin: 0 }}>
            <Img
              src={IMG_HERO}
              width="600"
              alt="DLF The Westpark — landscaped gardens, Andheri West"
              style={heroImg}
            />
            {/* Overlay headline on dark gradient */}
            <Section style={heroOverlay}>
              <Text style={heroEyebrow}>DLF THE WESTPARK · ANDHERI WEST</Text>
              <Text style={heroTitle}>Phase 2 is open.</Text>
              <Text style={heroSub}>Phase 1 sold out in 7 days.</Text>
            </Section>
          </Section>

          {/* ── Opening ── */}
          <Section style={openSection}>
            <Text style={greeting}>Dear {firstName},</Text>
            <Text style={para}>
              I wanted you to hear this before it reaches the open market.
            </Text>
            <Text style={para}>
              DLF launched The Westpark in Mumbai. Four towers. Phase 1
              was <strong>completely sold out within one week</strong>.
              That kind of velocity doesn&rsquo;t happen by accident — it
              happens when Mumbai finally gets what investors have been
              waiting for.
            </Text>
            <Text style={para}>
              Towers 6 &amp; 7 are now open for EOI. This is the window.
            </Text>
          </Section>

          {/* ── Proof strip ── */}
          <Section style={proofStrip}>
            <Row>
              <Column style={proofCol}>
                <Text style={proofNum}>7 days</Text>
                <Text style={proofLbl}>Phase 1 — 4 towers sold out</Text>
              </Column>
              <Column style={proofDiv} />
              <Column style={proofCol}>
                <Text style={proofNum}>18 acres</Text>
                <Text style={proofLbl}>landmark development</Text>
              </Column>
              <Column style={proofDiv} />
              <Column style={proofCol}>
                <Text style={proofNum}>40 floors</Text>
                <Text style={proofLbl}>8 towers · ultra luxury 4BHK</Text>
              </Column>
            </Row>
          </Section>

          {/* ── Why DLF ── */}
          <Section style={bodySection}>
            <Text style={sectionTitle}>Why this is different.</Text>
            <Text style={para}>
              DLF is not a speculative builder. They are India&rsquo;s most
              trusted luxury developer — 57 years, listed on NSE/BSE,
              with a track record of early investors seeing 10–15× returns
              on their landmark projects.
            </Text>
            <Text style={para}>
              This is their <em>first</em> project in Mumbai. They chose
              Andheri West — next to the proposed metro station, Western
              Express Highway, 10 minutes from the airport. Then Phase 1
              vanished in a week.
            </Text>
            <Text style={para}>
              Two reasons Phase 2 is still the right moment: pre-launch
              pricing is still active, and there is no lock-in period.
              DLF also offers <strong>lifetime maintenance</strong> — something
              no Mumbai developer currently matches.
            </Text>
          </Section>

          {/* ── Show flat photo ── */}
          <Section style={{ padding: "0 0 0" }}>
            <Img
              src={IMG_LIVING}
              width="600"
              alt="DLF The Westpark — show flat living room"
              style={flatImg}
            />
            <Text style={imgCaption}>
              Show flat · 4BHK · marble floors · Mumbai city view
              <br /><em>(actual completed interior, not a render)</em>
            </Text>
          </Section>

          {/* ── What you get ── */}
          <Section style={bodySection}>
            <Text style={sectionTitle}>The product.</Text>
            {[
              "Ultra Luxury 4BHK residences, 40 storeys",
              "3 levels of world-class amenities · 60,000+ sq ft",
              "Fine Dining Restaurant + Café within the development",
              "25m pool · Spa · Sky Lounge · Cricket Pitch · TRX · Bowling",
              "Adjacent to proposed Andheri metro station",
              "No lock-in period · Lifetime maintenance by DLF",
              "MahaRERA: PR1181012500079 · RERA registered",
            ].map((item, i) => (
              <Text key={i} style={bullet}>
                <span style={{ color: "#b6862c", marginRight: "8px" }}>—</span>
                {item}
              </Text>
            ))}
          </Section>

          {/* ── CTA ── */}
          <Section style={ctaSection}>
            <Text style={ctaHeadline}>EOI is open now.</Text>
            <Text style={ctaSub}>
              I can send you the price list, floor plans, and brochure — and
              arrange a private presentation if you&rsquo;d like to go deeper.
              No commitment, just information.
            </Text>
            <Button href={ctaUrl} style={ctaBtn}>
              Request the full brief →
            </Button>
            <Text style={ctaOrText}>or</Text>
            <Button href={waUrl} style={waBtn}>
              WhatsApp me directly →
            </Button>
          </Section>

          {/* ── Signature ── */}
          <Section style={sigSection}>
            <Hr style={sigHr} />
            <Text style={sigName}>Padmini Jain</Text>
            <Text style={sigTitle2}>Director, Real Deal Housing Pvt. Ltd.</Text>
            <Text style={sigContact}>+91 82912 93889 · padmini@realdealhousing.com</Text>
          </Section>

          {/* ── Footer ── */}
          <Section style={footer}>
            <Hr style={footerHr} />
            <Text style={footerText}>
              Real Deal Housing Pvt. Ltd. · Mumbai
            </Text>
            <Text style={footerText}>
              MahaRERA: PR1181012500079 · valid 30/06/2032 · maharera.maharashtra.gov.in
            </Text>
            <Text style={footerText}>
              You&rsquo;re receiving this as a valued RDH client.{" "}
              <Link href={unsubUrl} style={footerLink}>Unsubscribe</Link>
            </Text>
            <Text style={disclaimer}>
              Artist&rsquo;s impressions used where indicated. This is not financial advice.
              Past performance of DLF projects does not guarantee future returns.
            </Text>
          </Section>

        </Container>
      </Body>
    </Html>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const body: React.CSSProperties = {
  backgroundColor: "#f4f3f0",
  margin: 0,
  padding: 0,
  fontFamily: "Georgia, 'Times New Roman', serif",
};

const labelBar: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  padding: "10px 0",
  textAlign: "center",
};
const labelText: React.CSSProperties = {
  color: "#b6862c",
  fontSize: "10px",
  fontWeight: "700",
  letterSpacing: "3px",
  fontFamily: "Arial, sans-serif",
  margin: 0,
};

const container: React.CSSProperties = {
  maxWidth: "600px",
  margin: "0 auto",
  backgroundColor: "#ffffff",
};

const heroImg: React.CSSProperties = {
  width: "600px",
  maxWidth: "100%",
  display: "block",
  height: "340px",
  objectFit: "cover",
  objectPosition: "center bottom",
};
const heroOverlay: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  padding: "24px 40px 28px",
};
const heroEyebrow: React.CSSProperties = {
  color: "#b6862c",
  fontSize: "10px",
  fontWeight: "700",
  letterSpacing: "3px",
  fontFamily: "Arial, sans-serif",
  margin: "0 0 10px",
};
const heroTitle: React.CSSProperties = {
  color: "#ffffff",
  fontSize: "36px",
  fontWeight: "700",
  margin: "0 0 6px",
  lineHeight: "1.1",
  fontFamily: "Georgia, serif",
};
const heroSub: React.CSSProperties = {
  color: "rgba(255,255,255,0.55)",
  fontSize: "15px",
  margin: 0,
  fontFamily: "Arial, sans-serif",
  fontStyle: "italic",
};

const openSection: React.CSSProperties = { padding: "36px 40px 8px" };
const greeting: React.CSSProperties = {
  fontSize: "19px",
  color: "#1a1a1a",
  margin: "0 0 20px",
  fontWeight: "normal",
};
const para: React.CSSProperties = {
  fontSize: "15px",
  lineHeight: "1.8",
  color: "#333",
  margin: "0 0 16px",
  fontFamily: "Georgia, serif",
};

const proofStrip: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  padding: "24px 20px",
  margin: "8px 0 0",
};
const proofCol: React.CSSProperties = { textAlign: "center", width: "32%" };
const proofDiv: React.CSSProperties = { width: "1px", backgroundColor: "rgba(182,134,44,0.3)" };
const proofNum: React.CSSProperties = {
  fontSize: "22px",
  fontWeight: "700",
  color: "#b6862c",
  margin: "0 0 4px",
  fontFamily: "Arial, sans-serif",
};
const proofLbl: React.CSSProperties = {
  fontSize: "10px",
  color: "rgba(255,255,255,0.6)",
  margin: 0,
  fontFamily: "Arial, sans-serif",
  letterSpacing: "0.3px",
  lineHeight: "1.4",
};

const bodySection: React.CSSProperties = { padding: "28px 40px 4px" };
const sectionTitle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "2px",
  color: "#b6862c",
  fontFamily: "Arial, sans-serif",
  margin: "0 0 14px",
  textTransform: "uppercase" as const,
};
const bullet: React.CSSProperties = {
  fontSize: "14px",
  lineHeight: "1.6",
  color: "#444",
  margin: "0 0 8px",
  fontFamily: "Arial, sans-serif",
};

const flatImg: React.CSSProperties = {
  width: "600px",
  maxWidth: "100%",
  display: "block",
  height: "320px",
  objectFit: "cover",
  objectPosition: "center",
};
const imgCaption: React.CSSProperties = {
  fontSize: "11px",
  color: "#999",
  textAlign: "center",
  fontFamily: "Arial, sans-serif",
  padding: "10px 40px",
  margin: 0,
  lineHeight: "1.5",
};

const ctaSection: React.CSSProperties = {
  backgroundColor: "#0c1a23",
  padding: "36px 40px",
  textAlign: "center",
};
const ctaHeadline: React.CSSProperties = {
  fontSize: "26px",
  fontWeight: "700",
  color: "#ffffff",
  fontFamily: "Georgia, serif",
  margin: "0 0 10px",
};
const ctaSub: React.CSSProperties = {
  fontSize: "14px",
  lineHeight: "1.7",
  color: "rgba(255,255,255,0.65)",
  margin: "0 0 28px",
  fontFamily: "Arial, sans-serif",
};
const ctaBtn: React.CSSProperties = {
  backgroundColor: "#b6862c",
  color: "#ffffff",
  padding: "15px 32px",
  borderRadius: "2px",
  fontSize: "13px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  fontFamily: "Arial, sans-serif",
  textDecoration: "none",
  display: "inline-block",
};
const ctaOrText: React.CSSProperties = {
  color: "rgba(255,255,255,0.3)",
  fontSize: "11px",
  margin: "14px 0",
  fontFamily: "Arial, sans-serif",
};
const waBtn: React.CSSProperties = {
  backgroundColor: "transparent",
  color: "#b6862c",
  padding: "12px 28px",
  borderRadius: "2px",
  border: "1px solid #b6862c",
  fontSize: "13px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  fontFamily: "Arial, sans-serif",
  textDecoration: "none",
  display: "inline-block",
};

const sigSection: React.CSSProperties = { padding: "28px 40px" };
const sigHr: React.CSSProperties = { borderColor: "#eef1ef", margin: "0 0 20px" };
const sigName: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: "700",
  color: "#1a1a1a",
  margin: "0 0 3px",
  fontFamily: "Arial, sans-serif",
};
const sigTitle2: React.CSSProperties = {
  fontSize: "12px",
  color: "#888",
  margin: "0 0 3px",
  fontFamily: "Arial, sans-serif",
};
const sigContact: React.CSSProperties = {
  fontSize: "12px",
  color: "#888",
  margin: 0,
  fontFamily: "Arial, sans-serif",
};

const footer: React.CSSProperties = { padding: "0 40px 36px" };
const footerHr: React.CSSProperties = { borderColor: "#eee", margin: "0 0 16px" };
const footerText: React.CSSProperties = {
  fontSize: "10px",
  color: "#bbb",
  textAlign: "center",
  fontFamily: "Arial, sans-serif",
  margin: "0 0 4px",
  lineHeight: "1.5",
};
const footerLink: React.CSSProperties = { color: "#bbb", textDecoration: "underline" };
const disclaimer: React.CSSProperties = {
  fontSize: "10px",
  color: "#ccc",
  textAlign: "center",
  fontFamily: "Arial, sans-serif",
  fontStyle: "italic",
  margin: "12px 0 0",
  lineHeight: "1.5",
};
