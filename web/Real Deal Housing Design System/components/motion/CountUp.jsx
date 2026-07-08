import React, { useEffect, useRef, useState } from "react";

/** Count-up stat — animates 0 → value when scrolled into view (1.4s, expo ease). */
export function CountUp({ value, prefix = "", suffix = "", duration = 1.4, style }) {
  const ref = useRef(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(value); return; }
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const step = (t) => {
        const p = Math.min(1, (t - t0) / (duration * 1000));
        const eased = 1 - Math.pow(1 - p, 4);
        setN(Math.round(value * eased));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, { rootMargin: "-40px" });
    io.observe(el);
    return () => io.disconnect();
  }, [value, duration]);
  return <span ref={ref} style={{ fontVariantNumeric: "tabular-nums", ...style }}>{prefix}{n}{suffix}</span>;
}
