import React, { useState } from "react";
import { PlaceholderFrame } from "../marketing/PlaceholderFrame.jsx";

/** Featured project card — 16/9 image, hover mist wash, arrow affordance. */
export function ProjectCard({ name, location, meta, href = "#", src }) {
  const [hover, setHover] = useState(false);
  return (
    <a
      href={href}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "block", borderRadius: 16, border: "1px solid var(--mist-deep)",
        padding: 28, textDecoration: "none", fontFamily: "var(--font-sans)",
        background: hover ? "rgba(238,241,239,0.4)" : "transparent",
        transition: "background .15s", boxSizing: "border-box",
      }}
    >
      <PlaceholderFrame ratio="16/9" radius={12} src={src} />
      <h3 style={{ margin: "20px 0 0", fontSize: 20, fontWeight: 700, color: "var(--teal)" }}>{name}</h3>
      <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--ink-55)" }}>{location} · {meta}</p>
      <span style={{ display: "inline-block", marginTop: 16, fontSize: 14, fontWeight: 600, color: "var(--teal)", textDecoration: hover ? "underline" : "none", textUnderlineOffset: 4 }}>
        View project →
      </span>
    </a>
  );
}
