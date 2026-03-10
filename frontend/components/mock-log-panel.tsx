import { Card } from "@/components/ui/card";

export interface MockLogEntry {
  id: string;
  at: string;
  source: string;
  message: string;
}

interface MockLogPanelProps {
  entries: MockLogEntry[];
  title?: string;
  kicker?: string;
}

export function MockLogPanel({ entries, title = "Логи mock-режима", kicker = "Debug Console" }: MockLogPanelProps) {
  return (
    <Card className="space-y-3 bg-[var(--card-2)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="crt-kicker">{kicker}</p>
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">{title}</h3>
        </div>
        <p className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-black uppercase tracking-[0.08em]">
          {entries.length} событий
        </p>
      </div>

      <div className="max-h-80 overflow-y-auto rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-4 py-3">
        {entries.length === 0 ? <p className="text-sm font-semibold text-[var(--muted)]">Ожидание событий...</p> : null}
        <div className="space-y-2">
          {entries.map((entry) => (
            <div key={entry.id} className="py-1">
              <p className="text-xs font-black uppercase tracking-[0.08em] text-[var(--muted)]">
                [{entry.at}] {entry.source.toUpperCase()}
              </p>
              <p className="mt-1 text-sm font-semibold leading-relaxed sm:text-base">{entry.message}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
