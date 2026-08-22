import Link from "next/link";

import { LogoInline } from "@/components/brand/logo";

type Props = {
  eyebrow: string;
  title: string;
  aside: React.ReactNode;
  children: React.ReactNode;
};

export function AuthLayout({ eyebrow, title, aside, children }: Props) {
  return (
    <main className="min-h-dvh lg:grid lg:grid-cols-[1fr_44%]">
      <div className="relative flex flex-col px-6 py-12 sm:px-14 lg:px-20">
        <Link
          href="/"
          aria-label="FlashCart home"
          className="lg:absolute lg:left-20 lg:top-12"
        >
          <LogoInline />
        </Link>

        <div className="flex flex-1 items-center">
          <div className="w-full max-w-sm py-12 lg:py-0">
            <p className="font-script text-2xl leading-none text-ink-soft">{eyebrow}</p>
            <h1 className="mt-3 font-display text-4xl uppercase leading-[1.05] tracking-[0.045em] sm:text-5xl">
              {title}
            </h1>
            {children}
          </div>
        </div>
      </div>

      <aside className="hidden bg-panel lg:block">{aside}</aside>
    </main>
  );
}
