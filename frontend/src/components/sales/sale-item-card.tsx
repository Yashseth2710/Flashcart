import Image from "next/image";
import Link from "next/link";

import { ReserveControl } from "@/components/sales/reserve-control";
import { formatPrice } from "@/lib/catalogue";
import { badgeWorthy, discountPercent, scarcityOf, type SaleItem } from "@/lib/sales";

/** How many are left, said the way the number deserves.
 *
 *  Only the last few earn the warm colour. Once everything on a page is urgent
 *  nothing is, so a healthy count is printed as plainly as any other fact and
 *  the eye is left free for the one card that is nearly gone. */
function StockLine({ available }: { available: number }) {
  const scarcity = scarcityOf(available);

  if (scarcity === "gone") {
    return <span className="text-reject">All gone</span>;
  }

  if (scarcity === "last-few") {
    /* Announced as it changes, since someone using a screen reader cannot see
       the number drop while they are deciding. The visible words are the
       announcement: a second hidden copy would read the count out twice. */
    return (
      <span className="text-hold" aria-live="polite">
        Only {available} left
      </span>
    );
  }

  if (scarcity === "going") {
    return <span className="text-ink">{available} left</span>;
  }

  return <span className="text-muted">{available} left</span>;
}

export function SaleItemCard({ item, isRunning }: { item: SaleItem; isRunning: boolean }) {
  const off = discountPercent(item.normal_price, item.sale_price);
  const soldOut = item.available_quantity === 0;

  return (
    <div className="group flex flex-col">
      {/* The picture and the name lead to the product. The button below sits
          outside that link, since one cannot be nested inside the other. */}
      <Link href={`/products/${item.product_slug}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden bg-panel">
          {item.image_url ? (
            <Image
              src={item.image_url}
              alt=""
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
              className={`object-contain p-6 transition-transform duration-500 group-hover:scale-[1.03] ${
                soldOut ? "opacity-40" : ""
              }`}
            />
          ) : null}
          {badgeWorthy(off) ? (
            <span className="label absolute left-0 top-0 bg-ink px-3 py-1.5 text-paper">
              {off}% off
            </span>
          ) : null}
        </div>

        <p className="mt-4 text-sm leading-snug text-ink">{item.product_name}</p>

        <p className="tabular mt-2 flex items-baseline gap-3 text-xs">
          <span className="text-ink">{formatPrice(item.sale_price)}</span>
          <span className="text-muted line-through">{formatPrice(item.normal_price)}</span>
        </p>
      </Link>

      <p className="tabular mt-2 text-xs">
        {isRunning ? (
          <StockLine available={item.available_quantity} />
        ) : (
          <span className="text-muted">{item.allocated_quantity} in the sale</span>
        )}
      </p>

      {/* Pushed to the bottom so the controls sit on one line across a row,
          whether or not a given card has a stepper above its button. */}
      <div className="mt-auto pt-4">
        {isRunning ? <ReserveControl item={item} /> : null}
        {!isRunning && item.max_per_user < item.allocated_quantity ? (
          <p className="label py-3.5 text-muted">Limit {item.max_per_user} each</p>
        ) : null}
      </div>
    </div>
  );
}
