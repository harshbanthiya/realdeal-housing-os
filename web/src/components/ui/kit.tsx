import Link from "next/link";
import type { ReactNode } from "react";
import { Reveal } from "@/components/reveal";

/* ---------- Buttons ----------
   Shape lock: primary actions are full-pill. Tactile press on :active.
   Primary = teal fill (brand). Secondary = hairline outline. */

const base =
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-semibold whitespace-nowrap transition-all duration-200 active:translate-y-px active:scale-[0.99]";

export function ButtonLink({
  href,
  children,
  variant = "primary",
  className = "",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
  className?: string;
}) {
  const v =
    variant === "primary"
      ? "bg-teal px-6 py-3.5 text-white hover:bg-teal-deep"
      : "border border-mist-deep bg-white/60 px-6 py-3.5 text-teal hover:border-teal/40 hover:bg-mist";
  const isHash = href.startsWith("#") || href.startsWith("tel:") || href.startsWith("mailto:");
  if (isHash) {
    return (
      <a href={href} className={`${base} ${v} ${className}`}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={`${base} ${v} ${className}`}>
      {children}
    </Link>
  );
}

/* ---------- Page intro (the one eyebrow a page is allowed) ---------- */

export function PageIntro({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow?: string;
  title: ReactNode;
  lead?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <Reveal>
      {eyebrow && (
        <p className="mb-5 font-mono text-xs uppercase tracking-[0.2em] text-warm">
          {eyebrow}
        </p>
      )}
      <h1 className="display max-w-4xl text-balance text-[clamp(2.2rem,5vw,3.75rem)] font-extrabold leading-[1.05] text-teal">
        {title}
      </h1>
      {lead && (
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink/65">
          {lead}
        </p>
      )}
      {children}
    </Reveal>
  );
}

/* ---------- Section heading with a side action ---------- */

export function SectionHead({
  title,
  action,
}: {
  title: ReactNode;
  action?: { href: string; label: string };
}) {
  return (
    <div className="flex items-end justify-between gap-6">
      <h2 className="display text-3xl font-bold text-teal md:text-[2.5rem] md:leading-[1.1]">
        {title}
      </h2>
      {action && (
        <Link
          href={action.href}
          className="shrink-0 text-sm font-semibold text-teal underline-offset-4 hover:underline"
        >
          {action.label}
        </Link>
      )}
    </div>
  );
}
