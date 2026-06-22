"use client";

import { useState, useTransition, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { SheetSortKey } from "@/lib/cockpit/contacts-types";

interface Props {
  defaultQ: string;
  sort: SheetSortKey;
  dir: "asc" | "desc";
}

export function ContactSearchBar({ defaultQ, sort, dir }: Props) {
  const router = useRouter();
  const [value, setValue] = useState(defaultQ);
  const [isPending, startTransition] = useTransition();
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync when external navigation changes the search param (e.g. browser back)
  useEffect(() => { setValue(defaultQ); }, [defaultQ]);

  const navigate = (q: string) => {
    const params = new URLSearchParams();
    const trimmed = q.trim();
    if (trimmed) params.set("q", trimmed);
    params.set("sort", sort);
    params.set("dir", dir);
    params.set("page", "1");
    startTransition(() => { router.push(`/cockpit/contacts/sheet?${params.toString()}`); });
  };

  const handleChange = (v: string) => {
    setValue(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => navigate(v), 350);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      clearTimeout(timerRef.current);
      navigate(value);
    }
    if (e.key === "Escape") {
      clearTimeout(timerRef.current);
      setValue("");
      navigate("");
    }
  };

  return (
    <div className="relative flex items-center">
      <input
        type="search"
        aria-label="Search contacts by name or phone"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search by name or phone…"
        className={`w-64 rounded-lg border border-mist-deep bg-white py-1.5 pl-3 pr-8 text-sm text-ink placeholder:text-ink/35 focus:outline-none focus:ring-2 focus:ring-teal/30 transition-opacity ${isPending ? "opacity-50" : ""}`}
      />
      {value && !isPending && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => { setValue(""); navigate(""); }}
          className="absolute right-2 text-ink/35 hover:text-ink/70"
        >
          ×
        </button>
      )}
      {isPending && (
        <span className="absolute right-2 text-[10px] text-teal animate-pulse">…</span>
      )}
    </div>
  );
}
