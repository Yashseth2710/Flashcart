"use client";

import { useEffect, useState } from "react";

type Remaining = {
  total: number;
  hours: number;
  minutes: number;
  seconds: number;
  hasPassed: boolean;
};

function measure(target: number): Remaining {
  const total = Math.max(0, target - Date.now());
  return {
    total,
    hours: Math.floor(total / 3_600_000),
    minutes: Math.floor((total % 3_600_000) / 60_000),
    seconds: Math.floor((total % 60_000) / 1000),
    hasPassed: total === 0,
  };
}

/** Counts down to a moment, ticking only while there is time left. */
export function useCountdown(isoTime: string): Remaining {
  const target = new Date(isoTime).getTime();
  const [remaining, setRemaining] = useState(() => measure(target));
  const [countingTo, setCountingTo] = useState(target);

  // Pointing at a different moment restarts the count during render rather than
  // after it, which avoids a frame showing the old time.
  if (countingTo !== target) {
    setCountingTo(target);
    setRemaining(measure(target));
  }

  useEffect(() => {
    if (Date.now() >= target) return;

    const timer = setInterval(() => {
      const next = measure(target);
      setRemaining(next);
      if (next.hasPassed) clearInterval(timer);
    }, 1000);

    return () => clearInterval(timer);
  }, [target]);

  return remaining;
}

export function formatRemaining({ hours, minutes, seconds }: Remaining): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0
    ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
    : `${pad(minutes)}:${pad(seconds)}`;
}
