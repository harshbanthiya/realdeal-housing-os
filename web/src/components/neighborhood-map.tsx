"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { Map as MLMap, Marker } from "maplibre-gl";
import { neighborhoods, POI_CATEGORIES } from "@/lib/neighborhoods";

/**
 * Tavalo-style "Explore the neighborhood" — Gallery White basemap, the
 * building at centre, categorised POI pins (OSM data) with a toggleable
 * legend. Lazy-loads maplibre on approach; scroll never hijacked.
 */
export function NeighborhoodMap({
  slug,
  buildingName,
  lat,
  lng,
}: {
  slug: string;
  buildingName: string;
  lat: number;
  lng: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Record<string, Marker[]>>({});
  const mapRef = useRef<MLMap | null>(null);
  const [ready, setReady] = useState(false);
  const [active, setActive] = useState<Set<string>>(
    () => new Set(POI_CATEGORIES.map((c) => c.key))
  );

  const pois = neighborhoods[slug] ?? {};

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
          center: [lng, lat],
          zoom: 13.6,
          scrollZoom: false,
          cooperativeGestures: true,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.on("load", () => !cancelled && setReady(true));

        // building pin (same glyph as the hero)
        const home = document.createElement("div");
        home.className = "rdh-pin";
        home.innerHTML = `<span class="rdh-pin-dot"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 14V5l4-2v11M6 14V3l6 2v9" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 14h14" stroke="white" stroke-width="1.4" stroke-linecap="round"/></svg></span><span class="rdh-pin-label">${buildingName}</span>`;
        new maplibregl.Marker({ element: home, anchor: "bottom" }).setLngLat([lng, lat]).addTo(map);

        // category pins — tooltip via maplibre popup (hover on desktop, tap on touch)
        for (const cat of POI_CATEGORIES) {
          markersRef.current[cat.key] = (pois[cat.key] ?? []).map((p) => {
            const dot = document.createElement("div");
            dot.className = "rdh-poi";
            dot.style.setProperty("--poi", cat.color);
            dot.setAttribute("role", "button");
            dot.setAttribute("aria-label", `${p.name} (${cat.label})`);
            dot.innerHTML = `<span class="rdh-poi-dot"></span>`;
            const popup = new maplibregl.Popup({
              offset: 10,
              closeButton: false,
              className: "rdh-popup",
            }).setText(p.name);
            const marker = new maplibregl.Marker({ element: dot })
              .setLngLat([p.lng, p.lat])
              .setPopup(popup) // toggles on click/tap
              .addTo(map);
            dot.addEventListener("mouseenter", () => popup.isOpen() || marker.togglePopup());
            dot.addEventListener("mouseleave", () => popup.isOpen() && marker.togglePopup());
            return marker;
          });
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, lat, lng]);

  // visibility is derived from state so toggles stay correct even if the map
  // finishes loading after the user has already clicked categories
  useEffect(() => {
    for (const cat of POI_CATEGORIES) {
      const show = active.has(cat.key);
      for (const m of markersRef.current[cat.key] ?? []) {
        m.getElement().style.display = show ? "" : "none";
        if (!show && m.getPopup()?.isOpen()) m.togglePopup();
      }
    }
  }, [active, ready]);

  const toggle = (key: string) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="grid gap-6 md:grid-cols-[220px_1fr]">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/55">
          Explore the neighbourhood
        </p>
        <ul className="mt-4 space-y-1">
          {POI_CATEGORIES.map((c) => {
            const count = (pois[c.key] ?? []).length;
            if (count === 0) return null;
            const on = active.has(c.key);
            return (
              <li key={c.key}>
                <button
                  type="button"
                  onClick={() => toggle(c.key)}
                  aria-pressed={on}
                  className={`flex w-full items-center gap-2.5 border border-transparent px-2 py-1.5 text-left text-sm transition-opacity hover:border-mist-deep ${on ? "" : "opacity-35"}`}
                >
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                  <span className="font-medium text-teal">{c.label}</span>
                  <span className="ml-auto font-mono text-[10px] text-ink/45">{count}</span>
                </button>
              </li>
            );
          })}
        </ul>
        <p className="mt-4 font-mono text-[10px] leading-relaxed text-ink/40">
          Data © OpenStreetMap contributors · locations indicative
        </p>
      </div>
      <div className="relative h-[420px] overflow-hidden rounded-2xl border border-mist-deep bg-mist md:h-[480px]">
        <div
          ref={containerRef}
          className={`absolute inset-0 transition-opacity duration-700 ${ready ? "opacity-100" : "opacity-0"}`}
        />
      </div>
    </div>
  );
}
