import { ServiceBoard } from "@/components/board/service-board";

export default function Home() {
  return (
    <main className="mx-auto min-h-dvh w-full max-w-3xl px-6 py-16 sm:py-24">
      <header className="border-b-2 border-ink pb-4">
        <p className="font-display text-xs uppercase tracking-[0.3em] text-dim">Status board</p>
        <h1 className="mt-2 font-display text-5xl uppercase leading-none tracking-tight sm:text-7xl">
          FlashCart
        </h1>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-ink/70">
          Buy before it&apos;s gone. Nothing is on sale yet — this board reports whether the
          storefront can reach the service that will hold your stock.
        </p>
      </header>

      <ServiceBoard />
    </main>
  );
}
