import React from "react";

const MAP = {
  operator_confirmed: { label: "Confirmed", background: "var(--tone-ready-bg)", color: "var(--tone-ready-fg)" },
  pending_review: { label: "Under review", background: "var(--tone-blocked-bg)", color: "var(--tone-blocked-fg)" },
  pending: { label: "Pending", background: "var(--mist)", color: "var(--ink-50)" },
};

/** Verified-facts-ledger status badge. */
export function StatusBadge({ status = "pending" }) {
  const s = MAP[status] || MAP.pending;
  return (
    <span
      style={{
        borderRadius: 9999, padding: "4px 10px",
        fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 500,
        background: s.background, color: s.color,
      }}
    >
      {s.label}
    </span>
  );
}
