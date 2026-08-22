import Image from "next/image";
import Link from "next/link";

import { formatPrice, type ProductSummary } from "@/lib/catalogue";

export function ProductCard({ product }: { product: ProductSummary }) {
  return (
    <Link href={`/products/${product.slug}`} className="group block">
      <div className="relative aspect-[4/5] overflow-hidden bg-panel">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt=""
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-6 transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : null}
      </div>

      <p className="mt-4 text-sm leading-snug text-ink">{product.name}</p>
      {product.brand ? <p className="mt-1 text-xs text-muted">{product.brand}</p> : null}
      <p className="tabular mt-2 text-xs text-ink-soft">{formatPrice(product.base_price)}</p>
    </Link>
  );
}
