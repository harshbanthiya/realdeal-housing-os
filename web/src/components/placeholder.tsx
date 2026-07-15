import { PLACEHOLDER_TOKENS } from "@/lib/content";

/** Buyer-friendly wording for internal placeholder tokens. */
const TOKEN_LABELS: Record<string, string> = {
  VERIFY: "being verified",
  RERA_VERIFY: "RERA being verified",
  PRICE_VERIFY: "price being verified",
  BROCHURE_LINK_PENDING: "coming soon",
};

/** A single honest "pending verification" chip rendered in monospace. */
export function PendingChip({ token }: { token: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-[4px] bg-mist px-1.5 py-0.5 font-mono text-[0.78em] font-medium tracking-tight text-teal/80 align-baseline"
      title="Pending verification — not yet confirmed"
    >
      <span
        aria-hidden
        className="inline-block h-1.5 w-1.5 rounded-full bg-warm/70"
      />
      {TOKEN_LABELS[token] ?? token.replace(/_/g, " ").toLowerCase()}
    </span>
  );
}

const TOKEN_RE = new RegExp(`\\b(${PLACEHOLDER_TOKENS.join("|")})\\b`, "g");

/** Renders text, replacing any known placeholder token with a PendingChip. */
export function Tokenize({ text }: { text: string }) {
  const parts = text.split(TOKEN_RE);
  return (
    <>
      {parts.map((part, i) =>
        PLACEHOLDER_TOKENS.includes(part) ? (
          <PendingChip key={i} token={part} />
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}
