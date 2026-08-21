"use client";

import { useEffect, useRef, useState } from "react";

type Tone = "fill" | "hold" | "reject" | "dim";

const toneClass: Record<Tone, string> = {
  fill: "text-fill",
  hold: "text-hold",
  reject: "text-reject",
  dim: "text-dim",
};

export function BoardRow({ label, value, tone = "dim" }: { label: string; value: string; tone?: Tone }) {
  const [flipping, setFlipping] = useState(false);
  const previous = useRef(value);

  useEffect(() => {
    if (previous.current === value) return;
    previous.current = value;
    setFlipping(true);
    const timer = setTimeout(() => setFlipping(false), 260);
    return () => clearTimeout(timer);
  }, [value]);

  return (
    <div className="flex items-baseline gap-6 border-b border-ink/15 py-3">
      <span className="font-display text-xs uppercase tracking-[0.18em] text-dim">{label}</span>
      <span
        className={`tabular ml-auto text-sm uppercase ${toneClass[tone]} ${
          flipping ? "animate-flip" : ""
        }`}
      >
        {value}
      </span>
    </div>
  );
}
