import Link from "next/link";
import { Reveal } from "@/components/reveal";
import { Media, Frame } from "@/components/media";
import type { Project, Listing } from "@/lib/site";

const seed = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function ProjectCard({
  project: p,
  delay = 0,
}: {
  project: Project;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <Link
        href={`/projects/${p.slug}`}
        className="group block overflow-hidden rounded-2xl ring-1 ring-mist-deep transition-all duration-300 hover:-translate-y-1 hover:ring-teal/30"
      >
        <Frame ratio="aspect-[16/10]" className="rounded-none ring-0">
          <Media
            seed={`rdh-${p.slug}-tower`}
            w={760}
            h={475}
            alt={`${p.name}, ${p.location}`}
            className="transition-transform duration-500 group-hover:scale-[1.04]"
          />
          {p.isNew && (
            <span className="absolute left-4 top-4 rounded-full bg-warm px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
              New
            </span>
          )}
        </Frame>
        <div className="p-6">
          <h3 className="text-xl font-bold text-teal">{p.name}</h3>
          <p className="mt-1.5 text-sm text-ink/55">
            {p.location} · {p.meta}
          </p>
          <span className="mt-4 inline-block text-sm font-semibold text-teal underline-offset-4 group-hover:underline">
            View project →
          </span>
        </div>
      </Link>
    </Reveal>
  );
}

export function ListingCard({
  listing: l,
  delay = 0,
}: {
  listing: Listing;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <div className="group flex h-full flex-col overflow-hidden rounded-2xl ring-1 ring-mist-deep transition-all duration-300 hover:-translate-y-1 hover:ring-teal/30">
        <Frame ratio="aspect-[4/3]" className="rounded-none ring-0">
          <Media
            seed={`rdh-${seed(l.title)}`}
            w={560}
            h={420}
            alt={l.title}
            className="transition-transform duration-500 group-hover:scale-[1.04]"
          />
          <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-teal shadow-sm">
            {l.type === "rent" ? "For rent" : "For sale"}
          </span>
        </Frame>
        <div className="flex flex-1 flex-col p-5">
          <h3 className="text-base font-semibold leading-snug text-teal">
            {l.title}
          </h3>
          <p className="mt-1 text-xs text-ink/50">
            {l.location} · {l.config}
            {l.sqft !== " - " ? ` · ${l.sqft} sqft` : ""}
          </p>
          <p className="mt-auto pt-3 text-lg font-bold text-teal">{l.price}</p>
        </div>
      </div>
    </Reveal>
  );
}
