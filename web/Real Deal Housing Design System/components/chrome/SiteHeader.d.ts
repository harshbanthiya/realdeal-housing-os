/**
 * Sticky site header — white/85 + blur, RDH monogram, nav, teal phone pill.
 * @startingPoint section="Chrome" subtitle="Sticky blurred header with phone CTA" viewport="1200x64"
 */
export interface SiteHeaderProps {
  nav?: string[];
  phone?: string;
  /** label of the active nav item */
  active?: string;
}
