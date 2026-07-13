"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { mapBuildings, company } from "@/lib/site";
import type { Map as MLMap } from "maplibre-gl";

/**
 * Interactive map hero — Gallery White basemap (OpenFreeMap positron, free/no key)
 * with the four focus buildings as pins. Click a pin → camera flies in and a
 * verified-facts panel opens. Map JS lazy-loads on approach so LCP stays text.
 */
export function MapHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let cancelled = false;

    const io = new IntersectionObserver(
      async ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        const maplibregl = (await import("maplibre-gl")).default;
        if (cancelled) return;
        const map = new maplibregl.Map({
          container: el,
          style: "https://tiles.openfreemap.org/styles/positron",
          center: [72.8355, 19.1465], // fallback; fitBounds below frames all pins
          zoom: 12.1,
          pitch: 48,
          bearing: -12,
          scrollZoom: false, // never hijack page scroll
          cooperativeGestures: true,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.on("load", () => !cancelled && setReady(true));

        // Frame all four buildings in the zone the headline does NOT cover:
        // desktop → right half of the canvas; mobile → bottom ~40%.
        const bounds = new maplibregl.LngLatBounds();
        for (const b of mapBuildings) bounds.extend([b.lng, b.lat]);
        const w = el.clientWidth;
        const h = el.clientHeight;
        const narrow = w < 768;
        // fitBounds over-zooms-out when pitched, so fit flat first, then tilt.
        map.fitBounds(bounds, {
          padding: narrow
            ? { top: Math.round(h * 0.55), bottom: 90, left: 44, right: 44 }
            : { top: 140, bottom: 90, left: Math.round(w * 0.52), right: Math.round(w * 0.06) },
          pitch: 0,
          bearing: 0,
          duration: 0,
        });
        map.jumpTo({ pitch: 32, bearing: -8 });

        for (const b of mapBuildings) {
          const pin = document.createElement("button");
          pin.type = "button";
          pin.className = "rdh-pin";
          pin.setAttribute("aria-label", `${b.name}, ${b.location}`);
          pin.innerHTML = `<span class="rdh-pin-dot"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 14V5l4-2v11M6 14V3l6 2v9M9 7.5v.01M9 10v.01M4 7v.01M4 9.5v.01" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 14h14" stroke="white" stroke-width="1.4" stroke-linecap="round"/></svg></span><span class="rdh-pin-label">${b.name}</span>`;
          pin.addEventListener("click", () => {
            setActive(b.slug);
            map.flyTo({ center: [b.lng, b.lat], zoom: 14.4, pitch: 55, duration: 1400 });
          });
          new maplibregl.Marker({ element: pin, anchor: "bottom" })
            .setLngLat([b.lng, b.lat])
            .addTo(map);
        }
      },
      { rootMargin: "300px" }
    );
    io.observe(el);
    return () => {
      cancelled = true;
      io.disconnect();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  const building = mapBuildings.find((b) => b.slug === active);

  return (
    <section className="relative h-[92vh] min-h-[620px] w-full overflow-hidden bg-mist">
      {/* map canvas */}
      <div
        ref={containerRef}
        className={`absolute inset-0 transition-opacity duration-700 ${ready ? "opacity-100" : "opacity-0"}`}
      />

      {/* headline overlay — scrim keeps text legible, map stays draggable below */}
      <div className="pointer-events-none absolute inset-x-0 top-0 bg-gradient-to-b from-white via-white/80 to-transparent pb-24">
        <div className="mx-auto max-w-6xl px-6 pt-10 md:pt-16">
          <p className="pointer-events-auto inline-flex items-center gap-2 border border-mist-deep bg-white/80 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/60">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
            {company.areas.join(" · ")} — {company.years} years
          </p>
          <h1 className="mt-6 text-[clamp(2.2rem,5.5vw,4.5rem)] font-extrabold uppercase leading-[1.0] tracking-tight text-teal">
            {(company.heroStatement ?? [company.tagline]).map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-ink/70 md:text-lg">
            Flats for sale and rent in four towers we know floor by floor —
            Ekta Tripolis, Imperial Heights and Kalpataru Radiance in Goregaon
            West, and the new DLF Westpark launch in Andheri West.
          </p>
          <div className="pointer-events-auto mt-7 flex flex-wrap items-center gap-4">
            <Link
              href="/buy"
              className="rounded-full bg-teal px-7 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              See what&rsquo;s available →
            </Link>
            <span className="hidden font-mono text-[11px] uppercase tracking-[0.15em] text-ink/45 md:inline">
              Tap a building on the map
            </span>
          </div>
        </div>
      </div>

      {/* building facts panel */}
      {building && (
        <div className="absolute inset-x-4 bottom-4 z-10 border border-mist-deep bg-white p-6 md:inset-x-auto md:bottom-8 md:right-8 md:w-96">
          <div className="flex items-start justify-between gap-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink/55">
              {building.location} · {building.status}
              {!building.coordsVerified && (
                <span className="ml-2 bg-mist px-1.5 py-0.5 text-warm">PIN_VERIFY</span>
              )}
            </p>
            <button
              type="button"
              aria-label="Close building details"
              onClick={() => setActive(null)}
              className="-mr-1 -mt-1 px-1 text-ink/40 hover:text-teal"
            >
              ✕
            </button>
          </div>
          <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-teal">{building.name}</h2>
          <ul className="mt-3 space-y-1.5 text-sm text-ink/70">
            {building.facts.map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-warm">·</span> {f}
              </li>
            ))}
          </ul>
          <div className="mt-5 flex gap-5 border-t border-mist-deep pt-4 text-sm font-semibold text-teal">
            <Link href={building.href} className="hover:underline">
              View building →
            </Link>
            <Link href="/buy" className="hover:underline">
              Listings →
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
