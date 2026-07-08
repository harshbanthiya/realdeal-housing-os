import React, { useEffect, useRef } from "react";

/** Scroll parallax — child drifts vertically against scroll. speed 0.05–0.2 feels right. */
export function Parallax({ speed = 0.12, children, style }) {
  const outer = useRef(null);
  const inner = useRef(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const tick = () => {
      const o = outer.current, n = inner.current;
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
  return (
    <div ref={outer} style={{ overflow: "hidden", ...style }}>
      <div ref={inner} style={{ willChange: "transform" }}>{children}</div>
    </div>
  );
}
