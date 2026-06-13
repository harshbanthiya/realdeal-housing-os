import { Reveal } from "@/components/reveal";
import { ListingGrid } from "@/components/listing-grid";
import { listings } from "@/lib/site";

export const metadata = {
  title: "Buy",
  description:
    "Buy premium apartments in Imperial Heights, Ekta Tripolis, Kalpataru Radiance and more across Mumbai's Western Suburbs.",
};

export default function Page() {
  const sale = listings.filter((l) => l.type === "sale");
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Buy</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Buy your next property
        </h1>
        <p className="mt-5 max-w-2xl text-ink/65">
          Premium homes for sale in Mumbai&rsquo;s top buildings — handpicked for
          builder reputation, layout and location. Every offer in the building,
          maximum negotiation room.
        </p>
      </Reveal>
      <ListingGrid items={sale} />
    </section>
  );
}
