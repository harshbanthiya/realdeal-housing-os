import { notFound } from "next/navigation";
import { Sidebar } from "@/components/cockpit/sidebar";
import { Pill } from "@/components/ui/primitives";
import { getBuildings } from "@/lib/cockpit/data";

export const metadata = { title: "Cockpit", robots: { index: false, follow: false } };

// Internal, live-DB tool — render per request, never prerender at build time.
export const dynamic = "force-dynamic";

export default async function CockpitLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Internal tool — never serve on a public/production deploy (e.g. Vercel).
  // Stays available in local dev; to run it on a protected host, set COCKPIT_ENABLED=true + add auth.
  if (process.env.NODE_ENV === "production" && process.env.COCKPIT_ENABLED !== "true") {
    notFound();
  }

  const buildings = await getBuildings();
  const launch = buildings.find((b) => b.mode === "launch");

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar buildings={buildings} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-mist-deep px-6">
          <div className="flex items-center gap-3 text-sm text-ink/50">
            <span className="font-mono text-[12px]">⌘K</span>
            <span className="hidden sm:inline">Search buildings, leads, reviews…</span>
          </div>
          {launch && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-ink/50">{launch.name} launch</span>
              <Pill tone="blocked">{launch.stats.blockers} blockers · go-live locked</Pill>
            </div>
          )}
        </header>
        <main className="flex-1 overflow-y-auto bg-white">{children}</main>
      </div>
    </div>
  );
}
