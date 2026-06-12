import { Reveal } from "@/components/reveal";
import type { Listing } from "@/lib/site";

export function ListingGrid({ items }: { items: Listing[] }) {
  return (
    <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((l, i) => (
        <Reveal key={l.title + i} delay={(i % 3) * 0.05}>
          <div className="flex h-full flex-col rounded-2xl border border-mist-deep bg-white p-5">
            <div className="relative aspect-[4/3] rounded-lg border border-dashed border-mist-deep bg-mist/50">
              <span className="absolute left-3 top-3 rounded-full bg-teal px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
                {l.type === "rent" ? "For rent" : "For sale"}
              </span>
            </div>
            <h3 className="mt-4 text-base font-semibold leading-snug text-teal">{l.title}</h3>
            <p className="mt-1 text-xs text-ink/50">
              {l.location} · {l.config}
              {l.sqft !== "—" ? ` · ${l.sqft} sqft` : ""}
            </p>
            <p className="mt-3 text-lg font-bold text-teal">{l.price}</p>
          </div>
        </Reveal>
      ))}
    </div>
  );
}
