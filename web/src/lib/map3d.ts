import type { Map as MLMap } from "maplibre-gl";

/**
 * Adds OSM building extrusions to a loaded MapLibre map. The geometry ships in
 * the vector tiles we already download (openmaptiles `building` layer), so this
 * costs no extra network — only a small GPU draw that is disabled below z13.5
 * and grows in smoothly as the camera flies closer.
 */
export function add3dBuildings(map: MLMap) {
  const style = map.getStyle();
  const srcId = Object.entries(style.sources).find(([, s]) => s.type === "vector")?.[0];
  if (!srcId || map.getLayer("rdh-3d-buildings")) return;
  // Insert below the first symbol layer so street/place labels stay readable.
  const labelLayerId = style.layers.find((l) => l.type === "symbol")?.id;
  map.addLayer(
    {
      id: "rdh-3d-buildings",
      source: srcId,
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: 13,
      paint: {
        "fill-extrusion-color": "#dde3e8",
        // Grow from flat at z13 to full OSM height by z14.5 — no pop-in.
        "fill-extrusion-height": [
          "interpolate",
          ["linear"],
          ["zoom"],
          13,
          0,
          14.5,
          ["coalesce", ["get", "render_height"], 12],
        ],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.6,
      },
    },
    labelLayerId
  );
}
