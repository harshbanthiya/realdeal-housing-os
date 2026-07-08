import Image from "next/image";
import Link from "next/link";
import { Reveal } from "@/components/reveal";
import { projects } from "@/lib/site";
import type { Listing } from "@/lib/listings";

function imageFor(l: Listing) {
  return l.image ?? projects.find((p) => p.name === l.project)?.image;
}

export function ListingGrid({ items }: { items: Listing[] }) {
  return (
    <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((l, i) => {
        const img = imageFor(l);
        return (
          <Reveal key={l.slug} delay={(i % 3) * 0.05}>
            <Link
              href={`/listings/${l.slug}`}
              className="group flex h-full flex-col rounded-2xl border border-mist-deep bg-white p-5 transition-colors hover:bg-mist/30"
            >
              <div
                className={`rdh-zoom relative aspect-[4/3] overflow-hidden rounded-lg ${img ? "" : "border border-dashed border-mist-deep bg-mist/50"}`}
              >
                {img && (
                  <Image
                    src={img.src}
                    alt={img.alt}
                    fill
                    sizes="(max-width: 640px) 100vw, 33vw"
                    className="object-cover"
                  />
                )}
                <span className="absolute left-3 top-3 z-10 rounded-full bg-teal px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
                  {l.type === "rent" ? "For rent" : "For sale"}
                </span>
              </div>
              <h3 className="mt-4 text-base font-semibold leading-snug text-teal group-hover:underline">
                {l.title}
              </h3>
              <p className="mt-1 text-xs text-ink/50">
                {l.location} · {l.config}
                {l.sqft !== "—" ? ` · ${l.sqft} sqft` : ""}
              </p>
              <p className="mt-3 text-lg font-bold text-teal">{l.price}</p>
            </Link>
          </Reveal>
        );
      })}
    </div>
  );
}
