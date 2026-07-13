import React, { useEffect, useRef, useState } from "react";

/** Masked line-by-line headline reveal (Halston-style). Pass lines as an array. */
export function RevealLines({ lines = [], as = "h2", delay = 0, style, lineStyle }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setVisible(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); io.disconnect(); } }, { rootMargin: "-60px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const Tag = as;
  return (
    <Tag ref={ref} className={visible ? "is-visible" : ""} style={{ margin: 0, ...style }}>
      {lines.map((line, i) => (
        <span key={i} className="rdh-line" style={lineStyle}>
          <span className="rdh-line-inner" style={{ transitionDelay: `${delay + i * 0.09}s` }}>{line}</span>
        </span>
      ))}
    </Tag>
  );
}
