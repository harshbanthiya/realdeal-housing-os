"use client";

import { useEffect, useState } from "react";

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
      <a
        href="https://wa.me/918291293889?text=Hi%20Padmini%2C%20I%27m%20interested%20in%20DLF%20Westpark%20%E2%80%94%20can%20you%20share%20details%3F"
        target="_blank"
        rel="noopener noreferrer"
        className="flex-1 bg-warm py-4 text-center text-sm font-semibold text-white"
      >
        WhatsApp
      </a>
    </div>
  );
}
