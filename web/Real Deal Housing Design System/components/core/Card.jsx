import React from "react";

export function Card({ children, radius = 12, padding, style }) {
  return (
    <div
      style={{
        borderRadius: radius,
        border: "1px solid var(--mist-deep)",
        background: "#fff",
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
