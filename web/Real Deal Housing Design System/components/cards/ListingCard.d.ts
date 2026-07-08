/**
 * Property listing card from the buy/rent grids.
 * @startingPoint section="Cards" subtitle="Listing card with badge, meta and Indian price format" viewport="700x340"
 */
export interface ListingCardProps {
  title: string;
  location: string;
  config: string;
  /** numeric string or "—" to omit */
  sqft?: string;
  /** Indian format: "₹4,59,00,000" · "₹1,10,000 / mo" · "On request" */
  price: string;
  type?: "sale" | "rent";
  /** real photo; omit for honest placeholder */
  src?: string;
}
