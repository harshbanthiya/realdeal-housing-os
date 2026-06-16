import { ListingCard } from "@/components/cards";
import type { Listing } from "@/lib/site";

export function ListingGrid({ items }: { items: Listing[] }) {
  return (
    <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((l, i) => (
        <ListingCard key={l.title + i} listing={l} delay={(i % 3) * 0.05} />
      ))}
    </div>
  );
}
