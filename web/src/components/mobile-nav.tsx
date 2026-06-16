"use client";

import { useState } from "react";
import Link from "next/link";

/**
 * Compact mobile navigation. Hidden at lg+ (the inline nav takes over there).
 * A single toggle reveals a full-width panel; selecting a link closes it.
 */
export function MobileNav({
  items,
}: {
  items: { label: string; href: string }[];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-full text-teal transition-colors hover:bg-mist active:scale-95"
      >
        <span className="relative block h-3.5 w-5">
          <span
            className={`absolute left-0 block h-0.5 w-5 bg-current transition-all duration-300 ${
              open ? "top-1.5 rotate-45" : "top-0"
            }`}
          />
          <span
            className={`absolute left-0 top-1.5 block h-0.5 w-5 bg-current transition-opacity duration-200 ${
              open ? "opacity-0" : "opacity-100"
            }`}
          />
          <span
            className={`absolute left-0 block h-0.5 w-5 bg-current transition-all duration-300 ${
              open ? "top-1.5 -rotate-45" : "top-3"
            }`}
          />
        </span>
      </button>

      {open && (
        <>
          <button
            aria-hidden
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="fixed inset-0 top-[68px] z-30 cursor-default bg-ink/10"
          />
          <nav className="absolute inset-x-0 top-[68px] z-40 border-b border-mist-deep bg-paper shadow-[0_20px_40px_-24px_rgba(31,61,77,0.4)]">
            <ul className="mx-auto grid max-w-6xl gap-1 px-6 py-4">
              {items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className="block rounded-lg px-3 py-2.5 text-[15px] font-medium text-ink/75 transition-colors hover:bg-mist hover:text-teal"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </>
      )}
    </div>
  );
}
