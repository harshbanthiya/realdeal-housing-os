/**
 * Seeded architectural photography placeholder.
 *
 * Picks a deterministic image (stable per `seed`) from a curated pool of real
 * Unsplash architecture / interior / skyline photos. These are SWAP-IN SLOTS:
 * replace the chosen URL with a real shoot / listing photo (or a Wix CMS image
 * URL) when available. The pool is curated so a placeholder is always
 * on-subject (a building or interior), never a random portrait.
 *
 * Plain <img> (not next/image) is intentional: it avoids the remote-optimizer
 * round-trip for external placeholders and keeps CLS at zero via the reserved
 * aspect-ratio wrapper at every call site.
 */

// Verified Unsplash photo IDs (architecture, interiors, skylines).
const POOL = [
  "1545324418-cc1a3fa10c00", // modern luxury house + pool
  "1512917774080-9991f1c4c750", // city skyline at dusk
  "1480714378408-67cf0d13bc1b", // glass towers, upward
  "1486406146926-c627a92ad1ab", // skyscraper facade
  "1502672260266-1c1ef2d93688", // bright apartment interior
  "1560448204-e02f11c3d0e2", // staged living room
  "1502005229762-cf1b2da7c5d6", // living room with view
  "1564013799919-ab600027ffc6", // contemporary house exterior
  "1600596542815-ffad4c1539a9", // modern living interior
  "1600585154340-be6161a56a0c", // suburban modern home
  "1600607687939-ce8a6c25118c", // interior corridor
  "1512453979798-5ea266f8880c", // residential high-rise
  "1449844908441-8829872d2607", // glass apartment block
  "1567496898669-ee935f5f647a", // luxury living room
  "1570129477492-45c003edd2be", // tall residential tower
  "1605276374104-dee2a0ed3cd6", // balcony / terrace
  "1560185007-cde436f6a4d0", // apartment building facade
  "1582268611958-ebfd161ef9cf", // bedroom interior
  "1554995207-c18c203602cb", // modern building exterior
];

function pick(seed: string) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return POOL[Math.abs(h) % POOL.length];
}

export function Media({
  seed,
  w,
  h,
  alt,
  priority = false,
  className = "",
}: {
  seed: string;
  w: number;
  h: number;
  alt: string;
  priority?: boolean;
  className?: string;
}) {
  const src = `https://images.unsplash.com/photo-${pick(
    seed
  )}?w=${w}&h=${h}&fit=crop&crop=entropy&q=70&auto=format`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      width={w}
      height={h}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : undefined}
      decoding="async"
      data-swap-in={seed}
      className={`h-full w-full object-cover ${className}`}
    />
  );
}

/**
 * Framed media: reserved aspect-ratio box + rounded frame + a faint inner
 * ring so the photo sits like a gallery print. Children render on top
 * (badges, captions).
 */
export function Frame({
  ratio = "aspect-[4/3]",
  className = "",
  children,
}: {
  ratio?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-mist ring-1 ring-inset ring-mist-deep ${ratio} ${className}`}
    >
      {children}
    </div>
  );
}
