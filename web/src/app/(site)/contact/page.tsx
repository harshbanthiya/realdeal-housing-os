import { Reveal } from "@/components/reveal";
import { EnquiryForm } from "@/components/enquiry-form";
import { company } from "@/lib/site";

export const metadata = {
  alternates: { canonical: "/contact" },
  title: "Contact",
  description: "Get in touch with Real Deal Housing — Goregaon West, Mumbai.",
};

export default function Page() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-24">
      <Reveal>
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-warm">Contact</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
          Leave us a message
        </h1>
      </Reveal>
      <div className="mt-12 grid gap-12 md:grid-cols-[1fr_1.1fr]">
        <Reveal>
          <div className="space-y-6 text-sm">
            <Detail label="Phone" value={company.phone} href={company.phoneHref} />
            <Detail label="Email" value={company.email} href={`mailto:${company.email}`} />
            <Detail label="Office" value={company.address} />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <EnquiryForm source="contact" />
        </Reveal>
      </div>
    </section>
  );
}

function Detail({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink/45">{label}</div>
      {href ? (
        <a href={href} className="text-lg font-medium text-teal hover:underline">{value}</a>
      ) : (
        <div className="text-lg font-medium text-teal">{value}</div>
      )}
    </div>
  );
}
