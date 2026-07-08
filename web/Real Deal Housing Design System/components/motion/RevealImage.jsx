import React, { useEffect, useRef, useState } from "react";

/** Image clip reveal — container unclips upward while the image settles from 1.12× to 1. */
export function RevealImage({ src, alt = "", ratio = "16/9", radius = 16, delay = 0, style }) {
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
  return (
    <div
      ref={ref}
      className={`rdh-clip${visible ? " is-visible" : ""}`}
      style={{ aspectRatio: ratio, borderRadius: radius, overflow: "hidden", transitionDelay: `${delay}s`, ...style }}
    >
      <img src={src} alt={alt} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", transitionDelay: `${delay}s` }} />
    </div>
  );
}
