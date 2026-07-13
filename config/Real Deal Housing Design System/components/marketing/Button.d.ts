/**
 * Pill CTA link-button. Solid teal (primary), hairline outline (secondary),
 * warm (WhatsApp / high-intent only — one warm accent per viewport).
 * @startingPoint section="Core" subtitle="Pill CTA — teal / outline / warm" viewport="700x150"
 */
export interface ButtonProps {
  variant?: "primary" | "outline" | "warm";
  size?: "sm" | "md";
  href?: string;
  onClick?: (e: React.MouseEvent) => void;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
