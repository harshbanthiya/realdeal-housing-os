import Link from "next/link";
import { company } from "@/lib/site";
import { Logo } from "@/components/brand-mark";
import { MobileNav } from "@/components/mobile-nav";

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
    <header className="sticky top-0 z-40 border-b border-mist-deep/70 bg-paper/80 backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-6xl items-center justify-between px-6">
        <Logo />
        <nav className="hidden items-center gap-6 lg:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[13.5px] font-medium text-ink/60 transition-colors hover:text-teal"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <a
            href={company.phoneHref}
            className="rounded-full bg-teal px-4 py-2 text-[13px] font-semibold text-white transition-all duration-200 hover:bg-teal-deep active:translate-y-px"
          >
            <span className="hidden sm:inline">{company.phone}</span>
            <span className="sm:hidden">Call</span>
          </a>
          <MobileNav items={NAV} />
        </div>
      </div>
    </header>
  );
}
