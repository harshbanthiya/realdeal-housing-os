/**
 * DLF Westpark — Email 1 (Gallery White design)
 * Gmail fixes v2: block eyebrow table, table-based buttons with bgcolor,
 * WhatsApp opt-in CTA replacing broken mailto.
 */
import {
  Html, Head, Body, Container, Section, Row, Column,
  Img, Heading, Text, Link, Hr,
} from "@react-email/components";

export type DlfWestparkEmailProps = {
  firstName?: string;
  waUrl?: string;
  youtubeUrl?: string;
  assetBase?: string;
  showProofStrip?: boolean;
  showGardens?: boolean;
};

const TEAL  = "#1F3D4D";
const RED   = "#C2493D";
const BLUE  = "#3E82B0";
const MONO  = "'IBM Plex Mono', monospace";
const SANS  = "'Montserrat', system-ui, sans-serif";

// Gmail fix: width="100%" keeps this as a block element (not a float).
// align="right" on <td> right-aligns the inner content.
// Previously used <table align="right"> which creates a CSS float and wraps
// adjacent heading text around it — looks broken in Gmail.
const eyebrow = (label: string, dot: string) => (
  <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ marginBottom: 14 }}>
    <tr>
      <td align="right">
        <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "2.5px", textTransform: "uppercase" as const, color: "rgba(26,26,26,0.5)", paddingRight: 8 }}>{label}</span>
        <span style={{ display: "inline-block", width: 7, height: 7, background: dot, borderRadius: "50%", verticalAlign: "middle" }} />
      </td>
    </tr>
  </table>
);

const tick = (color: string, text: string) => (
  <Row style={{ marginBottom: 11 }}>
    <Column style={{ width: 22, verticalAlign: "top", color, fontWeight: 700, lineHeight: "1.5" }}>—</Column>
    <Column style={{ fontFamily: SANS, fontSize: 14, lineHeight: "1.5", color: "rgba(26,26,26,0.8)" }}>{text}</Column>
  </Row>
);

// Gmail-safe button: background goes on <td> via bgcolor attribute (not on <a>).
// Gmail strips background-color from <a> tags but honours bgcolor on table cells.
function EmailButton({ href, bg, border, color, children }: {
  href: string; bg: string; border?: string; color: string; children: string;
}) {
  return (
    <table cellPadding={0} cellSpacing={0} role="presentation" style={{ marginBottom: 10 }}>
      <tr>
        <td
          bgcolor={bg}
          style={{ backgroundColor: bg, borderRadius: 2, border: border ?? "none" }}
        >
          <a
            href={href}
            style={{
              display: "inline-block",
              fontFamily: SANS,
              fontWeight: 600,
              fontSize: 13,
              color,
              padding: "14px 28px",
              textDecoration: "none",
            }}
          >
            {children}
          </a>
        </td>
      </tr>
    </table>
  );
}

function waOptInUrl(waBase: string, firstName: string) {
  const msg = [
    `Hi Padmini, I received your private invite about DLF Westpark Phase 2.`,
    ``,
    `I'm interested. Please reach me on the details below:`,
    `Name: ${firstName !== "there" ? firstName : ""}`,
    `Phone: `,
    `Email: `,
    `Configuration (3 BHK / 4 BHK): `,
    ``,
    `— Sent from Real Deal Housing private invite`,
  ].join("\n");
  const base = waBase.split("?")[0];
  return `${base}?text=${encodeURIComponent(msg)}`;
}

export default function DlfWestparkEmail({
  firstName  = "there",
  waUrl      = "https://wa.me/918291293889",
  youtubeUrl = "https://www.youtube.com/@RealDealHousing",
  assetBase   = "",
  showProofStrip = true,
  showGardens    = true,
}: DlfWestparkEmailProps) {
  const WIX: Record<string, string> = {
    "rdh-icon.png":              "https://static.wixstatic.com/media/77ab1a_a79e024dffb94e01a19fab09913a2203~mv2.png",
    "rdh-logo-full.png":         "https://static.wixstatic.com/media/77ab1a_1c2c2403692f401fae342354823ccee4~mv2.png",
    "westpark-exterior.jpg":     "https://static.wixstatic.com/media/77ab1a_c28efc2061634aff9bb7b5a017227c88~mv2.jpeg",
    "westpark-gardens.jpg":      "https://static.wixstatic.com/media/77ab1a_99c3e0e06c5d4b0f90066e08e3e10c6c~mv2.jpeg",
    "westpark-location.png":     "https://static.wixstatic.com/media/77ab1a_ff96bbb73e5b4c5b80b3c9e1b2c504b2~mv2.png",
    "westpark-masterlayout.png": "https://static.wixstatic.com/media/77ab1a_5e66202ba05d4b6fbb113be140c70404~mv2.png",
  };
  const A   = (f: string) => WIX[f] ?? (assetBase ? `${assetBase}/${f}` : f);
  const pad = { paddingLeft: 44, paddingRight: 44 };
  const waLink = waOptInUrl(waUrl, firstName);

  return (
    <Html>
      <Head>
        {/* Load full Montserrat + IBM Plex Mono family — all weights used in the template */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </Head>
      <Body style={{ margin: 0, background: "#E7EAE7", fontFamily: SANS }}>
        <Container style={{ maxWidth: 600, margin: "0 auto", background: "#fff" }}>

          {/* Top accent rule */}
          <Row>
            <Column style={{ height: 4, background: TEAL }} />
            <Column style={{ height: 4, width: 130, background: RED }} />
          </Row>

          {/* Masthead — two-column: project brand left, RDH brand right */}
          <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ paddingLeft: 44, paddingRight: 44, paddingTop: 32, paddingBottom: 26 }}>
            <tr>
              <td valign="bottom" style={{ width: "50%" }}>
                <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 32, lineHeight: "0.95", letterSpacing: "-1.2px", color: TEAL }}>DLF<br />Westpark</div>
                <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(26,26,26,0.4)", marginTop: 8 }}>Phase 2 · Andheri West</div>
              </td>
              <td valign="bottom" align="right" style={{ width: "50%" }}>
                <Img src={A("rdh-icon.png")} alt="Real Deal Housing" height={38} style={{ display: "inline-block", marginBottom: 14 }} />
                {eyebrow("Private client note", RED)}
                <Heading as="h1" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 32, lineHeight: "0.95", letterSpacing: "-1.4px", color: TEAL, margin: 0, textAlign: "right" }}>
                  Real Deal<br />Housing
                </Heading>
              </td>
            </tr>
          </table>

          <Img src={A("westpark-exterior.jpg")} alt="The Westpark towers — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />

          {/* Hero headline */}
          <Section style={{ ...pad, paddingTop: 36, paddingBottom: 28, textAlign: "right" }}>
            {eyebrow("The Westpark · DLF & Trident Realty", RED)}
            <Heading as="h1" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 48, lineHeight: "0.98", letterSpacing: "-1.8px", color: TEAL, margin: 0, textAlign: "right" }}>
              Phase&nbsp;2<br />is open.
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 16, color: "rgba(26,26,26,0.6)", margin: "16px 0 0", textAlign: "right" }}>
              Phase&nbsp;1 sold out in seven days.
            </Text>
          </Section>

          <Hr style={{ borderColor: "#E3E8E5", margin: "0 44px" }} />

          {/* Opening note */}
          <Section style={{ ...pad, paddingTop: 28, paddingBottom: 30 }}>
            <Text style={{ fontFamily: SANS, fontWeight: 600, fontSize: 16, color: TEAL, margin: "0 0 16px" }}>
              Dear {firstName},
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: "0 0 14px" }}>
              DLF chose Mumbai for their first project here — and Phase&nbsp;1 was gone in a week. I wanted you to see Phase&nbsp;2 before it reaches the open market.
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: 0 }}>
              Towers 6 &amp; 7 are now open for Expression of Interest — pre-launch pricing, no lock-in. This is the window.
            </Text>
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

          {showGardens && (
            <Img src={A("westpark-gardens.jpg")} alt="Landscaped gardens — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />
          )}

          {/* The residence */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 30 }}>
            {eyebrow("The residence", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, lineHeight: "1.05", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>
              Ultra-luxury<br />3 &amp; 4 BHK.
            </Heading>
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
            <Text style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.4)", margin: 0 }}>
              Master layout · not to scale, representation only
            </Text>
          </Section>

          {/* Location */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 32, borderTop: "1px solid #E3E8E5" }}>
            {eyebrow("Location", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, lineHeight: "1.08", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>
              Right behind<br />Lotus Petrol Pump.
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 14, color: "rgba(26,26,26,0.6)", margin: "12px 0 0", textAlign: "right" }}>
              Andheri West · off Jogeshwari–Vikhroli Link Road
            </Text>
            <Img src={A("westpark-location.png")} alt="Connectivity map — The Westpark, Andheri West" width={600} style={{ display: "block", width: "100%", height: "auto", marginTop: 22 }} />
            <Section style={{ marginTop: 22 }}>
              {tick(BLUE, "Heart of Andheri West, behind Lotus Petrol Pump")}
              {tick(BLUE, "Proposed metro station adjacent to the site")}
              {tick(BLUE, "Strong rental & capital-appreciation market")}
            </Section>
          </Section>

          {/* The developer */}
          <Section style={{ ...pad, paddingTop: 36, paddingBottom: 36, background: "#EEF1EF" }}>
            {eyebrow("The developer", RED)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, lineHeight: "1.05", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>
              Built by DLF.
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 13.5, lineHeight: "1.7", color: "rgba(26,26,26,0.6)", margin: "12px 0 0", textAlign: "right" }}>
              India's largest listed real estate developer — 78+ years, the firm that built Gurugram &amp; Cyber City. With Trident Realty, The Westpark marks their landmark entry into Mumbai.
            </Text>
            <Row style={{ marginTop: 26 }}>
              {[["1946", "Founded"], ["330M+", "Sq ft delivered"], ["No. 1", "Listed in India"]].map(([n, l], i) => (
                <Column key={i} style={{ textAlign: "center", borderLeft: i === 1 ? "1px solid #D6DDD8" : undefined, borderRight: i === 1 ? "1px solid #D6DDD8" : undefined }}>
                  <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: TEAL, lineHeight: "1", marginBottom: 7 }}>{n}</div>
                  <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.45)" }}>{l}</div>
                </Column>
              ))}
            </Row>
            <Text style={{ fontFamily: SANS, fontWeight: 500, fontSize: 12.5, color: TEAL, textAlign: "center", margin: "24px 0 0" }}>
              No lock-in period · Lifetime maintenance by DLF
            </Text>
          </Section>

          {/* CTA */}
          <Section style={{ ...pad, paddingTop: 38, paddingBottom: 38, background: TEAL }}>
            {eyebrow("EOI is open now", RED)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 27, lineHeight: "1.1", letterSpacing: "-0.8px", color: "#fff", margin: "0 0 12px", textAlign: "right" }}>
              Shall I send you<br />the full brief?
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 13.5, lineHeight: "1.7", color: "rgba(255,255,255,0.7)", margin: "0 0 28px", textAlign: "right" }}>
              Price list, floor plans and brochure. Tap below to share your phone and preferred configuration — I'll reach you within the day.
            </Text>

            {/* WhatsApp opt-in — pre-fills name + blanks for phone/email/config */}
            <EmailButton href={waLink} bg={RED} color="#fff">
              WhatsApp Padmini — share my details →
            </EmailButton>

            <Text style={{ fontFamily: MONO, fontSize: 9.5, color: "rgba(255,255,255,0.4)", margin: "8px 0 0", textAlign: "right" }}>
              No commitment · No brokerage pressure
            </Text>
          </Section>

          {/* YouTube — table wraps the <a> so we avoid invalid table-inside-<a> */}
          <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ borderTop: "1px solid #E3E8E5", borderBottom: "1px solid #E3E8E5" }}>
            <tr>
              <td style={{ paddingLeft: 44, paddingRight: 44, paddingTop: 18, paddingBottom: 18 }}>
                <table width="100%" cellPadding={0} cellSpacing={0} role="presentation">
                  <tr>
                    <td style={{ fontFamily: SANS, fontWeight: 600, fontSize: 13, color: TEAL }}>
                      <Link href={youtubeUrl} style={{ textDecoration: "none", color: TEAL }}>▸ Watch our home tours</Link>
                    </td>
                    <td align="right" style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "1px", textTransform: "uppercase" as const, color: "rgba(26,26,26,0.5)" }}>
                      <Link href={youtubeUrl} style={{ textDecoration: "none", color: "rgba(26,26,26,0.5)" }}>@RealDealHousing →</Link>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>

          {/* Signature */}
          <Section style={{ ...pad, paddingTop: 30, paddingBottom: 6, textAlign: "right" }}>
            <Text style={{ fontFamily: SANS, fontWeight: 700, fontSize: 15, color: TEAL, margin: "0 0 3px" }}>Padmini Jain</Text>
            <Text style={{ fontFamily: SANS, fontSize: 12, color: "rgba(26,26,26,0.5)", margin: 0 }}>Director · Real Deal Housing Pvt. Ltd.</Text>
            <Text style={{ fontFamily: SANS, fontWeight: 700, fontSize: 15, color: TEAL, margin: "10px 0 0" }}>
              <Link href="tel:+918291293889" style={{ color: TEAL, textDecoration: "none" }}>+91 82912 93889</Link>
            </Text>
          </Section>

          {/* Footer */}
          <Section style={{ ...pad, paddingTop: 26, paddingBottom: 36 }}>
            <Hr style={{ borderColor: "#E3E8E5", marginBottom: 18 }} />
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>
              Real Deal Housing Pvt. Ltd. · Goregaon West, Mumbai
            </Text>
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>
              MahaRERA PR1181012500079 · valid 30/06/2032
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 10, lineHeight: "1.6", color: "rgba(26,26,26,0.6)", textAlign: "center", margin: "0 0 10px" }}>
              Sent to you as a valued RDH client.{" "}
              <Link href="{{unsubscribe}}" style={{ color: "rgba(26,26,26,0.6)" }}>Unsubscribe</Link>
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 9.5, fontStyle: "italic", lineHeight: "1.6", color: "rgba(26,26,26,0.4)", textAlign: "center", margin: 0 }}>
              Artist's impressions used where indicated. Not financial advice. Past performance of DLF projects does not guarantee future returns.
            </Text>
          </Section>

        </Container>
      </Body>
    </Html>
  );
}
