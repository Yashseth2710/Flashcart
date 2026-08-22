import Link from "next/link";

import { SiteHeader } from "@/components/site-header";

const rules = [
  { term: "Fixed stock", detail: "A sale opens with a set number of units and no more appear." },
  { term: "Fixed window", detail: "It runs for a stated length of time, then it is over." },
  { term: "One hold each", detail: "Reserving puts a unit aside for five minutes while you decide." },
] as const;

export default function Home() {
  return (
    <>
      <SiteHeader />

      <main className="px-6 sm:px-12">
        <section className="grid items-end gap-10 py-16 lg:grid-cols-[1.15fr_1fr] lg:gap-20 lg:py-24">
          <div>
            <p className="font-script text-3xl leading-none text-ink-soft">Coming soon</p>
            <h1 className="mt-3 font-display text-5xl uppercase leading-[1.02] tracking-[0.045em] sm:text-6xl xl:text-7xl">
              Sales that
              <br />
              actually
              <br />
              run out
            </h1>
          </div>

          <div className="lg:pb-3">
            <p className="max-w-md text-[0.95rem] leading-[1.85] text-ink-soft">
              A flash sale puts a fixed number of units on the floor for a fixed length of
              time. Reserve one and it is held while you decide. Nothing is sold twice, however
              many people reach for it at once.
            </p>
            <Link
              href="/register"
              className="label mt-8 inline-block border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
            >
              Create an account
            </Link>
          </div>
        </section>

        <section className="border-t border-rule">
          <dl className="grid sm:grid-cols-3">
            {rules.map((rule, index) => (
              <div
                key={rule.term}
                className={`py-8 sm:py-10 ${index > 0 ? "border-t border-rule sm:border-l sm:border-t-0 sm:pl-8" : "sm:pr-8"}`}
              >
                <dt className="label text-ink">{rule.term}</dt>
                <dd className="mt-3 max-w-xs text-sm leading-relaxed text-ink-soft">
                  {rule.detail}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="flex flex-wrap items-baseline justify-between gap-4 border-t border-rule py-10">
          <p className="label text-muted">The catalogue is being stocked</p>
          <p className="text-sm text-ink-soft">
            Accounts work now, so you can be ready when the floor opens.
          </p>
        </section>
      </main>
    </>
  );
}
