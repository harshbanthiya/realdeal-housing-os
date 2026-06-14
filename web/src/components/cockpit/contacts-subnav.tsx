"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/cockpit/contacts", label: "Overview" },
  { href: "/cockpit/contacts/pipeline", label: "Pipeline" },
  { href: "/cockpit/contacts/sheet", label: "All contacts" },
];

export function ContactsSubnav() {
  const path = usePathname();
  return (
    <nav className="mt-4 flex gap-1 border-b border-mist-deep" aria-label="Contacts views">
      {TABS.map((t) => {
        const active = path === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={active ? "page" : undefined}
            className={`border-b-2 px-3 py-2 text-[13px] font-medium transition-colors ${
              active ? "border-teal text-teal" : "border-transparent text-ink/55 hover:text-teal"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
