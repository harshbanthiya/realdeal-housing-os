import Link from "next/link";
import { Card, Mono, PanelTitle, Pill } from "@/components/ui/primitives";
import {
  audienceScope,
  getAudienceFilterOptions,
  getAudienceSummary,
  parseAudienceFilters,
} from "@/lib/cockpit/audiences";

export const dynamic = "force-dynamic";
export const metadata = { title: "Audience Exports", robots: { index: false, follow: false } };

export default async function AudiencesPage({
  searchParams,
}: {
  searchParams: Promise<{ building?: string; role?: string }>;
}) {
  const sp = await searchParams;
  const filters = parseAudienceFilters(sp);
  const [options, summary] = await Promise.all([
    getAudienceFilterOptions(),
    getAudienceSummary(filters),
  ]);
  const params = new URLSearchParams();
  if (filters.building) params.set("building", filters.building);
  if (filters.role) params.set("role", filters.role);
  const metaHref = `/cockpit/audiences/meta${params.size ? `?${params.toString()}` : ""}`;
  const scope = audienceScope(filters);

  return (
    <div className="px-6 py-7">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-teal">Audience exports</h1>
          <p className="mt-1 max-w-2xl text-sm text-ink/55">
            Build hashed Meta audience CSVs from attached canonical contacts. Raw phone and email values are used only server-side for hashing.
          </p>
        </div>
        <Pill tone="review">operator-only</Pill>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <Card className="p-5">
          <PanelTitle hint={scope}>Filters</PanelTitle>
          <form className="space-y-4" action="/cockpit/audiences">
            <label className="block">
              <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink/40">Building</span>
              <select
                name="building"
                defaultValue={filters.building ?? "all"}
                className="w-full rounded-lg border border-mist-deep bg-white px-3 py-2 text-sm text-ink/75 outline-none focus:border-teal"
              >
                <option value="all">All buildings</option>
                {options.buildings.map((b) => (
                  <option key={b.value} value={b.value}>{b.label}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink/40">Role</span>
              <select
                name="role"
                defaultValue={filters.role ?? "all"}
                className="w-full rounded-lg border border-mist-deep bg-white px-3 py-2 text-sm text-ink/75 outline-none focus:border-teal"
              >
                <option value="all">All roles</option>
                {options.roles.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </label>
            <button type="submit" className="w-full rounded-lg bg-teal px-3 py-2 text-sm font-semibold text-white hover:opacity-90">
              Update preview
            </button>
          </form>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <PanelTitle hint="Meta Business">Custom / lookalike audience CSV</PanelTitle>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Metric label="contacts" value={summary.attached} />
              <Metric label="usable phones" value={summary.usablePhones} />
              <Metric label="emails" value={summary.emails} />
              <Metric label="hashed rows" value={summary.metaRows} />
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Link
                href={metaHref}
                className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
              >
                Download Meta CSV
              </Link>
              <Mono className="text-[11px]">email, phone · SHA-256 · no raw values</Mono>
            </div>
            <p className="mt-4 text-sm text-ink/50">
              Active suppression rows are excluded. Confirm your Meta customer-list basis before upload.
            </p>
          </Card>

          <Card className="p-5">
            <PanelTitle hint="WhatsApp">Send strategy</PanelTitle>
            <div className="grid gap-3 md:grid-cols-3">
              <State label="WhatsApp allowed permissions" value={summary.whatsappAllowed} tone={summary.whatsappAllowed ? "ready" : "blocked"} />
              <State label="Suppressed contacts" value={summary.suppressed} tone={summary.suppressed ? "review" : "neutral"} />
              <State label="Direct API state" value="not connected" tone="blocked" />
            </div>
            <div className="mt-5 space-y-3 text-sm text-ink/60">
              <p>
                Direct cockpit sending should support multiple sender identities: a director personal/manual route for known owners, and a WhatsApp Business Cloud route for approved campaign templates.
              </p>
              <p>
                Fast path today: export the WhatsApp recipient CSV from the script, then use WhatsApp Web or WhatsApp Business manually. The current sender script dry-runs safely, but real sending stays blocked until credentials and explicit channel permissions exist.
              </p>
            </div>
            <div className="mt-4 rounded-lg border border-mist-deep bg-mist/30 p-3">
              <Mono className="block text-[11px]">python3 scripts/export_audiences.py --apply --building &quot;{filters.building ?? "BUILDING"}&quot; --role {filters.role ?? "owner"}</Mono>
              <Mono className="mt-1 block text-[11px]">python3 scripts/whatsapp_send.py --from-csv exports/audiences/whatsapp_recipients_{scope}.csv --max 5</Mono>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-mist-deep bg-mist/20 p-3">
      <div className="text-2xl font-semibold text-teal tabular-nums">{value}</div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-ink/40">{label}</div>
    </div>
  );
}

function State({ label, value, tone }: { label: string; value: number | string; tone: "ready" | "blocked" | "review" | "neutral" }) {
  return (
    <div className="rounded-lg border border-mist-deep p-3">
      <div><Pill tone={tone}>{value}</Pill></div>
      <div className="mt-2 text-xs text-ink/50">{label}</div>
    </div>
  );
}
