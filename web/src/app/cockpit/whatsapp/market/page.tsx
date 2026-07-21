import Link from "next/link";
import { Card, Pill, Mono, PanelTitle, type Tone } from "@/components/ui/primitives";
import { getOurBuildingOffers, getOfferMatrix, waLink, type WaOffer } from "@/lib/cockpit/whatsapp";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

const TXN_TONE: Record<string, Tone> = { rent: "active", sale: "ready", pg: "neutral", unknown: "neutral" };
const TXN_LABEL: Record<string, string> = { rent: "Rent", sale: "Sale", pg: "PG", unknown: "Unclear" };

function fmt(ts: string): string {
  return new Date(ts).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function bhkLabel(bhk: number | null): string {
  if (bhk == null) return "BHK unstated";
  if (bhk === 0.5) return "RK";
  return `${bhk % 1 === 0 ? bhk.toFixed(0) : bhk} BHK`;
}

function OfferRow({ o, showBuilding }: { o: WaOffer; showBuilding?: boolean }) {
  return (
    <li className="py-2.5">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink/50">
        <span>{fmt(o.occurredAt)}</span>
        <Pill tone={TXN_TONE[o.transaction] ?? "neutral"}>{TXN_LABEL[o.transaction]}</Pill>
        {o.bhk != null && <Mono>{bhkLabel(o.bhk)}</Mono>}
        {showBuilding && o.buildingName && <span className="font-medium text-teal">{o.buildingName}</span>}
        {o.priceText && <Mono className="text-amber">{o.priceText}</Mono>}
        {o.areaText && <Mono>{o.areaText}</Mono>}
        {o.furnished && <Mono>{o.furnished}</Mono>}
        {o.locality && <span>{o.locality}</span>}
      </div>
      <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-ink/50">
        <span className="font-medium text-ink/70">{o.senderName || o.senderPhone || "unknown sender"}</span>
        {o.senderPhone && (
          <a href={waLink(o.senderPhone)} target="_blank" className="text-teal/70 hover:text-teal">wa.me ↗</a>
        )}
        {o.contactId && (
          <Link href={`/cockpit/contacts/c/${o.contactId}`} className="text-teal hover:underline">contact →</Link>
        )}
        <span className="text-ink/40">in {o.chatTitle || "chat"}</span>
      </div>
      {o.body && (
        <details className="mt-1">
          <summary className="cursor-pointer text-[12px] text-ink/60 hover:text-teal">
            <span className="align-middle">{o.body.slice(0, 110)}{o.body.length > 110 ? "…" : ""}</span>
          </summary>
          <p className="mt-1 whitespace-pre-wrap rounded-md bg-mist/50 p-2 text-[12px] text-ink/80">{o.body}</p>
        </details>
      )}
    </li>
  );
}

export default async function MarketPage() {
  const [ours, matrix] = await Promise.all([getOurBuildingOffers(), getOfferMatrix()]);

  const byBuilding = new Map<string, WaOffer[]>();
  for (const o of ours) {
    const k = o.buildingName || "Other";
    byBuilding.set(k, [...(byBuilding.get(k) ?? []), o]);
  }
  // matrix boxes: rent then sale, by BHK descending frequency ordering (2,3 first)
  const boxes = new Map<string, WaOffer[]>();
  for (const o of matrix) {
    if (o.transaction === "unknown" && o.bhk == null) continue; // noise bucket
    const k = `${o.transaction}|${o.bhk ?? "?"}`;
    boxes.set(k, [...(boxes.get(k) ?? []), o]);
  }
  const boxOrder = [...boxes.entries()].sort((a, b) => {
    const [ta] = a[0].split("|"); const [tb] = b[0].split("|");
    if (ta !== tb) return ["rent", "sale", "pg", "unknown"].indexOf(ta) - ["rent", "sale", "pg", "unknown"].indexOf(tb);
    return b[1].length - a[1].length;
  });

  return (
    <div className="px-6 py-7">
      <Link href="/cockpit/whatsapp" className="text-[12px] text-ink/50 hover:text-teal">← WhatsApp</Link>
      <div className="mt-3 mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Broker market</h1>
        <p className="mt-1 text-[13px] text-ink/60">
          Auto-parsed from broker-group posts · {matrix.length} offers (30d) · refreshed every ingest cycle
        </p>
      </div>

      {/* OUR BUILDINGS */}
      <Card className="mb-6 border-teal/30 p-4">
        <PanelTitle hint={`${ours.length} mentions · 90d`}>Our buildings</PanelTitle>
        {ours.length === 0 && <p className="mt-2 text-[13px] text-ink/50">No mentions yet.</p>}
        <div className="mt-2 grid gap-5 lg:grid-cols-3">
          {["Imperial Heights", "Kalpataru Radiance", "Ekta Tripolis"].map((name) => {
            const list = byBuilding.get(name) ?? [];
            return (
              <div key={name} className="rounded-lg border border-mist-deep p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-teal">{name}</span>
                  <Mono className="text-[11px]">{list.length}</Mono>
                </div>
                <ul className="mt-1 max-h-[420px] divide-y divide-mist overflow-y-auto">
                  {list.slice(0, 30).map((o) => <OfferRow key={o.id} o={o} />)}
                  {list.length === 0 && <p className="py-2 text-[12px] text-ink/45">Quiet.</p>}
                </ul>
              </div>
            );
          })}
        </div>
      </Card>

      {/* TRANSACTION × BHK MATRIX */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {boxOrder.map(([key, list]) => {
          const [txn, bhk] = key.split("|");
          return (
            <Card key={key} className="p-4">
              <div className="flex items-center justify-between">
                <PanelTitle hint={`${list.length}`}>
                  {bhk === "?" ? "" : `${bhk === "0.5" ? "RK" : bhk + " BHK"} · `}{TXN_LABEL[txn]}
                </PanelTitle>
              </div>
              <ul className="mt-1 max-h-[380px] divide-y divide-mist overflow-y-auto">
                {list.slice(0, 25).map((o) => <OfferRow key={o.id} o={o} showBuilding />)}
              </ul>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
