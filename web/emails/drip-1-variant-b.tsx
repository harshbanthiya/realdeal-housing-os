/**
 * Email 1 — Awareness, Variant B: "The Investment Brief"
 * Tone: editorial, data-first, like a VC memo to a smart investor.
 * Audience: same warm investors but reached via credibility not warmth.
 * Design: structured like a magazine brief — bold headers, stat callouts, dark hero.
 */
import {
  Body, Button, Container, Head, Hr, Html, Img,
  Preview, Section, Text, Link, Row, Column, Font,
} from "@react-email/components";
import * as React from "react";

interface Props {
  firstName?: string;
  ctaUrl?: string;
  unsubUrl?: string;
}

export default function DripOneB({
  firstName = "Investor",
  ctaUrl = "https://realdealhousing.com/dlf-westpark-andheri-west",
  unsubUrl = "#",
}: Props) {
  return (
    <Html lang="en" dir="ltr">
      <Head />
      <Preview>
        DLF's first Mumbai project. Early access. Here's what the numbers say.
      </Preview>
      <Body style={body}>

        {/* ── Dark hero ── */}
        <Section style={darkHero}>
          <Text style={heroEyebrow}>REAL DEAL HOUSING · INVESTOR BRIEF</Text>
          <Text style={heroHeadline}>
            DLF enters Mumbai.<br />
            The Westpark — Andheri West.<br />
            Pre-launch. MahaRERA registered.
          </Text>
          <Text style={heroDate}>June 2026 · Private Distribution</Text>

          <Button style={heroCtaButton} href={ctaUrl}>
            Request early access →
          </Button>
        </Section>

        <Container style={container}>

          {/* ── "Why this matters" bar ── */}
          <Section style={whyBar}>
            <Text style={whyBarText}>
              DLF has never launched in Mumbai before.
              When India's largest developer enters a new city,
              the micro-market moves — permanently.
            </Text>
          </Section>

          {/* ── Stat row ── */}
          <Section style={statsSection}>
            <Row>
              <Column style={statCol}>
                <Text style={statNumber}>57 yrs</Text>
                <Text style={statLabel}>DLF track record</Text>
              </Column>
              <Column style={statDivider} />
              <Column style={statCol}>
                <Text style={statNumber}>~10–15×</Text>
                <Text style={statLabel}>avg early-stage returns, DLF projects</Text>
              </Column>
              <Column style={statDivider} />
              <Column style={statCol}>
                <Text style={statNumber}>Andheri W</Text>
                <Text style={statLabel}>Mumbai's highest-velocity micro-market</Text>
              </Column>
            </Row>
          </Section>

          {/* ── Section: The Developer ── */}
          <Section style={contentSection}>
            <Text style={sectionEyebrow}>THE DEVELOPER</Text>
            <Text style={sectionHeadline}>DLF: the name that built India's most valuable neighbourhoods.</Text>

            <Text style={bodyText}>
              DLF built DLF Cyber City (Gurgaon), DLF Avenue (Delhi), and DLF
              The Crest — properties that have delivered between 8× and 15× to
              investors who entered at launch pricing. Their residential pipeline
              has a consistent record: deliver on time, build a premium address
              from scratch, and watch early investors compound.
            </Text>

            <Text style={bodyText}>
              They are not a speculative developer. They are India&rsquo;s largest
              listed real estate company by market cap. When DLF chooses a city,
              it is because they intend to own its skyline.
            </Text>

            {/* callout box */}
            <Section style={calloutBox}>
              <Text style={calloutText}>
                DLF has <strong>never</strong> launched a project in Mumbai
                before DLF Westpark. This is their market-entry project — the
                one they will protect most fiercely.
              </Text>
            </Section>
          </Section>

          <Hr style={sectionDivider} />

          {/* ── Section: The Location ── */}
          <Section style={contentSection}>
            <Text style={sectionEyebrow}>THE LOCATION</Text>
            <Text style={sectionHeadline}>Andheri West: connectivity + premium supply crunch.</Text>

            <Text style={bodyText}>
              Andheri West sits at the intersection of the Western Express
              Highway and the metro corridor — office workers from BKC can
              reach it in 20 minutes, airport in 10. The micro-market has
              seen consistent 12–18% YoY price appreciation on new-build
              inventory over the past 4 years.
            </Text>

            <Text style={bodyText}>
              Premium supply (2Cr+ ticket) has been constrained — Oberoi,
              Lodha, and Rustomjee have absorbed most land parcels. DLF
              entering here is not incremental — it is a compression event.
            </Text>

            {/* mini stat row */}
            <Section style={miniStatRow}>
              <Row>
                <Column style={miniStatCol}>
                  <Text style={miniStatNum}>10 min</Text>
                  <Text style={miniStatLbl}>to airport</Text>
                </Column>
                <Column style={miniStatCol}>
                  <Text style={miniStatNum}>20 min</Text>
                  <Text style={miniStatLbl}>to BKC via metro</Text>
                </Column>
                <Column style={miniStatCol}>
                  <Text style={miniStatNum}>12–18%</Text>
                  <Text style={miniStatLbl}>YoY price appreciation (Andheri W)</Text>
                </Column>
              </Row>
            </Section>
          </Section>

          <Hr style={sectionDivider} />

          {/* ── Section: The Opportunity ── */}
          <Section style={contentSection}>
            <Text style={sectionEyebrow}>THE OPPORTUNITY</Text>
            <Text style={sectionHeadline}>Pre-launch pricing: the window that closes first.</Text>

            <Text style={bodyText}>
              Pre-launch pricing on any DLF project has historically been 15–25%
              below the first public price list. The projects that moved fastest
              were the ones where informed investors moved in the pre-launch
              window — before the brochure went public.
            </Text>

            <Text style={bodyText}>
              We are offering our existing clients — you included — first
              access to the project brief before it goes to the wider market.
              No commitment. Just information.
            </Text>
          </Section>

          {/* ── CTA section ── */}
          <Section style={ctaSection}>
            <Text style={ctaHeadline}>Request the DLF Westpark brief.</Text>
            <Text style={ctaSubhead}>
              Floor plans, RERA details, pricing estimates, and our view on
              the investment case. Sent within the hour.
            </Text>
            <Button style={ctaButton} href={ctaUrl}>
              Get the project brief →
            </Button>
            <Text style={ctaAlt}>
              Prefer a call?{" "}
              <Link href="https://wa.me/918291293889" style={ctaAltLink}>
                WhatsApp Padmini directly →
              </Link>
            </Text>
          </Section>

          {/* ── Signature / from line ── */}
          <Section style={fromSection}>
            <Hr style={fromDivider} />
            <Row>
              <Column style={{ width: "40px" }}>
                <Section style={avatarCircle}>
                  <Text style={avatarInitial}>P</Text>
                </Section>
              </Column>
              <Column style={{ paddingLeft: "12px" }}>
                <Text style={fromName}>Padmini Jain</Text>
                <Text style={fromTitle}>Director, Real Deal Housing · +91 82912 93889</Text>
              </Column>
            </Row>
          </Section>

          {/* ── Footer ── */}
          <Section style={footer}>
            <Hr style={footerDivider} />
            <Text style={footerText}>
              Real Deal Housing Pvt. Ltd. · Mumbai, Maharashtra, India
            </Text>
            <Text style={footerText}>
              You are receiving this as a client of Real Deal Housing.{" "}
              <Link href={unsubUrl} style={footerLink}>Unsubscribe</Link>
              {" · "}
              <Link href="https://realdealhousing.com/privacy" style={footerLink}>Privacy</Link>
            </Text>
            <Text style={disclaimer}>
              This is not financial advice. Return figures are historical references from
              publicly available DLF project data. Past performance does not guarantee future
              returns. MahaRERA: PR1181012500079 · valid 30/06/2032 · maharera.maharashtra.gov.in
            </Text>
          </Section>

        </Container>
      </Body>
    </Html>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const body: React.CSSProperties = {
  backgroundColor: "#f5f5f0",
  fontFamily: "Arial, Helvetica, sans-serif",
  margin: 0,
  padding: 0,
};

const darkHero: React.CSSProperties = {
  backgroundColor: "#1f3d4d",
  padding: "48px 40px 40px",
  textAlign: "center",
};
const heroEyebrow: React.CSSProperties = {
  color: "#b6862c",
  fontSize: "10px",
  fontWeight: "700",
  letterSpacing: "3px",
  margin: "0 0 24px",
};
const heroHeadline: React.CSSProperties = {
  color: "#ffffff",
  fontSize: "32px",
  lineHeight: "1.2",
  fontWeight: "700",
  fontFamily: "Georgia, serif",
  margin: "0 0 16px",
};
const heroDate: React.CSSProperties = {
  color: "rgba(255,255,255,0.5)",
  fontSize: "11px",
  letterSpacing: "1px",
  margin: "0 0 32px",
};
const heroCtaButton: React.CSSProperties = {
  backgroundColor: "#b6862c",
  color: "#ffffff",
  padding: "14px 28px",
  borderRadius: "3px",
  fontSize: "13px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  textDecoration: "none",
  display: "inline-block",
};

const container: React.CSSProperties = {
  maxWidth: "600px",
  margin: "0 auto",
  backgroundColor: "#ffffff",
};

const whyBar: React.CSSProperties = {
  backgroundColor: "#eef1ef",
  padding: "20px 40px",
  borderLeft: "4px solid #1f3d4d",
};
const whyBarText: React.CSSProperties = {
  fontSize: "15px",
  lineHeight: "1.6",
  color: "#1f3d4d",
  fontStyle: "italic",
  margin: 0,
  fontFamily: "Georgia, serif",
};

const statsSection: React.CSSProperties = {
  padding: "32px 40px",
  backgroundColor: "#ffffff",
};
const statCol: React.CSSProperties = { textAlign: "center", width: "30%" };
const statDivider: React.CSSProperties = { width: "1px", backgroundColor: "#eef1ef" };
const statNumber: React.CSSProperties = {
  fontSize: "22px",
  fontWeight: "700",
  color: "#1f3d4d",
  margin: "0 0 4px",
};
const statLabel: React.CSSProperties = {
  fontSize: "10px",
  color: "#888",
  letterSpacing: "0.5px",
  margin: 0,
  lineHeight: "1.4",
};

const contentSection: React.CSSProperties = { padding: "24px 40px 8px" };
const sectionEyebrow: React.CSSProperties = {
  fontSize: "10px",
  fontWeight: "700",
  letterSpacing: "2.5px",
  color: "#b6862c",
  margin: "0 0 8px",
};
const sectionHeadline: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: "700",
  color: "#1a1a1a",
  fontFamily: "Georgia, serif",
  margin: "0 0 16px",
  lineHeight: "1.3",
};
const bodyText: React.CSSProperties = {
  fontSize: "15px",
  lineHeight: "1.75",
  color: "#444",
  margin: "0 0 16px",
};

const calloutBox: React.CSSProperties = {
  backgroundColor: "#1f3d4d",
  borderRadius: "4px",
  padding: "20px 24px",
  margin: "16px 0 24px",
};
const calloutText: React.CSSProperties = {
  fontSize: "15px",
  lineHeight: "1.6",
  color: "#ffffff",
  margin: 0,
};

const sectionDivider: React.CSSProperties = { borderColor: "#eef1ef", margin: "8px 40px" };

const miniStatRow: React.CSSProperties = {
  backgroundColor: "#f8f9f8",
  borderRadius: "4px",
  padding: "16px 0",
  margin: "16px 0 24px",
};
const miniStatCol: React.CSSProperties = { textAlign: "center", width: "33%" };
const miniStatNum: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: "700",
  color: "#1f3d4d",
  margin: "0 0 2px",
};
const miniStatLbl: React.CSSProperties = { fontSize: "10px", color: "#888", margin: 0 };

const ctaSection: React.CSSProperties = {
  padding: "32px 40px",
  backgroundColor: "#1a1a1a",
  textAlign: "center",
};
const ctaHeadline: React.CSSProperties = {
  fontSize: "22px",
  fontWeight: "700",
  color: "#ffffff",
  fontFamily: "Georgia, serif",
  margin: "0 0 8px",
};
const ctaSubhead: React.CSSProperties = {
  fontSize: "14px",
  color: "rgba(255,255,255,0.65)",
  lineHeight: "1.6",
  margin: "0 0 24px",
};
const ctaButton: React.CSSProperties = {
  backgroundColor: "#b6862c",
  color: "#ffffff",
  padding: "16px 32px",
  borderRadius: "3px",
  fontSize: "14px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  textDecoration: "none",
  display: "inline-block",
};
const ctaAlt: React.CSSProperties = {
  fontSize: "12px",
  color: "rgba(255,255,255,0.45)",
  marginTop: "16px",
};
const ctaAltLink: React.CSSProperties = { color: "#b6862c", textDecoration: "none" };

const fromSection: React.CSSProperties = { padding: "24px 40px" };
const fromDivider: React.CSSProperties = { borderColor: "#eef1ef", margin: "0 0 20px" };
const avatarCircle: React.CSSProperties = {
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  backgroundColor: "#1f3d4d",
  textAlign: "center",
};
const avatarInitial: React.CSSProperties = {
  color: "#b6862c",
  fontSize: "18px",
  fontWeight: "700",
  lineHeight: "40px",
  margin: 0,
};
const fromName: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: "700",
  color: "#1a1a1a",
  margin: "0 0 2px",
};
const fromTitle: React.CSSProperties = {
  fontSize: "12px",
  color: "#888",
  margin: 0,
};

const footer: React.CSSProperties = { padding: "0 40px 40px" };
const footerDivider: React.CSSProperties = { borderColor: "#eef1ef", margin: "0 0 16px" };
const footerText: React.CSSProperties = {
  fontSize: "11px",
  color: "#aaa",
  textAlign: "center",
  lineHeight: "1.6",
  margin: "0 0 4px",
};
const footerLink: React.CSSProperties = { color: "#aaa", textDecoration: "underline" };
const disclaimer: React.CSSProperties = {
  fontSize: "10px",
  color: "#ccc",
  textAlign: "center",
  lineHeight: "1.5",
  margin: "16px 0 0",
  fontStyle: "italic",
};
