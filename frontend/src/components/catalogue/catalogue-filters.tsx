"use client";

type Props = {
  categories: string[];
  active: string | null;
  search: string;
  onCategory: (category: string | null) => void;
  onSearch: (term: string) => void;
  total: number;
};

export function CatalogueFilters({
  categories,
  active,
  search,
  onCategory,
  onSearch,
  total,
}: Props) {
  return (
    <div className="border-b border-rule pb-6">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <input
          type="search"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder="Search by name or brand"
          aria-label="Search products"
          className="w-full max-w-xs border-b border-rule bg-transparent pb-2 text-sm
                     outline-none transition-colors placeholder:text-muted/70 focus:border-ink sm:w-64"
        />
        <p className="tabular text-xs text-muted">
          {total} {total === 1 ? "product" : "products"}
        </p>
      </div>

      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-3">
        <FilterButton label="Everything" isActive={active === null} onClick={() => onCategory(null)} />
        {categories.map((category) => (
          <FilterButton
            key={category}
            label={category.replace(/-/g, " ")}
            isActive={active === category}
            onClick={() => onCategory(category)}
          />
        ))}
      </div>
    </div>
  );
}

function FilterButton({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={isActive}
      className={`label transition-colors ${
        isActive ? "text-ink underline underline-offset-[6px]" : "text-muted hover:text-ink"
      }`}
    >
      {label}
    </button>
  );
}
