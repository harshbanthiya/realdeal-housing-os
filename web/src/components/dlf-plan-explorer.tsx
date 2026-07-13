"use client";

import { useMemo, useState } from "react";
import { ZoomImage } from "@/components/zoom-image";
import { dlfTowers, type DlfConfig } from "@/lib/dlf-plans";

const fmt = (n: number) => n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
const WA_LINK =
  "https://wa.me/918291293889?text=Hi%20Padmini%2C%20I%27m%20interested%20in%20DLF%20Westpark%20%E2%80%94%20can%20you%20share%20details%3F";

function areas(c: DlfConfig) {
  return `${fmt(c.carpetSqft)} sqft carpet${c.balconySqft > 0 ? ` · ${fmt(c.balconySqft)} sqft balcony` : ""}`;
}

/**
 * Floor-selector (flostefoy pattern, v1 without SVG unit polygons — unit list
 * stands in for plate hotspots; polygons are a later polish, see plan §4c).
 * Two views: floor-by-floor, or all configurations as a flat list.
 * Pricing is deliberately absent: dynamic launch pricing is handled by the
 * sales team on call/WhatsApp.
 */
export function DlfPlanExplorer() {
  const [view, setView] = useState<"floors" | "list">("floors");
  const [towerId, setTowerId] = useState(dlfTowers[0].id);
  const tower = dlfTowers.find((t) => t.id === towerId)!;
  const [floorN, setFloorN] = useState(3);
  const [openConfig, setOpenConfig] = useState<DlfConfig | null>(null);

  const floor = tower.floors.find((f) => f.n === floorN) ?? tower.floors[0];
  const floorConfigs = useMemo(
    () => tower.configs.filter((c) => floor.configs.includes(c.id)),
    [tower, floor]
  );

  const pickTower = (id: string) => {
    setTowerId(id);
    setFloorN(3);
    setOpenConfig(null);
  };

  return (
    <div>
      {/* view + tower pickers */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {dlfTowers.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => pickTower(t.id)}
              className={`border px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] transition-colors ${
                t.id === towerId && view === "floors"
                  ? "border-teal bg-teal text-white"
                  : "border-mist-deep text-ink/60 hover:border-teal hover:text-teal"
              } ${view === "list" ? "opacity-40" : ""}`}
              disabled={view === "list"}
            >
              {t.name}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {(["floors", "list"] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={`border px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] transition-colors ${
                view === v
                  ? "border-teal bg-teal text-white"
                  : "border-mist-deep text-ink/60 hover:border-teal hover:text-teal"
              }`}
            >
              {v === "floors" ? "By floor" : "All configurations"}
            </button>
          ))}
        </div>
      </div>

      {view === "list" ? (
        /* ——— flat listing view: every configuration across all towers ——— */
        <div className="mt-10 space-y-12">
          {dlfTowers.map((t) => (
            <div key={t.id}>
              <p className="border-t border-mist-deep pt-6 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/55">
                {t.name} · {t.configs.length} configurations
              </p>
              <div className="mt-5 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {t.configs.map((c) => (
                  <div key={c.id} className="border border-mist-deep p-5">
                    {c.planImage && (
                      <ZoomImage
                        src={c.planImage}
                        alt={`${c.label} unit plan, ${t.name}, DLF Westpark`}
                        sizes="(max-width: 640px) 100vw, 33vw"
                        className="aspect-[4/3] border border-mist-deep bg-white"
                        imgClassName="object-contain"
                      />
                    )}
                    <div className="mt-4 flex items-baseline justify-between gap-2">
                      <span className="text-lg font-bold text-teal">{c.label}</span>
                      <span className="font-mono text-[10px] uppercase tracking-wide text-ink/50">
                        Unit {c.unit}
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-ink/55">{areas(c)}</p>
                    <p className="mt-2 text-xs text-ink/50">Floors {c.floors}</p>
                    <a href={WA_LINK} className="mt-4 inline-block text-sm font-semibold text-teal hover:underline">
                      Pricing on request →
                    </a>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-8 grid gap-8 lg:grid-cols-[88px_1fr_320px]">
          {/* floor rail */}
          <div className="flex gap-1 overflow-x-auto lg:max-h-[640px] lg:flex-col-reverse lg:overflow-y-auto lg:overflow-x-visible">
            {tower.floors.map((f) => (
              <button
                key={f.n}
                type="button"
                onClick={() => {
                  setFloorN(f.n);
                  setOpenConfig(null);
                }}
                className={`shrink-0 border px-3 py-1.5 font-mono text-xs transition-colors ${
                  f.n === floor.n
                    ? "border-teal bg-teal text-white"
                    : f.kind === "refuge"
                      ? "border-dashed border-mist-deep text-ink/35"
                      : "border-mist-deep text-ink/60 hover:border-teal hover:text-teal"
                }`}
                aria-label={`Floor ${f.n}${f.kind === "refuge" ? " — refuge floor" : ""}`}
              >
                {String(f.n).padStart(2, "0")}
              </button>
            ))}
          </div>

          {/* floor plate */}
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/55">
              {tower.name} · Floor {floor.n}
              {floor.kind === "refuge" && " · Refuge floor — no residences"}
              {floor.kind === "refuge-variant" && " · Refuge floor"}
              {floor.kind === "duplex" && " · Duplex level"}
            </p>
            {floor.plate ? (
              <ZoomImage
                src={floor.plate}
                alt={`${tower.name} floor ${floor.n} plate plan, DLF Westpark`}
                sizes="(max-width: 1024px) 100vw, 60vw"
                className="mt-4 aspect-[4/3] border border-mist-deep bg-white"
                imgClassName="object-contain"
              />
            ) : (
              <div className="mt-4 flex aspect-[4/3] items-center justify-center border border-dashed border-mist-deep bg-mist/40 font-mono text-xs text-ink/40">
                REFUGE FLOOR — NO RESIDENCES
              </div>
            )}
            <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.15em] text-ink/40">
              Click plan to enlarge · source: official brochure · not to scale
            </p>
          </div>

          {/* units on this floor */}
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/55">
              Residences on floor {floor.n}
            </p>
            <div className="mt-4 space-y-2">
              {floorConfigs.length === 0 && (
                <p className="text-sm text-ink/50">None — this is a refuge level.</p>
              )}
              {floorConfigs.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setOpenConfig(openConfig?.id === c.id ? null : c)}
                  className={`block w-full border p-4 text-left transition-colors ${
                    openConfig?.id === c.id
                      ? "border-teal bg-mist/40"
                      : "border-mist-deep hover:border-teal"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-base font-bold text-teal">{c.label}</span>
                    <span className="font-mono text-[10px] uppercase tracking-wide text-ink/50">
                      Unit {c.unit}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-ink/55">{areas(c)}</p>
                </button>
              ))}
            </div>

            {openConfig && (
              <div className="mt-5 border border-mist-deep bg-white p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink/50">
                  {openConfig.id}
                </p>
                {openConfig.planImage && (
                  <ZoomImage
                    src={openConfig.planImage}
                    alt={`${openConfig.label} unit plan, ${tower.name}, DLF Westpark`}
                    sizes="320px"
                    className="mt-3 aspect-[4/3] border border-mist-deep"
                    imgClassName="object-contain"
                  />
                )}
                <dl className="mt-4 space-y-1.5 text-sm text-ink/70">
                  <div className="flex justify-between"><dt>Carpet area</dt><dd className="font-semibold text-teal">{fmt(openConfig.carpetSqft)} sqft</dd></div>
                  <div className="flex justify-between"><dt>Balcony</dt><dd>{openConfig.balconySqft > 0 ? `${fmt(openConfig.balconySqft)} sqft` : "—"}</dd></div>
                  <div className="flex justify-between"><dt>Total</dt><dd>{fmt(openConfig.totalSqft)} sqft</dd></div>
                  <div className="flex justify-between gap-4"><dt>Floors</dt><dd className="text-right font-mono text-xs">{openConfig.floors}</dd></div>
                </dl>
                <p className="mt-4 border-t border-mist-deep pt-3 text-xs leading-relaxed text-ink/55">
                  Launch pricing is dynamic — our team shares the current price
                  list for this configuration on call or WhatsApp.
                </p>
                <a
                  href={WA_LINK}
                  className="mt-4 block rounded-full bg-teal px-5 py-3 text-center text-sm font-semibold text-white transition-opacity hover:opacity-90"
                >
                  Get pricing for this layout →
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
