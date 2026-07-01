/**
 * DLF Westpark — Email 1 (APPROVED design)
 * Real Deal Housing "Gallery White" system: white card, deep teal (#1F3D4D),
 * brick-red accent (#C2493D), Montserrat display + IBM Plex Mono data type,
 * right-aligned stacked titles. Mirrors "DLF Westpark Email.dc.html".
 *
 * Drop into web/emails/. Replace ASSET_BASE with your CDN/Wix image URLs.
 * Renders with @react-email/components.
 */
import {
  Html, Head, Font, Body, Container, Section, Row, Column,
  Img, Heading, Text, Button, Link, Hr,
} from "@react-email/components";

export type DlfWestparkEmailProps = {
  firstName?: string;
  leadEmail?: string;       // pre-typed "interested" email lands here
  waUrl?: string;
  youtubeUrl?: string;
  assetBase?: string;       // base URL for the 4 brochure images + logo
  showProofStrip?: boolean;
  showGardens?: boolean;
};

const TEAL = "#1F3D4D";
const RED = "#C2493D";
const BLUE = "#3E82B0";
const MONO = "'IBM Plex Mono', monospace";
const SANS = "'Montserrat', system-ui, sans-serif";

function briefMailto(leadEmail: string) {
  const subject = "I'm interested — DLF Westpark, Phase 2 (Towers 6 & 7)";
  const body = [
    "Hi Padmini,",
    "",
    "I'd like the DLF Westpark details — price list, floor plans and brochure.",
    "I'm interested in Phase 2 (Towers 6 & 7). Please reach me on my verified contact below.",
    "",
    "Name: ",
    "Verified mobile: ",
    "Verified email: ",
    "Preferred configuration (3 / 4 BHK): ",
    "",
    "— Sent from the Real Deal Housing private invite",
  ].join("\n");
  return `mailto:${leadEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

const eyebrow = (label: string, dot: string, align: "right" = "right") => (
  <table align="right" cellPadding={0} cellSpacing={0} role="presentation" style={{ marginBottom: 14 }}>
    <tr>
      <td style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "2.5px", textTransform: "uppercase", color: "rgba(26,26,26,0.5)", paddingRight: 10 }}>{label}</td>
      <td><div style={{ width: 7, height: 7, background: dot, borderRadius: "50%" }} /></td>
    </tr>
  </table>
);

const tick = (color: string, text: string) => (
  <Row style={{ marginBottom: 11 }}>
    <Column style={{ width: 22, verticalAlign: "top", color, fontWeight: 700, lineHeight: "1.5" }}>—</Column>
    <Column style={{ fontFamily: SANS, fontSize: 14, lineHeight: "1.5", color: "rgba(26,26,26,0.8)" }}>{text}</Column>
  </Row>
);

export default function DlfWestparkEmail({
  firstName = "there",
  leadEmail = "PadminiJain1@gmail.com",
  waUrl = "https://wa.me/918291293889",
  youtubeUrl = "https://www.youtube.com/@RealDealHousing",
  assetBase = "https://CHANGE-ME.cdn/realdealhousing",
  showProofStrip = true,
  showGardens = true,
}: DlfWestparkEmailProps) {
  const A = (f: string) => `${assetBase}/${f}`;
  const pad = { paddingLeft: 44, paddingRight: 44 };

  return (
    <Html>
      <Head>
        <Font fontFamily="Montserrat" fallbackFontFamily="Arial" webFont={{ url: "https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Hw5aXo.woff2", format: "woff2" }} fontWeight={800} fontStyle="normal" />
      </Head>
      <Body style={{ margin: 0, background: "#E7EAE7", fontFamily: SANS }}>
        <Container style={{ maxWidth: 600, margin: "0 auto", background: "#fff" }}>
          {/* Top accent rule */}
          <Row><Column style={{ height: 4, background: TEAL }} /><Column style={{ height: 4, width: 130, background: RED }} /></Row>

          {/* Masthead */}
          <Section style={{ ...pad, paddingTop: 32, paddingBottom: 26, textAlign: "right" }}>
            <Img src={A("rdh-icon.png")} alt="Real Deal Housing" height={44} style={{ display: "inline-block", marginBottom: 18 }} />
            {eyebrow("Private client note", RED)}
            <Heading as="h1" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 38, lineHeight: "0.95", letterSpacing: "-1.6px", color: TEAL, margin: 0 }}>Real Deal<br />Housing</Heading>
          </Section>

          <Img src={A("westpark-exterior.jpg")} alt="The Westpark towers — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />

          {/* Hero headline */}
          <Section style={{ ...pad, paddingTop: 36, paddingBottom: 28, textAlign: "right" }}>
            {eyebrow("The Westpark · DLF & Trident Realty", RED)}
            <Heading as="h1" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 48, lineHeight: "0.98", letterSpacing: "-1.8px", color: TEAL, margin: 0 }}>Phase&nbsp;2<br />is open.</Heading>
            <Text style={{ fontFamily: SANS, fontSize: 16, color: "rgba(26,26,26,0.6)", margin: "16px 0 0" }}>Phase&nbsp;1 sold out in seven days.</Text>
          </Section>

          <Hr style={{ borderColor: "#E3E8E5", margin: "0 44px" }} />

          {/* Opening note */}
          <Section style={{ ...pad, paddingTop: 28, paddingBottom: 30 }}>
            <Text style={{ fontFamily: SANS, fontWeight: 600, fontSize: 16, color: TEAL, margin: "0 0 16px" }}>Dear {firstName},</Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: "0 0 14px" }}>DLF chose Mumbai for their first project here — and Phase&nbsp;1 was gone in a week. I wanted you to see Phase&nbsp;2 before it reaches the open market.</Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: 0 }}>Towers 6 &amp; 7 are now open for Expression of Interest — pre-launch pricing, no lock-in. This is the window.</Text>
          </Section>

          {/* Proof strip */}
          {showProofStrip && (
            <Section style={{ ...pad, paddingTop: 30, paddingBottom: 30, background: TEAL, borderTop: `2px solid ${RED}` }}>
              <Row>
                {[["7 days", "Phase 1 sold out"], ["18 acres", "Landmark scale"], ["40 floors", "8 towers · 3 & 4 BHK"]].map(([n, l], i) => (
                  <Column key={i} style={{ textAlign: "center", borderLeft: i === 1 ? "1px solid rgba(255,255,255,0.12)" : undefined, borderRight: i === 1 ? "1px solid rgba(255,255,255,0.12)" : undefined }}>
                    <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, color: "#fff", lineHeight: "1", marginBottom: 8 }}>{n}</div>
                    <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "#9FC0D4" }}>{l}</div>
                  </Column>
                ))}
              </Row>
            </Section>
          )}

          {showGardens && <Img src={A("westpark-gardens.jpg")} alt="Landscaped gardens — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />}

          {/* The residence */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 30 }}>
            {eyebrow("The residence", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, lineHeight: "1.05", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>Ultra-luxury<br />3 &amp; 4 BHK.</Heading>
            <Section style={{ marginTop: 24 }}>
              {tick(RED, "3 & 4 BHK ultra-luxury residences")}
              {tick(RED, "8 iconic towers · 40 storeys")}
              {tick(RED, "3 levels of amenities across 60,000+ sq ft")}
              {tick(RED, "25m pool · sky lounge · spa · cricket pitch")}
              {tick(RED, "Exclusive fine-dining restaurant & café")}
              {tick(RED, "Lifetime maintenance by DLF · no lock-in")}
            </Section>
          </Section>

          <Img src={A("westpark-masterlayout.png")} alt="The Westpark master layout — not to scale, representation only" width={600} style={{ display: "block", width: "100%", height: "auto" }} />
          <Section style={{ ...pad, paddingTop: 10, textAlign: "right" }}>
            <Text style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.4)", margin: 0 }}>Master layout · not to scale, representation only</Text>
          </Section>

          {/* Location */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 32, borderTop: "1px solid #E3E8E5" }}>
            {eyebrow("Location", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, lineHeight: "1.08", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>Right behind<br />Lotus Petrol Pump.</Heading>
            <Text style={{ fontFamily: SANS, fontSize: 14, color: "rgba(26,26,26,0.6)", margin: "12px 0 0", textAlign: "right" }}>Andheri West · off Jogeshwari–Vikhroli Link Road</Text>
            <Img src={A("westpark-location.png")} alt="Connectivity map — The Westpark, Andheri West" width={600} style={{ display: "block", width: "100%", height: "auto", marginTop: 22, background: "#fff" }} />
            <Section style={{ marginTop: 22 }}>
              {tick(BLUE, "Heart of Andheri West, behind Lotus Petrol Pump")}
              {tick(BLUE, "Proposed metro station adjacent to the site")}
              {tick(BLUE, "Strong rental & capital-appreciation market")}
            </Section>
          </Section>

          {/* The developer */}
          <Section style={{ ...pad, paddingTop: 36, paddingBottom: 36, background: "#EEF1EF" }}>
            {eyebrow("The developer", RED)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, lineHeight: "1.05", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>Built by DLF.</Heading>
            <Text style={{ fontFamily: SANS, fontSize: 13.5, lineHeight: "1.7", color: "rgba(26,26,26,0.6)", margin: "12px 0 0", textAlign: "right" }}>India's largest listed real estate developer — 78+ years, the firm that built Gurugram &amp; Cyber City. With Trident Realty, The Westpark marks their landmark entry into Mumbai.</Text>
            <Row style={{ marginTop: 26 }}>
              {[["1946", "Founded"], ["330M+", "Sq ft delivered"], ["No. 1", "Listed in India"]].map(([n, l], i) => (
                <Column key={i} style={{ textAlign: "center", borderLeft: i === 1 ? "1px solid #D6DDD8" : undefined, borderRight: i === 1 ? "1px solid #D6DDD8" : undefined }}>
                  <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: TEAL, lineHeight: "1", marginBottom: 7 }}>{n}</div>
                  <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.45)" }}>{l}</div>
                </Column>
              ))}
            </Row>
            <Text style={{ fontFamily: SANS, fontWeight: 500, fontSize: 12.5, color: TEAL, textAlign: "center", margin: "24px 0 0" }}>No lock-in period · Lifetime maintenance by DLF</Text>
          </Section>

          {/* CTA */}
          <Section style={{ ...pad, paddingTop: 38, paddingBottom: 38, background: TEAL }}>
            {eyebrow("EOI is open now", RED)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 27, lineHeight: "1.1", letterSpacing: "-0.8px", color: "#fff", margin: "0 0 12px", textAlign: "right" }}>Shall I send you<br />the full brief?</Heading>
            <Text style={{ fontFamily: SANS, fontSize: 13.5, lineHeight: "1.7", color: "rgba(255,255,255,0.7)", margin: "0 0 24px", textAlign: "right" }}>Price list, floor plans and brochure — and a private presentation if you'd like to go deeper. No commitment.</Text>
            <table align="right" cellPadding={0} cellSpacing={0} role="presentation"><tr>
              <td style={{ paddingRight: 12 }}><Button href={briefMailto(leadEmail)} style={{ background: RED, color: "#fff", fontFamily: SANS, fontWeight: 600, fontSize: 13, padding: "14px 26px", borderRadius: 2 }}>Request the brief →</Button></td>
              <td><Button href={waUrl} style={{ background: "transparent", color: "#fff", fontFamily: SANS, fontWeight: 600, fontSize: 13, padding: "13px 25px", borderRadius: 2, border: "1px solid rgba(255,255,255,0.3)" }}>WhatsApp Padmini →</Button></td>
            </tr></table>
          </Section>

          {/* YouTube */}
          <Link href={youtubeUrl} style={{ display: "block", ...pad, paddingTop: 18, paddingBottom: 18, textDecoration: "none", borderTop: "1px solid #E3E8E5", borderBottom: "1px solid #E3E8E5" }}>
            <Row>
              <Column style={{ fontFamily: SANS, fontWeight: 600, fontSize: 13, color: TEAL }}>▸ Watch our home tours</Column>
              <Column style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.5)", textAlign: "right" }}>@RealDealHousing →</Column>
            </Row>
          </Link>

          {/* Signature */}
          <Section style={{ ...pad, paddingTop: 30, paddingBottom: 6, textAlign: "right" }}>
            <Text style={{ fontFamily: SANS, fontWeight: 700, fontSize: 15, color: TEAL, margin: "0 0 3px" }}>Padmini Jain</Text>
            <Text style={{ fontFamily: SANS, fontSize: 12, color: "rgba(26,26,26,0.5)", margin: 0 }}>Director · Real Deal Housing Pvt. Ltd.</Text>
            <Text style={{ fontFamily: MONO, fontSize: 11, color: "rgba(26,26,26,0.5)", margin: "6px 0 0" }}>+91 82912 93889</Text>
          </Section>

          {/* Footer */}
          <Section style={{ ...pad, paddingTop: 26, paddingBottom: 36 }}>
            <Hr style={{ borderColor: "#E3E8E5", marginBottom: 18 }} />
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>Real Deal Housing Pvt. Ltd. · Goregaon West, Mumbai</Text>
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>MahaRERA PR1181012500079 · valid 30/06/2032</Text>
            <Text style={{ fontFamily: SANS, fontSize: 10, lineHeight: "1.6", color: "rgba(26,26,26,0.6)", textAlign: "center", margin: "0 0 10px" }}>Sent to you as a valued RDH client. <Link href="{{unsubscribe}}" style={{ color: "rgba(26,26,26,0.6)" }}>Unsubscribe</Link></Text>
            <Text style={{ fontFamily: SANS, fontSize: 9.5, fontStyle: "italic", lineHeight: "1.6", color: "rgba(26,26,26,0.4)", textAlign: "center", margin: 0 }}>Artist's impressions used where indicated. Not financial advice. Past performance of DLF projects does not guarantee future returns.</Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}
