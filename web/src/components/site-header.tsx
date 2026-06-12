import Link from "next/link";
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
  return (
    <header className="sticky top-0 z-40 border-b border-mist-deep/60 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-teal text-[11px] font-bold text-white">
            RDH
          </span>
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
        <a
          href={company.phoneHref}
          className="rounded-full bg-teal px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-90"
        >
          {company.phone}
        </a>
      </div>
    </header>
  );
}
