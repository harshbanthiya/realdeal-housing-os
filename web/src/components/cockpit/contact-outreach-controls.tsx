"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { enqueueContact, addContactsToGroup } from "@/lib/cockpit/actions";

export function ContactOutreachControls({
  contactId, groups, inOutreach,
}: {
  contactId: string;
  groups: { slug: string; name: string }[];
  inOutreach: { status: string; step: number } | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [groupSlug, setGroupSlug] = useState(groups[0]?.slug ?? "");
  const [msg, setMsg] = useState<string | null>(null);

  function addToOutreach() {
    setMsg(null);
    startTransition(async () => {
      const res = await enqueueContact({ contactId, apply: true });
      setMsg(res.message);
      if (res.applied) router.refresh();
    });
  }

  function addToGroup() {
    if (!groupSlug) return;
    setMsg(null);
    startTransition(async () => {
      const res = await addContactsToGroup({ groupSlug, contactIds: [contactId], apply: true });
      setMsg(res.message);
      if (res.applied) router.refresh();
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {inOutreach ? (
        <span className="rounded-lg bg-teal/10 px-3 py-1.5 text-[13px] font-medium text-teal">
          In outreach · {inOutreach.status.replace(/_/g, " ")} (step {inOutreach.step})
        </span>
      ) : (
        <button
          onClick={addToOutreach} disabled={pending}
          className="rounded-lg bg-teal px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal/90 disabled:opacity-40"
        >
          + Add to outreach
        </button>
      )}

      {groups.length > 0 && (
        <>
          <select
            value={groupSlug} onChange={(e) => setGroupSlug(e.target.value)}
            className="rounded-lg border border-mist-deep px-2 py-1.5 text-sm text-ink/70"
          >
            {groups.map((g) => <option key={g.slug} value={g.slug}>{g.name}</option>)}
          </select>
          <button
            onClick={addToGroup} disabled={pending}
            className="rounded-lg border border-mist-deep px-3 py-1.5 text-sm font-medium text-ink/70 hover:bg-mist/40 disabled:opacity-40"
          >
            Add to group
          </button>
        </>
      )}

      {msg && <span className="font-mono text-[11px] text-ink/55">{msg}</span>}
    </div>
  );
}
