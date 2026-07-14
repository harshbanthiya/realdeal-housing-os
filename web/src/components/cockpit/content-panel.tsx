"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { attachListingContent, setListingContentStatus } from "@/lib/cockpit/actions";
import type { ListingContentRow, AttachableAsset } from "@/lib/cockpit/content";

const ROLES = ["reel", "story", "tour", "photo_set", "ambient_loop", "thumbnail"];
const PLATFORMS = ["instagram", "youtube", "facebook", "site"];

export function AttachForm({ assets }: { assets: AttachableAsset[] }) {
  const router = useRouter();
  const [assetId, setAssetId] = useState("");
  const [slug, setSlug] = useState("");
  const [role, setRole] = useState("reel");
  const [msg, setMsg] = useState("");
  const [pending, start] = useTransition();

  function run(apply: boolean) {
    start(async () => {
      const res = await attachListingContent({ mediaAssetId: assetId, listingSlug: slug, role, apply });
      setMsg(res.message);
      if (res.applied) router.refresh();
    });
  }

  const field = "w-full rounded-lg border border-mist-deep bg-white px-3 py-2 text-sm text-ink/80";
  return (
    <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto]">
      <select value={assetId} onChange={(e) => setAssetId(e.target.value)} className={field} aria-label="Media asset">
        <option value="">Select a reviewed asset…</option>
        {assets.map((a) => (
          <option key={a.id} value={a.id}>
            {(a.title ?? a.id.slice(0, 8))} · {a.media_type}
            {a.building_name ? ` · ${a.building_name}` : ""}
          </option>
        ))}
      </select>
      <input
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        placeholder="listing slug (or 'home')"
        className={field}
        aria-label="Listing slug"
      />
      <select value={role} onChange={(e) => setRole(e.target.value)} className={field} aria-label="Role">
        {ROLES.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>
      <div className="flex gap-2">
        <button
          onClick={() => run(false)}
          disabled={pending || !assetId || !slug}
          className="rounded-lg border border-mist-deep px-4 py-2 text-sm font-medium text-teal hover:bg-mist disabled:opacity-50"
        >
          Dry run
        </button>
        <button
          onClick={() => run(true)}
          disabled={pending || !assetId || !slug}
          className="rounded-lg bg-teal px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          Attach
        </button>
      </div>
      {msg && <p className="font-mono text-[11px] text-ink/60 md:col-span-4">{msg}</p>}
    </div>
  );
}

export function ContentRow({ row }: { row: ListingContentRow }) {
  const router = useRouter();
  const [platform, setPlatform] = useState(row.platform ?? "");
  const [postUrl, setPostUrl] = useState(row.post_url ?? "");
  const [msg, setMsg] = useState("");
  const [pending, start] = useTransition();

  function move(status: string) {
    start(async () => {
      const res = await setListingContentStatus({
        id: row.id,
        status,
        platform: platform || undefined,
        postUrl: postUrl || undefined,
        apply: true,
      });
      setMsg(res.message);
      if (res.applied) router.refresh();
    });
  }

  return (
    <div className="border-t border-mist-deep py-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="font-medium text-ink/80">{row.asset_title ?? row.asset_id.slice(0, 8)}</span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-ink/45">
          {row.role} → {row.listing_slug}
        </span>
        <span className={`font-mono text-[11px] uppercase tracking-wider ${row.status === "posted" ? "text-teal" : "text-warm"}`}>
          {row.status}
        </span>
        {row.building_name && <span className="text-xs text-ink/45">{row.building_name}</span>}
        {row.post_url && (
          <a href={row.post_url} target="_blank" rel="noopener" className="text-xs text-teal underline">
            permalink
          </a>
        )}
      </div>
      {row.status !== "posted" && row.status !== "retired" && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="rounded border border-mist-deep bg-white px-2 py-1 text-xs"
            aria-label="Platform"
          >
            <option value="">platform…</option>
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <input
            value={postUrl}
            onChange={(e) => setPostUrl(e.target.value)}
            placeholder="post URL once live"
            className="w-64 rounded border border-mist-deep bg-white px-2 py-1 text-xs"
            aria-label="Post URL"
          />
          <button onClick={() => move("scheduled")} disabled={pending} className="rounded border border-mist-deep px-3 py-1 text-xs font-medium text-teal hover:bg-mist disabled:opacity-50">
            Mark scheduled
          </button>
          <button onClick={() => move("posted")} disabled={pending} className="rounded bg-teal px-3 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50">
            Mark posted
          </button>
          <button onClick={() => move("retired")} disabled={pending} className="rounded px-3 py-1 text-xs text-ink/45 hover:text-warm disabled:opacity-50">
            Retire
          </button>
        </div>
      )}
      {msg && <p className="mt-1 font-mono text-[11px] text-ink/55">{msg}</p>}
    </div>
  );
}
