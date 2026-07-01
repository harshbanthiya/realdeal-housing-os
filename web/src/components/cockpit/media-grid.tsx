"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Pill, Mono, type Tone } from "@/components/ui/primitives";
import { approveMediaAsset } from "@/lib/cockpit/actions";
import type { BrochureAssetRow, NeedsTaggingRow } from "@/lib/cockpit/media";

const ASSET_TYPES = [
  "floor_plan", "exterior", "interior", "amenity",
  "master_layout", "location_map", "video", "brochure", "virtual_stage", "other",
] as const;

const TYPE_TONE: Record<string, Tone> = {
  floor_plan: "active", exterior: "ready", interior: "ready",
  amenity: "active", master_layout: "neutral", location_map: "neutral",
  video: "active", brochure: "neutral", virtual_stage: "review", other: "neutral",
};

function basename(p: string) {
  return p.split("/").pop() ?? p;
}

// ── Brochure extract row ──────────────────────────────────────────────────────

export function BrochureGrid({ rows }: { rows: BrochureAssetRow[] }) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [msgs, setMsgs] = useState<Record<string, string>>({});

  function approve(id: string) {
    startTransition(async () => {
      const res = await approveMediaAsset({ assetId: id, apply: true });
      setMsgs((m) => ({ ...m, [id]: res.message }));
      if (res.applied) router.refresh();
    });
  }

  function unapprove(id: string) {
    startTransition(async () => {
      const res = await approveMediaAsset({ assetId: id, unapprove: true, apply: true });
      setMsgs((m) => ({ ...m, [id]: res.message }));
      if (res.applied) router.refresh();
    });
  }

  if (!rows.length) return <p className="text-sm text-ink/45">No brochure assets found.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-mist-deep">
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">preview</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">page</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">file</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">type</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">level</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">config</th>
            <th className="py-2 text-left font-mono text-[11px] text-ink/40">action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className={`border-b border-mist/60 ${row.reviewed ? "opacity-50" : ""}`}>
              <td className="py-2 pr-4">
                <a href={`/api/cockpit/media/${row.id}`} target="_blank" rel="noreferrer">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/api/cockpit/media/${row.id}`}
                    alt=""
                    className="h-14 w-20 rounded object-cover bg-mist hover:opacity-80 cursor-zoom-in"
                  />
                </a>
              </td>
              <td className="py-2 pr-4">
                <Mono className="text-[11px]">{row.brochurePage ?? "—"}</Mono>
              </td>
              <td className="max-w-[200px] truncate py-2 pr-4 text-ink/70" title={row.filePath}>
                {basename(row.filePath)}
              </td>
              <td className="py-2 pr-4">
                {row.assetType ? (
                  <Pill tone={TYPE_TONE[row.assetType] ?? "neutral"}>{row.assetType}</Pill>
                ) : (
                  <span className="text-ink/35">—</span>
                )}
              </td>
              <td className="py-2 pr-4">
                <Mono className="text-[11px]">{row.assetLevel ?? "—"}</Mono>
              </td>
              <td className="py-2 pr-4">
                <Mono className="text-[11px]">{row.configurationType ?? "—"}</Mono>
              </td>
              <td className="py-2">
                {msgs[row.id] ? (
                  <span className="font-mono text-[11px] text-teal">{msgs[row.id]}</span>
                ) : row.reviewed ? (
                  <button
                    onClick={() => unapprove(row.id)}
                    className="rounded px-2 py-0.5 font-mono text-[11px] text-ink/40 hover:bg-mist"
                  >
                    undo
                  </button>
                ) : (
                  <button
                    onClick={() => approve(row.id)}
                    className="rounded bg-teal/10 px-2 py-0.5 font-mono text-[11px] text-teal hover:bg-teal/20"
                  >
                    approve
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Needs-tagging row ─────────────────────────────────────────────────────────

export function TaggingGrid({ rows }: { rows: NeedsTaggingRow[] }) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [msgs, setMsgs] = useState<Record<string, string>>({});

  function save(id: string) {
    const assetType = selected[id];
    if (!assetType) return;
    startTransition(async () => {
      const res = await approveMediaAsset({ assetId: id, assetType, apply: true });
      setMsgs((m) => ({ ...m, [id]: res.message }));
      if (res.applied) router.refresh();
    });
  }

  if (!rows.length) return <p className="text-sm text-ink/45">All disk-scan assets are tagged.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-mist-deep">
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">file</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">level</th>
            <th className="py-2 pr-4 text-left font-mono text-[11px] text-ink/40">set type</th>
            <th className="py-2 text-left font-mono text-[11px] text-ink/40">save</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-mist/60">
              <td className="max-w-[260px] truncate py-2 pr-4 text-ink/70" title={row.filePath}>
                {basename(row.filePath)}
              </td>
              <td className="py-2 pr-4">
                <Mono className="text-[11px]">{row.assetLevel ?? "—"}</Mono>
              </td>
              <td className="py-2 pr-4">
                <select
                  className="rounded border border-mist-deep bg-white px-2 py-0.5 font-mono text-[11px] text-ink/70 focus:outline-none"
                  value={selected[row.id] ?? ""}
                  onChange={(e) => setSelected((s) => ({ ...s, [row.id]: e.target.value }))}
                >
                  <option value="">— pick type —</option>
                  {ASSET_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </td>
              <td className="py-2">
                {msgs[row.id] ? (
                  <span className="font-mono text-[11px] text-teal">{msgs[row.id]}</span>
                ) : (
                  <button
                    onClick={() => save(row.id)}
                    disabled={!selected[row.id]}
                    className="rounded bg-teal/10 px-2 py-0.5 font-mono text-[11px] text-teal hover:bg-teal/20 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    save
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
