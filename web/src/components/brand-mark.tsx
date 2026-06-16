import Link from "next/link";

/**
 * Real Deal Housing brand mark - a vector rebuild of the supplied logo:
 * a navy house body, a tessellated warm roof, and a steel-blue door.
 * Vectorised (not the raster) so it stays crisp at any size and themes
 * cleanly. To use the original raster instead, drop it at
 * /public/logo-original.png and swap <BrandMark/> for an <img>.
 *
 * Roof facets are the brand's geometric language; the same triangle ramp
 * feeds the decorative <Facets/> motif elsewhere on the site.
 */

// Warm roof ramp, sampled from the logo (deep red -> orange -> magenta).
const C = {
  red: "#b3122a",
  scarlet: "#d21f3a",
  orange: "#f0612a",
  flame: "#e8412e",
  magenta: "#e1356b",
  crimson: "#cf1f4f",
};

const ROOF: Array<[string, string]> = [
  ["120,30 102.5,50 137.5,50", C.red],
  ["102.5,50 85,70 120,70", C.magenta],
  ["102.5,50 120,70 137.5,50", C.scarlet],
  ["137.5,50 120,70 155,70", C.flame],
  ["85,70 67.5,90 102.5,90", C.orange],
  ["85,70 102.5,90 120,70", C.crimson],
  ["120,70 102.5,90 137.5,90", C.scarlet],
  ["120,70 137.5,90 155,70", C.flame],
  ["155,70 137.5,90 172.5,90", C.orange],
  ["67.5,90 50,110 85,110", C.magenta],
  ["67.5,90 85,110 102.5,90", C.flame],
  ["102.5,90 85,110 120,110", C.orange],
  ["102.5,90 120,110 137.5,90", C.crimson],
  ["137.5,90 120,110 155,110", C.flame],
  ["137.5,90 155,110 172.5,90", C.orange],
  ["172.5,90 155,110 190,110", C.magenta],
];

export function BrandMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 200"
      className={className}
      role="img"
      aria-label="Real Deal Housing"
    >
      {/* House body */}
      <rect x="70" y="110" width="100" height="72" fill="#1f3d4d" />
      {/* Tessellated roof */}
      {ROOF.map(([pts, fill], i) => (
        <polygon key={i} points={pts} fill={fill} />
      ))}
      {/* Steel-blue door, two facets */}
      <polygon points="120,124 104,138 104,182 120,182" fill="#34ace0" />
      <polygon points="120,124 136,138 136,182 120,182" fill="#1c7fb0" />
    </svg>
  );
}

/**
 * Mark + wordmark lockup. The wordmark is set in the site typeface (Manrope)
 * rather than the original logo font - a deliberate "enhance for web" choice
 * that keeps the lockup consistent with the rest of the site.
 */
export function Logo({
  tone = "dark",
  className = "",
}: {
  tone?: "dark" | "light";
  className?: string;
}) {
  const word = tone === "light" ? "text-white" : "text-teal";
  return (
    <Link
      href="/"
      aria-label="Real Deal Housing - home"
      className={`group inline-flex items-center gap-2.5 ${className}`}
    >
      <span
        className={
          tone === "light"
            ? "flex h-9 w-9 items-center justify-center rounded-xl bg-white/95 p-1 shadow-sm"
            : "flex h-9 w-9 items-center justify-center"
        }
      >
        <BrandMark className="h-full w-full" />
      </span>
      <span
        className={`text-[15px] font-extrabold leading-none tracking-tight ${word}`}
      >
        Real Deal Housing
      </span>
    </Link>
  );
}
