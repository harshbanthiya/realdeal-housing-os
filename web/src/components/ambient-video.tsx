"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Ambient background loop (MEDIA-SOCIAL-FUNNEL-PLAN Task A).
 * Poster renders immediately; the video element mounts only when the section
 * nears the viewport (never competes with LCP), autoplays muted, loops.
 * prefers-reduced-motion users get the poster only.
 */
export function AmbientVideo({
  src,
  poster,
  caption,
  className = "",
}: {
  src: string;
  poster: string;
  caption?: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [showVideo, setShowVideo] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShowVideo(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={ref} className={`relative overflow-hidden ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={poster} alt="" className="absolute inset-0 h-full w-full object-cover" />
      {showVideo && (
        <video
          src={src}
          poster={poster}
          muted
          loop
          playsInline
          autoPlay
          preload="none"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
      {caption && (
        <span className="absolute bottom-4 left-4 inline-flex items-center gap-2 bg-white/90 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-ink/70 md:bottom-6 md:left-6">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-warm" />
          {caption}
        </span>
      )}
    </div>
  );
}
