/** Vertical scroll parallax wrapper. Size the child ~15% taller than the window to avoid gaps. */
export interface ParallaxProps {
  /** drift factor; 0.05 subtle → 0.2 pronounced. Default 0.12 */
  speed?: number;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
