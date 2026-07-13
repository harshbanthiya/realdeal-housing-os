/** Mobile sticky bottom CTA bar; hide it when the enquiry form is in view. */
export interface StickyCtaProps {
  hidden?: boolean;
  onRequest?: (e: React.MouseEvent) => void;
  whatsappHref?: string;
}
