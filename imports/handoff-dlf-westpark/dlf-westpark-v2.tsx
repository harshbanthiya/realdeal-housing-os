/**
 * DLF Westpark — Email 1, v2 (Gallery White design)
 * Copy into web/emails/ (replaces dlf-westpark.tsx).
 *
 * v2 changes (from design QA audit):
 * - Hidden preheader div (fixes garbled inbox snippet)
 * - Single compact masthead: icon + bold teal wordmark left, building name right
 *   (replaces the dueling 32px titles; icon has fixed dimensions so it can't stretch)
 * - Hero headline moved onto a TEAL panel with white text — survives Gmail dark mode
 * - Greeting falls back to "Hello," instead of "Dear there,"
 * - New CDN images: cleaned gardens (brochure chrome cropped), show-apartment set
 *   (brightened +16%, crops baked in — email clients don't support object-fit)
 * - Zero-width breaks in "Phase 2 · Andheri West" to stop Gmail auto-linking
 * - Shorter CTA label (was wrapping to two lines at 375px)
 */
import {
  Html, Head, Body, Container, Section, Row, Column,
  Img, Heading, Text, Link, Hr,
} from "@react-email/components";

export type DlfWestparkEmailProps = {
  firstName?: string;
  waUrl?: string;
  youtubeUrl?: string;
  unsubscribeUrl?: string;
  showProofStrip?: boolean;
  showGardens?: boolean;
};

const TEAL = "#1F3D4D";
const RED  = "#C2493D";
const BLUE = "#3E82B0";
const MONO = "'IBM Plex Mono', Consolas, monospace";
const SANS = "'Montserrat', 'Helvetica Neue', Arial, sans-serif";

const IMG = {
  icon:        "https://static.wixstatic.com/media/77ab1a_a79e024dffb94e01a19fab09913a2203~mv2.png",
  exterior:    "https://static.wixstatic.com/media/77ab1a_c28efc2061634aff9bb7b5a017227c88~mv2.jpeg",
  gardens:     "https://static.wixstatic.com/media/77ab1a_31f7234684564bf0a2655e3a4bebbd84~mv2.jpeg",
  location:    "https://static.wixstatic.com/media/77ab1a_ff96bbb73e5b4c5b80b3c9e1b2c504b2~mv2.png",
  masterplan:  "https://static.wixstatic.com/media/77ab1a_5e66202ba05d4b6fbb113be140c70404~mv2.png",
  livingHero:  "https://static.wixstatic.com/media/77ab1a_cc5905a93d414681a26280f6ea9f4425~mv2.jpeg",
  diningGrid:  "https://static.wixstatic.com/media/77ab1a_5f9e50fd9d0b49d2a8e7b8a00e09effc~mv2.jpeg",
  kitchenGrid: "https://static.wixstatic.com/media/77ab1a_dce5744687d442eea7464c685e2fb94e~mv2.jpeg",
  bedroomGrid: "https://static.wixstatic.com/media/77ab1a_f0410679ef15409d927d7e4879801ea6~mv2.jpeg",
};

// Gmail-safe right-aligned eyebrow (block table, no float)
const eyebrow = (label: string, dot: string, light = false) => (
  <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ marginBottom: 14 }}>
    <tr>
      <td align="right">
        <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "2.5px", textTransform: "uppercase" as const, color: light ? "#9FC0D4" : "rgba(26,26,26,0.5)", paddingRight: 8 }}>{label}</span>
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

function waOptInUrl(waBase: string, firstName: string) {
  const msg = [
    `Hi Padmini, I received your private invite about DLF Westpark Phase 2.`,
    ``,
    `I'm interested. Please reach me on the details below:`,
    `Name: ${firstName !== "there" ? firstName : ""}`,
    `Phone: `,
    `Configuration (3 BHK / 4 BHK): `,
    ``,
    `— Sent from Real Deal Housing private invite`,
  ].join("\n");
  const base = waBase.split("?")[0];
  return `${base}?text=${encodeURIComponent(msg)}`;
}

export default function DlfWestparkEmail({
  firstName      = "there",
  waUrl          = "https://wa.me/918291293889",
  youtubeUrl     = "https://www.youtube.com/@RealDealHousing",
  unsubscribeUrl = "{{unsubscribe}}",
  showProofStrip = true,
  showGardens    = true,
}: DlfWestparkEmailProps) {
  const pad = { paddingLeft: 44, paddingRight: 44 };
  const waLink = waOptInUrl(waUrl, firstName);
  const greeting = firstName && firstName !== "there" ? `Dear ${firstName},` : "Hello,";

  return (
    <Html>
      <Head>
        <meta name="color-scheme" content="light" />
        <meta name="supported-color-schemes" content="light" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </Head>
      <Body style={{ margin: 0, background: "#E7EAE7", fontFamily: SANS }}>

        {/* Preheader — hidden inbox snippet */}
        <div style={{ display: "none", fontSize: 1, lineHeight: "1px", maxHeight: 0, maxWidth: 0, opacity: 0, overflow: "hidden" }}>
          Phase 1 sold out in 7 days. Towers 6 &amp; 7 now open for EOI — pre-launch pricing, no lock-in. A private note from Padmini.&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </div>

        <Container style={{ maxWidth: 600, margin: "0 auto", background: "#fff" }}>

          {/* Top accent rule */}
          <Row>
            <Column style={{ height: 4, background: TEAL }} />
            <Column style={{ height: 4, width: 130, background: RED }} />
          </Row>

          {/* Compact masthead */}
          <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ paddingLeft: 44, paddingRight: 44, paddingTop: 22, paddingBottom: 20 }}>
            <tr>
              <td valign="bottom">
                <Img src={IMG.icon} alt="Real Deal Housing" width={38} height={34} style={{ display: "block", width: 38, height: 34 }} />
                <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 15, letterSpacing: "-0.3px", color: TEAL, lineHeight: "1", paddingTop: 7 }}>Real Deal Housing</div>
              </td>
              <td valign="bottom" align="right">
                <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase" as const, color: "rgba(26,26,26,0.45)", paddingBottom: 9 }}>
                  Private client note <span style={{ color: RED }}>&#9679;</span>
                </div>
                <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 20, letterSpacing: "-0.6px", color: TEAL, lineHeight: "1" }}>DLF Westpark</div>
                <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1.5px", textTransform: "uppercase" as const, color: "rgba(26,26,26,0.4)", paddingTop: 6 }}>
                  Phase&#8203;&nbsp;2 &middot; Andheri&#8203;&nbsp;West
                </div>
              </td>
            </tr>
          </table>

          {/* Hero image first (images are dark-mode-proof) */}
          <Img src={IMG.exterior} alt="The Westpark towers — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />

          {/* Hero statement on teal — survives Gmail dark-mode inversion */}
          <Section style={{ ...pad, paddingTop: 36, paddingBottom: 34, background: TEAL, borderTop: `3px solid ${RED}`, textAlign: "right" }}>
            {eyebrow("The Westpark · DLF & Trident Realty", RED, true)}
            <Heading as="h1" style={{ fontFamily: SANS, fontWeight: 800, fontSize: 48, lineHeight: "0.98", letterSpacing: "-1.8px", color: "#ffffff", margin: 0, textAlign: "right" }}>
              Phase&nbsp;2<br />is open.
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 15, color: "#B8C7D1", margin: "14px 0 0", textAlign: "right" }}>
              Phase&nbsp;1 sold out in seven days.
            </Text>
          </Section>

          {/* Opening note — written for people who already own in this bracket */}
          <Section style={{ ...pad, paddingTop: 30, paddingBottom: 30 }}>
            <Text style={{ fontFamily: SANS, fontWeight: 600, fontSize: 16, color: TEAL, margin: "0 0 16px" }}>
              {greeting}
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: "0 0 14px" }}>
              You already own in this bracket, so I&rsquo;ll be brief. DLF — the developer behind Gurugram and Cyber City — has entered Mumbai, and Phase&nbsp;1 was gone in a week.
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 14.5, lineHeight: "1.75", color: "rgba(26,26,26,0.8)", margin: 0 }}>
              Towers 6 &amp; 7 are now open for Expression of Interest. Whether it&rsquo;s an upgrade or a second address, an EOI holds your position at pre-launch pricing — with no lock-in, you decide later.
            </Text>
          </Section>

          {/* Proof strip */}
          {showProofStrip && (
            <Section style={{ ...pad, paddingTop: 30, paddingBottom: 30, background: TEAL, borderTop: `2px solid ${RED}` }}>
              <Row>
                {[["7 days", "Phase 1 sold out"], ["18 acres", "Landmark scale"], ["40 floors", "8 towers · 3 & 4 BHK"]].map(([n, l], i) => (
                  <Column key={i} style={{ textAlign: "center", borderLeft: i === 1 ? "1px solid #3A5566" : undefined, borderRight: i === 1 ? "1px solid #3A5566" : undefined }}>
                    <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, color: "#fff", lineHeight: "1", marginBottom: 8 }}>{n}</div>
                    <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "#9FC0D4" }}>{l}</div>
                  </Column>
                ))}
              </Row>
            </Section>
          )}

          {showGardens && (
            <Img src={IMG.gardens} alt="Landscaped gardens — artist's impression" width={600} style={{ display: "block", width: "100%", height: "auto" }} />
          )}

          {/* The residence */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 30 }}>
            {eyebrow("The residence", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, lineHeight: "1.05", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>
              Ultra-luxury<br />3 &amp; 4 BHK.
            </Heading>
            <Section style={{ marginTop: 24 }}>
              {tick(RED, "3 levels of amenities across 60,000+ sq ft")}
              {tick(RED, "25m pool · sky lounge · spa · cricket pitch")}
              {tick(RED, "Exclusive fine-dining restaurant & café")}
              {tick(RED, "Lifetime maintenance by DLF · no lock-in")}
            </Section>
          </Section>

          {/* Show apartment */}
          <Img src={IMG.livingHero} alt="Show apartment — living room" width={600} style={{ display: "block", width: "100%", height: "auto" }} />
          <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ marginTop: 3 }}>
            <tr>
              <td style={{ width: "33%", paddingRight: 2 }}><Img src={IMG.diningGrid} alt="Show apartment — dining" width={198} style={{ display: "block", width: "100%", height: "auto" }} /></td>
              <td style={{ width: "33%", paddingLeft: 1, paddingRight: 1 }}><Img src={IMG.kitchenGrid} alt="Show apartment — kitchen" width={198} style={{ display: "block", width: "100%", height: "auto" }} /></td>
              <td style={{ width: "33%", paddingLeft: 2 }}><Img src={IMG.bedroomGrid} alt="Show apartment — master bedroom" width={198} style={{ display: "block", width: "100%", height: "auto" }} /></td>
            </tr>
          </table>
          <Section style={{ ...pad, paddingTop: 10, paddingBottom: 30, textAlign: "right" }}>
            <Text style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.4)", margin: 0 }}>
              The show apartment · living · dining · kitchen · master bedroom
            </Text>
          </Section>

          {/* Master layout */}
          <Img src={IMG.masterplan} alt="The Westpark master layout — not to scale, representation only" width={600} style={{ display: "block", width: "100%", height: "auto" }} />
          <Section style={{ ...pad, paddingTop: 10, textAlign: "right" }}>
            <Text style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.4)", margin: 0 }}>
              Master layout · not to scale, representation only
            </Text>
          </Section>

          {/* Location */}
          <Section style={{ ...pad, paddingTop: 34, paddingBottom: 32 }}>
            {eyebrow("Location", BLUE)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, lineHeight: "1.08", letterSpacing: "-1px", color: TEAL, margin: 0, textAlign: "right" }}>
              Right behind<br />Lotus Petrol Pump.
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 14, color: "rgba(26,26,26,0.6)", margin: "12px 0 0", textAlign: "right" }}>
              Andheri&#8203; West · off Jogeshwari–Vikhroli Link Road
            </Text>
            <Img src={IMG.location} alt="Connectivity map — The Westpark, Andheri West" width={600} style={{ display: "block", width: "100%", height: "auto", marginTop: 22 }} />
            <Section style={{ marginTop: 22 }}>
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
              India&rsquo;s largest listed real estate developer — the firm that built Gurugram &amp; Cyber City. With Trident Realty, The Westpark marks their landmark entry into Mumbai.
            </Text>
            <Row style={{ marginTop: 26 }}>
              {[["1946", "Founded"], ["330M+", "Sq ft delivered"], ["No. 1", "Listed in India"]].map(([n, l], i) => (
                <Column key={i} style={{ textAlign: "center", borderLeft: i === 1 ? "1px solid #D6DDD8" : undefined, borderRight: i === 1 ? "1px solid #D6DDD8" : undefined }}>
                  <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: TEAL, lineHeight: "1", marginBottom: 7 }}>{n}</div>
                  <div style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", color: "rgba(26,26,26,0.45)" }}>{l}</div>
                </Column>
              ))}
            </Row>
          </Section>

          {/* CTA */}
          <Section style={{ ...pad, paddingTop: 38, paddingBottom: 38, background: TEAL }}>
            {eyebrow("EOI is open now", RED, true)}
            <Heading as="h2" style={{ fontFamily: SANS, fontWeight: 700, fontSize: 27, lineHeight: "1.1", letterSpacing: "-0.8px", color: "#fff", margin: "0 0 12px", textAlign: "right" }}>
              Shall I send you<br />the full brief?
            </Heading>
            <Text style={{ fontFamily: SANS, fontSize: 13.5, lineHeight: "1.7", color: "#B8C7D1", margin: "0 0 26px", textAlign: "right" }}>
              Price band, floor plans and brochure. One tap on WhatsApp — I&rsquo;ll call you back the same day.
            </Text>
            <table width="100%" cellPadding={0} cellSpacing={0} role="presentation">
              <tr>
                <td align="right">
                  <table cellPadding={0} cellSpacing={0} role="presentation">
                    <tr>
                      <td style={{ backgroundColor: RED, borderRadius: 2 }}>
                        <a href={waLink} style={{ display: "inline-block", fontFamily: SANS, fontWeight: 600, fontSize: 13, color: "#fff", padding: "14px 28px", textDecoration: "none" }}>
                          WhatsApp Padmini for the brief &rarr;
                        </a>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            <Text style={{ fontFamily: MONO, fontSize: 9.5, color: "#7E93A1", margin: "12px 0 0", textAlign: "right" }}>
              No commitment · No brokerage pressure
            </Text>
          </Section>

          {/* YouTube */}
          <table width="100%" cellPadding={0} cellSpacing={0} role="presentation" style={{ borderBottom: "1px solid #E3E8E5" }}>
            <tr>
              <td style={{ paddingLeft: 44, paddingRight: 44, paddingTop: 18, paddingBottom: 18 }}>
                <table width="100%" cellPadding={0} cellSpacing={0} role="presentation">
                  <tr>
                    <td style={{ fontFamily: SANS, fontWeight: 600, fontSize: 13 }}>
                      <Link href={youtubeUrl} style={{ textDecoration: "none", color: TEAL }}>▸ Watch our home tours</Link>
                    </td>
                    <td align="right" style={{ fontFamily: MONO, fontSize: 10, letterSpacing: "1px", textTransform: "uppercase" as const }}>
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
            <Text style={{ fontFamily: SANS, fontWeight: 700, fontSize: 15, margin: "10px 0 0" }}>
              <Link href="tel:+918291293889" style={{ color: TEAL, textDecoration: "none" }}>+91 82912 93889</Link>
            </Text>
          </Section>

          {/* Footer */}
          <Section style={{ ...pad, paddingTop: 26, paddingBottom: 36 }}>
            <Hr style={{ borderColor: "#E3E8E5", marginBottom: 18 }} />
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>
              Real Deal Housing Pvt. Ltd. · Goregaon&#8203; West, Mumbai
            </Text>
            <Text style={{ fontFamily: MONO, fontSize: 9.5, lineHeight: "1.7", color: "rgba(26,26,26,0.45)", textAlign: "center", margin: "0 0 5px" }}>
              MahaRERA PR1181012500079 · valid 30/06/2032
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 10, lineHeight: "1.6", color: "rgba(26,26,26,0.6)", textAlign: "center", margin: "0 0 10px" }}>
              Sent to you as a valued RDH client.{" "}
              <Link href={unsubscribeUrl} style={{ color: "rgba(26,26,26,0.6)" }}>Unsubscribe</Link>
            </Text>
            <Text style={{ fontFamily: SANS, fontSize: 9.5, fontStyle: "italic", lineHeight: "1.6", color: "rgba(26,26,26,0.4)", textAlign: "center", margin: 0 }}>
              Artist&rsquo;s impressions used where indicated. Not financial advice. Past performance of DLF projects does not guarantee future returns.
            </Text>
          </Section>

        </Container>
      </Body>
    </Html>
  );
}
