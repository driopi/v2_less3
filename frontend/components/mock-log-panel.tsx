import { Card } from "@/components/ui/card";

export interface MockLogEntry {
  id: string;
  at: string;
  source: "ui" | "mock" | "job";
  message: string;
}

interface MockLogPanelProps {
  entries: MockLogEntry[];
}

const sourceLabel: Record<MockLogEntry["source"], string> = {
  ui: "UI",
  mock: "MOCK",
  job: "JOB"
};

export function MockLogPanel({ entries }: MockLogPanelProps) {
  return (
    <Card className="space-y-3 bg-[var(--card-2)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="crt-kicker">Debug Console</p>
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">Логи mock-режима</h3>
        </div>
        <p className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-black uppercase tracking-[0.08em]">
          {entries.length} событий
        </p>
      </div>

      <div className="max-h-80 space-y-2 overflow-y-auto rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-3">
        {entries.length === 0 ? <p className="text-sm font-semibold text-[var(--muted)]">Ожидание событий...</p> : null}
        {entries.map((entry) => (
          <div key={entry.id} className="rounded-md border-4 border-[var(--line)] bg-[var(--card-2)] px-3 py-2">
            <p className="text-xs font-black uppercase tracking-[0.08em] text-[var(--muted)]">
              [{entry.at}] {sourceLabel[entry.source]}
            </p>
            <p className="mt-1 text-sm font-semibold leading-relaxed sm:text-base">{entry.message}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
