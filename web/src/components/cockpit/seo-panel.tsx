"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updateSeoItem } from "@/lib/cockpit/actions";
import type { SeoDraftRow, AnswerRow } from "@/lib/cockpit/seo";

const badge = (s: string) =>
  `inline-block rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide ${
    s === "approved" || s === "published" || s === "posted"
      ? "bg-teal/10 text-teal"
      : s === "rejected" || s === "stale"
        ? "bg-warm/10 text-warm"
        : "bg-mist text-ink/60"
  }`;

function ReviewButtons({
  table,
  id,
  approveAs,
  onDone,
}: {
  table: string;
  id: string;
  approveAs: string;
  onDone: (msg: string) => void;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();

  function run(status: string) {
    start(async () => {
      const res = await updateSeoItem({ table, id, status, reviewedBy: "operator", apply: true });
      onDone(res.message);
      if (res.applied) router.refresh();
    });
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => run(approveAs)}
        disabled={pending}
        className="rounded-lg bg-teal px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        Approve
      </button>
      <button
        onClick={() => run("rejected")}
        disabled={pending}
        className="rounded-lg border border-mist-deep px-3 py-1.5 text-sm font-medium text-warm hover:bg-mist disabled:opacity-50"
      >
        Reject
      </button>
    </div>
  );
}

export function DraftCard({ row }: { row: SeoDraftRow }) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const reviewable = row.status === "draft";

  return (
    <div className="border-t border-mist-deep py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className={badge(row.status)}>{row.status}</span>
          <button onClick={() => setOpen(!open)} className="ml-3 text-left text-sm font-semibold text-teal hover:underline">
            {row.title}
          </button>
          <div className="mt-1 font-mono text-[11px] text-ink/45">
            {row.kind} · /blog/{row.slug}
            {row.building_name ? ` · ${row.building_name}` : ""} ·{" "}
            {row.target_keywords.join(", ")}
          </div>
        </div>
        {reviewable && (
          <ReviewButtons table="seo_content_drafts" id={row.id} approveAs="approved" onDone={setMsg} />
        )}
      </div>
      {msg && <p className="mt-2 font-mono text-[11px] text-warm">{msg}</p>}
      {open && (
        <div className="mt-3 max-h-96 overflow-y-auto rounded-lg bg-mist/50 p-4 text-sm leading-relaxed text-ink/75">
          {row.seo_title && (
            <p className="mb-2 font-mono text-[11px] text-ink/50">
              SEO: {row.seo_title} — {row.seo_description}
            </p>
          )}
          <pre className="whitespace-pre-wrap font-sans">{row.body_md}</pre>
        </div>
      )}
    </div>
  );
}

export function AnswerCard({ row }: { row: AnswerRow }) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const reviewable = row.status === "drafted";

  return (
    <div className="border-t border-mist-deep py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <span className={badge(row.status)}>{row.status}</span>
          <a href={row.url} target="_blank" rel="noopener" className="ml-3 text-sm font-semibold text-teal hover:underline">
            {row.title}
          </a>
          <div className="mt-1 font-mono text-[11px] text-ink/45">
            {row.platform}
            {row.community ? ` · r/${row.community}` : ""}
            {row.relevance ? ` · ${row.relevance}` : ""}
          </div>
        </div>
        {reviewable && (
          <ReviewButtons table="answer_opportunities" id={row.id} approveAs="approved" onDone={setMsg} />
        )}
      </div>
      {msg && <p className="mt-2 font-mono text-[11px] text-warm">{msg}</p>}
      {row.draft_answer_md && (
        <button onClick={() => setOpen(!open)} className="mt-2 font-mono text-[11px] text-teal hover:underline">
          {open ? "hide draft answer" : "show draft answer"}
        </button>
      )}
      {open && row.draft_answer_md && (
        <div className="mt-2 rounded-lg bg-mist/50 p-4 text-sm leading-relaxed text-ink/75">
          <pre className="whitespace-pre-wrap font-sans">{row.draft_answer_md}</pre>
          {row.suggested_link && (
            <p className="mt-2 font-mono text-[11px] text-ink/50">link: {row.suggested_link}</p>
          )}
        </div>
      )}
    </div>
  );
}
