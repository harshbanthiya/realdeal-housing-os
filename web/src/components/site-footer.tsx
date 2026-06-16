import Link from "next/link";
import { company } from "@/lib/site";
import { Logo } from "@/components/brand-mark";

export function SiteFooter() {
  return (
    <footer className="mt-24 bg-teal-deep text-white/90">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-col gap-12 md:flex-row md:justify-between">
          <div className="max-w-sm">
            <Logo tone="light" />
            <p className="mt-5 text-sm leading-relaxed text-white/65">
              {company.years} years finding premium homes across Mumbai&rsquo;s
              Western Suburbs: Goregaon, Andheri and Malad.
            </p>
            <div className="mt-6 space-y-1.5 text-sm text-white/75">
              <div>
                Tel:{" "}
                <a href={company.phoneHref} className="hover:text-white">
                  {company.phone}
                </a>
              </div>
              <div>
                Email:{" "}
                <a href={`mailto:${company.email}`} className="hover:text-white">
                  {company.email}
                </a>
              </div>
              <div className="text-white/55">{company.address}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-12 text-sm">
            <div>
              <div className="mb-3.5 text-xs uppercase tracking-wider text-white/45">
                Explore
              </div>
              <ul className="space-y-2.5 text-white/75">
                <li><Link href="/buy" className="hover:text-white">Buy</Link></li>
                <li><Link href="/rent" className="hover:text-white">Rent</Link></li>
                <li><Link href="/sell" className="hover:text-white">Sell</Link></li>
                <li><Link href="/projects" className="hover:text-white">Projects</Link></li>
              </ul>
            </div>
            <div>
              <div className="mb-3.5 text-xs uppercase tracking-wider text-white/45">
                Company
              </div>
              <ul className="space-y-2.5 text-white/75">
                <li><Link href="/about" className="hover:text-white">About</Link></li>
                <li><Link href="/blog" className="hover:text-white">Blog</Link></li>
                <li><Link href="/faq" className="hover:text-white">FAQ</Link></li>
                <li><Link href="/contact" className="hover:text-white">Contact</Link></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-14 flex flex-col gap-2 border-t border-white/15 pt-6 text-xs text-white/45 md:flex-row md:items-center md:justify-between">
          <span>© {company.legalName} - staging preview, not for public distribution.</span>
          <span className="font-mono">New project facts shown as pending placeholders until verified.</span>
        </div>
      </div>
    </footer>
  );
}
