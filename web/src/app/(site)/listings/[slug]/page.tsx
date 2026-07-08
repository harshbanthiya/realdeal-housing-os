import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reveal } from "@/components/reveal";
import { RevealImage } from "@/components/reveal-image";
import { ListingGrid } from "@/components/listing-grid";
import { listings } from "@/lib/listings";
import { projects, company } from "@/lib/site";

export function generateStaticParams() {
  return listings.map((l) => ({ slug: l.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const l = listings.find((x) => x.slug === slug);
  if (!l) return { title: "Listing" };
  return {
    title: `${l.title} — ${l.location}`,
    description: `${l.config}, ${l.sqft} sq ft, ${l.price} — ${l.project}, ${l.location}. ${l.description[0].slice(0, 120)}`,
    alternates: { canonical: `/listings/${slug}` },
    openGraph: {
      title: l.title,
      description: l.description[0],
      images: l.image ? [l.image.src] : undefined,
    },
  };
}

export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const l = listings.find((x) => x.slug === slug);
  if (!l) notFound();

  const project = projects.find((p) => p.name === l.project);
  const more = listings.filter((x) => x.project === l.project && x.slug !== l.slug).slice(0, 3);
  const facts: [string, string][] = [
    ["Configuration", l.config],
    ["Carpet area", l.sqft !== "—" ? `${l.sqft} sq ft` : "On request"],
    [l.type === "rent" ? "Rent" : "Price", l.price],
    ["Building", l.project],
    ["Locality", `${l.location}, Mumbai`],
  ];

  return (
    <article>
      <section className="mx-auto max-w-6xl px-6 pt-16 md:pt-24">
        <Reveal>
          <Link href={l.type === "rent" ? "/rent" : "/buy"} className="text-sm font-medium text-ink/50 hover:text-teal">
            ← All {l.type === "rent" ? "rentals" : "properties for sale"}
          </Link>
          <p className="mt-6 flex items-center gap-2 text-sm font-medium text-ink/55">
            <span className="inline-block h-2 w-2 rounded-full bg-warm" />
            {l.location}, Mumbai ·{" "}
            <span className="font-mono text-xs uppercase tracking-wider">
              {l.type === "rent" ? "For rent" : "For sale"}
            </span>
          </p>
          <h1 className="mt-3 max-w-4xl text-[clamp(2.2rem,4.5vw,3.6rem)] font-extrabold leading-[1.06] tracking-tight text-teal">
            {l.title}
          </h1>
          <p className="mt-4 text-2xl font-bold text-teal">{l.price}</p>
        </Reveal>
        {l.image && (
          <RevealImage
            src={l.image.src}
            alt={l.image.alt}
            priority
            sizes="(max-width: 1152px) 100vw, 1152px"
            className="mt-10 aspect-[16/9] w-full rounded-2xl md:aspect-[21/9]"
          />
        )}
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr]">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-teal">About this home</h2>
            {l.description.map((para) => (
              <p key={para.slice(0, 32)} className="mt-5 text-lg leading-relaxed text-ink/70">
                {para}
              </p>
            ))}
            {project && (
              <p className="mt-6 text-sm text-ink/55">
                Part of{" "}
                <Link href={`/projects/${project.slug}`} className="font-semibold text-teal hover:underline">
                  {project.name}
                </Link>{" "}
                — {project.meta}.
              </p>
            )}
          </Reveal>
          <Reveal delay={0.1}>
            <div className="rounded-2xl border border-mist-deep bg-mist/40 p-7">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-ink/50">At a glance</h3>
              <dl className="mt-4 space-y-3 text-sm">
                {facts.map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4">
                    <dt className="text-ink/50">{k}</dt>
                    <dd className="text-right font-semibold text-teal">{v}</dd>
                  </div>
                ))}
              </dl>
              <Link
                href="/contact"
                className="mt-7 block rounded-full bg-teal px-6 py-3.5 text-center text-sm font-semibold text-white transition-opacity hover:opacity-90"
              >
                Arrange a viewing →
              </Link>
              <a
                href={company.phoneHref}
                className="mt-3 block rounded-full border border-mist-deep px-6 py-3.5 text-center text-sm font-semibold text-teal transition-colors hover:bg-mist"
              >
                Call {company.phone}
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      {more.length > 0 && (
        <section className="border-t border-mist-deep bg-mist/40">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <Reveal>
              <h2 className="text-2xl font-bold tracking-tight text-teal">
                More in {l.project}
              </h2>
            </Reveal>
            <ListingGrid items={more} />
          </div>
        </section>
      )}

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "RealEstateListing",
            name: l.title,
            description: l.description.join(" "),
            image: l.image?.src,
            offers: {
              "@type": "Offer",
              price: l.price.replace(/[^\d]/g, ""),
              priceCurrency: "INR",
            },
            address: {
              "@type": "PostalAddress",
              addressLocality: `${l.location}, Mumbai`,
              addressRegion: "MH",
              addressCountry: "IN",
            },
          }),
        }}
      />
    </article>
  );
}
