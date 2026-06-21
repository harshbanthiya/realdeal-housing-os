import { notFound } from "next/navigation";
import { Pill, type Tone } from "@/components/ui/primitives";
import { WorkspaceTabs } from "@/components/cockpit/workspace-tabs";
import {
  getBuilding, getOwnersTenants, getListings, getKeywords,
  getCampaigns, getReraFacts, getWebsitePages, getBuildingReviews, getAgentTasks,
  getLaunchKanban, getLaunchCalendar, getUnitRegistry, type Mode,
} from "@/lib/cockpit/data";

export const dynamic = "force-dynamic";

const MODE_LABEL: Record<Mode, string> = {
  launch: "Launch", active: "Active", prospecting: "Prospecting", post_launch: "Post-launch",
};
const MODE_TONE: Record<Mode, Tone> = {
  launch: "blocked", active: "ready", prospecting: "review", post_launch: "neutral",
};

export default async function WorkspacePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const building = await getBuilding(slug);
  if (!building) notFound();

  const [owners, units, listings, keywords, campaigns, rera, pages, reviews, agents, kanban, calendar] = await Promise.all([
    getOwnersTenants(slug), getUnitRegistry(slug), getListings(slug), getKeywords(slug), getCampaigns(slug),
    getReraFacts(slug), getWebsitePages(slug), getBuildingReviews(slug), getAgentTasks(slug), getLaunchKanban(slug),
    getLaunchCalendar(slug),
  ]);
  const data = { building, owners, units, listings, keywords, campaigns, rera, pages, reviews, agents, kanban, calendar };

  return (
    <div className="px-6 py-7">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-teal">{building.name}</h1>
            <Pill tone={MODE_TONE[building.mode]}>{MODE_LABEL[building.mode]}</Pill>
          </div>
          <p className="mt-1 text-sm text-ink/55">
            {building.location}
            {building.launchInDays ? ` · launch in ${building.launchInDays} days` : ""} · SEO {building.seoRank}
          </p>
        </div>
      </div>

      <WorkspaceTabs data={data} />
    </div>
  );
}
