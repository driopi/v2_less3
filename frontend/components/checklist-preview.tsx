import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChecklistItem, PortraitCard, ToolInsight } from "@/lib/types";

interface ChecklistPreviewProps {
  sessionId: string;
  checklist: ChecklistItem[];
  toolInsights: ToolInsight[];
  roundSummaries: string[];
  portrait?: PortraitCard;
  onDownload: () => void;
}

const statusMeta: Record<ChecklistItem["status"], { label: string; cls: string }> = {
  confirmed: {
    label: "Подтверждено",
    cls: "border-[#2f5f2f] bg-[#8fb07c] text-[#0d150d]"
  },
  needs_clarification: {
    label: "Нужно уточнить",
    cls: "border-[#7c5f1f] bg-[#c6b07b] text-[#171108]"
  },
  not_discussed: {
    label: "Не обсуждали",
    cls: "border-[#4a5647] bg-[#9aab92] text-[#142013]"
  }
};

function groupByCategory(items: ChecklistItem[]) {
  return items.reduce<Record<string, ChecklistItem[]>>((acc, item) => {
    if (!acc[item.category]) acc[item.category] = [];
    acc[item.category].push(item);
    return acc;
  }, {});
}

export function ChecklistPreview({ sessionId, checklist, toolInsights, roundSummaries, portrait, onDownload }: ChecklistPreviewProps) {
  const grouped = groupByCategory(checklist);
  const categories = Object.keys(grouped);

  return (
    <div className="space-y-4">
      <Card className="space-y-4 bg-[var(--card-2)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="crt-kicker">Результат</p>
            <h2 className="text-2xl font-black uppercase tracking-[0.05em] sm:text-3xl">Итоговый чеклист</h2>
          </div>
          <p className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
            Сессия: {sessionId.slice(0, 8)}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2">
            <p className="crt-kicker">Категории</p>
            <p className="mt-1 text-2xl font-black">{categories.length}</p>
          </div>
          <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2">
            <p className="crt-kicker">Пункты</p>
            <p className="mt-1 text-2xl font-black">{checklist.length}</p>
          </div>
          <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2">
            <p className="crt-kicker">Раундов</p>
            <p className="mt-1 text-2xl font-black">{roundSummaries.length || 3}</p>
          </div>
        </div>

        <Button className="w-full sm:w-auto" onClick={onDownload}>
          Скачать .md
        </Button>
      </Card>

      {categories.length === 0 ? (
        <Card className="bg-[var(--card-2)]">
          <p className="text-sm font-semibold sm:text-base">Чеклист пока пустой.</p>
        </Card>
      ) : (
        categories.map((category) => (
          <Card key={category} className="space-y-3 bg-[var(--card-2)]">
            <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">{category}</h3>
            <div className="space-y-3">
              {grouped[category].map((item, idx) => {
                const meta = statusMeta[item.status];
                return (
                  <div key={`${item.item}-${idx}`} className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <p className="max-w-3xl text-sm font-bold leading-relaxed sm:text-base">{item.item}</p>
                      <span className={`rounded-md border-4 px-3 py-1 text-xs font-black uppercase tracking-[0.08em] ${meta.cls}`}>
                        {meta.label}
                      </span>
                    </div>
                    {item.notes ? <p className="mt-3 text-sm font-semibold text-[var(--muted)]">{item.notes}</p> : null}
                  </div>
                );
              })}
            </div>
          </Card>
        ))
      )}

      {roundSummaries.length > 0 ? (
        <Card className="space-y-3 bg-[var(--card-2)]">
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">Итоги раундов</h3>
          {roundSummaries.map((summary, idx) => (
            <p key={idx} className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-4 py-3 text-sm font-semibold leading-relaxed sm:text-base">
              {idx + 1}. {summary}
            </p>
          ))}
        </Card>
      ) : null}

      {toolInsights.length > 0 ? (
        <Card className="space-y-3 bg-[var(--card-2)]">
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">Инструменты агента</h3>
          {toolInsights.map((insight, idx) => (
            <div key={`${insight.tool_name}-${idx}`} className="space-y-2 rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
              <p className="text-sm font-black uppercase tracking-[0.07em]">{insight.title}</p>
              <p className="text-sm font-semibold leading-relaxed sm:text-base">{insight.summary}</p>
              {Object.keys(insight.details).length > 0 ? (
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
                  {Object.entries(insight.details)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(" • ")}
                </p>
              ) : null}
            </div>
          ))}
        </Card>
      ) : null}

      {portrait ? (
        <Card className="space-y-4 bg-[var(--card-2)]">
          <h3 className="text-xl font-black uppercase tracking-[0.04em] sm:text-2xl">Карточка портрета</h3>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
              <p className="crt-kicker">Эмоциональная стабильность</p>
              <p className="mt-2 text-3xl font-black">{portrait.emotional_stability}/10</p>
            </div>
            <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
              <p className="crt-kicker">Скрытое напряжение</p>
              <p className="mt-2 text-3xl font-black">{portrait.hidden_tension}/10</p>
            </div>
            <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
              <p className="crt-kicker">Уверенность формулировок</p>
              <p className="mt-2 text-3xl font-black">{portrait.confidence_proxy}/10</p>
            </div>
            <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
              <p className="crt-kicker">Темы-триггеры</p>
              <p className="mt-2 text-2xl font-black">
                {portrait.triggers.length > 0 ? `${portrait.triggers.length} зоны` : "не выявлены"}
              </p>
            </div>
          </div>

          <div className="space-y-3 rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
            <p className="crt-kicker">Детализация триггеров</p>
            {portrait.triggers.length === 0 ? (
              <p className="text-base font-semibold">Существенных триггеров по ответам не обнаружено.</p>
            ) : (
              portrait.triggers.map((trigger) => (
                <div key={`${trigger.question_number}-${trigger.score}`} className="rounded-md border-4 border-[var(--line)] bg-[var(--card-2)] p-3">
                  <p className="text-sm font-black uppercase tracking-[0.06em]">
                    Раунд {trigger.round_number}, вопрос {trigger.question_in_round}
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-relaxed">{trigger.question_text}</p>
                  <p className="mt-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
                    {trigger.reason} • score {Math.round(trigger.score * 100) / 100}
                  </p>
                </div>
              ))
            )}
          </div>

          <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
            <p className="crt-kicker">Доминирующие эмоции</p>
            <p className="mt-2 text-base font-bold">{portrait.dominant_emotions.join(", ") || "спокойствие"}</p>
          </div>

          <div className="rounded-md border-4 border-[var(--line)] bg-[var(--card)] p-4">
            <p className="crt-kicker">Рекомендация</p>
            <p className="mt-2 text-base font-semibold leading-relaxed">{portrait.recommendation}</p>
            <p className="mt-3 text-xs font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">
              Это индикаторы речи и формулировок, а не медицинский или психологический диагноз.
            </p>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
