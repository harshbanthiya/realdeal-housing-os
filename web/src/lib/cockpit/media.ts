/**
 * Cockpit media data layer (Phase D — /cockpit/media).
 * Read-only; all writes go through approve_media_asset.py via server actions.
 */
import { isDbConfigured, readQuery } from "@/lib/db";

const live = isDbConfigured;

export interface MediaOverview {
  live: boolean;
  total: number;
  reviewed: number;
  brochureExtract: number;
  diskScan: number;
  needsTagging: number;   // disk_scan with null asset_type
  needsReview: number;    // brochure_extract with reviewed=false
}

export interface BrochureAssetRow {
  id: string;
  filePath: string;
  assetType: string | null;
  assetLevel: string | null;
  configurationType: string | null;
  brochurePage: number | null;
  altText: string | null;
  reviewed: boolean;
}

export interface NeedsTaggingRow {
  id: string;
  filePath: string;
  assetLevel: string | null;
  mediaType: string;
  fileSizeBytes: number | null;
}

export async function getMediaOverview(): Promise<MediaOverview> {
  const empty: MediaOverview = {
    live: false, total: 0, reviewed: 0, brochureExtract: 0,
    diskScan: 0, needsTagging: 0, needsReview: 0,
  };
  if (!live()) return empty;

  const rows = await readQuery<Record<string, string>>(`
    SELECT
      COUNT(*)                                                          AS total,
      COUNT(*) FILTER (WHERE reviewed)                                  AS reviewed,
      COUNT(*) FILTER (WHERE source = 'brochure_extract')              AS brochure_extract,
      COUNT(*) FILTER (WHERE source = 'disk_scan')                     AS disk_scan,
      COUNT(*) FILTER (WHERE source = 'disk_scan' AND asset_type IS NULL) AS needs_tagging,
      COUNT(*) FILTER (WHERE source = 'brochure_extract' AND NOT reviewed) AS needs_review
    FROM media_assets
  `);

  if (!rows[0]) return { ...empty, live: true };
  const r = rows[0];
  return {
    live: true,
    total: Number(r.total),
    reviewed: Number(r.reviewed),
    brochureExtract: Number(r.brochure_extract),
    diskScan: Number(r.disk_scan),
    needsTagging: Number(r.needs_tagging),
    needsReview: Number(r.needs_review),
  };
}

export async function getBrochureAssets(): Promise<BrochureAssetRow[]> {
  if (!live()) return [];
  return readQuery<BrochureAssetRow>(`
    SELECT
      id,
      file_path         AS "filePath",
      asset_type        AS "assetType",
      asset_level       AS "assetLevel",
      configuration_type AS "configurationType",
      brochure_page     AS "brochurePage",
      alt_text          AS "altText",
      reviewed
    FROM media_assets
    WHERE source = 'brochure_extract'
    ORDER BY reviewed ASC, brochure_page ASC NULLS LAST
    LIMIT 200
  `);
}

export async function getNeedsTaggingAssets(limit = 100): Promise<NeedsTaggingRow[]> {
  if (!live()) return [];
  return readQuery<NeedsTaggingRow>(`
    SELECT
      id,
      file_path         AS "filePath",
      asset_level       AS "assetLevel",
      media_type        AS "mediaType",
      file_size_bytes   AS "fileSizeBytes"
    FROM media_assets
    WHERE source = 'disk_scan' AND asset_type IS NULL
    ORDER BY asset_level NULLS LAST, file_path
    LIMIT $1
  `, [limit]);
}
