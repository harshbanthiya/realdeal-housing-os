"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mono, Pill, type Tone } from "@/components/ui/primitives";
import type { ContactSheetRow } from "@/lib/cockpit/contacts-types";

const ROLE_TONE: Record<string, Tone> = { owner: "active", tenant: "ready", broker: "review", lead: "neutral" };

export function ContactSheetRowView({ r }: { r: ContactSheetRow }) {
  const router = useRouter();
  const href = `/cockpit/contacts/c/${r.contactId}`;

  function open() {
    router.push(href);
  }

  return (
    <tr
      role="link"
      tabIndex={0}
      aria-label={`Open contact ${r.displayHint}`}
      onClick={open}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
        }
      }}
      className="cursor-pointer border-b border-mist last:border-0 hover:bg-mist/20 focus-visible:bg-mist/30 focus-visible:outline-none"
    >
      <td className="px-4 py-3">
        <Link
          href={href}
          onClick={(event) => event.stopPropagation()}
          className="text-ink/85 underline-offset-2 hover:text-teal hover:underline"
        >
          {r.displayHint}
        </Link>
      </td>
      <td className="px-4 py-3"><Pill tone={r.canonicalStatus === "active" ? "ready" : "neutral"}>{r.canonicalStatus || "—"}</Pill></td>
      <td className="px-4 py-3">{r.role ? <Pill tone={ROLE_TONE[r.role] ?? "neutral"}>{r.role}</Pill> : <span className="text-ink/30">—</span>}</td>
      <td className="px-4 py-3 text-ink/70">{r.building ?? <span className="text-ink/30">—</span>}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.methodCount}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.leadRequirementCount}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.sourceFileCount}</td>
      <td className="px-4 py-3"><Mono className="text-[11px]">{r.createdAt.slice(0, 10) || "—"}</Mono></td>
    </tr>
  );
}
