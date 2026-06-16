import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, Pill, Mono, PanelTitle, type Tone } from "@/components/ui/primitives";
import { getContactDetail } from "@/lib/cockpit/contacts";
import { roleLabel, statusLabel, type ContactMethodDetail } from "@/lib/cockpit/contacts-types";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

const ROLE_TONE: Record<string, Tone> = { owner: "active", tenant: "ready", broker: "review", lead: "neutral" };
const METHOD_LABEL: Record<string, string> = { mobile: "Mobile", phone: "Landline", email: "Email", website: "Website", google_maps: "Maps" };

export default async function ContactDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await getContactDetail(id);
  if (!c) notFound();

  const phones = c.methods.filter((m) => m.methodType === "mobile" || m.methodType === "phone");
  const emails = c.methods.filter((m) => m.methodType === "email");
  const others = c.methods.filter((m) => !["mobile", "phone", "email"].includes(m.methodType));

  return (
    <div className="px-6 py-7">
      <Link href="/cockpit/contacts/sheet" className="text-[12px] text-ink/50 hover:text-teal">← All contacts</Link>

      <div className="mt-3 mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-teal">{c.fullName}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <Pill tone={ROLE_TONE[c.contactType] ?? "neutral"}>{roleLabel(c.contactType)}</Pill>
            <Pill tone={c.status === "active" ? "ready" : "neutral"}>{statusLabel(c.status)}</Pill>
            {c.source && <Mono className="text-[11px]">via {c.source}</Mono>}
          </div>
        </div>
        <span className="rounded-md bg-amber/10 px-2.5 py-1 text-[11px] font-medium text-amber">Full details · operator-only</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Contact methods (unmasked) */}
        <Card className="p-5">
          <PanelTitle hint={`${c.methods.length}`}>Contact methods</PanelTitle>
          {c.methods.length === 0 ? (
            <p className="text-sm text-ink/45">No methods on file.</p>
          ) : (
            <div className="space-y-4">
              {phones.length > 0 && <MethodGroup title="Phone" items={phones} />}
              {emails.length > 0 && <MethodGroup title="Email" items={emails} />}
              {others.length > 0 && <MethodGroup title="Other" items={others} />}
            </div>
          )}
        </Card>

        {/* Buildings / relationships */}
        <Card className="p-5">
          <PanelTitle hint={`${c.relationships.length}`}>Buildings</PanelTitle>
          {c.relationships.length === 0 ? (
            <p className="text-sm text-ink/45">Not attached to a building yet.</p>
          ) : (
            <ul className="space-y-3">
              {c.relationships.map((r, i) => (
                <li key={i} className="flex items-center justify-between rounded-lg border border-mist-deep p-3">
                  <div>
                    <div className="text-sm font-medium text-teal">{r.building ?? "—"}</div>
                    <div className="mt-0.5 text-[12px] text-ink/55">
                      {[r.wing ? `Wing ${r.wing}` : "", r.unitNumber ? `Unit ${r.unitNumber}` : ""].filter(Boolean).join(" · ") || "building-level"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Pill tone={ROLE_TONE[r.relationshipType] ?? "neutral"}>{roleLabel(r.relationshipType)}</Pill>
                    <Pill tone={r.relationshipStatus === "active" ? "ready" : "neutral"}>{statusLabel(r.relationshipStatus)}</Pill>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {c.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {c.tags.map((t) => <Mono key={t} className="rounded bg-mist px-1.5 py-0.5 text-[10px]">{t}</Mono>)}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function MethodGroup({ title, items }: { title: string; items: ContactMethodDetail[] }) {
  return (
    <div>
      <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-ink/40">{title}</div>
      <ul className="space-y-1.5">
        {items.map((m, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="text-sm text-ink/85 tabular-nums">{m.value}</span>
            {m.isPrimary && <Pill tone="active">primary</Pill>}
            {m.methodType !== "mobile" && m.methodType !== "email" && (
              <Mono className="text-[10px]">{METHOD_LABEL[m.methodType] ?? m.methodType}</Mono>
            )}
            {m.validationStatus && m.validationStatus !== "valid" && (
              <span className="text-[10px] text-warm">{m.validationStatus}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
