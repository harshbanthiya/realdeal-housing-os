/** In-view count-up for stat numerals. Only for verified numbers — never invent stats. */
export interface CountUpProps {
  value: number;
  prefix?: string;
  suffix?: string;
  /** seconds, default 1.4 */
  duration?: number;
  style?: React.CSSProperties;
}
