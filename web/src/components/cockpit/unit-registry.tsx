"use client";

import { useMemo, useState } from "react";
import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import type { UnitRegistry as UnitRegistryData, UnitCell, UnitTimelineEvent, RegParty } from "@/lib/cockpit/types";

const STATUS_META: Record<UnitCell["status"], { label: string; dot: string; cell: string; tone: Tone }> = {
  tenanted: { label: "Tenanted", dot: "bg-emerald-500", cell: "border-emerald-300 bg-emerald-50 text-emerald-900", tone: "ready" },
  owned: { label: "Owner-held", dot: "bg-teal", cell: "border-teal/40 bg-teal/10 text-teal", tone: "active" },
  registered: { label: "Registered", dot: "bg-amber-500", cell: "border-amber-300 bg-amber-50 text-amber-900", tone: "review" },
  unknown: { label: "No data", dot: "bg-mist-deep", cell: "border-mist bg-white text-ink/30", tone: "neutral" },
};
const CAT_TONE: Record<string, Tone> = { ownership: "active", tenancy: "ready", encumbrance: "review", other: "neutral" };

function inr(n?: number): string {
  if (!n) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}
function ymd(d?: string): string { return d ? d.slice(0, 10) : "—"; }
function expiringTone(end?: string): Tone {
  if (!end) return "neutral";
  const days = (new Date(end).getTime() - Date.now()) / 86_400_000;
  if (days < 0) return "blocked";
  if (days < 183) return "review";
  return "ready";
}

export function UnitRegistry({ data }: { data: UnitRegistryData }) {
  const towers = data.towers.length ? data.towers : [{ letter: "", label: "All units", floors: 1, unitsPerFloor: 6, unitCount: data.units.length }];
  const [tower, setTower] = useState(towers[0]?.letter ?? "");
  const [selected, setSelected] = useState<string | null>(null);

  const tUnits = useMemo(() => data.units.filter((u) => u.tower === tower), [data.units, tower]);
  const byPos = useMemo(() => { const m = new Map<string, UnitCell>(); for (const u of tUnits) m.set(`${u.floor}-${u.position}`, u); return m; }, [tUnits]);
  const sel = selected ? data.units.find((u) => `${u.tower}-${u.flat}` === selected) ?? null : null;
  const tMeta = towers.find((t) => t.letter === tower) ?? towers[0];

  if (!data.units.length) {
    return <Card className="p-6 text-sm text-ink/55">No units for {data.buildingName} yet.</Card>;
  }

  const s = data.stats;
  const perFloor = Math.max(tMeta.unitsPerFloor ?? data.unitsPerFloor, 1);
  const floors = Array.from({ length: Math.max(tMeta.floors, 1) }, (_, i) => Math.max(tMeta.floors, 1) - i);

  return (
    <div className="space-y-6">
      {/* stats strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat n={s.registrations} label="Registrations parsed" sub={`${s.withRegistration} units · ${s.panCount} PANs`} />
        <Stat n={`${s.occupancyPct}%`} label="Tenanted (of mapped)" sub={`${s.tenanted} active leases`} tone="ready" />
        <Stat n={s.owned} label="Owner-held" sub={`${s.mappedUnits} units with data`} tone="active" />
        <Stat n={inr(s.avgRent)} label="Avg monthly rent" sub="active leases" />
        <Stat n={s.expiring12mo} label="Leases expiring ≤12mo" sub={`${s.expiring6mo} within 6mo`} tone={s.expiring6mo ? "review" : "neutral"} />
        <Stat n={s.minPrice ? `${inr(s.minPrice)}–${inr(s.maxPrice)}` : "—"} label="Sale price range" sub={`avg tenure ${s.avgOwnershipYears}y`} />
      </div>

      {/* tower switcher */}
      <div className="flex flex-wrap items-center gap-2">
        {towers.map((t) => (
          <button key={t.letter} onClick={() => { setTower(t.letter); setSelected(null); }}
            className={`rounded-full border px-3.5 py-1 text-[13px] font-medium transition ${
              t.letter === tower ? "border-teal bg-teal text-white" : "border-mist-deep text-ink/55 hover:text-teal"}`}>
            {t.label} <span className="opacity-60">· {t.unitCount}</span>
          </button>
        ))}
        <span className="ml-auto flex flex-wrap items-center gap-3 text-[12px] text-ink/55">
          {(Object.keys(STATUS_META) as UnitCell["status"][]).map((k) => (
            <span key={k} className="inline-flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-full ${STATUS_META[k].dot}`} />{STATUS_META[k].label}</span>
          ))}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
        {/* building stack */}
        <Card className="overflow-hidden p-0">
          <div className="border-b border-mist px-4 py-2 text-[12px] text-ink/45">{tMeta.label} · {tMeta.floors} floors × {perFloor}/floor (inferred grid)</div>
          <div className="max-h-[620px] overflow-y-auto p-3">
            {floors.map((fl) => (
              <div key={fl} className="flex items-center gap-2 border-b border-mist/60 py-1.5 last:border-0">
                <span className="w-9 shrink-0 text-right text-[11px] tabular-nums text-ink/40">{fl}</span>
                <div className="grid flex-1 gap-1.5" style={{ gridTemplateColumns: `repeat(${perFloor}, minmax(0, 1fr))` }}>
                  {Array.from({ length: perFloor }, (_, i) => i + 1).map((pos) => {
                    const u = byPos.get(`${fl}-${pos}`);
                    const meta = STATUS_META[u?.status ?? "unknown"];
                    const key = u ? `${u.tower}-${u.flat}` : "";
                    return (
                      <button key={pos} onClick={() => u && setSelected(key)} disabled={!u}
                        title={u ? `Flat ${u.flat} — ${meta.label}` : "no unit"}
                        className={`h-9 rounded-md border text-[11px] font-medium tabular-nums transition ${meta.cell} ${
                          u ? "cursor-pointer hover:ring-2 hover:ring-teal/40" : "cursor-default opacity-50"} ${selected === key ? "ring-2 ring-teal" : ""}`}>
                        {u ? u.flat : ""}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-3">
          {sel ? <UnitDetail unit={sel} /> : <Card className="p-5 text-sm text-ink/50">Select a unit to see its full ownership &amp; tenancy record.</Card>}
        </div>
      </div>
    </div>
  );
}

function UnitDetail({ unit }: { unit: UnitCell }) {
  const meta = STATUS_META[unit.status];
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-teal">Flat {unit.flat}</h3>
        <Pill tone={meta.tone}>{meta.label}</Pill>
      </div>
      <p className="mt-0.5 text-[12px] text-ink/45">Tower {unit.tower} · floor {unit.floor} · {unit.registrationCount} registration{unit.registrationCount === 1 ? "" : "s"}</p>

      <div className="mt-4 grid grid-cols-2 gap-3 text-[13px]">
        <Field label={unit.ownerContact ? "Owner (from contacts)" : "Current owner"} value={unit.currentOwner ?? "—"} />
        <Field label="Owned since" value={ymd(unit.ownerSince)} />
        <Field label="Last sale price" value={inr(unit.lastPrice)} />
        <Field label="Active tenant" value={unit.currentTenant ?? "—"} />
        {unit.currentTenant && <Field label="Rent / month" value={inr(unit.rent)} />}
        {unit.currentTenant && (
          <div>
            <div className="text-[11px] uppercase tracking-wide text-ink/40">Lease expires</div>
            <Pill tone={expiringTone(unit.tenancyEnd)}>{ymd(unit.tenancyEnd)}</Pill>
          </div>
        )}
      </div>

      {unit.events.length === 0 ? (
        <p className="mt-5 text-[12px] text-ink/40">No IGR registrations parsed for this unit yet — owner shown from imported contacts where available.</p>
      ) : (
        <div className="mt-5 space-y-2.5">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink/45">Registration timeline</div>
          {unit.events.map((e, i) => <EventCard key={i} e={e} />)}
        </div>
      )}
      <p className="mt-4 text-[11px] text-ink/35">Sourced from IGR registrations (review-gated, parsed_candidate). Names romanized from Devanagari; verify before action. PAN enables later business-profile enrichment.</p>
    </Card>
  );
}

function EventCard({ e }: { e: UnitTimelineEvent }) {
  const headline = e.category === "tenancy"
    ? (e.rent ? `${inr(e.rent)}/mo` : "lease")
    : (e.consideration ? inr(e.consideration) : "—");
  return (
    <div className="rounded-lg border border-mist bg-white p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13px] font-medium text-ink/85">{e.year || "—"} · {e.docType.replace(/_/g, " ")}</span>
        <span className={`text-[12px] tabular-nums ${e.category === "tenancy" && expiringTone(e.tenancyEnd) === "blocked" ? "text-red-600" : "text-ink/75"}`}>{headline}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        <Pill tone={CAT_TONE[e.category] ?? "neutral"}>{e.category}</Pill>
        {e.active && <Pill tone={expiringTone(e.tenancyEnd)}>active{e.tenancyEnd ? ` · to ${ymd(e.tenancyEnd)}` : " · end unknown"}</Pill>}
        <Mono className="text-[11px] text-ink/40">doc {e.docNumber}{e.sro ? ` · ${e.sro}` : ""}{e.date ? ` · ${ymd(e.date)}` : ""}</Mono>
      </div>

      {/* money + area row */}
      {(e.marketValue || e.stampDuty || e.regFee || e.area || e.deposit || e.category === "tenancy") && (
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-ink/55 sm:grid-cols-3">
          {e.category === "tenancy" ? <Mini label="Lease period" v={`${ymd(e.tenancyStart)} to ${ymd(e.tenancyEnd)}`} /> : null}
          {e.marketValue ? <Mini label="Market value" v={inr(e.marketValue)} /> : null}
          {e.stampDuty ? <Mini label="Stamp duty" v={inr(e.stampDuty)} /> : null}
          {e.regFee ? <Mini label="Reg fee" v={inr(e.regFee)} /> : null}
          {e.deposit ? <Mini label="Deposit" v={inr(e.deposit)} /> : null}
          {e.area ? <Mini label="Area" v={e.area.replace(/^क्षेत्रफळ\s*/, "")} /> : null}
        </div>
      )}

      {/* parties */}
      <div className="mt-2 space-y-1.5">
        {e.parties.map((p, i) => <PartyRow key={i} p={p} />)}
      </div>
    </div>
  );
}

function PartyRow({ p }: { p: RegParty }) {
  return (
    <div className="rounded-md bg-mist/30 px-2.5 py-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[12.5px] font-medium text-ink/85">{p.english}</span>
        <span className="shrink-0 text-[10px] uppercase tracking-wide text-ink/45">{p.role}</span>
      </div>
      {p.devanagari && p.devanagari !== p.english && <div className="text-[11px] text-ink/45">{p.devanagari}</div>}
      <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[10.5px] text-ink/50">
        {p.pan && <span>PAN <Mono className="text-ink/70">{p.pan}</Mono></span>}
        {p.age ? <span>age {p.age}</span> : null}
        {p.type && p.type !== "individual" && <span className="text-teal">{p.type}</span>}
      </div>
      {p.address && <div className="mt-0.5 line-clamp-2 text-[10.5px] text-ink/40">{p.address}</div>}
    </div>
  );
}

function Stat({ n, label, sub, tone = "neutral" }: { n: string | number; label: string; sub?: string; tone?: Tone }) {
  const accent = tone === "ready" ? "text-emerald-600" : tone === "active" ? "text-teal" : tone === "review" ? "text-amber-600" : "text-ink";
  return (
    <Card className="p-3">
      <div className={`text-xl font-semibold tabular-nums ${accent}`}>{n}</div>
      <div className="text-[12px] text-ink/60">{label}</div>
      {sub && <div className="text-[11px] text-ink/40">{sub}</div>}
    </Card>
  );
}
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-ink/40">{label}</div>
      <div className="text-ink/85">{value}</div>
    </div>
  );
}
function Mini({ label, v }: { label: string; v: string }) {
  return <span><span className="text-ink/35">{label}:</span> <span className="text-ink/70 tabular-nums">{v}</span></span>;
}
