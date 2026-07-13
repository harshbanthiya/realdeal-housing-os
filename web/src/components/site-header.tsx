"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { company } from "@/lib/site";

const NAV = [
  { label: "Buy", href: "/buy" },
  { label: "Rent", href: "/rent" },
  { label: "Sell", href: "/sell" },
  { label: "Projects", href: "/projects" },
  { label: "Blog", href: "/blog" },
  { label: "About", href: "/about" },
  { label: "FAQ", href: "/faq" },
  { label: "Contact", href: "/contact" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-mist-deep/60 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <Image
            src="/rdh-mark.png"
            alt=""
            width={554}
            height={489}
            className="h-8 w-auto"
            priority
          />
          <span className="text-[15px] font-semibold tracking-tight text-teal">
            {company.name}
          </span>
        </Link>
        <nav className="hidden items-center gap-6 lg:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[13.5px] font-medium text-ink/65 transition-colors hover:text-teal"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <a
            href={company.phoneHref}
            className="whitespace-nowrap rounded-full bg-teal px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-90"
          >
            <span className="hidden md:inline">{company.phone}</span>
            <span className="md:hidden">Call us</span>
          </a>
          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-mist-deep text-teal lg:hidden"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              {open ? (
                <path d="M3 3l12 12M15 3L3 15" />
              ) : (
                <path d="M2 5h14M2 9h14M2 13h14" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu overlay — absolute because the header's backdrop-blur makes it the containing block for fixed children */}
      <div
        className={`absolute inset-x-0 top-full z-40 flex h-[calc(100dvh-4rem)] flex-col overflow-y-auto bg-white transition-opacity duration-300 lg:hidden ${
          open ? "opacity-100" : "pointer-events-none invisible opacity-0"
        }`}
      >
        <nav className="flex flex-col px-6 py-8">
          {NAV.map((item, i) => (
            <Link
              key={item.href}
              href={item.href}
              tabIndex={open ? 0 : -1}
              onClick={() => setOpen(false)}
              className={`border-b border-mist-deep/60 py-4 text-2xl font-bold tracking-tight text-teal transition-all duration-300 ${
                open ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
              }`}
              style={{ transitionDelay: open ? `${i * 40}ms` : "0ms" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto px-6 pb-10">
          <a
            href={company.phoneHref}
            tabIndex={open ? 0 : -1}
            className="block rounded-full bg-teal px-6 py-3.5 text-center text-sm font-semibold text-white"
          >
            {company.phone}
          </a>
        </div>
      </div>
    </header>
  );
}
