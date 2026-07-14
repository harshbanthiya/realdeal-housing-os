import { Card, PanelTitle, Mono } from "@/components/ui/primitives";
import { AttachForm, ContentRow } from "@/components/cockpit/content-panel";
import { getListingContent, getAttachableAssets, getContentOverview } from "@/lib/cockpit/content";

export const dynamic = "force-dynamic";

export default async function ContentPage() {
  const [overview, rows, assets] = await Promise.all([
    getContentOverview(),
    getListingContent(),
    getAttachableAssets(),
  ]);

  return (
    <div className="px-6 py-7">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-teal">Listing content</h1>
        <p className="mt-1 text-sm text-ink/55">
          Attach reviewed media to listings and track the social lifecycle
          (draft → scheduled → posted). Posting itself stays human — record the
          permalink here after publishing natively. <Mono>listing_content</Mono>, migration 063.
        </p>
      </div>

      <Card className="mb-6 p-5">
        <PanelTitle hint={`${overview.total} total · ${overview.draft} draft · ${overview.scheduled} scheduled · ${overview.posted} posted`}>
          Attach content
        </PanelTitle>
        <AttachForm assets={assets} />
        {!overview.live && (
          <p className="mt-3 font-mono text-[11px] text-warm">
            DATABASE_URL not set — showing empty state.
          </p>
        )}
      </Card>

      <Card className="p-5">
        <PanelTitle hint="newest first · 200 max">Attached content</PanelTitle>
        {rows.length === 0 ? (
          <p className="text-sm text-ink/45">Nothing attached yet.</p>
        ) : (
          rows.map((r) => <ContentRow key={r.id} row={r} />)
        )}
      </Card>
    </div>
  );
}
