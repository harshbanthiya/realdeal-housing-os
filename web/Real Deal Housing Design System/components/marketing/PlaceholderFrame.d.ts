/** Fixed-aspect image well: real photo if `src`, else the honest dashed placeholder. */
export interface PlaceholderFrameProps {
  /** CSS aspect-ratio, e.g. "21/9", "16/9", "4/3", "1/1" */
  ratio?: string;
  /** mono label shown when no src (e.g. "VISUAL_DIRECTION_PENDING") */
  label?: React.ReactNode;
  src?: string;
  alt?: string;
  radius?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}
