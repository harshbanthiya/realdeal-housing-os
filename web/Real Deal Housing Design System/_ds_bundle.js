/* @ds-bundle: {"format":4,"namespace":"RealDealHousingDesignSystem_83c048","components":[{"name":"ListingCard","sourcePath":"components/cards/ListingCard.jsx"},{"name":"ProjectCard","sourcePath":"components/cards/ProjectCard.jsx"},{"name":"SiteFooter","sourcePath":"components/chrome/SiteFooter.jsx"},{"name":"SiteHeader","sourcePath":"components/chrome/SiteHeader.jsx"},{"name":"StickyCta","sourcePath":"components/chrome/StickyCta.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Dot","sourcePath":"components/core/Dot.jsx"},{"name":"Mono","sourcePath":"components/core/Mono.jsx"},{"name":"PanelTitle","sourcePath":"components/core/PanelTitle.jsx"},{"name":"TONE_STYLES","sourcePath":"components/core/Pill.jsx"},{"name":"Pill","sourcePath":"components/core/Pill.jsx"},{"name":"Button","sourcePath":"components/marketing/Button.jsx"},{"name":"Eyebrow","sourcePath":"components/marketing/Eyebrow.jsx"},{"name":"PendingChip","sourcePath":"components/marketing/PendingChip.jsx"},{"name":"PlaceholderFrame","sourcePath":"components/marketing/PlaceholderFrame.jsx"},{"name":"Reveal","sourcePath":"components/marketing/Reveal.jsx"},{"name":"StatusBadge","sourcePath":"components/marketing/StatusBadge.jsx"},{"name":"CountUp","sourcePath":"components/motion/CountUp.jsx"},{"name":"Parallax","sourcePath":"components/motion/Parallax.jsx"},{"name":"RevealImage","sourcePath":"components/motion/RevealImage.jsx"},{"name":"RevealLines","sourcePath":"components/motion/RevealLines.jsx"},{"name":"Ticker","sourcePath":"components/motion/Ticker.jsx"},{"name":"CockpitContacts","sourcePath":"ui_kits/cockpit/CockpitContacts.jsx"},{"name":"CockpitPortfolio","sourcePath":"ui_kits/cockpit/CockpitPortfolio.jsx"},{"name":"CP_BUILDINGS","sourcePath":"ui_kits/cockpit/CockpitSidebar.jsx"},{"name":"CockpitSidebar","sourcePath":"ui_kits/cockpit/CockpitSidebar.jsx"},{"name":"CockpitTopbar","sourcePath":"ui_kits/cockpit/CockpitSidebar.jsx"},{"name":"MotionHome","sourcePath":"ui_kits/website-motion/MotionHome.jsx"},{"name":"RDH_PROJECTS","sourcePath":"ui_kits/website/WebsiteHome.jsx"},{"name":"RDH_LISTINGS","sourcePath":"ui_kits/website/WebsiteHome.jsx"},{"name":"WebsiteHome","sourcePath":"ui_kits/website/WebsiteHome.jsx"},{"name":"WebsiteListings","sourcePath":"ui_kits/website/WebsiteListings.jsx"},{"name":"WebsiteMobile","sourcePath":"ui_kits/website/WebsiteMobile.jsx"},{"name":"WebsiteWestpark","sourcePath":"ui_kits/website/WebsiteWestpark.jsx"}],"sourceHashes":{"components/cards/ListingCard.jsx":"94eda787df70","components/cards/ProjectCard.jsx":"d41bb81063b3","components/chrome/SiteFooter.jsx":"a4bd5a85acb8","components/chrome/SiteHeader.jsx":"8db8167cddbf","components/chrome/StickyCta.jsx":"c1249afa8c9c","components/core/Card.jsx":"b560ec840cbe","components/core/Dot.jsx":"8dee189561de","components/core/Mono.jsx":"b9d781078b54","components/core/PanelTitle.jsx":"fe73be8dc8ee","components/core/Pill.jsx":"b117af5ab86b","components/marketing/Button.jsx":"677dbb897683","components/marketing/Eyebrow.jsx":"d29013320e0e","components/marketing/PendingChip.jsx":"2390bc038f9e","components/marketing/PlaceholderFrame.jsx":"28f4da526cd3","components/marketing/Reveal.jsx":"f2bea705cb0a","components/marketing/StatusBadge.jsx":"033cd70febc0","components/motion/CountUp.jsx":"2ea605d1768b","components/motion/Parallax.jsx":"7e70eefbf9e0","components/motion/RevealImage.jsx":"4dfd6332fed0","components/motion/RevealLines.jsx":"8bc1619e14e9","components/motion/Ticker.jsx":"912151ea228c","ui_kits/cockpit/CockpitContacts.jsx":"7ec71e869460","ui_kits/cockpit/CockpitPortfolio.jsx":"9a24352f0c93","ui_kits/cockpit/CockpitSidebar.jsx":"4d8be4270b0d","ui_kits/website-motion/MotionHome.jsx":"f8fee1f02b01","ui_kits/website/WebsiteHome.jsx":"6890ac9a36b9","ui_kits/website/WebsiteListings.jsx":"081223477ffe","ui_kits/website/WebsiteMobile.jsx":"125c7588b135","ui_kits/website/WebsiteWestpark.jsx":"1e1a610c17f9"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.RealDealHousingDesignSystem_83c048 = window.RealDealHousingDesignSystem_83c048 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/chrome/SiteFooter.jsx
try { (() => {
const COLS = {
  Explore: ["Buy", "Rent", "Sell", "Projects"],
  Company: ["About", "Blog", "FAQ", "Contact"]
};

/** Teal footer — brand blurb, contacts, link columns, mono compliance line. */
function SiteFooter() {
  const linkStyle = {
    color: "var(--on-teal-75)",
    textDecoration: "none"
  };
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "var(--teal)",
      color: "var(--on-teal-90)",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "0 auto",
      maxWidth: 1152,
      padding: "56px 24px",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      gap: 40,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 384
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 600,
      letterSpacing: "-0.01em"
    }
  }, "Real Deal Housing"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "12px 0 0",
      fontSize: 14,
      lineHeight: 1.625,
      color: "var(--on-teal-65)"
    }
  }, "15 years finding premium homes across Mumbai's Western Suburbs \u2014 Goregaon, Andheri & Malad."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: "flex",
      flexDirection: "column",
      gap: 4,
      fontSize: 14,
      color: "var(--on-teal-75)"
    }
  }, /*#__PURE__*/React.createElement("div", null, "Tel: ", /*#__PURE__*/React.createElement("a", {
    href: "tel:+918291293889",
    style: linkStyle
  }, "+91 829 129 3889")), /*#__PURE__*/React.createElement("div", null, "Email: ", /*#__PURE__*/React.createElement("a", {
    href: "mailto:support@realdealhousing.com",
    style: linkStyle
  }, "support@realdealhousing.com")), /*#__PURE__*/React.createElement("div", {
    style: {
      color: "var(--on-teal-55)"
    }
  }, "Motilal Nagar, Goregaon West, Mumbai 400104"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 40,
      fontSize: 14
    }
  }, Object.entries(COLS).map(([title, links]) => /*#__PURE__*/React.createElement("div", {
    key: title
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 12,
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: "var(--on-teal-45)"
    }
  }, title), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 8
    }
  }, links.map(l => /*#__PURE__*/React.createElement("li", {
    key: l
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: linkStyle
  }, l)))))))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 48,
      display: "flex",
      justifyContent: "space-between",
      gap: 8,
      flexWrap: "wrap",
      borderTop: "1px solid var(--on-teal-border)",
      paddingTop: 24,
      fontSize: 12,
      color: "var(--on-teal-45)"
    }
  }, /*#__PURE__*/React.createElement("span", null, "\xA9 Real Deal Housing Private Limited"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)"
    }
  }, "New project facts shown as pending placeholders until verified."))));
}
Object.assign(__ds_scope, { SiteFooter });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/chrome/SiteFooter.jsx", error: String((e && e.message) || e) }); }

// components/chrome/SiteHeader.jsx
try { (() => {
const NAV = ["Buy", "Rent", "Sell", "Projects", "Blog", "About", "FAQ", "Contact"];

/** Sticky marketing-site header — blur, hairline, monogram, teal phone pill. */
function SiteHeader({
  nav = NAV,
  phone = "+91 829 129 3889",
  active
}) {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      position: "sticky",
      top: 0,
      zIndex: 40,
      borderBottom: "1px solid rgba(227,232,229,0.6)",
      background: "rgba(255,255,255,0.85)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "0 auto",
      display: "flex",
      height: 64,
      maxWidth: 1152,
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      textDecoration: "none"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      height: 28,
      width: 28,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 9999,
      background: "var(--teal)",
      color: "#fff",
      fontSize: 11,
      fontWeight: 700
    }
  }, "RDH"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 15,
      fontWeight: 600,
      letterSpacing: "-0.01em",
      color: "var(--teal)"
    }
  }, "Real Deal Housing")), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 24
    }
  }, nav.map(item => /*#__PURE__*/React.createElement("a", {
    key: item,
    href: "#",
    style: {
      fontSize: 13.5,
      fontWeight: 500,
      textDecoration: "none",
      color: item === active ? "var(--teal)" : "var(--ink-65)",
      transition: "color .15s"
    },
    onMouseEnter: e => e.currentTarget.style.color = "var(--teal)",
    onMouseLeave: e => e.currentTarget.style.color = item === active ? "var(--teal)" : "var(--ink-65)"
  }, item))), /*#__PURE__*/React.createElement("a", {
    href: "tel:+918291293889",
    style: {
      borderRadius: 9999,
      background: "var(--teal)",
      padding: "8px 16px",
      fontSize: 13,
      fontWeight: 600,
      color: "#fff",
      textDecoration: "none",
      transition: "opacity .15s",
      whiteSpace: "nowrap"
    },
    onMouseEnter: e => e.currentTarget.style.opacity = "0.9",
    onMouseLeave: e => e.currentTarget.style.opacity = "1"
  }, phone)));
}
Object.assign(__ds_scope, { SiteHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/chrome/SiteHeader.jsx", error: String((e && e.message) || e) }); }

// components/chrome/StickyCta.jsx
try { (() => {
/** Mobile two-segment sticky bottom CTA — teal "Request details" | warm "WhatsApp". */
function StickyCta({
  hidden = false,
  onRequest,
  whatsappHref = "#"
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      insetInline: 0,
      bottom: 0,
      zIndex: 40,
      display: "flex",
      fontFamily: "var(--font-sans)",
      transform: hidden ? "translateY(100%)" : "translateY(0)",
      transition: "transform .3s"
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#enquiry",
    onClick: onRequest,
    style: {
      flex: 1,
      background: "var(--teal)",
      padding: "16px 0",
      textAlign: "center",
      fontSize: 14,
      fontWeight: 600,
      color: "#fff",
      textDecoration: "none"
    }
  }, "Request details"), /*#__PURE__*/React.createElement("a", {
    href: whatsappHref,
    style: {
      flex: 1,
      background: "var(--warm)",
      padding: "16px 0",
      textAlign: "center",
      fontSize: 14,
      fontWeight: 600,
      color: "#fff",
      textDecoration: "none"
    }
  }, "WhatsApp"));
}
Object.assign(__ds_scope, { StickyCta });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/chrome/StickyCta.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function Card({
  children,
  radius = 12,
  padding,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: radius,
      border: "1px solid var(--mist-deep)",
      background: "#fff",
      padding,
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Dot.jsx
try { (() => {
const TONES = {
  ready: "var(--teal)",
  blocked: "var(--warm)",
  review: "var(--amber)",
  active: "var(--accent)",
  neutral: "var(--ink-30)"
};
function Dot({
  tone = "neutral",
  style
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-block",
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: TONES[tone],
      ...style
    }
  });
}
Object.assign(__ds_scope, { Dot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Dot.jsx", error: String((e && e.message) || e) }); }

// components/core/Mono.jsx
try { (() => {
function Mono({
  children,
  size = 12,
  style,
  title
}) {
  return /*#__PURE__*/React.createElement("span", {
    title: title,
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: size,
      color: "var(--ink-55)",
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Mono });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Mono.jsx", error: String((e && e.message) || e) }); }

// components/core/PanelTitle.jsx
try { (() => {
function PanelTitle({
  children,
  hint
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16,
      display: "flex",
      alignItems: "baseline",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontFamily: "var(--font-sans)",
      fontSize: 15,
      fontWeight: 600,
      letterSpacing: "-0.01em",
      color: "var(--teal)"
    }
  }, children), hint && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      color: "var(--ink-40)"
    }
  }, hint));
}
Object.assign(__ds_scope, { PanelTitle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/PanelTitle.jsx", error: String((e && e.message) || e) }); }

// components/core/Pill.jsx
try { (() => {
const TONE_STYLES = {
  ready: {
    background: "var(--tone-ready-bg)",
    color: "var(--tone-ready-fg)"
  },
  blocked: {
    background: "var(--tone-blocked-bg)",
    color: "var(--tone-blocked-fg)"
  },
  review: {
    background: "var(--tone-review-bg)",
    color: "var(--tone-review-fg)"
  },
  active: {
    background: "var(--tone-active-bg)",
    color: "var(--tone-active-fg)"
  },
  neutral: {
    background: "var(--tone-neutral-bg)",
    color: "var(--tone-neutral-fg)"
  }
};
function Pill({
  tone = "neutral",
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      borderRadius: 9999,
      padding: "2px 10px",
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      fontWeight: 500,
      ...TONE_STYLES[tone],
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { TONE_STYLES, Pill });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Pill.jsx", error: String((e && e.message) || e) }); }

// components/marketing/Button.jsx
try { (() => {
const VARIANTS = {
  primary: {
    background: "var(--teal)",
    color: "#fff",
    border: "1px solid var(--teal)"
  },
  outline: {
    background: "transparent",
    color: "var(--teal)",
    border: "1px solid var(--mist-deep)"
  },
  warm: {
    background: "var(--warm)",
    color: "#fff",
    border: "1px solid var(--warm)"
  }
};

/** Pill CTA — the recurring link-button pattern from the site source. */
function Button({
  variant = "primary",
  size = "md",
  href = "#",
  onClick,
  children,
  style
}) {
  const pad = size === "sm" ? "8px 16px" : "14px 24px";
  const font = size === "sm" ? 12 : 14;
  const v = VARIANTS[variant];
  return /*#__PURE__*/React.createElement("a", {
    href: href,
    onClick: onClick,
    onMouseEnter: e => {
      if (variant === "outline") e.currentTarget.style.background = "var(--mist)";else e.currentTarget.style.opacity = "0.9";
    },
    onMouseLeave: e => {
      if (variant === "outline") e.currentTarget.style.background = "transparent";else e.currentTarget.style.opacity = "1";
    },
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      whiteSpace: "nowrap",
      borderRadius: 9999,
      padding: pad,
      textDecoration: "none",
      fontFamily: "var(--font-sans)",
      fontSize: font,
      fontWeight: 600,
      transition: "opacity .15s, background .15s",
      cursor: "pointer",
      ...v,
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/Button.jsx", error: String((e && e.message) || e) }); }

// components/marketing/Eyebrow.jsx
try { (() => {
/** Numbered section eyebrow — mono warm numeral, 32px hairline, tracked uppercase label. */
function Eyebrow({
  n,
  label,
  onDark = false
}) {
  return /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 20px",
      display: "flex",
      alignItems: "center",
      gap: 12,
      fontFamily: "var(--font-sans)",
      fontSize: 12,
      fontWeight: 600,
      textTransform: "uppercase",
      letterSpacing: "0.18em",
      color: onDark ? "var(--on-teal-45)" : "var(--ink-45)"
    }
  }, n && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      color: "var(--warm)"
    }
  }, n), /*#__PURE__*/React.createElement("span", {
    style: {
      height: 1,
      width: 32,
      background: onDark ? "rgba(255,255,255,.25)" : "var(--mist-deep)"
    }
  }), label);
}
Object.assign(__ds_scope, { Eyebrow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/Eyebrow.jsx", error: String((e && e.message) || e) }); }

// components/marketing/PendingChip.jsx
try { (() => {
/** Honest "pending verification" chip — mono, mist bg, warm tick. Never fabricate a value. */
function PendingChip({
  token
}) {
  return /*#__PURE__*/React.createElement("span", {
    title: "Pending verification \u2014 not yet confirmed",
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      borderRadius: 4,
      background: "var(--mist)",
      padding: "2px 6px",
      fontFamily: "var(--font-mono)",
      fontSize: "0.78em",
      fontWeight: 500,
      letterSpacing: "-0.01em",
      color: "rgba(31,61,77,0.8)",
      verticalAlign: "baseline"
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": true,
    style: {
      display: "inline-block",
      height: 6,
      width: 6,
      borderRadius: 9999,
      background: "rgba(194,73,61,0.7)"
    }
  }), token);
}
Object.assign(__ds_scope, { PendingChip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/PendingChip.jsx", error: String((e && e.message) || e) }); }

// components/marketing/PlaceholderFrame.jsx
try { (() => {
/** Honest image placeholder — dashed mist frame with mono label; or a real image with fixed ratio. */
function PlaceholderFrame({
  ratio = "4/3",
  label,
  src,
  alt = "",
  radius = 12,
  style,
  children
}) {
  if (src) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        aspectRatio: ratio,
        borderRadius: radius,
        overflow: "hidden",
        position: "relative",
        ...style
      }
    }, /*#__PURE__*/React.createElement("img", {
      src: src,
      alt: alt,
      style: {
        width: "100%",
        height: "100%",
        objectFit: "cover",
        display: "block"
      }
    }), children);
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      aspectRatio: ratio,
      borderRadius: radius,
      border: "1px dashed var(--mist-deep)",
      background: "rgba(238,241,239,0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      position: "relative",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: "var(--ink-40)",
      ...style
    }
  }, label, children);
}
Object.assign(__ds_scope, { PlaceholderFrame });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/PlaceholderFrame.jsx", error: String((e && e.message) || e) }); }

// components/cards/ListingCard.jsx
try { (() => {
/** Listing card — 4/3 image well with type badge, teal title, meta line, bold price. */
function ListingCard({
  title,
  location,
  config,
  sqft,
  price,
  type = "sale",
  src
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      height: "100%",
      borderRadius: 16,
      border: "1px solid var(--mist-deep)",
      background: "#fff",
      padding: 20,
      fontFamily: "var(--font-sans)",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "4/3",
    radius: 8,
    src: src
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      left: 12,
      top: 12,
      borderRadius: 9999,
      background: "var(--teal)",
      color: "#fff",
      padding: "4px 10px",
      fontFamily: "var(--font-mono)",
      fontSize: 10,
      fontWeight: 600,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      whiteSpace: "nowrap"
    }
  }, type === "rent" ? "For rent" : "For sale")), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: "16px 0 0",
      fontSize: 16,
      fontWeight: 600,
      lineHeight: 1.375,
      color: "var(--teal)"
    }
  }, title), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "4px 0 0",
      fontSize: 12,
      color: "var(--ink-50)"
    }
  }, location, " \xB7 ", config, sqft && sqft !== "—" ? ` · ${sqft} sqft` : ""), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "12px 0 0",
      fontSize: 18,
      fontWeight: 700,
      color: "var(--teal)"
    }
  }, price));
}
Object.assign(__ds_scope, { ListingCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/ListingCard.jsx", error: String((e && e.message) || e) }); }

// components/cards/ProjectCard.jsx
try { (() => {
const {
  useState
} = React;
/** Featured project card — 16/9 image, hover mist wash, arrow affordance. */
function ProjectCard({
  name,
  location,
  meta,
  href = "#",
  src
}) {
  const [hover, setHover] = useState(false);
  return /*#__PURE__*/React.createElement("a", {
    href: href,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: "block",
      borderRadius: 16,
      border: "1px solid var(--mist-deep)",
      padding: 28,
      textDecoration: "none",
      fontFamily: "var(--font-sans)",
      background: hover ? "rgba(238,241,239,0.4)" : "transparent",
      transition: "background .15s",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "16/9",
    radius: 12,
    src: src
  }), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: "20px 0 0",
      fontSize: 20,
      fontWeight: 700,
      color: "var(--teal)"
    }
  }, name), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "4px 0 0",
      fontSize: 14,
      color: "var(--ink-55)"
    }
  }, location, " \xB7 ", meta), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-block",
      marginTop: 16,
      fontSize: 14,
      fontWeight: 600,
      color: "var(--teal)",
      textDecoration: hover ? "underline" : "none",
      textUnderlineOffset: 4
    }
  }, "View project \u2192"));
}
Object.assign(__ds_scope, { ProjectCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/ProjectCard.jsx", error: String((e && e.message) || e) }); }

// components/marketing/Reveal.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
/**
 * Scroll reveal — fade + 26px rise, once, house ease. Port of the framer-motion
 * <Reveal/> from the codebase (duration .75s, ease [0.22,1,0.36,1], margin -80px).
 */
function Reveal({
  children,
  delay = 0,
  style
}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setVisible(true);
        io.disconnect();
      }
    }, {
      rootMargin: "-80px"
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    style: {
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(26px)",
      transition: `opacity .75s cubic-bezier(.22,1,.36,1) ${delay}s, transform .75s cubic-bezier(.22,1,.36,1) ${delay}s`,
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Reveal });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/Reveal.jsx", error: String((e && e.message) || e) }); }

// components/marketing/StatusBadge.jsx
try { (() => {
const MAP = {
  operator_confirmed: {
    label: "Confirmed",
    background: "var(--tone-ready-bg)",
    color: "var(--tone-ready-fg)"
  },
  pending_review: {
    label: "Under review",
    background: "var(--tone-blocked-bg)",
    color: "var(--tone-blocked-fg)"
  },
  pending: {
    label: "Pending",
    background: "var(--mist)",
    color: "var(--ink-50)"
  }
};

/** Verified-facts-ledger status badge. */
function StatusBadge({
  status = "pending"
}) {
  const s = MAP[status] || MAP.pending;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      borderRadius: 9999,
      padding: "4px 10px",
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      fontWeight: 500,
      background: s.background,
      color: s.color
    }
  }, s.label);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/marketing/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/motion/CountUp.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
/** Count-up stat — animates 0 → value when scrolled into view (1.4s, expo ease). */
function CountUp({
  value,
  prefix = "",
  suffix = "",
  duration = 1.4,
  style
}) {
  const ref = useRef(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(value);
      return;
    }
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const step = t => {
        const p = Math.min(1, (t - t0) / (duration * 1000));
        const eased = 1 - Math.pow(1 - p, 4);
        setN(Math.round(value * eased));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, {
      rootMargin: "-40px"
    });
    io.observe(el);
    return () => io.disconnect();
  }, [value, duration]);
  return /*#__PURE__*/React.createElement("span", {
    ref: ref,
    style: {
      fontVariantNumeric: "tabular-nums",
      ...style
    }
  }, prefix, n, suffix);
}
Object.assign(__ds_scope, { CountUp });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/motion/CountUp.jsx", error: String((e && e.message) || e) }); }

// components/motion/Parallax.jsx
try { (() => {
const {
  useEffect,
  useRef
} = React;
/** Scroll parallax — child drifts vertically against scroll. speed 0.05–0.2 feels right. */
function Parallax({
  speed = 0.12,
  children,
  style
}) {
  const outer = useRef(null);
  const inner = useRef(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const tick = () => {
      const o = outer.current,
        n = inner.current;
      if (o && n) {
        const r = o.getBoundingClientRect();
        const mid = r.top + r.height / 2 - window.innerHeight / 2;
        n.style.transform = `translateY(${(-mid * speed).toFixed(1)}px)`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [speed]);
  return /*#__PURE__*/React.createElement("div", {
    ref: outer,
    style: {
      overflow: "hidden",
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: inner,
    style: {
      willChange: "transform"
    }
  }, children));
}
Object.assign(__ds_scope, { Parallax });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/motion/Parallax.jsx", error: String((e && e.message) || e) }); }

// components/motion/RevealImage.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
/** Image clip reveal — container unclips upward while the image settles from 1.12× to 1. */
function RevealImage({
  src,
  alt = "",
  ratio = "16/9",
  radius = 16,
  delay = 0,
  style
}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        setVisible(true);
        io.disconnect();
      }
    }, {
      rootMargin: "-60px"
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    className: `rdh-clip${visible ? " is-visible" : ""}`,
    style: {
      aspectRatio: ratio,
      borderRadius: radius,
      overflow: "hidden",
      transitionDelay: `${delay}s`,
      ...style
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: src,
    alt: alt,
    style: {
      width: "100%",
      height: "100%",
      objectFit: "cover",
      display: "block",
      transitionDelay: `${delay}s`
    }
  }));
}
Object.assign(__ds_scope, { RevealImage });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/motion/RevealImage.jsx", error: String((e && e.message) || e) }); }

// components/motion/RevealLines.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
/** Masked line-by-line headline reveal (Halston-style). Pass lines as an array. */
function RevealLines({
  lines = [],
  as = "h2",
  delay = 0,
  style,
  lineStyle
}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        setVisible(true);
        io.disconnect();
      }
    }, {
      rootMargin: "-60px"
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const Tag = as;
  return /*#__PURE__*/React.createElement(Tag, {
    ref: ref,
    className: visible ? "is-visible" : "",
    style: {
      margin: 0,
      ...style
    }
  }, lines.map((line, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: "rdh-line",
    style: lineStyle
  }, /*#__PURE__*/React.createElement("span", {
    className: "rdh-line-inner",
    style: {
      transitionDelay: `${delay + i * 0.09}s`
    }
  }, line))));
}
Object.assign(__ds_scope, { RevealLines });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/motion/RevealLines.jsx", error: String((e && e.message) || e) }); }

// components/motion/Ticker.jsx
try { (() => {
/** Continuous marquee strip — building names with warm mid-dot separators. */
function Ticker({
  items = [],
  speed = 28,
  style,
  itemStyle
}) {
  const row = (key, hidden) => /*#__PURE__*/React.createElement("div", {
    key: key,
    "aria-hidden": hidden || undefined,
    style: {
      display: "flex",
      flexShrink: 0,
      alignItems: "center",
      animation: `rdh-ticker ${speed}s linear infinite`
    }
  }, items.map((it, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      display: "flex",
      alignItems: "center",
      whiteSpace: "nowrap"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: itemStyle
  }, it), /*#__PURE__*/React.createElement("span", {
    style: {
      margin: "0 28px",
      color: "var(--warm)"
    }
  }, "\xB7"))));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      overflow: "hidden",
      ...style
    }
  }, /*#__PURE__*/React.createElement("style", null, `@keyframes rdh-ticker { from { transform: translateX(0); } to { transform: translateX(-100%); } }
        @media (prefers-reduced-motion: reduce) { [data-rdh-ticker] > div { animation: none !important; } }`), /*#__PURE__*/React.createElement("div", {
    "data-rdh-ticker": true,
    style: {
      display: "flex"
    }
  }, row("a", false), row("b", true)));
}
Object.assign(__ds_scope, { Ticker });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/motion/Ticker.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cockpit/CockpitContacts.jsx
try { (() => {
const QUEUES = [{
  label: "Merge candidates",
  approved: 4,
  pending: 7
}, {
  label: "Duplicates",
  approved: 12,
  pending: 2
}, {
  label: "Property hints",
  approved: 3,
  pending: 5
}, {
  label: "Inventory matches",
  approved: 9,
  pending: 0
}, {
  label: "Lead requirements",
  approved: 1,
  pending: 3
}];
const BATCHES = [{
  label: "Imperial Heights unit data",
  real: true,
  rows: 214,
  pending: 7,
  approved: 41
}, {
  label: "Kalpataru Radiance owners",
  real: true,
  rows: 148,
  pending: 4,
  approved: 96
}, {
  label: "Oberoi Esquire data",
  real: false,
  rows: 62,
  pending: 0,
  approved: 0
}];
const MERGES = [{
  id: "RVW-2211",
  a: "Rakesh Sharma · +91 98200 11223",
  b: "R. Sharma · rakesh.s@gmail.com",
  building: "Imperial Heights",
  confidence: "0.92"
}, {
  id: "RVW-2214",
  a: "Meena Kapoor · +91 98333 40911",
  b: "Meena K · +91 98333 40911",
  building: "Kalpataru Radiance",
  confidence: "0.88"
}];
function Stage({
  n,
  label,
  tone,
  sub
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: 8,
      border: "1px solid var(--mist-deep)",
      padding: 12,
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 22,
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, n), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 2,
      fontSize: 12,
      color: "var(--ink-65)"
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 6
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: tone
  }, sub || "—")));
}
function CockpitContacts() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "28px 24px",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 24,
      fontWeight: 600,
      letterSpacing: "-0.02em",
      color: "var(--teal)"
    }
  }, "Contacts"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "4px 0 0",
      fontSize: 14,
      color: "var(--ink-55)"
    }
  }, "137 cleaned canonical \xB7 17 awaiting review across 2 real import batches")), /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20,
    style: {
      marginBottom: 28
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "programmatic pipeline \xB7 review-gated"
  }, "Cleanup funnel"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(Stage, {
    n: 424,
    label: "Imported rows",
    tone: "neutral",
    sub: "lossless"
  }), /*#__PURE__*/React.createElement(Stage, {
    n: 17,
    label: "In review",
    tone: "review",
    sub: "needs your decision"
  }), /*#__PURE__*/React.createElement(Stage, {
    n: 137,
    label: "Approved",
    tone: "active",
    sub: "ready to merge"
  }), /*#__PURE__*/React.createElement(Stage, {
    n: 137,
    label: "Canonical",
    tone: "ready",
    sub: "cleaned contacts"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.7fr 1fr",
      gap: 24
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "7 pending"
  }, "Merge candidates"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, MERGES.map(m => /*#__PURE__*/React.createElement(__ds_scope.Card, {
    key: m.id,
    padding: 16
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 11,
    style: {
      color: "var(--warm)"
    }
  }, m.id), /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "review"
  }, "confidence ", m.confidence)), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10,
      display: "grid",
      gridTemplateColumns: "1fr auto 1fr",
      alignItems: "center",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: 8,
      background: "var(--mist)",
      padding: "10px 12px",
      fontSize: 13,
      color: "rgba(26,26,26,0.8)"
    }
  }, m.a), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: "var(--ink-40)"
    }
  }, "\u2194"), /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: 8,
      background: "var(--mist)",
      padding: "10px 12px",
      fontSize: 13,
      color: "rgba(26,26,26,0.8)"
    }
  }, m.b)), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 12,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: "var(--ink-45)"
    }
  }, m.building), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      borderRadius: 9999,
      border: "1px solid var(--mist-deep)",
      background: "transparent",
      padding: "6px 14px",
      fontFamily: "var(--font-sans)",
      fontSize: 12,
      fontWeight: 600,
      color: "var(--teal)",
      cursor: "pointer"
    }
  }, "Skip"), /*#__PURE__*/React.createElement("button", {
    style: {
      borderRadius: 9999,
      border: "1px solid var(--teal)",
      background: "var(--teal)",
      padding: "6px 14px",
      fontFamily: "var(--font-sans)",
      fontSize: 12,
      fontWeight: 600,
      color: "#fff",
      cursor: "pointer"
    }
  }, "Preview approve"))))), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      color: "var(--ink-40)"
    }
  }, "\"Preview approve\" runs the guarded script in dry-run (no writes). Applying stays disabled until enabled."))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 24
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "46 items"
  }, "Review queues"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 10
    }
  }, QUEUES.map((g, i) => /*#__PURE__*/React.createElement("li", {
    key: g.label,
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      borderBottom: i < QUEUES.length - 1 ? "1px solid var(--mist)" : "none",
      paddingBottom: i < QUEUES.length - 1 ? 10 : 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      color: "rgba(26,26,26,0.75)"
    }
  }, g.label), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8
    }
  }, g.approved > 0 && /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "ready"
  }, g.approved, " ok"), /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: g.pending > 0 ? "review" : "neutral"
  }, g.pending, " pending")))))), /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "2 real"
  }, "Import batches"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, BATCHES.map(b => /*#__PURE__*/React.createElement("li", {
    key: b.label,
    style: {
      borderRadius: 8,
      border: "1px solid var(--mist-deep)",
      padding: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
      fontSize: 13,
      fontWeight: 500,
      color: "var(--teal)"
    }
  }, b.label), b.real ? /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "active"
  }, "real") : /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "neutral"
  }, "test")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 8,
      textAlign: "center",
      fontSize: 11
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, b.rows), /*#__PURE__*/React.createElement("div", {
    style: {
      color: "var(--ink-40)"
    }
  }, "rows")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 600,
      color: "var(--amber)"
    }
  }, b.pending), /*#__PURE__*/React.createElement("div", {
    style: {
      color: "var(--ink-40)"
    }
  }, "pending")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, b.approved), /*#__PURE__*/React.createElement("div", {
    style: {
      color: "var(--ink-40)"
    }
  }, "approved"))))))))));
}
Object.assign(__ds_scope, { CockpitContacts });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cockpit/CockpitContacts.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cockpit/CockpitSidebar.jsx
try { (() => {
const CP_BUILDINGS = [{
  slug: "dlf-westpark",
  name: "DLF Westpark",
  location: "Andheri West",
  mode: "launch",
  launchInDays: 58,
  stats: {
    owners: 4,
    tenants: 0,
    leads: 12,
    warm: 3,
    listings: 2,
    openReviews: 5,
    blockers: 3
  },
  seoRank: "n/a"
}, {
  slug: "imperial-heights",
  name: "Imperial Heights",
  location: "Goregaon West",
  mode: "active",
  stats: {
    owners: 212,
    tenants: 64,
    leads: 31,
    warm: 9,
    listings: 6,
    openReviews: 2,
    blockers: 0
  },
  seoRank: "#3"
}, {
  slug: "kalpataru-radiance",
  name: "Kalpataru Radiance",
  location: "Goregaon West",
  mode: "active",
  stats: {
    owners: 148,
    tenants: 41,
    leads: 18,
    warm: 4,
    listings: 4,
    openReviews: 0,
    blockers: 0
  },
  seoRank: "#5"
}, {
  slug: "ekta-tripolis",
  name: "Ekta Tripolis",
  location: "Goregaon West",
  mode: "prospecting",
  stats: {
    owners: 96,
    tenants: 22,
    leads: 7,
    warm: 1,
    listings: 2,
    openReviews: 1,
    blockers: 0
  },
  seoRank: "#8"
}];
const MODE_TONE = {
  launch: "blocked",
  active: "ready",
  prospecting: "review",
  post_launch: "neutral"
};
function CockpitSidebar({
  screen,
  go
}) {
  const item = (key, label) => /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => {
      e.preventDefault();
      go(key);
    },
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      borderRadius: 8,
      padding: "8px 12px",
      fontSize: 14,
      fontWeight: 500,
      textDecoration: "none",
      marginTop: 2,
      background: screen === key ? "#fff" : "transparent",
      boxShadow: screen === key ? "0 0 0 1px var(--mist-deep)" : "none",
      color: screen === key ? "var(--teal)" : "var(--ink-65)"
    }
  }, label);
  return /*#__PURE__*/React.createElement("aside", {
    style: {
      display: "flex",
      width: 240,
      flexShrink: 0,
      flexDirection: "column",
      borderRight: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.3)",
      fontFamily: "var(--font-sans)",
      height: "100%",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      height: 56,
      alignItems: "center",
      gap: 8,
      borderBottom: "1px solid var(--mist-deep)",
      padding: "0 20px"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      height: 24,
      width: 24,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 6,
      background: "var(--teal)",
      color: "#fff",
      fontSize: 10,
      fontWeight: 700
    }
  }, "RDH"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      letterSpacing: "-0.01em",
      color: "var(--teal)"
    }
  }, "Operations cockpit")), /*#__PURE__*/React.createElement("nav", {
    style: {
      flex: 1,
      overflowY: "auto",
      padding: "16px 12px"
    }
  }, item("portfolio", "Portfolio"), item("contacts", "Contacts"), item("audiences", "Audiences"), item("outreach", "Outreach"), item("media", "Media"), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "20px 0 8px",
      padding: "0 12px",
      fontFamily: "var(--font-mono)",
      fontSize: 10,
      textTransform: "uppercase",
      letterSpacing: "0.15em",
      color: "var(--ink-40)"
    }
  }, "Buildings \xB7 ", CP_BUILDINGS.length), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 2
    }
  }, CP_BUILDINGS.map(b => /*#__PURE__*/React.createElement("li", {
    key: b.slug
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => e.preventDefault(),
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      borderRadius: 8,
      padding: "8px 12px",
      fontSize: 14,
      color: "var(--ink-65)",
      textDecoration: "none"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Dot, {
    tone: MODE_TONE[b.mode]
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap"
    }
  }, b.name), b.stats.blockers > 0 && /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 10,
    style: {
      color: "var(--warm)"
    }
  }, b.stats.blockers)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      padding: 12,
      fontSize: 14
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => e.preventDefault(),
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      borderRadius: 8,
      padding: "8px 12px",
      color: "var(--ink-55)",
      textDecoration: "none"
    }
  }, "\u2197 Marketing site"), /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => e.preventDefault(),
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      borderRadius: 8,
      padding: "8px 12px",
      color: "var(--ink-55)",
      textDecoration: "none"
    }
  }, "\u23FB Sign out")));
}
function CockpitTopbar() {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      display: "flex",
      height: 56,
      flexShrink: 0,
      alignItems: "center",
      justifyContent: "space-between",
      borderBottom: "1px solid var(--mist-deep)",
      padding: "0 24px",
      fontFamily: "var(--font-sans)",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      fontSize: 14,
      color: "var(--ink-50)"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 12
  }, "\u2318K"), /*#__PURE__*/React.createElement("span", null, "Search buildings, leads, reviews\u2026")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: "var(--ink-50)"
    }
  }, "DLF Westpark launch"), /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "blocked"
  }, "3 blockers \xB7 go-live locked")));
}
Object.assign(__ds_scope, { CP_BUILDINGS, CockpitSidebar, CockpitTopbar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cockpit/CockpitSidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/cockpit/CockpitPortfolio.jsx
try { (() => {
const MODE_LABEL = {
  launch: "Launch",
  active: "Active",
  prospecting: "Prospecting",
  post_launch: "Post-launch"
};
const MODE_TONE = {
  launch: "blocked",
  active: "ready",
  prospecting: "review",
  post_launch: "neutral"
};
const STREAMS = [{
  label: "Contacts & permissions",
  tone: "ready",
  state: "ready",
  passed: 6,
  total: 6
}, {
  label: "Campaign copy",
  tone: "review",
  state: "in review",
  passed: 3,
  total: 5
}, {
  label: "Wix landing build",
  tone: "active",
  state: "building",
  passed: 4,
  total: 9
}, {
  label: "Tracking & consent",
  tone: "blocked",
  state: "blocked",
  passed: 0,
  total: 3
}];
const REVIEWS = [{
  title: "Merge candidate — R. Sharma ↔ Rakesh S.",
  building: "Imperial Heights",
  domain: "contacts",
  age: "2h",
  tone: "review"
}, {
  title: "RERA snapshot parse — Tower 6",
  building: "DLF Westpark",
  domain: "facts",
  age: "5h",
  tone: "blocked"
}, {
  title: "Unit audit rows 41–58",
  building: "Kalpataru Radiance",
  domain: "inventory",
  age: "1d",
  tone: "review"
}];
const AGENTS = [{
  action: "Normalized 214 contact rows",
  agent: "normalize_contact_file",
  building: "Ekta Tripolis",
  status: "ready"
}, {
  action: "Drafted drip-1 email variant B",
  agent: "content_draft",
  building: "DLF Westpark",
  status: "active"
}, {
  action: "Profiled Archive_2 workbook",
  agent: "profile_archive",
  building: "Imperial Heights",
  status: "neutral"
}];
const BLOCKERS = [{
  id: "BLK-071",
  statement: "Consent evidence missing for 2 contact segments",
  building: "DLF Westpark",
  openFor: "3d"
}, {
  id: "BLK-074",
  statement: "RERA registration number unverified",
  building: "DLF Westpark",
  openFor: "6d"
}];
function Stat({
  n,
  label,
  sub,
  tone = "neutral"
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 600,
      color: tone === "review" ? "var(--amber)" : "var(--teal)"
    }
  }, n), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: "var(--ink-40)"
    }
  }, label), sub && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10,
      color: "rgba(31,61,77,0.6)"
    }
  }, sub));
}
function CockpitPortfolio() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "28px 24px",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 24,
      fontWeight: 600,
      letterSpacing: "-0.02em",
      color: "var(--teal)"
    }
  }, "Portfolio"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "4px 0 0",
      fontSize: 14,
      color: "var(--ink-55)"
    }
  }, __ds_scope.CP_BUILDINGS.length, " buildings \xB7 1 in launch \xB7 ", REVIEWS.length, " items awaiting review")), /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20,
    style: {
      marginBottom: 28
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "DLF Westpark \xB7 T-58d"
  }, "Launch readiness"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 12
    }
  }, STREAMS.map(s => /*#__PURE__*/React.createElement("div", {
    key: s.label,
    style: {
      borderRadius: 8,
      border: "1px solid var(--mist-deep)",
      padding: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: "var(--ink-65)"
    }
  }, s.label), /*#__PURE__*/React.createElement(__ds_scope.Dot, {
    tone: s.tone
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: s.tone
  }, s.state), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10,
      color: "var(--ink-40)"
    }
  }, s.passed, "/", s.total)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.8fr 1fr",
      gap: 24
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "click to open workspace"
  }, "Buildings"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 16
    }
  }, __ds_scope.CP_BUILDINGS.map(b => /*#__PURE__*/React.createElement(__ds_scope.Card, {
    key: b.slug,
    padding: 20,
    style: {
      height: "100%",
      boxSizing: "border-box",
      cursor: "pointer"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, b.name), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 2,
      fontSize: 12,
      color: "var(--ink-50)"
    }
  }, b.location)), /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: MODE_TONE[b.mode]
  }, MODE_LABEL[b.mode])), b.launchInDays && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      color: "var(--warm)"
    }
  }, "launch in ", b.launchInDays, "d"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16,
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 8,
      borderTop: "1px solid var(--mist)",
      paddingTop: 12
    }
  }, /*#__PURE__*/React.createElement(Stat, {
    n: b.stats.owners + b.stats.tenants,
    label: "people"
  }), /*#__PURE__*/React.createElement(Stat, {
    n: b.stats.leads,
    label: "leads",
    sub: `${b.stats.warm} warm`
  }), /*#__PURE__*/React.createElement(Stat, {
    n: b.stats.listings,
    label: "listings"
  }), /*#__PURE__*/React.createElement(Stat, {
    n: b.stats.openReviews,
    label: "reviews",
    tone: b.stats.openReviews > 0 ? "review" : "neutral"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 12,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 11
  }, "SEO ", b.seoRank), b.stats.blockers > 0 ? /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "blocked"
  }, b.stats.blockers, " blockers") : /*#__PURE__*/React.createElement(__ds_scope.Pill, {
    tone: "ready"
  }, "clear")))))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 24
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: `${REVIEWS.length}`
  }, "Needs review"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, REVIEWS.map((r, i) => /*#__PURE__*/React.createElement("li", {
    key: i,
    style: {
      display: "flex",
      alignItems: "flex-start",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Dot, {
    tone: r.tone,
    style: {
      marginTop: 4
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0,
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
      fontSize: 14,
      color: "rgba(26,26,26,0.8)"
    }
  }, r.title), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 2,
      fontSize: 11,
      color: "var(--ink-45)"
    }
  }, r.building, " \xB7 ", /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 11
  }, r.domain), " \xB7 ", r.age)))))), /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: "last 24h"
  }, "Agents"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, AGENTS.map((a, i) => /*#__PURE__*/React.createElement("li", {
    key: i,
    style: {
      display: "flex",
      alignItems: "flex-start",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Dot, {
    tone: a.status,
    style: {
      marginTop: 4
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0,
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "rgba(26,26,26,0.8)"
    }
  }, a.action), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 2,
      fontSize: 11,
      color: "var(--ink-45)"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 11
  }, a.agent), " \xB7 ", a.building)))))), /*#__PURE__*/React.createElement(__ds_scope.Card, {
    padding: 20
  }, /*#__PURE__*/React.createElement(__ds_scope.PanelTitle, {
    hint: `${BLOCKERS.length} open`
  }, "Blockers"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, BLOCKERS.map(b => /*#__PURE__*/React.createElement("li", {
    key: b.id,
    style: {
      borderRadius: 8,
      border: "1px solid var(--mist-deep)",
      padding: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Mono, {
    size: 11,
    style: {
      color: "var(--warm)"
    }
  }, b.id), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: "var(--ink-45)"
    }
  }, "open ", b.openFor)), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 4,
      fontSize: 14,
      color: "rgba(26,26,26,0.8)"
    }
  }, b.statement), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 2,
      fontSize: 11,
      color: "var(--ink-45)"
    }
  }, b.building))))))));
}
Object.assign(__ds_scope, { CockpitPortfolio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/cockpit/CockpitPortfolio.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website-motion/MotionHome.jsx
try { (() => {
const {
  useEffect,
  useState
} = React;
const wrap = {
  margin: "0 auto",
  maxWidth: 1152,
  padding: "0 24px",
  boxSizing: "border-box"
};
const SLIDES = [{
  src: "../../assets/imagery/westpark-exterior.jpg",
  label: "DLF Westpark · Andheri West"
}, {
  src: "../../assets/imagery/westpark-gardens.jpg",
  label: "Gardens & amenity deck"
}];

/* ——— Hero: full-bleed slider, slow ken-burns, numbered pagination (luxury-places style) ——— */
function MotionHero() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI(v => (v + 1) % SLIDES.length), 5200);
    return () => clearInterval(t);
  }, []);
  return /*#__PURE__*/React.createElement("section", {
    style: {
      position: "relative",
      height: "86vh",
      minHeight: 560,
      overflow: "hidden",
      background: "var(--teal)"
    }
  }, /*#__PURE__*/React.createElement("style", null, `@keyframes rdh-kenburns { from { transform: scale(1.0); } to { transform: scale(1.1); } }
        @media (prefers-reduced-motion: reduce) { [data-kb] { animation: none !important; } }`), SLIDES.map((s, idx) => /*#__PURE__*/React.createElement("div", {
    key: s.src,
    style: {
      position: "absolute",
      inset: 0,
      opacity: idx === i ? 1 : 0,
      transition: "opacity 1.2s var(--ease-expo)"
    }
  }, /*#__PURE__*/React.createElement("img", {
    "data-kb": true,
    src: s.src,
    alt: s.label,
    style: {
      width: "100%",
      height: "100%",
      objectFit: "cover",
      animation: idx === i ? "rdh-kenburns 7s var(--ease-expo) forwards" : "none"
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: 0,
      background: "rgba(31,61,77,0.6)"
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      flexDirection: "column",
      justifyContent: "flex-end"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      width: "100%",
      paddingBottom: 64
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 20px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 14,
      fontWeight: 500,
      color: "rgba(255,255,255,0.75)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: "var(--warm)"
    }
  }), "15 years \xB7 Mumbai Western Suburbs"), /*#__PURE__*/React.createElement(__ds_scope.RevealLines, {
    as: "h1",
    delay: 0.15,
    lines: ["Your Future Home", "Is Right Here"],
    style: {
      fontSize: "clamp(3rem,7vw,6rem)",
      fontWeight: 800,
      lineHeight: 1.02,
      letterSpacing: "-0.025em",
      color: "#fff"
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 36,
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "space-between",
      gap: 24,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      maxWidth: 480,
      fontSize: 17,
      lineHeight: 1.625,
      color: "rgba(255,255,255,0.75)"
    }
  }, "Premium limited buildings across Goregaon, Andheri & Malad \u2014 every fact verified before it's published."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 20
    }
  }, SLIDES.map((s, idx) => /*#__PURE__*/React.createElement("button", {
    key: idx,
    onClick: () => setI(idx),
    style: {
      background: "none",
      border: "none",
      cursor: "pointer",
      padding: 0,
      textAlign: "left"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: idx === i ? "#fff" : "rgba(255,255,255,0.45)"
    }
  }, "0", idx + 1), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      marginTop: 8,
      height: 2,
      width: 56,
      background: "rgba(255,255,255,0.25)",
      position: "relative",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      inset: 0,
      background: "#fff",
      transform: idx === i ? "scaleX(1)" : "scaleX(0)",
      transformOrigin: "left",
      transition: idx === i ? "transform 5.2s linear" : "none"
    }
  })))))))));
}

/* ——— Stats band with count-up (Halston achievements) — real numbers only ——— */
function MotionStats() {
  const stats = [{
    v: 15,
    s: "",
    l: "years in the market"
  }, {
    v: 4,
    s: "",
    l: "signature projects"
  }, {
    v: 10,
    s: "",
    l: "live listings"
  }, {
    v: 3,
    s: "",
    l: "western suburbs"
  }];
  return /*#__PURE__*/React.createElement("section", {
    style: {
      borderBottom: "1px solid var(--mist-deep)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 24,
      padding: "56px 24px"
    }
  }, stats.map((st, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: st.l,
    delay: i * 0.06
  }, /*#__PURE__*/React.createElement(__ds_scope.CountUp, {
    value: st.v,
    suffix: st.s,
    style: {
      fontSize: 56,
      fontWeight: 800,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 6,
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      textTransform: "uppercase",
      letterSpacing: "0.15em",
      color: "var(--ink-45)"
    }
  }, st.l)))));
}

/* ——— Projects: hover rows with swapping preview image (Halston services list) ——— */
const ROWS = [{
  name: "Imperial Heights",
  location: "Goregaon West",
  meta: "44 storeys · 2–4.5 BHK",
  src: "../../assets/imagery/westpark-exterior.jpg"
}, {
  name: "Kalpataru Radiance",
  location: "Goregaon West",
  meta: "4 towers · 4.2 acres",
  src: "../../assets/imagery/westpark-gardens.jpg"
}, {
  name: "Ekta Tripolis",
  location: "Goregaon West",
  meta: "36 storeys · trilogy",
  src: "../../assets/imagery/westpark-masterlayout.png"
}, {
  name: "DLF Westpark",
  location: "Andheri West",
  meta: "New launch · Phase 2",
  src: "../../assets/imagery/westpark-location.png"
}];
function MotionProjects({
  go
}) {
  const [active, setActive] = useState(0);
  return /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "96px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "02",
    label: "Signature buildings"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.3fr 1fr",
      gap: 48,
      alignItems: "start"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: "1px solid var(--mist-deep)"
    }
  }, ROWS.map((r, i) => /*#__PURE__*/React.createElement("a", {
    key: r.name,
    href: "#",
    onClick: e => {
      e.preventDefault();
      if (r.name === "DLF Westpark") go("westpark");
    },
    onMouseEnter: () => setActive(i),
    style: {
      display: "grid",
      gridTemplateColumns: "auto 1fr auto",
      alignItems: "baseline",
      gap: 20,
      padding: "26px 4px",
      borderBottom: "1px solid var(--mist-deep)",
      textDecoration: "none",
      background: active === i ? "rgba(238,241,239,0.4)" : "transparent",
      transition: "background .3s"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: active === i ? "var(--warm)" : "var(--ink-40)"
    }
  }, "0", i + 1), /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontSize: 26,
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "var(--teal)"
    }
  }, r.name), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      marginTop: 2,
      fontSize: 13,
      color: "var(--ink-50)"
    }
  }, r.location, " \xB7 ", r.meta)), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--teal)",
      opacity: active === i ? 1 : 0.35,
      transition: "opacity .3s"
    }
  }, "View \u2192")))), /*#__PURE__*/React.createElement("div", {
    className: "rdh-zoom",
    style: {
      position: "sticky",
      top: 96,
      aspectRatio: "4/3",
      borderRadius: 16,
      overflow: "hidden"
    }
  }, ROWS.map((r, i) => /*#__PURE__*/React.createElement("img", {
    key: r.src,
    src: r.src,
    alt: r.name,
    style: {
      position: "absolute",
      inset: 0,
      width: "100%",
      height: "100%",
      objectFit: "cover",
      opacity: active === i ? 1 : 0,
      transform: active === i ? "scale(1)" : "scale(1.06)",
      transition: "opacity .6s var(--ease-expo), transform 1.2s var(--ease-expo)"
    }
  })))));
}

/* ——— Editorial statement + parallax feature ——— */
function MotionStatement({
  go
}) {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.4)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "112px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "03",
    label: "Our promise"
  })), /*#__PURE__*/React.createElement(__ds_scope.RevealLines, {
    as: "p",
    lines: ["A calmer, verification-first way", "to evaluate premium Mumbai", "residences."],
    style: {
      fontSize: "clamp(1.8rem,3.4vw,2.6rem)",
      fontWeight: 500,
      lineHeight: 1.25,
      letterSpacing: "-0.02em",
      color: "var(--teal)",
      maxWidth: 860
    }
  }), /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0.3
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "28px 0 0",
      maxWidth: 520,
      fontSize: 16,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, "Every claim is shown with its verification status. Pending facts stay honest placeholders \u2014 we never invent a value to fill a frame.")))), /*#__PURE__*/React.createElement("section", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Parallax, {
    speed: 0.1,
    style: {
      height: "70vh",
      minHeight: 440
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/imagery/westpark-gardens.jpg",
    alt: "DLF Westpark gardens",
    style: {
      width: "100%",
      height: "118%",
      objectFit: "cover",
      display: "block"
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 48
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "inline-block",
      borderRadius: 16,
      background: "rgba(255,255,255,0.92)",
      backdropFilter: "blur(8px)",
      padding: "28px 32px",
      maxWidth: 420
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      textTransform: "uppercase",
      letterSpacing: "0.15em",
      color: "var(--warm)"
    }
  }, "New launch"), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: "10px 0 0",
      fontSize: 26,
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "var(--teal)"
    }
  }, "DLF Westpark, Andheri West"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "8px 0 0",
      fontSize: 14,
      lineHeight: 1.6,
      color: "var(--ink-65)"
    }
  }, "Now previewing \u2014 pricing and RERA shown as pending until verified."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "sm",
    onClick: e => {
      e.preventDefault();
      go("westpark");
    }
  }, "Explore the launch \u2192"))))))));
}

/* ——— Ticker + dark CTA chapter ——— */
function MotionCta() {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      borderBottom: "1px solid var(--mist-deep)",
      padding: "36px 0",
      background: "#fff"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Ticker, {
    items: ["Imperial Heights", "Kalpataru Radiance", "Ekta Tripolis", "Bharat Auravistas", "DLF Westpark"],
    itemStyle: {
      fontSize: 44,
      fontWeight: 800,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  })), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--teal)",
      color: "#fff"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "128px 24px",
      textAlign: "center"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.RevealLines, {
    as: "h2",
    lines: ["Request the full brief.", "No lock-in, no pressure."],
    style: {
      fontSize: "clamp(2.2rem,4.5vw,3.6rem)",
      fontWeight: 800,
      lineHeight: 1.08,
      letterSpacing: "-0.025em",
      color: "#fff"
    }
  }), /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0.25
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "flex",
      justifyContent: "center",
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "warm",
    href: "https://wa.me/918291293889"
  }, "WhatsApp Padmini"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "outline",
    href: "tel:+918291293889",
    style: {
      borderColor: "rgba(255,255,255,0.3)",
      color: "#fff"
    }
  }, "+91 829 129 3889"))))));
}
function MotionHome({
  go = () => {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement(MotionHero, null), /*#__PURE__*/React.createElement(MotionStats, null), /*#__PURE__*/React.createElement(MotionProjects, {
    go: go
  }), /*#__PURE__*/React.createElement(MotionStatement, {
    go: go
  }), /*#__PURE__*/React.createElement(MotionCta, null));
}
Object.assign(__ds_scope, { MotionHome });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website-motion/MotionHome.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/WebsiteHome.jsx
try { (() => {
const RDH_PROJECTS = [{
  slug: "imperial-heights",
  name: "Imperial Heights",
  location: "Goregaon West",
  meta: "44-storey tower · 2–4.5 BHK",
  src: "../../assets/imagery/westpark-exterior.jpg"
}, {
  slug: "kalpataru-radiance",
  name: "Kalpataru Radiance",
  location: "Goregaon West",
  meta: "4 towers · 4.2 acres · 2–4 BHK",
  src: "../../assets/imagery/westpark-gardens.jpg"
}, {
  slug: "ekta-tripolis",
  name: "Ekta Tripolis",
  location: "Goregaon West",
  meta: "36 storeys · Skypolis · Caliopolis · Theopolis"
}, {
  slug: "bharat-auravistas",
  name: "Bharat Auravistas",
  location: "Oshiwara, Andheri West",
  meta: "36-storey · 3 BHK · Luxe & Grande"
}];
const RDH_LISTINGS = [{
  title: "Bharat Auravistas — Luxe 3 BHK",
  location: "Andheri West",
  config: "3 BHK",
  sqft: "1140",
  price: "₹4,59,00,000",
  type: "sale"
}, {
  title: "Exclusive 3.5 BHK — Imperial Heights",
  location: "Goregaon West",
  config: "3.5 BHK",
  sqft: "1409",
  price: "₹5,25,00,000",
  type: "sale"
}, {
  title: "Imperial Heights — 3.5 BHK",
  location: "Goregaon West",
  config: "3.5 BHK",
  sqft: "1445",
  price: "₹4,50,00,000",
  type: "sale"
}, {
  title: "Kalpataru Radiance — 3 BHK",
  location: "Goregaon West",
  config: "3 BHK",
  sqft: "1033",
  price: "₹3,75,00,000",
  type: "sale"
}, {
  title: "Ekta Tripolis — 2.5 BHK",
  location: "Goregaon West",
  config: "2.5 BHK",
  sqft: "—",
  price: "On request",
  type: "sale"
}, {
  title: "Kalpataru Radiance — 2 BHK",
  location: "Goregaon West",
  config: "2 BHK",
  sqft: "—",
  price: "On request",
  type: "sale"
}, {
  title: "Imperial Heights — 4.5 BHK Fully Furnished",
  location: "Goregaon West",
  config: "4.5 BHK",
  sqft: "1893",
  price: "₹2,00,000 / mo",
  type: "rent"
}, {
  title: "Kalpataru Radiance — 3 BHK",
  location: "Goregaon West",
  config: "3 BHK",
  sqft: "1017",
  price: "₹1,10,000 / mo",
  type: "rent"
}, {
  title: "Ekta Tripolis — 2.5 BHK",
  location: "Goregaon West",
  config: "2.5 BHK",
  sqft: "908",
  price: "₹90,000 / mo",
  type: "rent"
}, {
  title: "Imperial Heights — 2 BHK Duplex",
  location: "Goregaon West",
  config: "2 BHK Duplex",
  sqft: "727",
  price: "₹85,000 / mo",
  type: "rent"
}];
const PILLARS = [{
  title: "Truly Modern Buildings",
  points: ["Handpicked for builder reputation and credibility", "Spacious apartments and common areas", "Prime locations and proximity", "Top-notch modern amenities"]
}, {
  title: "All Apartments on Offer",
  points: ["Our dedicated team continually finds apartments for rent or sale", "If it's on the market, we have it", "Maximum choices for better negotiation and ideal layouts"]
}, {
  title: "Best Deals for You",
  points: ["Negotiating the lowest prices and best layouts", "Maximum negotiation room across floors and layouts", "Relax and let us handle the documentation"]
}];
const wrap = {
  margin: "0 auto",
  maxWidth: 1152,
  padding: "0 24px",
  boxSizing: "border-box"
};
const h2 = {
  margin: 0,
  fontSize: 34,
  fontWeight: 700,
  letterSpacing: "-0.025em",
  color: "var(--teal)"
};
const seeAll = {
  fontSize: 14,
  fontWeight: 600,
  color: "var(--teal)",
  textDecoration: "none",
  textUnderlineOffset: 4
};
function WebsiteHome({
  go
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "96px 24px 80px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 24px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 14,
      fontWeight: 500,
      color: "var(--ink-50)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: "var(--warm)"
    }
  }), "15 years \xB7 Mumbai Western Suburbs"), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      maxWidth: 900,
      fontSize: "clamp(2.6rem,6.5vw,5.5rem)",
      fontWeight: 800,
      lineHeight: 1.02,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  }, "Your Future Home Is Right Here"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "28px 0 0",
      maxWidth: 576,
      fontSize: 18,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, "2, 3 & 4 BHK apartments for sale and rent in Mumbai's most sought-after towers \u2014 Imperial Heights, Kalpataru Radiance, Ekta Tripolis and more across Goregaon, Andheri & Malad."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "flex",
      gap: 16,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    onClick: e => {
      e.preventDefault();
      go("buy");
    }
  }, "View listings \u2192"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "outline",
    onClick: e => {
      e.preventDefault();
      go("westpark");
    }
  }, "New launch \xB7 DLF Westpark")))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      borderBottom: "1px solid var(--mist-deep)",
      background: "var(--teal)",
      color: "#fff"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 16,
      padding: "28px 24px",
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      borderRadius: 9999,
      background: "var(--warm)",
      padding: "4px 10px",
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      fontWeight: 600,
      textTransform: "uppercase",
      letterSpacing: "0.05em"
    }
  }, "New"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 18,
      fontWeight: 600
    }
  }, "DLF Westpark, Andheri West \u2014 now previewing")), /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => {
      e.preventDefault();
      go("westpark");
    },
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--on-teal-90)",
      textDecoration: "none",
      textUnderlineOffset: 4
    },
    onMouseEnter: e => e.currentTarget.style.textDecoration = "underline",
    onMouseLeave: e => e.currentTarget.style.textDecoration = "none"
  }, "Explore the launch \u2192"))), /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Featured projects"), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: seeAll,
    onClick: e => e.preventDefault()
  }, "All projects \u2192"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 24
    }
  }, RDH_PROJECTS.map((p, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: p.slug,
    delay: i * 0.06
  }, /*#__PURE__*/React.createElement(__ds_scope.ProjectCard, {
    name: p.name,
    location: p.location,
    meta: p.meta,
    src: p.src,
    href: "#"
  }))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.4)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Featured properties"), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: seeAll,
    onClick: e => {
      e.preventDefault();
      go("buy");
    }
  }, "View all \u2192"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 20
    }
  }, RDH_LISTINGS.filter(l => l.type === "sale").slice(0, 4).map((l, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: l.title,
    delay: i * 0.05,
    style: {
      height: "100%"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.ListingCard, l)))))), /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Why work with us?")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 32
    }
  }, PILLARS.map((p, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: p.title,
    delay: i * 0.07
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: 16,
      border: "1px solid var(--mist-deep)",
      padding: 28
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 14,
      color: "var(--warm)"
    }
  }, "0", i + 1), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: "12px 0 0",
      fontSize: 20,
      fontWeight: 700,
      color: "var(--teal)"
    }
  }, p.title), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: "16px 0 0",
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, p.points.map(pt => /*#__PURE__*/React.createElement("li", {
    key: pt,
    style: {
      display: "flex",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--warm)"
    }
  }, "\xB7"), " ", pt)))))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "var(--teal)",
      color: "#fff"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "0 auto",
      maxWidth: 896,
      padding: "96px 24px",
      textAlign: "center",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.2em",
      color: "var(--on-teal-45)"
    }
  }, "What our clients say"), /*#__PURE__*/React.createElement("blockquote", {
    style: {
      margin: "24px auto 0",
      maxWidth: 768,
      fontSize: 28,
      fontWeight: 500,
      lineHeight: 1.375,
      letterSpacing: "-0.01em"
    }
  }, "\u201CMs. Padmini Jain came to the forefront in lining up various apartments to choose from and helped me at each step until I registered my own apartment.\u201D"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 28,
      fontSize: 14,
      color: "var(--on-teal-75)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 600,
      color: "#fff"
    }
  }, "Dr. Gopal Kewalramani"), " \xB7 Physician \u2014 Andheri West")))));
}
Object.assign(__ds_scope, { RDH_PROJECTS, RDH_LISTINGS, WebsiteHome });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/WebsiteHome.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/WebsiteListings.jsx
try { (() => {
const {
  useState
} = React;
/** Buy/Rent listings screen with an interactive type toggle. */
function WebsiteListings() {
  const [type, setType] = useState("sale");
  const items = __ds_scope.RDH_LISTINGS.filter(l => l.type === type);
  const seg = (t, label) => /*#__PURE__*/React.createElement("button", {
    onClick: () => setType(t),
    style: {
      borderRadius: 9999,
      border: type === t ? "1px solid var(--teal)" : "1px solid var(--mist-deep)",
      background: type === t ? "var(--teal)" : "transparent",
      color: type === t ? "#fff" : "var(--teal)",
      padding: "8px 18px",
      fontFamily: "var(--font-sans)",
      fontSize: 13,
      fontWeight: 600,
      cursor: "pointer",
      transition: "background .15s"
    }
  }, label);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "0 auto",
      maxWidth: 1152,
      padding: "72px 24px 96px",
      boxSizing: "border-box",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 24px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 14,
      fontWeight: 500,
      color: "var(--ink-50)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: "var(--warm)"
    }
  }), items.length, " listings \xB7 Goregaon \xB7 Andheri \xB7 Malad"), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 52,
      fontWeight: 800,
      lineHeight: 1.05,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  }, type === "sale" ? "Apartments for sale" : "Apartments for rent"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 28,
      display: "flex",
      gap: 10
    }
  }, seg("sale", "For sale"), seg("rent", "For rent"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20
    }
  }, items.map((l, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: l.title + i,
    delay: i % 3 * 0.05,
    style: {
      height: "100%"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.ListingCard, l)))));
}
Object.assign(__ds_scope, { WebsiteListings });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/WebsiteListings.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/WebsiteMobile.jsx
try { (() => {
const {
  useEffect,
  useRef,
  useState
} = React;
/** Mobile (390px) view of the Westpark landing inside a phone frame, with the two-segment sticky CTA. */
function WebsiteMobile() {
  const scrollRef = useRef(null);
  const enquiryRef = useRef(null);
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const root = scrollRef.current,
      target = enquiryRef.current;
    if (!root || !target) return;
    const io = new IntersectionObserver(([e]) => setHidden(e.isIntersecting), {
      root,
      rootMargin: "0px 0px -40% 0px"
    });
    io.observe(target);
    return () => io.disconnect();
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "center",
      padding: "56px 24px 96px",
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 390,
      height: 760,
      borderRadius: 40,
      border: "1px solid var(--mist-deep)",
      boxShadow: "0 0 0 8px var(--ink)",
      background: "#fff",
      overflow: "hidden",
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 44,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: "var(--ink)",
      borderBottom: "1px solid rgba(227,232,229,0.6)",
      background: "rgba(255,255,255,0.85)"
    }
  }, /*#__PURE__*/React.createElement("span", null, "9:41"), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      height: 20,
      width: 20,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 9999,
      background: "var(--teal)",
      color: "#fff",
      fontSize: 7,
      fontWeight: 700,
      fontFamily: "var(--font-sans)"
    }
  }, "RDH"))), /*#__PURE__*/React.createElement("div", {
    ref: scrollRef,
    style: {
      height: 716,
      overflowY: "auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "40px 20px 0"
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 16px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 13,
      fontWeight: 500,
      color: "var(--ink-55)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: "var(--warm)"
    }
  }), "DLF & Trident Realty \xB7 Andheri West"), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 44,
      fontWeight: 800,
      lineHeight: 1.03,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  }, "DLF Westpark"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "16px 0 0",
      fontSize: 16,
      lineHeight: 1.625,
      color: "var(--ink-70)"
    }
  }, "A calmer, verification-first preview of Andheri West's new launch."), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "20px 0 0",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, /*#__PURE__*/React.createElement("span", null, "Pricing ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "PRICE_VERIFY"
  })), /*#__PURE__*/React.createElement("span", null, "RERA ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "RERA_VERIFY"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "28px 0 0"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "16/9",
    radius: 12,
    src: "../../assets/imagery/westpark-exterior.jpg",
    alt: "DLF Westpark exterior"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "56px 20px 0"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "02",
    label: "Project overview"
  }), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontSize: 22,
      fontWeight: 500,
      lineHeight: 1.375,
      letterSpacing: "-0.01em",
      color: "var(--teal)"
    }
  }, "Built by DLF \u2014 verified before it's published.")), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "48px 0 0",
      background: "var(--teal)",
      color: "#fff",
      padding: "48px 20px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "05",
    label: "Lifestyle & amenities",
    onDark: true
  }), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontSize: 26,
      fontWeight: 700,
      letterSpacing: "-0.02em"
    }
  }, "The everyday, considered."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 24,
      display: "flex",
      flexDirection: "column",
      gap: 1,
      borderRadius: 12,
      overflow: "hidden",
      background: "rgba(255,255,255,0.15)"
    }
  }, ["Clubhouse & gym", "Gardens & deck", "Kids & community"].map(n => /*#__PURE__*/React.createElement("div", {
    key: n,
    style: {
      background: "var(--teal)",
      padding: 20
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      fontWeight: 600
    }
  }, n), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "6px 0 0",
      fontSize: 13,
      color: "var(--on-teal-55)"
    }
  }, "Details ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  })))))), /*#__PURE__*/React.createElement("div", {
    ref: enquiryRef,
    style: {
      padding: "56px 20px 96px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "09",
    label: "Get in touch"
  }), /*#__PURE__*/React.createElement("h2", {
    style: {
      margin: 0,
      fontSize: 28,
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "var(--teal)"
    }
  }, "Request the full brief."), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "12px 0 0",
      fontSize: 14,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, "Price list, floor plans and brochure. No commitment, no lock-in."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: "flex",
      flexDirection: "column",
      gap: 10,
      alignItems: "flex-start"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "warm",
    href: "https://wa.me/918291293889"
  }, "WhatsApp Padmini"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "outline",
    href: "#"
  }, "Email instead \u2192")), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "20px 0 0",
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      color: "var(--ink-40)"
    }
  }, "sticky CTA slides away while this form is in view \u2193"))), /*#__PURE__*/React.createElement(__ds_scope.StickyCta, {
    hidden: hidden,
    whatsappHref: "https://wa.me/918291293889"
  })));
}
Object.assign(__ds_scope, { WebsiteMobile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/WebsiteMobile.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/WebsiteWestpark.jsx
try { (() => {
const {
  useState
} = React;
const wrap = {
  margin: "0 auto",
  maxWidth: 1152,
  padding: "0 24px",
  boxSizing: "border-box"
};
const h2 = {
  margin: 0,
  fontSize: 34,
  fontWeight: 700,
  letterSpacing: "-0.025em",
  color: "var(--teal)"
};
const AMENITIES = [{
  category: "Wellness",
  name: "Clubhouse & gym",
  description: "Full amenity schedule VERIFY."
}, {
  category: "Outdoors",
  name: "Gardens & deck",
  description: "Landscape particulars VERIFY."
}, {
  category: "Family",
  name: "Kids & community",
  description: "Facility list VERIFY."
}];
const RESIDENCES = [{
  config: "3 BHK — Towers 6 & 7",
  carpetArea: "AREA_VERIFY",
  price: "PRICE_VERIFY"
}, {
  config: "4 BHK — Towers 6 & 7",
  carpetArea: "AREA_VERIFY",
  price: "PRICE_VERIFY"
}];
const FACTS = [{
  key: "developer",
  label: "Developer",
  value: "DLF & Trident Realty",
  status: "operator_confirmed"
}, {
  key: "location",
  label: "Micro-market",
  value: "Andheri West · D.N. Nagar / Link Road",
  status: "operator_confirmed"
}, {
  key: "rera",
  label: "RERA registration",
  value: "RERA_VERIFY",
  status: "pending_review"
}, {
  key: "pricing",
  label: "Pricing",
  value: "PRICE_VERIFY",
  status: "pending"
}, {
  key: "brochure",
  label: "Brochure",
  value: "BROCHURE_VERIFY",
  status: "pending"
}];
const FAQS = [{
  q: "Where is DLF Westpark located?",
  a: "Andheri West, in the D.N. Nagar / Link Road micro-market. Exact addressing stays pending until verified."
}, {
  q: "What configurations are offered?",
  a: "3 and 4 BHK residences in Towers 6 & 7 (Phase 2). Carpet areas are shown once verified."
}, {
  q: "Is the pricing final?",
  a: "Pricing is shown as a pending placeholder until we can verify it — we never invent a value."
}];
const MAP_STATES = ["Transit", "Schools", "Retail"];
function WebsiteWestpark() {
  const [mapState, setMapState] = useState("Transit");
  return /*#__PURE__*/React.createElement("article", {
    style: {
      fontFamily: "var(--font-sans)"
    }
  }, /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 24px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 14,
      fontWeight: 500,
      color: "var(--ink-55)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      height: 8,
      width: 8,
      borderRadius: 9999,
      background: "var(--warm)"
    }
  }), "DLF & Trident Realty \xB7 Andheri West"), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      maxWidth: 900,
      fontSize: "clamp(2.5rem,6.5vw,5.25rem)",
      fontWeight: 800,
      lineHeight: 1.03,
      letterSpacing: "-0.025em",
      color: "var(--teal)"
    }
  }, "DLF Westpark"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "28px 0 0",
      maxWidth: 672,
      fontSize: 20,
      lineHeight: 1.625,
      color: "var(--ink-70)"
    }
  }, "A calmer, verification-first preview of Andheri West's new launch \u2014 every fact shown with its status."), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "32px 0 0",
      display: "flex",
      alignItems: "center",
      gap: 24,
      flexWrap: "wrap",
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, /*#__PURE__*/React.createElement("span", null, "Pricing ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "PRICE_VERIFY"
  })), /*#__PURE__*/React.createElement("span", null, "RERA ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "RERA_VERIFY"
  })), /*#__PURE__*/React.createElement("span", null, "Micro-market \xB7 D.N. Nagar / Link Road")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      display: "flex",
      gap: 16,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    href: "#enquiry"
  }, "Request details"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "outline",
    href: "#facts"
  }, "See verified facts"))), /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0.1
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 56
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "21/9",
    radius: 16,
    src: "../../assets/imagery/westpark-exterior.jpg",
    alt: "DLF Westpark exterior"
  })))), /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "02",
    label: "Project overview"
  }), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      maxWidth: 768,
      fontSize: 30,
      fontWeight: 500,
      lineHeight: 1.375,
      letterSpacing: "-0.01em",
      color: "var(--teal)"
    }
  }, "Built by DLF \u2014 verified before it's published. Full particulars remain under review; every pending marker is replaced with a sourced fact before anything goes live."))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.4)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "80px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "04",
    label: "Location"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 48
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Andheri West \xB7 D.N. Nagar / Link Road"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "20px 0 0",
      fontSize: 16,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, "Positioned in one of Mumbai's most established western micro-markets. Exact addressing, distances and connectivity times stay ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  }), " until confirmed."), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: "24px 0 0",
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      fontSize: 14,
      color: "var(--ink-60, var(--ink-65))"
    }
  }, /*#__PURE__*/React.createElement("li", null, "\xB7 Commute & metro access \u2014 ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  })), /*#__PURE__*/React.createElement("li", null, "\xB7 Schools & institutions \u2014 ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  })), /*#__PURE__*/React.createElement("li", null, "\xB7 Retail & lifestyle \u2014 ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  })))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "1/1",
    radius: 16,
    src: "../../assets/imagery/westpark-location.png",
    alt: "Location map"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      left: 12,
      bottom: 12,
      display: "flex",
      gap: 6
    }
  }, MAP_STATES.map(s => /*#__PURE__*/React.createElement("button", {
    key: s,
    onClick: () => setMapState(s),
    style: {
      borderRadius: 9999,
      border: "none",
      cursor: "pointer",
      padding: "6px 14px",
      fontFamily: "var(--font-sans)",
      fontSize: 12,
      fontWeight: 600,
      background: mapState === s ? "var(--teal)" : "rgba(255,255,255,0.9)",
      color: mapState === s ? "#fff" : "var(--teal)"
    }
  }, s))), /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      right: 12,
      top: 12,
      borderRadius: 4,
      background: "rgba(255,255,255,0.9)",
      padding: "4px 8px",
      fontFamily: "var(--font-mono)",
      fontSize: 10,
      color: "var(--ink-55)"
    }
  }, mapState, " \xB7 static card \u2014 live embed deferred"))))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "var(--teal)",
      color: "#fff"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "96px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "05",
    label: "Lifestyle & amenities",
    onDark: true
  }), /*#__PURE__*/React.createElement("h2", {
    style: {
      ...h2,
      color: "#fff",
      maxWidth: 512
    }
  }, "The everyday, considered.")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 48,
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 1,
      overflow: "hidden",
      borderRadius: 16,
      background: "rgba(255,255,255,0.15)"
    }
  }, AMENITIES.map((a, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: a.name,
    delay: i * 0.05,
    style: {
      height: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: "100%",
      background: "var(--teal)",
      padding: 28,
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: "var(--warm)"
    }
  }, a.category), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 12,
      fontSize: 18,
      fontWeight: 600
    }
  }, a.name), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "8px 0 0",
      fontSize: 14,
      lineHeight: 1.625,
      color: "var(--on-teal-55)"
    }
  }, a.description.split("VERIFY")[0], /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: "VERIFY"
  })))))))), /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "96px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "06",
    label: "Residences"
  }), /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Configurations")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      borderTop: "1px solid var(--mist-deep)",
      borderBottom: "1px solid var(--mist-deep)"
    }
  }, RESIDENCES.map((r, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: r.config,
    delay: i * 0.05
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1.4fr 1fr 1fr auto",
      alignItems: "center",
      gap: 16,
      padding: "24px 0",
      borderBottom: i === 0 ? "1px solid var(--mist-deep)" : "none"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, r.config), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, "Carpet area \xB7 ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: r.carpetArea
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, "Price \xB7 ", /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: r.price
  })), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "sm",
    variant: "outline",
    href: "#enquiry"
  }, "Request details")))))), /*#__PURE__*/React.createElement("section", {
    style: {
      ...wrap,
      padding: "0 24px 96px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "07",
    label: "Gallery"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "4/3",
    src: "../../assets/imagery/westpark-gardens.jpg",
    alt: "Gardens"
  })), /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0.04
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "4/3",
    src: "../../assets/imagery/westpark-masterlayout.png",
    alt: "Master layout"
  })), /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    delay: 0.08
  }, /*#__PURE__*/React.createElement(__ds_scope.PlaceholderFrame, {
    ratio: "4/3",
    label: /*#__PURE__*/React.createElement("span", null, "Walkthrough video", /*#__PURE__*/React.createElement("br", null), "VISUAL_DIRECTION_PENDING")
  })))), /*#__PURE__*/React.createElement("section", {
    id: "facts",
    style: {
      borderTop: "1px solid var(--mist-deep)",
      borderBottom: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.4)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...wrap,
      padding: "96px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "08",
    label: "Verified facts ledger"
  }), /*#__PURE__*/React.createElement("h2", {
    style: {
      ...h2,
      maxWidth: 512
    }
  }, "Every claim, with its verification status.")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      overflow: "hidden",
      borderRadius: 16,
      border: "1px solid var(--mist-deep)",
      background: "#fff"
    }
  }, FACTS.map((f, i) => /*#__PURE__*/React.createElement(__ds_scope.Reveal, {
    key: f.key,
    delay: i * 0.03
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1.4fr auto",
      alignItems: "center",
      gap: 12,
      padding: "16px 24px",
      borderBottom: i < FACTS.length - 1 ? "1px solid var(--mist)" : "none"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--teal)"
    }
  }, f.label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "var(--ink-70)"
    }
  }, f.value.endsWith("_VERIFY") || f.value === "VERIFY" ? /*#__PURE__*/React.createElement(__ds_scope.PendingChip, {
    token: f.value
  }) : f.value), /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: f.status
  }))))), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "16px 0 0",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: "var(--ink-45)"
    }
  }, "Source of truth: local Postgres OS \xB7 website snapshot only \xB7 no value published until verified."))), /*#__PURE__*/React.createElement("section", {
    id: "enquiry",
    style: {
      ...wrap,
      padding: "96px 24px"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "09",
    label: "Get in touch"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1.1fr",
      gap: 48
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Request the full brief."), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "20px 0 0",
      maxWidth: 448,
      fontSize: 16,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, "Price list, floor plans and brochure \u2014 and a private presentation if you'd like to go deeper. No commitment, no lock-in."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 32,
      display: "flex",
      flexDirection: "column",
      gap: 12,
      alignItems: "flex-start"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "warm",
    href: "https://wa.me/918291293889"
  }, /*#__PURE__*/React.createElement("svg", {
    width: "18",
    height: "18",
    viewBox: "0 0 24 24",
    fill: "currentColor"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M12 0C5.373 0 0 5.373 0 12c0 2.117.549 4.107 1.51 5.84L.057 23.428a.5.5 0 0 0 .614.614l5.588-1.453A11.95 11.95 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.885 0-3.65-.52-5.16-1.426l-.37-.22-3.818.993.993-3.818-.22-.37A9.956 9.956 0 0 1 2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"
  })), "WhatsApp Padmini"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "outline",
    href: "mailto:PadminiJain1@gmail.com"
  }, "Email instead \u2192")), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "24px 0 0",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      color: "var(--ink-40)"
    }
  }, "+91 82912 93889 \xB7 Director, Real Deal Housing")), /*#__PURE__*/React.createElement("div", {
    style: {
      borderRadius: 16,
      border: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.3)",
      padding: 32
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "0 0 20px",
      fontFamily: "var(--font-mono)",
      fontSize: 12,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: "var(--ink-40)"
    }
  }, "What to expect"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      listStyle: "none",
      display: "flex",
      flexDirection: "column",
      gap: 16,
      fontSize: 14,
      color: "var(--ink-65)"
    }
  }, ["Price list and carpet area schedule for 3 & 4 BHK", "Floor plans for Towers 6 & 7 (Phase 2)", "Full brochure — DLF & Trident Realty", "Private presentation if you want to go deeper", "No lock-in, no brokerage pressure"].map(item => /*#__PURE__*/React.createElement("li", {
    key: item,
    style: {
      display: "flex",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--warm)",
      fontWeight: 700
    }
  }, "\u2014"), item))))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: "1px solid var(--mist-deep)",
      background: "rgba(238,241,239,0.3)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      margin: "0 auto",
      maxWidth: 768,
      padding: "96px 24px",
      boxSizing: "border-box"
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Reveal, null, /*#__PURE__*/React.createElement(__ds_scope.Eyebrow, {
    n: "10",
    label: "FAQ"
  }), /*#__PURE__*/React.createElement("h2", {
    style: h2
  }, "Questions, answered honestly.")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 40,
      borderTop: "1px solid var(--mist-deep)",
      borderBottom: "1px solid var(--mist-deep)"
    }
  }, FAQS.map((f, i) => /*#__PURE__*/React.createElement("details", {
    key: f.q,
    style: {
      padding: "20px 0",
      borderBottom: i < FAQS.length - 1 ? "1px solid var(--mist-deep)" : "none"
    }
  }, /*#__PURE__*/React.createElement("summary", {
    style: {
      display: "flex",
      cursor: "pointer",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 16,
      fontSize: 18,
      fontWeight: 600,
      color: "var(--teal)",
      listStyle: "none"
    }
  }, f.q, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono)",
      color: "var(--ink-40)"
    }
  }, "+")), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "12px 0 0",
      fontSize: 16,
      lineHeight: 1.625,
      color: "var(--ink-65)"
    }
  }, f.a)))))));
}
Object.assign(__ds_scope, { WebsiteWestpark });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/WebsiteWestpark.jsx", error: String((e && e.message) || e) }); }

__ds_ns.ListingCard = __ds_scope.ListingCard;

__ds_ns.ProjectCard = __ds_scope.ProjectCard;

__ds_ns.SiteFooter = __ds_scope.SiteFooter;

__ds_ns.SiteHeader = __ds_scope.SiteHeader;

__ds_ns.StickyCta = __ds_scope.StickyCta;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Dot = __ds_scope.Dot;

__ds_ns.Mono = __ds_scope.Mono;

__ds_ns.PanelTitle = __ds_scope.PanelTitle;

__ds_ns.TONE_STYLES = __ds_scope.TONE_STYLES;

__ds_ns.Pill = __ds_scope.Pill;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Eyebrow = __ds_scope.Eyebrow;

__ds_ns.PendingChip = __ds_scope.PendingChip;

__ds_ns.PlaceholderFrame = __ds_scope.PlaceholderFrame;

__ds_ns.Reveal = __ds_scope.Reveal;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.CountUp = __ds_scope.CountUp;

__ds_ns.Parallax = __ds_scope.Parallax;

__ds_ns.RevealImage = __ds_scope.RevealImage;

__ds_ns.RevealLines = __ds_scope.RevealLines;

__ds_ns.Ticker = __ds_scope.Ticker;

__ds_ns.CockpitContacts = __ds_scope.CockpitContacts;

__ds_ns.CockpitPortfolio = __ds_scope.CockpitPortfolio;

__ds_ns.CP_BUILDINGS = __ds_scope.CP_BUILDINGS;

__ds_ns.CockpitSidebar = __ds_scope.CockpitSidebar;

__ds_ns.CockpitTopbar = __ds_scope.CockpitTopbar;

__ds_ns.MotionHome = __ds_scope.MotionHome;

__ds_ns.RDH_PROJECTS = __ds_scope.RDH_PROJECTS;

__ds_ns.RDH_LISTINGS = __ds_scope.RDH_LISTINGS;

__ds_ns.WebsiteHome = __ds_scope.WebsiteHome;

__ds_ns.WebsiteListings = __ds_scope.WebsiteListings;

__ds_ns.WebsiteMobile = __ds_scope.WebsiteMobile;

__ds_ns.WebsiteWestpark = __ds_scope.WebsiteWestpark;

})();
