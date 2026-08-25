"use client";

import Image from "next/image";
import Link from "next/link";

import { KeepButton, KeepMark } from "@/components/saved/keep-button";
import { useSaved } from "@/hooks/use-saved";
import { formatPrice, type ProductSummary } from "@/lib/catalogue";

export function ProductCard({ product }: { product: ProductSummary }) {
  const { data: saved } = useSaved();
  const isKept = saved?.some((item) => item.product_id === product.id) ?? false;

  return (
    <div className="group relative flex h-full flex-col pl-4">
      {/* A marked page in a catalogue, rather than a heart on a photograph.
          The rule is the same one every card carries; keeping thickens it. */}
      <KeepMark isKept={isKept} />

      {/* The picture and the name lead to the product; the button below sits
          outside that link, since one cannot be nested inside the other. */}
      <Link href={`/products/${product.slug}`} className="block">
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

      {/* Pushed down so the button, and the rule beside it, line up across
          a row of cards whose names run to different lengths. */}
      <div className="mt-auto">
        <KeepButton productId={product.id} />
      </div>
    </div>
  );
}
