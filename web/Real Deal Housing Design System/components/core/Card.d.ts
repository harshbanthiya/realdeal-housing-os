/** Shadowless card — white bg + 1px mist-deep border. 12px radius in cockpit, 16px on the site. */
export interface CardProps {
  children?: React.ReactNode;
  /** 12 (cockpit, default) or 16 (marketing site) */
  radius?: number;
  padding?: number | string;
  style?: React.CSSProperties;
}
