import { Card } from "@/components/ui/card";
import { JobStep } from "@/lib/types";

interface JobProgressPanelProps {
  etaSecondsLeft: number;
  progressPct: number;
  steps: JobStep[];
  currentStep?: string;
}

const statusText: Record<JobStep["status"], string> = {
  pending: "Ожидает",
  running: "Выполняется",
  completed: "Готово",
  failed: "Ошибка"
};

const statusCls: Record<JobStep["status"], string> = {
  pending: "bg-[#9aab92] text-[#142013] border-[#4a5647]",
  running: "bg-[#c6b07b] text-[#171108] border-[#7c5f1f]",
  completed: "bg-[#8fb07c] text-[#0d150d] border-[#2f5f2f]",
  failed: "bg-[#cfa18f] text-[#2d0c0c] border-[#601b1b]"
};

export function JobProgressPanel({ etaSecondsLeft, progressPct, steps, currentStep }: JobProgressPanelProps) {
  return (
    <Card className="space-y-4 bg-[var(--card-2)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="crt-kicker">Обработка раунда</p>
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">Можно продолжать работать на странице</h3>
        </div>
        <p className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm font-black">
          ~{Math.max(0, etaSecondsLeft)} сек
        </p>
      </div>

      <div className="space-y-2 rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-3">
        <div className="h-4 w-full overflow-hidden rounded-sm border-2 border-[var(--line)] bg-[#95aa82]">
          <div className="h-full bg-[var(--accent)] transition-all duration-300" style={{ width: `${Math.max(0, Math.min(100, progressPct))}%` }} />
        </div>
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">{progressPct}% выполнено</p>
      </div>

      <div className="grid gap-2">
        {steps.length === 0 ? <p className="text-sm font-semibold text-[var(--muted)]">Инициализация этапов...</p> : null}
        {steps.map((step) => (
          <div
            key={step.key}
            className="flex flex-wrap items-center justify-between gap-2 rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2"
          >
            <p className="text-sm font-bold leading-relaxed sm:text-base">
              {step.label}
              {currentStep === step.key ? " ..." : ""}
            </p>
            <span className={`rounded-md border-4 px-2 py-1 text-xs font-black uppercase tracking-[0.08em] ${statusCls[step.status]}`}>
              {statusText[step.status]}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
