/** Infinite marquee of building names / areas with warm mid-dot separators. Max one per page. */
export interface TickerProps {
  items: React.ReactNode[];
  /** seconds per loop, default 28 */
  speed?: number;
  style?: React.CSSProperties;
  itemStyle?: React.CSSProperties;
}
