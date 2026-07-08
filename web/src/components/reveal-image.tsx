"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

/**
 * Design-system image clip reveal (Motion II): the frame unclips upward while
 * the image settles from 1.12× to 1. Combine with .rdh-zoom via `zoom` for
 * hover scale on cards. Uses next/image fill — parent supplies aspect ratio
 * via className (e.g. "aspect-[16/9]").
 */
export function RevealImage({
  src,
  alt,
  className = "",
  sizes = "(max-width: 768px) 100vw, 50vw",
  priority = false,
  zoom = false,
}: {
  src: string;
  alt: string;
  className?: string;
  sizes?: string;
  priority?: boolean;
  zoom?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin: "-60px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`rdh-clip relative overflow-hidden ${zoom ? "rdh-zoom " : ""}${visible ? "is-visible " : ""}${className}`}
    >
      <Image src={src} alt={alt} fill sizes={sizes} priority={priority} className="object-cover" />
    </div>
  );
}
