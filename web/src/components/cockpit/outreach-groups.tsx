"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Card, Pill, Mono, type Tone } from "@/components/ui/primitives";
import { buildOutreachQueue, createContactGroup } from "@/lib/cockpit/actions";
import type { ContactGroup } from "@/lib/cockpit/outreach";

const TYPE_TONE: Record<string, Tone> = { test: "review", custom: "active", system: "neutral" };

export function OutreachGroups({ groups, hasActiveSequence }: { groups: ContactGroup[]; hasActiveSequence: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  function create() {
    const name = newName.trim();
    if (name.length < 2) return;
    setMsg(null);
    startTransition(async () => {
      const res = await createContactGroup({ name, apply: true });
      setMsg(res.message);
      if (res.applied) { setNewName(""); router.refresh(); }
    });
  }

  function buildFrom(slug: string) {
    setMsg(null);
    startTransition(async () => {
      const res = await buildOutreachQueue({ source: "group", groupSlug: slug, limit: 25, apply: true });
      setMsg(res.message);
      if (res.applied) router.refresh();
    });
  }

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <input
          value={newName} onChange={(e) => setNewName(e.target.value)}
          placeholder="New group name…"
          className="flex-1 rounded-lg border border-mist-deep px-3 py-1.5 text-sm"
        />
        <button
          onClick={create} disabled={pending || newName.trim().length < 2}
          className="rounded-lg bg-teal px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal/90 disabled:opacity-40"
        >
          Create group
        </button>
      </div>

      {groups.length === 0 ? (
        <p className="text-sm text-ink/45">No groups yet. Create one above, then add contacts from their detail pages.</p>
      ) : (
        <ul className="space-y-2">
          {groups.map((g) => (
            <li key={g.slug} className="flex items-center gap-3 rounded-lg border border-mist-deep px-3 py-2">
              <Pill tone={TYPE_TONE[g.groupType] ?? "neutral"}>{g.groupType}</Pill>
              <div className="flex-1">
                <div className="text-sm font-medium text-ink/85">{g.name}</div>
                <Mono className="text-[10px]">
                  {g.memberCount} members · {g.reachableCount} reachable
                  {g.suppressedCount > 0 && ` · ${g.suppressedCount} suppressed`}
                </Mono>
              </div>
              <button
                onClick={() => buildFrom(g.slug)} disabled={pending || !hasActiveSequence || g.reachableCount === 0}
                className="rounded-lg border border-mist-deep px-2.5 py-1.5 text-[13px] font-medium text-ink/70 hover:bg-mist/40 disabled:opacity-40"
              >
                Build queue
              </button>
            </li>
          ))}
        </ul>
      )}

      {msg && <div className="mt-3 font-mono text-[11px] text-ink/55">{msg}</div>}
    </Card>
  );
}
