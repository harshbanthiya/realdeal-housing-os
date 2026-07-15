import { Reveal } from "@/components/reveal";
import { ListingGrid } from "@/components/listing-grid";
import { listings } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/rent" },
  title: "Flats for Rent in Goregaon West & Andheri West",
  description:
    "Luxury apartments for rent in Imperial Heights, Ekta Tripolis & Kalpataru Radiance — Mumbai's prestigious Western Suburbs.",
};

export default function Page() {
  const rent = listings.filter((l) => l.type === "rent");
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Rent</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Rent your next apartment
        </h1>
        <p className="mt-5 max-w-2xl text-ink/65">
          The largest inventory of rental homes in Goregaon West&rsquo;s most
          prestigious towers — fully furnished options, duplexes and penthouses.
        </p>
      </Reveal>
      <ListingGrid items={rent} />
    </section>
  );
}
