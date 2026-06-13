/**
 * Cockpit types + tab constants — client-safe (NO db/pg import).
 * Client components import from here; server data getters live in data.ts.
 */
import type { Tone } from "@/components/ui/primitives";
export type { Listing } from "@/lib/site";

export type Mode = "prospecting" | "active" | "launch" | "post_launch";

export interface Building {
  slug: string; name: string; location: string; mode: Mode;
  launchInDays?: number; seoRank: string;
  stats: { owners: number; tenants: number; leads: number; warm: number; listings: number; openReviews: number; blockers: number };
}
export interface ReviewItem { domain: string; title: string; building: string; age: string; tone: Tone }
export interface AgentEvent { agent: string; action: string; building: string; status: Tone }
export interface Blocker { id: string; building: string; statement: string; openFor: string }
export interface Person { name: string; role: "owner" | "tenant" | "client"; unit: string; phone: string }
export interface Keyword { term: string; rank: string; volume: string; status: Tone }
export interface Campaign { name: string; channel: string; status: Tone; note: string }
export interface Fact { label: string; value: string; status: Tone }
export interface WebPage { path: string; title: string; status: Tone }
export interface AgentTask { agent: string; task: string; cadence: string; status: Tone }
export interface KanbanTask { title: string; col: "todo" | "doing" | "blocked" | "done"; stream: string }
export interface CalendarItem { when: string; title: string; channel: string }

export const TAB_KEYS = ["overview","owners","leads","listings","seo","campaigns","rera","website","reviews","agents"] as const;
export type TabKey = (typeof TAB_KEYS)[number];
export const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" }, { key: "owners", label: "Owners & tenants" },
  { key: "leads", label: "Leads" }, { key: "listings", label: "Listings" },
  { key: "seo", label: "SEO & content" }, { key: "campaigns", label: "Campaigns" },
  { key: "rera", label: "RERA facts" }, { key: "website", label: "Website pages" },
  { key: "reviews", label: "Reviews" }, { key: "agents", label: "Agents" },
];
