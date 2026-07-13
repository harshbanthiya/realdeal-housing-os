import React from "react";

export function Mono({ children, size = 12, style, title }) {
  return (
    <span
      title={title}
      style={{ fontFamily: "var(--font-mono)", fontSize: size, color: "var(--ink-55)", ...style }}
    >
      {children}
    </span>
  );
}
