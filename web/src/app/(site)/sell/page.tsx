import { Reveal } from "@/components/reveal";
import { company } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/sell" },
  title: "Sell Your Flat in Goregaon West & Andheri West",
  description:
    "Sell your apartment in the Western Suburbs of Mumbai with trusted agents — 15 years selling premium homes in Imperial Heights, Ekta Tripolis & Kalpataru Radiance.",
};

const fields = ["First name", "Last name", "Email", "Neighbourhood", "Full address", "Floor", "Total bedrooms"];
const amenities = ["Doorman", "Storage", "Elevator", "Washer/Dryer", "Natural Light", "Laundry Room", "High Ceilings"];

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
        <p className="mt-4 inline-flex rounded-md bg-mist px-3 py-2 font-mono text-xs text-ink/60">
          Staging preview · form does not submit · no data captured
        </p>
      </Reveal>

      <Reveal delay={0.1}>
        <form aria-disabled className="mt-10 rounded-2xl border border-mist-deep bg-white p-7">
          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map((f) => (
              <div key={f}>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/50">{f}</label>
                <input disabled placeholder={f} className="w-full rounded-lg border border-mist-deep bg-mist/40 px-3.5 py-2.5 text-sm text-ink placeholder:text-ink/35" />
              </div>
            ))}
          </div>
          <div className="mt-5">
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-ink/50">Amenities</label>
            <div className="flex flex-wrap gap-2">
              {amenities.map((a) => (
                <span key={a} className="rounded-full border border-mist-deep px-3 py-1.5 text-xs text-ink/60">{a}</span>
              ))}
            </div>
          </div>
          <button type="button" disabled className="mt-6 cursor-not-allowed rounded-full bg-mist-deep px-6 py-3.5 text-sm font-semibold text-ink/50">
            Preview only — no live submission
          </button>
        </form>
      </Reveal>
    </section>
  );
}
