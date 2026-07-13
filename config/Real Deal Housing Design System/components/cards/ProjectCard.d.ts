/**
 * Featured project card (home / projects pages).
 * @startingPoint section="Cards" subtitle="Project card with 16/9 image and hover wash" viewport="700x380"
 */
export interface ProjectCardProps {
  name: string;
  location: string;
  /** e.g. "44-storey tower · 2–4.5 BHK" */
  meta: string;
  href?: string;
  src?: string;
}
