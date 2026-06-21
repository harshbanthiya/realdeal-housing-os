"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { logContactNote } from "@/lib/cockpit/actions";

interface Props {
  contactId: string;
}

export function ContactNoteForm({ contactId }: Props) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [isPending, startTransition] = useTransition();

  const remaining = 500 - note.length;

  const submit = () => {
    if (!note.trim() || isPending) return;
    startTransition(async () => {
      const result = await logContactNote({ contactId, note: note.trim(), by: "operator", apply: true });
      if (result.ok) {
        setNote("");
        setStatus({ ok: true, message: "Note recorded." });
        router.refresh(); // re-fetch timeline from server
        setTimeout(() => setStatus(null), 3000);
      } else {
        setStatus({ ok: false, message: result.message || "Failed to record note." });
      }
    });
  };

  return (
    <div className="mt-5 border-t border-mist pt-4">
      <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-ink/40">Add note</div>
      <textarea
        value={note}
        onChange={(e) => { setNote(e.target.value.slice(0, 500)); setStatus(null); }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
        }}
        placeholder="Log a phone call, visit, or manual interaction… (⌘↵ to submit)"
        rows={3}
        disabled={isPending}
        aria-label="Contact note text"
        className={`w-full resize-none rounded-lg border border-mist-deep bg-white px-3 py-2 text-sm text-ink placeholder:text-ink/35 focus:outline-none focus:ring-2 focus:ring-teal/30 transition-opacity ${isPending ? "opacity-50" : ""}`}
      />
      <div className="mt-2 flex items-center justify-between">
        <span className={`font-mono text-[10px] ${remaining < 50 ? "text-warm" : "text-ink/35"}`}>
          {remaining} chars left
        </span>
        <div className="flex items-center gap-3">
          {status && (
            <span
              role="status"
              className={`text-[12px] ${status.ok ? "text-teal" : "text-warm"}`}
            >
              {status.message}
            </span>
          )}
          <button
            type="button"
            onClick={submit}
            disabled={!note.trim() || isPending}
            className="rounded-full bg-teal px-4 py-1.5 text-[12px] font-medium text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-40 hover:opacity-90"
          >
            {isPending ? "Saving…" : "Add note"}
          </button>
        </div>
      </div>
    </div>
  );
}
