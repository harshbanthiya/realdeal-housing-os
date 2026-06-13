import { Sidebar } from "@/components/cockpit/sidebar";
import { Pill } from "@/components/ui/primitives";
import { getBuildings } from "@/lib/cockpit/data";

export const metadata = { title: "Cockpit" };

export default function CockpitLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const buildings = getBuildings();
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
