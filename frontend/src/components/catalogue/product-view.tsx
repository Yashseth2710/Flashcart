"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";

import { ApiError } from "@/lib/api";
import { fetchProduct, formatPrice } from "@/lib/catalogue";

export function ProductView({ slug }: { slug: string }) {
  const { data, isPending, error } = useQuery({
    queryKey: ["product", slug],
    queryFn: () => fetchProduct(slug),
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 1,
  });

  if (isPending) {
    return <p className="tabular px-6 py-20 text-sm text-muted sm:px-12">Loading…</p>;
  }

  if (error) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <main className="px-6 py-24 sm:px-12">
        <p className="font-display text-3xl uppercase tracking-[0.045em]">
          {missing ? "No such product" : "Something went wrong"}
        </p>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
          {missing
            ? "It may have been taken off the shop."
            : "The shop could not be reached. Try again in a moment."}
        </p>
        <Link
          href="/products"
          className="label mt-8 inline-block border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
        >
          Back to the shop
        </Link>
      </main>
    );
  }

  const variant = data.variants[0];
  const available = variant?.available_quantity ?? 0;

  return (
    <main className="px-6 pb-24 sm:px-12">
      <nav className="py-6">
        <Link href="/products" className="label text-muted hover:text-ink">
          ← The shop
        </Link>
      </nav>

      <div className="grid gap-12 lg:grid-cols-[1.1fr_1fr] lg:gap-20">
        <div className="relative aspect-[4/5] bg-panel">
          {data.image_url ? (
            <Image
              src={data.image_url}
              alt=""
              fill
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-contain p-10"
              priority
            />
          ) : null}
        </div>

        <div className="lg:py-8">
          {data.brand ? <p className="label text-muted">{data.brand}</p> : null}
          <h1 className="mt-3 font-display text-4xl uppercase leading-[1.08] tracking-[0.045em]">
            {data.name}
          </h1>
          <p className="tabular mt-5 text-lg">{formatPrice(data.base_price)}</p>

          {data.description ? (
            <p className="mt-8 max-w-md text-[0.95rem] leading-[1.85] text-ink-soft">
              {data.description}
            </p>
          ) : null}

          <dl className="mt-10 border-t border-rule">
            <Row term="In stock" value={available > 0 ? String(available) : "None left"} />
            {variant ? <Row term="Item code" value={variant.sku} /> : null}
            {data.category ? (
              <Row term="Category" value={data.category.replace(/-/g, " ")} />
            ) : null}
          </dl>

          <p className="mt-10 max-w-sm text-sm leading-relaxed text-muted">
            This product is not in a sale right now. When it is, you will be able to reserve one
            here and hold it while you check out.
          </p>
        </div>
      </div>
    </main>
  );
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-rule py-3.5">
      <dt className="label text-muted">{term}</dt>
      <dd className="tabular text-sm text-ink">{value}</dd>
    </div>
  );
}
