import React from "react";

/** Mobile two-segment sticky bottom CTA — teal "Request details" | warm "WhatsApp". */
export function StickyCta({ hidden = false, onRequest, whatsappHref = "#" }) {
  return (
    <div
      style={{
        position: "absolute", insetInline: 0, bottom: 0, zIndex: 40,
        display: "flex", fontFamily: "var(--font-sans)",
        transform: hidden ? "translateY(100%)" : "translateY(0)",
        transition: "transform .3s",
      }}
    >
      <a href="#enquiry" onClick={onRequest} style={{ flex: 1, background: "var(--teal)", padding: "16px 0", textAlign: "center", fontSize: 14, fontWeight: 600, color: "#fff", textDecoration: "none" }}>
        Request details
      </a>
      <a href={whatsappHref} style={{ flex: 1, background: "var(--warm)", padding: "16px 0", textAlign: "center", fontSize: 14, fontWeight: 600, color: "#fff", textDecoration: "none" }}>
        WhatsApp
      </a>
    </div>
  );
}
