import type { ReactNode } from "react";

export type Tone = "ready" | "blocked" | "review" | "active" | "neutral";

const TONES: Record<Tone, string> = {
  ready: "bg-teal/10 text-teal",
  blocked: "bg-warm/10 text-warm",
  review: "bg-amber/10 text-amber",
  active: "bg-accent/10 text-accent",
  neutral: "bg-mist text-ink/55",
};

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[11px] font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function Dot({ tone = "neutral" }: { tone?: Tone }) {
  const c: Record<Tone, string> = {
    ready: "bg-teal",
    blocked: "bg-warm",
    review: "bg-amber",
    active: "bg-accent",
    neutral: "bg-ink/30",
  };
  return <span className={`inline-block h-2 w-2 rounded-full ${c[tone]}`} />;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-mist-deep bg-white ${className}`}>{children}</div>;
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-ink/55 ${className}`}>{children}</span>;
}

export function PanelTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-4 flex items-baseline justify-between">
      <h2 className="text-[15px] font-semibold tracking-tight text-teal">{children}</h2>
      {hint && <span className="font-mono text-[11px] text-ink/40">{hint}</span>}
    </div>
  );
}
