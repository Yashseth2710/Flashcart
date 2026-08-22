import Image from "next/image";
import Link from "next/link";

import { formatPrice } from "@/lib/catalogue";
import { discountPercent, type SaleItem } from "@/lib/sales";

export function SaleItemCard({ item, isRunning }: { item: SaleItem; isRunning: boolean }) {
  const off = discountPercent(item.normal_price, item.sale_price);
  const soldOut = item.available_quantity === 0;

  return (
    <Link href={`/products/${item.product_slug}`} className="group block">
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
        {off > 0 ? (
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

      <p className="tabular mt-2 text-xs">
        {soldOut ? (
          <span className="text-reject">All gone</span>
        ) : isRunning ? (
          <span className="text-hold">{item.available_quantity} left</span>
        ) : (
          <span className="text-muted">{item.allocated_quantity} in the sale</span>
        )}
      </p>
    </Link>
  );
}
