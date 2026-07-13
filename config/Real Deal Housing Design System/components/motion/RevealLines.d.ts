/**
 * Masked line-by-line text reveal — each line rises out of an overflow clip, staggered 90ms.
 * @startingPoint section="Motion" subtitle="Halston-style masked headline reveal" viewport="700x220"
 */
export interface RevealLinesProps {
  /** one string per visual line — you control the line breaks */
  lines: React.ReactNode[];
  /** element tag, default "h2" */
  as?: string;
  /** base delay in seconds */
  delay?: number;
  style?: React.CSSProperties;
  lineStyle?: React.CSSProperties;
}
