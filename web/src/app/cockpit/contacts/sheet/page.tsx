import Link from "next/link";
import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import { ContactsSubnav } from "@/components/cockpit/contacts-subnav";
import { getContactSheet } from "@/lib/cockpit/contacts";
import { SHEET_SORTS, type SheetSortKey, type ContactSheetRow } from "@/lib/cockpit/contacts-types";

export const dynamic = "force-dynamic";

const ROLE_TONE: Record<string, Tone> = { owner: "active", tenant: "ready", broker: "review", lead: "neutral" };

function parseSort(v: string | undefined): SheetSortKey {
  return v && v in SHEET_SORTS ? (v as SheetSortKey) : "created";
}

export default async function ContactsSheet({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; sort?: string; dir?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page) || 1);
  const sort = parseSort(sp.sort);
  const dir = sp.dir === "asc" ? "asc" : "desc";

  const sheet = await getContactSheet({ page, sort, dir });
  const pageCount = Math.max(1, Math.ceil(sheet.total / sheet.pageSize));
  const from = sheet.total === 0 ? 0 : (sheet.page - 1) * sheet.pageSize + 1;
  const to = Math.min(sheet.page * sheet.pageSize, sheet.total);

  // Build a sortable header link that toggles dir when re-clicking the active column.
  const sortHref = (key: SheetSortKey) => {
    const nextDir = sort === key && dir === "desc" ? "asc" : "desc";
    return `/cockpit/contacts/sheet?sort=${key}&dir=${nextDir}&page=1`;
  };
  const pageHref = (p: number) => `/cockpit/contacts/sheet?sort=${sort}&dir=${dir}&page=${p}`;
  const arrow = (key: SheetSortKey) => (sort === key ? (dir === "desc" ? " ↓" : " ↑") : "");

  return (
    <div className="px-6 py-7">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-teal">All contacts</h1>
        <p className="mt-1 text-sm text-ink/55">
          {sheet.total} cleaned canonical {sheet.total === 1 ? "contact" : "contacts"} · masked · raw values only via consent-gated export
        </p>
        <ContactsSubnav />
      </div>

      {sheet.total === 0 ? (
        <div role="status" className="mt-6 rounded-xl border border-dashed border-mist-deep bg-mist/30 px-5 py-14 text-center">
          <h3 className="text-sm font-medium text-ink/70">No canonical contacts yet</h3>
          <p className="mx-auto mt-1 max-w-md text-sm text-ink/45">
            Approve and merge candidates in the{" "}
            <Link href="/cockpit/contacts" className="text-teal underline-offset-2 hover:underline">cleanup queue</Link>{" "}
            to populate this registry.
          </p>
        </div>
      ) : (
        <Card className="mt-6 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-mist-deep bg-mist/30 text-left">
                  <Th><SortLink href={sortHref("contact")} label={`Contact${arrow("contact")}`} /></Th>
                  <Th><SortLink href={sortHref("status")} label={`Status${arrow("status")}`} /></Th>
                  <Th>Role</Th>
                  <Th>Building</Th>
                  <Th className="text-right"><SortLink href={sortHref("methods")} label={`Methods${arrow("methods")}`} /></Th>
                  <Th className="text-right">Leads</Th>
                  <Th className="text-right">Sources</Th>
                  <Th><SortLink href={sortHref("created")} label={`Added${arrow("created")}`} /></Th>
                </tr>
              </thead>
              <tbody>
                {sheet.rows.map((r) => <Row key={r.contactId} r={r} />)}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {sheet.total > 0 && (
        <div className="mt-4 flex items-center justify-between text-[12px] text-ink/55">
          <span>Showing {from}-{to} of {sheet.total}</span>
          <div className="flex items-center gap-2">
            <PageLink href={pageHref(sheet.page - 1)} disabled={sheet.page <= 1} label="← Prev" />
            <Mono className="text-[11px]">page {sheet.page} / {pageCount}</Mono>
            <PageLink href={pageHref(sheet.page + 1)} disabled={sheet.page >= pageCount} label="Next →" />
          </div>
        </div>
      )}
    </div>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-4 py-2.5 font-mono text-[10px] font-medium uppercase tracking-wider text-ink/45 ${className}`}>{children}</th>;
}
function SortLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="hover:text-teal">{label}</Link>;
}
function Row({ r }: { r: ContactSheetRow }) {
  return (
    <tr className="border-b border-mist last:border-0 hover:bg-mist/20">
      <td className="px-4 py-3 text-ink/85">{r.displayHint}</td>
      <td className="px-4 py-3"><Pill tone={r.canonicalStatus === "active" ? "ready" : "neutral"}>{r.canonicalStatus || " - "}</Pill></td>
      <td className="px-4 py-3">{r.role ? <Pill tone={ROLE_TONE[r.role] ?? "neutral"}>{r.role}</Pill> : <span className="text-ink/30"> - </span>}</td>
      <td className="px-4 py-3 text-ink/70">{r.building ?? <span className="text-ink/30"> - </span>}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.methodCount}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.leadRequirementCount}</td>
      <td className="px-4 py-3 text-right tabular-nums text-ink/70">{r.sourceFileCount}</td>
      <td className="px-4 py-3"><Mono className="text-[11px]">{r.createdAt.slice(0, 10) || " - "}</Mono></td>
    </tr>
  );
}
function PageLink({ href, disabled, label }: { href: string; disabled: boolean; label: string }) {
  if (disabled) return <span className="cursor-not-allowed rounded-full border border-mist px-3 py-1 text-ink/30">{label}</span>;
  return <Link href={href} className="rounded-full border border-mist-deep px-3 py-1 text-ink/65 transition-colors hover:bg-mist/40">{label}</Link>;
}
