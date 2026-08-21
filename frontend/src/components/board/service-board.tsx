"use client";

import { useQuery } from "@tanstack/react-query";

import { BoardRow } from "@/components/board/board-row";
import { fetchHealth } from "@/lib/health";

const databaseLabel = {
  connected: { value: "Connected", tone: "fill" },
  unreachable: { value: "Unreachable", tone: "reject" },
  not_configured: { value: "Not configured", tone: "hold" },
} as const;

export function ServiceBoard() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
  });

  if (isPending) {
    return <p className="tabular mt-10 text-sm text-dim">Reading board…</p>;
  }

  if (isError) {
    return (
      <div className="mt-10">
        <BoardRow label="Service" value="No answer" tone="reject" />
        <p className="mt-4 text-sm leading-relaxed text-ink/70">
          The storefront could not reach the service. Start it with{" "}
          <code className="tabular text-ink">uvicorn app.main:app --reload</code> from the backend
          folder.
        </p>
      </div>
    );
  }

  const database = databaseLabel[data.database];

  return (
    <div className="mt-10">
      <BoardRow label="Service" value="Answering" tone="fill" />
      <BoardRow label="Database" value={database.value} tone={database.tone} />
      <BoardRow label="Environment" value={data.environment} tone="dim" />
    </div>
  );
}
