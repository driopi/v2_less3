import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface RoundIndicatorProps {
  currentRound: number;
  totalRounds: number;
  roundSummaries: string[];
}

export function RoundIndicator({ currentRound, totalRounds, roundSummaries }: RoundIndicatorProps) {
  const progress = ((currentRound - 1) / totalRounds) * 100;

  return (
    <Card className="space-y-4 bg-[var(--card-2)]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="crt-kicker">Интервью</p>
          <h2 className="text-3xl font-black uppercase tracking-[0.05em] sm:text-4xl">
            Раунд {currentRound} / {totalRounds}
          </h2>
        </div>
        <p className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
          До 9 вопросов
        </p>
      </div>

      <Progress value={progress} />

      {roundSummaries.length > 0 ? (
        <div className="space-y-2 rounded-lg border-4 border-[var(--line)] bg-[var(--card)] p-4">
          <p className="crt-kicker">Итоги прошлых раундов</p>
          {roundSummaries.map((item, idx) => (
            <p key={idx} className="text-sm font-semibold leading-relaxed sm:text-base">
              {idx + 1}. {item}
            </p>
          ))}
        </div>
      ) : null}
    </Card>
  );
}
