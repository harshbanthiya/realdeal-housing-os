"use client";

import { MotionConfig } from "framer-motion";
import type { ReactNode } from "react";

/** Makes every framer-motion animation respect prefers-reduced-motion. */
export function SiteMotionConfig({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
