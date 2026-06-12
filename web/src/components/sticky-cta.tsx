"use client";

import { useEffect, useState } from "react";

/**
 * Mobile sticky CTA — two segments (Request details | WhatsApp). Hides once the
 * enquiry section is in view (intersection), matching the approved Gallery
 * White spec. WhatsApp is a placeholder href (no live contact wired).
 */
export function StickyCta() {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const target = document.getElementById("enquiry");
    if (!target) return;
    const io = new IntersectionObserver(
      ([entry]) => setHidden(entry.isIntersecting),
      { rootMargin: "0px 0px -40% 0px" }
    );
    io.observe(target);
    return () => io.disconnect();
  }, []);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 flex md:hidden transition-transform duration-300 ${
        hidden ? "translate-y-full" : "translate-y-0"
      }`}
    >
      <a
        href="#enquiry"
        className="flex-1 bg-teal py-4 text-center text-sm font-semibold text-white"
      >
        Request details
      </a>
      <span
        aria-disabled
        title="Preview only — no live contact wired"
        className="flex-1 cursor-default bg-warm py-4 text-center text-sm font-semibold text-white/95"
      >
        WhatsApp
      </span>
    </div>
  );
}
