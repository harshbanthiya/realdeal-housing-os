/** Read layer for /cockpit/seo — content_scout output (migration 064). */
import { readQuery, isDbConfigured } from "@/lib/db";

export interface SeoDraftRow {
  id: string;
  kind: string;
  slug: string;
  title: string;
  excerpt: string | null;
  body_md: string;
  seo_title: string | null;
  seo_description: string | null;
  target_keywords: string[];
  target_area: string | null;
  building_name: string | null;
  status: string;
  created_at: string;
}

export interface AnswerRow {
  id: string;
  platform: string;
  url: string;
  title: string;
  snippet: string | null;
  community: string | null;
  relevance: string | null;
  draft_answer_md: string | null;
  suggested_link: string | null;
  status: string;
  created_at: string;
}

export interface LlmRunRow {
  worker: string;
  tier: string;
  model: string;
  purpose: string;
  status: string;
  duration_ms: number | null;
  created_at: string;
}

export async function getSeoDrafts(): Promise<SeoDraftRow[]> {
  if (!isDbConfigured()) return [];
  return readQuery<SeoDraftRow>(`
    SELECT d.id, d.kind, d.slug, d.title, d.excerpt, d.body_md, d.seo_title,
           d.seo_description, d.target_keywords, d.target_area,
           b.name AS building_name, d.status, d.created_at::text
    FROM seo_content_drafts d
    LEFT JOIN buildings b ON b.id = d.building_id
    ORDER BY d.status = 'draft' DESC, d.created_at DESC
    LIMIT 100`);
}

export async function getAnswerOpportunities(): Promise<AnswerRow[]> {
  if (!isDbConfigured()) return [];
  return readQuery<AnswerRow>(`
    SELECT id, platform, url, title, snippet, community, relevance,
           draft_answer_md, suggested_link, status, created_at::text
    FROM answer_opportunities
    WHERE status <> 'stale'
    ORDER BY status = 'drafted' DESC, created_at DESC
    LIMIT 100`);
}

export async function getRecentLlmRuns(): Promise<LlmRunRow[]> {
  if (!isDbConfigured()) return [];
  return readQuery<LlmRunRow>(`
    SELECT worker, tier, model, purpose, status, duration_ms, created_at::text
    FROM llm_runs ORDER BY created_at DESC LIMIT 25`);
}

export interface SocialPostRow {
  id: string;
  platform: string;
  title: string;
  description: string | null;
  tags: string[];
  edit_notes: string | null;
  building_name: string | null;
  asset_title: string | null;
  status: string;
  posted_url: string | null;
  created_at: string;
}

export interface VideoResearchRow {
  title: string;
  channel: string | null;
  views: number | null;
  url: string;
  status: string;
  why_it_works: string | null;
}

export async function getSocialPostDrafts(): Promise<SocialPostRow[]> {
  if (!isDbConfigured()) return [];
  return readQuery<SocialPostRow>(`
    SELECT d.id, d.platform, d.title, d.description, d.tags,
           d.edit_spec->>'notes' AS edit_notes,
           b.name AS building_name, m.title AS asset_title,
           d.status, d.posted_url, d.created_at::text
    FROM social_post_drafts d
    LEFT JOIN buildings b ON b.id = d.building_id
    LEFT JOIN media_assets m ON m.id = d.media_asset_id
    ORDER BY d.status = 'draft' DESC, d.created_at DESC LIMIT 100`);
}

export async function getVideoResearch(): Promise<VideoResearchRow[]> {
  if (!isDbConfigured()) return [];
  return readQuery<VideoResearchRow>(`
    SELECT title, channel, views, url, status,
           analysis->>'why_it_works' AS why_it_works
    FROM video_research ORDER BY views DESC NULLS LAST LIMIT 30`);
}
