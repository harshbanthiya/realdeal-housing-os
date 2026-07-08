"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dot, type Tone } from "@/components/ui/primitives";
import type { Building } from "@/lib/cockpit/data";

const MODE_TONE: Record<string, Tone> = {
  launch: "blocked",
  active: "ready",
  prospecting: "review",
  post_launch: "neutral",
};

export function Sidebar({ buildings }: { buildings: Building[] }) {
  const path = usePathname();
  const isHome = path === "/cockpit";

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-mist-deep bg-mist/30">
      <div className="flex h-14 items-center gap-2 border-b border-mist-deep px-5">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-teal text-[10px] font-bold text-white">RDH</span>
        <span className="text-sm font-semibold tracking-tight text-teal">Operations cockpit</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 text-sm">
        <Link
          href="/cockpit"
          className={`flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${isHome ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Portfolio
        </Link>
        <Link
          href="/cockpit/inbox"
          className={`mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${path === "/cockpit/inbox" ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Inbox
        </Link>
        <Link
          href="/cockpit/contacts"
          className={`mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${path === "/cockpit/contacts" ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Contacts
        </Link>
        <Link
          href="/cockpit/audiences"
          className={`mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${path === "/cockpit/audiences" ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Audiences
        </Link>
        <Link
          href="/cockpit/outreach"
          className={`mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${path === "/cockpit/outreach" ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Outreach
        </Link>
        <Link
          href="/cockpit/media"
          className={`mt-0.5 flex items-center gap-2 rounded-lg px-3 py-2 font-medium ${path === "/cockpit/media" ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
        >
          Media
        </Link>

        <div className="mt-5 mb-2 px-3 font-mono text-[10px] uppercase tracking-[0.15em] text-ink/40">
          Buildings · {buildings.length}
        </div>
        <ul className="space-y-0.5">
          {buildings.map((b) => {
            const active = path === `/cockpit/buildings/${b.slug}`;
            return (
              <li key={b.slug}>
                <Link
                  href={`/cockpit/buildings/${b.slug}`}
                  className={`flex items-center gap-2.5 rounded-lg px-3 py-2 ${active ? "bg-white text-teal shadow-[0_0_0_1px_var(--color-mist-deep)]" : "text-ink/65 hover:bg-white/60"}`}
                >
                  <Dot tone={MODE_TONE[b.mode]} />
                  <span className="flex-1 truncate">{b.name}</span>
                  {b.stats.blockers > 0 && (
                    <span className="font-mono text-[10px] text-warm">{b.stats.blockers}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-mist-deep p-3 text-sm">
        <Link href="/" className="flex items-center gap-2 rounded-lg px-3 py-2 text-ink/55 hover:bg-white/60">
          ↗ Marketing site
        </Link>
        <a href="/cockpit/logout" className="flex items-center gap-2 rounded-lg px-3 py-2 text-ink/55 hover:bg-white/60">
          ⏻ Sign out
        </a>
      </div>
    </aside>
  );
}
