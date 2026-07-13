export type Tone = "ready" | "blocked" | "review" | "active" | "neutral";

/**
 * Status pill — mono 11px, tint/10 background, fully rounded.
 * From web/src/components/ui/primitives.tsx.
 * @startingPoint section="Core" subtitle="Mono status pill with five tones" viewport="700x150"
 */
export interface PillProps {
  tone?: Tone;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
