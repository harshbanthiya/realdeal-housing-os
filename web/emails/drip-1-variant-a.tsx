/**
 * Email 1 — Awareness, Variant A: "The Inner Circle"
 * Tone: personal, warm, from Padmini directly to a known investor.
 * Audience: existing Kalpataru / Imperial Heights owners — warm, already trust RDH.
 * Design: minimal, white space, feels like a personal note not a blast.
 */
import {
  Body, Button, Container, Head, Hr, Html, Img,
  Preview, Section, Text, Link, Row, Column, Font,
} from "@react-email/components";
import * as React from "react";

const CDN = "https://realdealhousing.com"; // swap to Wix CDN once assets uploaded
const LOGO = `${CDN}/logo-rdh.png`; // upload RDH LOGO 2 png.png to Wix

interface Props {
  firstName?: string;   // "Rajkumar" — personalisation from contacts.full_name
  ctaUrl?: string;      // link to /dlf-westpark-andheri-west
  unsubUrl?: string;    // /unsubscribe?contact=<id>&sig=<hmac>
}

export default function DripOneA({
  firstName = "there",
  ctaUrl = "https://realdealhousing.com/dlf-westpark-andheri-west",
  unsubUrl = "#",
}: Props) {
  return (
    <Html lang="en" dir="ltr">
      <Head>
        <Font
          fontFamily="Georgia"
          fallbackFontFamily="serif"
          webFont={{ url: "", format: "woff2" }}
        />
      </Head>
      <Preview>
        DLF is entering Mumbai — and you should know about it before everyone else.
      </Preview>
      <Body style={body}>

        {/* ── Header bar ── */}
        <Section style={headerBar}>
          <Text style={headerBarText}>REAL DEAL HOUSING · PRIVATE CLIENT UPDATE</Text>
        </Section>

        {/* ── Logo ── */}
        <Container style={container}>
          <Section style={{ padding: "32px 0 0" }}>
            {/* ponytail: swap src to hosted logo once on Wix CDN */}
            <Text style={logoText}>Real Deal Housing</Text>
          </Section>

          {/* ── Hero image area ── */}
          <Section style={heroSection}>
            {/*
              TODO: replace with DLF Westpark render.
              Source options:
                - DLF official press kit (dlf.in/media)
                - Magicbricks / 99acres listing image (for personal use)
                - Your own site visit / drone footage once shoot arranged
              Upload to Wix Media, paste URL here.
            */}
            <Section style={heroPlaceholder}>
              <Text style={heroLabel}>DLF WESTPARK · ANDHERI WEST · MUMBAI</Text>
            </Section>
          </Section>

          {/* ── Personal letter ── */}
          <Section style={letterSection}>
            <Text style={greeting}>Dear {firstName},</Text>

            <Text style={body2}>
              I wanted to reach out personally before this becomes widely known.
            </Text>

            <Text style={body2}>
              DLF — the company that built Cyber City in Gurgaon, DLF Avenue in
              Delhi, and has delivered <strong>10–15× returns</strong> to early
              investors across their landmark projects — has chosen Andheri West
              for their very first project in Mumbai.
            </Text>

            <Text style={body2}>
              This is not a small thing. DLF entering a new city is a decade-level
              event. They don&rsquo;t do soft launches. When they arrive, the
              neighbourhood moves with them.
            </Text>

            <Text style={body2}>
              We&rsquo;ve been tracking this since it was first whispered in developer
              circles. Now it&rsquo;s real — and we have early access. I thought of
              you first because of your position in Imperial Heights / Kalpataru.
              You understand what a premium address means before the rest of the
              market catches on.
            </Text>

            {/* ── Pull quote ── */}
            <Section style={pullQuote}>
              <Text style={pullQuoteText}>
                &ldquo;DLF Westpark is the first DLF project in Mumbai.
                Andheri West. Pre-launch pricing. We&rsquo;re
                giving our clients the first look.&rdquo;
              </Text>
            </Section>

            <Text style={body2}>
              I&rsquo;d love to send you the full project brief — floor plans, RERA
              details, and the numbers we&rsquo;re seeing. No commitment, just
              information.
            </Text>

            <Text style={body2}>
              Click below and I&rsquo;ll have everything in your inbox within the hour.
            </Text>
          </Section>

          {/* ── CTA ── */}
          <Section style={ctaSection}>
            <Button style={ctaButton} href={ctaUrl}>
              Send me the project brief →
            </Button>
            <Text style={ctaSubtext}>
              Or reply to this email and I&rsquo;ll call you directly.
            </Text>
          </Section>

          {/* ── Signature ── */}
          <Section style={sigSection}>
            <Hr style={sigDivider} />
            <Text style={sigName}>Padmini Jain</Text>
            <Text style={sigTitle}>Director, Real Deal Housing Pvt. Ltd.</Text>
            <Text style={sigContact}>+91 82912 93889 · padmini@realdealhousing.com</Text>
          </Section>

          {/* ── Key facts strip ── */}
          <Section style={factStrip}>
            <Row>
              <Column style={factCol}>
                <Text style={factNum}>1st</Text>
                <Text style={factLabel}>DLF project in Mumbai</Text>
              </Column>
              <Column style={factColMid} />
              <Column style={factCol}>
                <Text style={factNum}>Andheri W</Text>
                <Text style={factLabel}>Western Express Hwy</Text>
              </Column>
              <Column style={factColMid} />
              <Column style={factCol}>
                <Text style={factNum}>Pre-launch</Text>
                <Text style={factLabel}>Early access pricing</Text>
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
              You&rsquo;re receiving this because you&rsquo;re a valued client of Real Deal Housing.{" "}
              <Link href={unsubUrl} style={unsubLink}>Unsubscribe</Link>
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const body: React.CSSProperties = {
  backgroundColor: "#ffffff",
  fontFamily: "Georgia, 'Times New Roman', serif",
  margin: 0,
  padding: 0,
};

const headerBar: React.CSSProperties = {
  backgroundColor: "#1f3d4d",
  padding: "10px 0",
  textAlign: "center",
};
const headerBarText: React.CSSProperties = {
  color: "#b6862c",
  fontSize: "11px",
  fontFamily: "Arial, sans-serif",
  fontWeight: "700",
  letterSpacing: "2.5px",
  margin: 0,
};

const container: React.CSSProperties = {
  maxWidth: "600px",
  margin: "0 auto",
  backgroundColor: "#ffffff",
};

const logoText: React.CSSProperties = {
  fontFamily: "Arial, sans-serif",
  fontSize: "13px",
  fontWeight: "700",
  letterSpacing: "1px",
  color: "#1f3d4d",
  textAlign: "center",
  margin: "0 0 24px",
};

const heroSection: React.CSSProperties = { padding: "0 32px" };
const heroPlaceholder: React.CSSProperties = {
  backgroundColor: "#1f3d4d",
  borderRadius: "4px",
  padding: "80px 40px",
  textAlign: "center",
};
const heroLabel: React.CSSProperties = {
  color: "#b6862c",
  fontFamily: "Arial, sans-serif",
  fontSize: "12px",
  fontWeight: "700",
  letterSpacing: "3px",
  margin: 0,
};

const letterSection: React.CSSProperties = { padding: "40px 40px 0" };
const greeting: React.CSSProperties = {
  fontSize: "20px",
  color: "#1a1a1a",
  marginBottom: "24px",
  fontWeight: "normal",
};
const body2: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: "1.75",
  color: "#1a1a1a",
  margin: "0 0 20px",
};

const pullQuote: React.CSSProperties = {
  borderLeft: "3px solid #b6862c",
  margin: "32px 0",
  paddingLeft: "20px",
};
const pullQuoteText: React.CSSProperties = {
  fontSize: "17px",
  lineHeight: "1.6",
  color: "#1f3d4d",
  fontStyle: "italic",
  margin: 0,
};

const ctaSection: React.CSSProperties = {
  padding: "32px 40px 16px",
  textAlign: "center",
};
const ctaButton: React.CSSProperties = {
  backgroundColor: "#1f3d4d",
  color: "#ffffff",
  padding: "16px 36px",
  borderRadius: "3px",
  fontFamily: "Arial, sans-serif",
  fontSize: "14px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  textDecoration: "none",
  display: "inline-block",
};
const ctaSubtext: React.CSSProperties = {
  fontSize: "13px",
  color: "#666",
  fontFamily: "Arial, sans-serif",
  marginTop: "12px",
};

const sigSection: React.CSSProperties = { padding: "0 40px 32px" };
const sigDivider: React.CSSProperties = { borderColor: "#eef1ef", margin: "32px 0 24px" };
const sigName: React.CSSProperties = { fontSize: "16px", fontWeight: "bold", color: "#1a1a1a", margin: "0 0 4px" };
const sigTitle: React.CSSProperties = { fontSize: "13px", color: "#666", fontFamily: "Arial, sans-serif", margin: "0 0 4px" };
const sigContact: React.CSSProperties = { fontSize: "13px", color: "#666", fontFamily: "Arial, sans-serif", margin: 0 };

const factStrip: React.CSSProperties = {
  backgroundColor: "#eef1ef",
  padding: "24px 40px",
  margin: "0",
};
const factCol: React.CSSProperties = { textAlign: "center", width: "30%" };
const factColMid: React.CSSProperties = {
  width: "1px",
  backgroundColor: "#d0d8d4",
  padding: 0,
};
const factNum: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: "bold",
  color: "#1f3d4d",
  margin: "0 0 4px",
  fontFamily: "Arial, sans-serif",
};
const factLabel: React.CSSProperties = {
  fontSize: "11px",
  color: "#666",
  fontFamily: "Arial, sans-serif",
  margin: 0,
  letterSpacing: "0.5px",
};

const footer: React.CSSProperties = { padding: "0 40px 40px" };
const footerDivider: React.CSSProperties = { borderColor: "#eef1ef", margin: "0 0 20px" };
const footerText: React.CSSProperties = {
  fontSize: "11px",
  color: "#999",
  fontFamily: "Arial, sans-serif",
  lineHeight: "1.6",
  margin: "0 0 6px",
  textAlign: "center",
};
const unsubLink: React.CSSProperties = { color: "#999", textDecoration: "underline" };
