import { NextResponse } from "next/server";
import {
  audienceScope,
  getMetaAudienceRows,
  metaCsvFromRows,
  parseAudienceFilters,
} from "@/lib/cockpit/audiences";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const filters = parseAudienceFilters({
    building: url.searchParams.get("building"),
    role: url.searchParams.get("role"),
  });
  const rows = await getMetaAudienceRows(filters);
  const csv = metaCsvFromRows(rows);
  const scope = audienceScope(filters);

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="meta_custom_audience_${scope}.csv"`,
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}
