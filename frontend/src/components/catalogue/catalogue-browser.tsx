"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { CatalogueFilters } from "@/components/catalogue/catalogue-filters";
import { ProductGrid } from "@/components/catalogue/product-grid";
import { browseProducts, fetchCategories } from "@/lib/catalogue";

const PAGE_SIZE = 24;

export function CatalogueBrowser() {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // Changing what is being looked for starts again at the first page, rather
  // than leaving someone on page four of a result that now has one page.
  function changeSearch(term: string) {
    setSearch(term);
    setPage(0);
  }

  function changeCategory(next: string | null) {
    setCategory(next);
    setPage(0);
  }

  // Waiting for a pause in typing keeps one request per word, not per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
    staleTime: 10 * 60_000,
  });

  const { data, isPending, isError } = useQuery({
    queryKey: ["products", debounced, category, page],
    queryFn: () =>
      browseProducts({
        search: debounced || undefined,
        category: category ?? undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const pages = Math.ceil(total / PAGE_SIZE);

  return (
    <>
      <CatalogueFilters
        categories={categories}
        active={category}
        search={search}
        onCategory={changeCategory}
        onSearch={changeSearch}
        total={total}
      />

      <div className="mt-12">
        {isError ? (
          <p className="border-l-2 border-reject pl-4 text-sm text-reject">
            The shop could not be loaded. Try again in a moment.
          </p>
        ) : isPending ? (
          <p className="tabular text-sm text-muted">Loading the shop…</p>
        ) : data.items.length === 0 ? (
          <EmptyResult search={debounced} onClear={() => {
              changeSearch("");
              changeCategory(null);
            }} />
        ) : (
          <ProductGrid products={data.items} />
        )}
      </div>

      {pages > 1 ? (
        <nav className="mt-16 flex items-center justify-between border-t border-rule pt-6">
          <PageButton disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            Previous
          </PageButton>
          <p className="tabular text-xs text-muted">
            {page + 1} of {pages}
          </p>
          <PageButton disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>
            Next
          </PageButton>
        </nav>
      ) : null}
    </>
  );
}

function EmptyResult({ search, onClear }: { search: string; onClear: () => void }) {
  return (
    <div className="py-12">
      <p className="font-display text-2xl text-ink">
        {search ? `Nothing matches “${search}”.` : "Nothing here yet."}
      </p>
      <button onClick={onClear} className="label mt-5 text-muted underline underline-offset-4 hover:text-ink">
        Clear the filters
      </button>
    </div>
  );
}

function PageButton({
  disabled,
  onClick,
  children,
}: {
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="label text-muted transition-colors hover:text-ink disabled:opacity-35 disabled:hover:text-muted"
    >
      {children}
    </button>
  );
}
