/** Read layer for /cockpit/content — listing_content ↔ media_assets (migration 063). */
import { readQuery, isDbConfigured } from "@/lib/db";

export interface ListingContentRow {
  id: string;
  listing_slug: string;
  role: string;
  status: string;
  platform: string | null;
  post_url: string | null;
  posted_at: string | null;
  notes: string | null;
  asset_id: string;
  asset_title: string | null;
  media_type: string;
  building_name: string | null;
}

export interface AttachableAsset {
  id: string;
  title: string | null;
  media_type: string;
  asset_level: string | null;
  building_name: string | null;
}

export async function getListingContent(): Promise<ListingContentRow[]> {
  return readQuery<ListingContentRow>(`
    SELECT lc.id, lc.listing_slug, lc.role, lc.status, lc.platform, lc.post_url,
           lc.posted_at::text AS posted_at, lc.notes,
           ma.id AS asset_id, ma.title AS asset_title, ma.media_type,
           b.name AS building_name
    FROM listing_content lc
    JOIN media_assets ma ON ma.id = lc.media_asset_id
    LEFT JOIN buildings b ON b.id = lc.building_id
    ORDER BY lc.created_at DESC
    LIMIT 200
  `);
}

/** Reviewed assets an operator can attach (newest first). */
export async function getAttachableAssets(): Promise<AttachableAsset[]> {
  return readQuery<AttachableAsset>(`
    SELECT ma.id, ma.title, ma.media_type, ma.asset_level, b.name AS building_name
    FROM media_assets ma
    LEFT JOIN buildings b ON b.id = ma.building_id
    WHERE ma.reviewed = true
    ORDER BY ma.updated_at DESC
    LIMIT 100
  `);
}

export async function getContentOverview() {
  const rows = await readQuery<{ status: string; n: string }>(
    "SELECT status, count(*) AS n FROM listing_content GROUP BY status",
  );
  const by = Object.fromEntries(rows.map((r) => [r.status, Number(r.n)]));
  return {
    live: isDbConfigured(),
    total: rows.reduce((s, r) => s + Number(r.n), 0),
    draft: by.draft ?? 0,
    scheduled: by.scheduled ?? 0,
    posted: by.posted ?? 0,
  };
}
