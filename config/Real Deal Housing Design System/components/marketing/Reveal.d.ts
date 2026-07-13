/** Scroll reveal (fade + rise, once). Stagger grids with delay = i * 0.05. */
export interface RevealProps {
  children?: React.ReactNode;
  /** seconds; grids use i * 0.03–0.07 */
  delay?: number;
  style?: React.CSSProperties;
}
