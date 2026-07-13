"use client";

import Image from "next/image";
import { useState } from "react";

/**
 * Lite YouTube embed: static thumbnail (i.ytimg.com) until clicked, then the
 * privacy-enhanced iframe. Keeps YouTube's ~1MB of JS off the critical path.
 */
export function YouTubeEmbed({ id, title }: { id: string; title: string }) {
  const [play, setPlay] = useState(false);

  if (play) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-mist-deep bg-ink">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1`}
          title={title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="absolute inset-0 h-full w-full"
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setPlay(true)}
      aria-label={`Play video: ${title}`}
      className="group relative block aspect-video w-full overflow-hidden rounded-xl border border-mist-deep bg-ink"
    >
      <Image
        src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`}
        alt={title}
        fill
        sizes="(max-width: 768px) 100vw, 50vw"
        className="object-cover opacity-90 transition-transform duration-700 group-hover:scale-105"
      />
      <span className="absolute inset-0 flex items-center justify-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/95 shadow-md transition-transform group-hover:scale-110">
          <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4 2.5v11l9-5.5-9-5.5z" fill="#1f3d4d" />
          </svg>
        </span>
      </span>
      <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/70 to-transparent px-4 pb-3 pt-8 text-left text-sm font-semibold text-white">
        {title}
      </span>
    </button>
  );
}
