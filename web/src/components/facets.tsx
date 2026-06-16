/**
 * Decorative facet motif - a sparse cluster of triangles echoing the logo
 * roof. Purely ornamental: aria-hidden, pointer-events-none, and it floats
 * only when reduced-motion is not requested (gated by the .facet-float
 * keyframe in globals.css). Used sparingly as a brand accent, not UI color.
 */
const RAMP = ["#c2493d", "#e8412e", "#f0612a", "#e1356b", "#cf1f4f"];

const TRIS = [
  "60,0 30,52 90,52",
  "90,52 60,104 120,104",
  "120,0 90,52 150,52",
  "30,52 0,104 60,104",
  "150,52 120,104 180,104",
];

export function Facets({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 180 104"
      aria-hidden
      className={`pointer-events-none select-none ${className}`}
    >
      {TRIS.map((pts, i) => (
        <polygon key={i} points={pts} fill={RAMP[i % RAMP.length]} opacity={0.9} />
      ))}
    </svg>
  );
}
