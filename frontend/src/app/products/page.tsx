import { SiteHeader } from "@/components/site-header";
import { CatalogueBrowser } from "@/components/catalogue/catalogue-browser";

export const metadata = { title: "Shop · FlashCart" };

export default function ProductsPage() {
  return (
    <>
      <SiteHeader />
      <main className="px-6 pb-24 sm:px-12">
        <header className="py-12 lg:py-16">
          <p className="font-script text-2xl leading-none text-ink-soft">Everything we stock</p>
          <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em] sm:text-5xl">
            The shop
          </h1>
        </header>

        <CatalogueBrowser />
      </main>
    </>
  );
}
