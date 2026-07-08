/**
 * Scroll-triggered image clip reveal with settle-scale.
 * @startingPoint section="Motion" subtitle="Clip + settle-scale image reveal" viewport="700x400"
 */
export interface RevealImageProps {
  src: string;
  alt?: string;
  /** CSS aspect-ratio, default "16/9" */
  ratio?: string;
  radius?: number;
  /** seconds */
  delay?: number;
  style?: React.CSSProperties;
}
