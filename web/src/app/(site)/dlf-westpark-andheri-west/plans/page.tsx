import type { Metadata } from "next";
import Link from "next/link";
import { DlfPlanExplorer } from "@/components/dlf-plan-explorer";
import { dlfProject, dlfTowers } from "@/lib/dlf-plans";

export const metadata: Metadata = {
  title: "DLF Westpark Floor Plans — Towers T02–T05, 3–5 BHK Configurations",
  description:
    "Explore DLF Westpark Andheri West floor by floor: tower plates, 3 BHK, 4 BHK, 5 BHK, duplex and studio configurations with carpet areas, from the official Phase 1 brochure.",
};

export default function DlfPlansPage() {
  const breadcrumbs = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: "/" },
      { "@type": "ListItem", position: 2, name: "DLF Westpark", item: "/dlf-westpark-andheri-west" },
      { "@type": "ListItem", position: 3, name: "Floor plans" },
    ],
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-14 md:py-20">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbs) }} />
      <Link href="/dlf-westpark-andheri-west" className="text-sm font-semibold text-teal hover:underline">
        ← DLF Westpark
      </Link>
      <p className="mt-8 flex w-fit items-center gap-2 border border-mist-deep px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/60">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
        Floor plans — {dlfProject.name}
      </p>
      <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-teal md:text-5xl">
        Every tower. Every floor. Every layout.
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink/65">
        {dlfTowers.length} towers, 40 floors each, from the official Phase 1 brochure —
        pick a tower and a floor to see its plate and the configurations on it.
        MahaRERA {dlfProject.rera} · developed by {dlfProject.developer}.
      </p>
      <div className="mt-12">
        <DlfPlanExplorer />
      </div>
    </div>
  );
}
