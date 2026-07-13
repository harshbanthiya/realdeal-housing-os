"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

/** Click-to-enlarge image: renders next/image in place, opens a full-screen
 * lightbox (Esc / click / ✕ to close). Parent supplies aspect via className. */
export function ZoomImage({
  src,
  alt,
  sizes = "(max-width: 768px) 100vw, 60vw",
  className = "",
  imgClassName = "object-cover",
}: {
  src: string;
  alt: string;
  sizes?: string;
  className?: string;
  imgClassName?: string;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`Enlarge image: ${alt}`}
        className={`relative block w-full cursor-zoom-in ${className}`}
      >
        <Image src={src} alt={alt} fill sizes={sizes} className={imgClassName} />
      </button>
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          className="fixed inset-0 z-[60] bg-ink/85 p-4 md:p-10"
          onClick={() => setOpen(false)}
        >
          <div className="relative h-full w-full">
            <Image src={src} alt={alt} fill sizes="100vw" className="object-contain" />
          </div>
          <button
            type="button"
            aria-label="Close enlarged image"
            onClick={() => setOpen(false)}
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white text-lg text-teal"
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
}
