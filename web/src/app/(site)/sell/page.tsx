import { Reveal } from "@/components/reveal";
import { EnquiryForm } from "@/components/enquiry-form";
import { company } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/sell" },
  title: "Sell Your Flat in Goregaon West & Andheri West",
  description:
    "Sell your apartment in the Western Suburbs of Mumbai with trusted agents — 15 years selling premium homes in Imperial Heights, Ekta Tripolis & Kalpataru Radiance.",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Sell</p>
        <h1 className="max-w-3xl text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          The fastest &amp; easiest way to sell your property
        </h1>
        <p className="mt-5 max-w-2xl text-ink/65">
          {company.years} years of trusted experience selling premium homes
          across Mumbai&rsquo;s Western Suburbs. Tell us about your property and
          our team handles the rest — pricing, marketing and documentation.
        </p>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="mt-10">
          <EnquiryForm source="sell" variant="sell" />
        </div>
      </Reveal>
    </section>
  );
}
