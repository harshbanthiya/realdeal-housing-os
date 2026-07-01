import { Card, Pill, PanelTitle, Mono, type Tone } from "@/components/ui/primitives";
import { BrochureGrid, TaggingGrid } from "@/components/cockpit/media-grid";
import { getMediaOverview, getBrochureAssets, getNeedsTaggingAssets } from "@/lib/cockpit/media";

export const dynamic = "force-dynamic";

export default async function MediaPage() {
  const [overview, brochure, tagging] = await Promise.all([
    getMediaOverview(),
    getBrochureAssets(),
    getNeedsTaggingAssets(100),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Media library</h1>
        <p className="mt-1 text-sm text-ink/55">
          Browse and approve brochure-extracted assets. Tag disk-scanned rows with missing type.
          Nothing publishes until <Mono>reviewed = true</Mono>.
        </p>
      </div>

      {/* Stats strip */}
      <Card className="mb-6 p-5">
        <PanelTitle hint="read-only · approve via button">Overview</PanelTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="Total assets" value={overview.total} tone="neutral" />
          <Stat label="Reviewed" value={overview.reviewed} tone="ready" sub={`of ${overview.total}`} />
          <Stat label="Brochure extract" value={overview.brochureExtract} tone="active" sub={`${overview.needsReview} pending`} />
          <Stat label="Disk scan" value={overview.diskScan} tone="neutral" />
          <Stat label="Needs tagging" value={overview.needsTagging} tone={overview.needsTagging > 0 ? "review" : "ready"} sub="null asset_type" />
        </div>
        {!overview.live && (
          <p className="mt-3 font-mono text-[11px] text-warm">
            DATABASE_URL not set — showing empty state. Set web/.env.local to read the live cockpit DB.
          </p>
        )}
      </Card>

      {/* Two panels */}
      <div className="space-y-8">
        <div>
          <PanelTitle hint={`${overview.needsReview} unreviewed · ${overview.brochureExtract} total`}>
            Brochure extracts — DLF Westpark
          </PanelTitle>
          <Card className="p-4">
            <BrochureGrid rows={brochure} />
          </Card>
        </div>

        <div>
          <PanelTitle hint={`showing first 100 of ${overview.needsTagging}`}>
            Disk scan — needs asset type
          </PanelTitle>
          <Card className="p-4">
            <TaggingGrid rows={tagging} />
          </Card>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label, value, tone, sub,
}: { label: string; value: number; tone: Tone; sub?: string }) {
  return (
    <div className="rounded-lg border border-mist-deep bg-mist/20 px-3 py-3">
      <div className="mb-1">
        <Pill tone={tone}>{label}</Pill>
      </div>
      <div className="text-lg font-semibold tabular-nums text-ink/85">{value}</div>
      {sub && <div className="font-mono text-[10px] text-ink/40">{sub}</div>}
    </div>
  );
}
