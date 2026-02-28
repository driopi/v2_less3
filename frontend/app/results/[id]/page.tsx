"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ChecklistPreview } from "@/components/checklist-preview";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { downloadResults, getResults } from "@/lib/api";
import { ChecklistItem } from "@/lib/types";

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getResults(sessionId);
        if (!cancelled) {
          setChecklist(res.checklist);
          setRoundSummaries(res.round_summaries);
          setIsComplete(res.is_complete);
        }
      } catch {
        if (!cancelled) setChecklist([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-5 px-4 py-8 sm:px-6 md:py-10">
      <section className="crt-shell w-full">
        <div className="space-y-5 rounded-[28px] border-4 border-[var(--line)] bg-[var(--card)] p-4 sm:p-6">
          <Card className="space-y-3 bg-[var(--card-2)]">
            <p className="crt-kicker">Финал</p>
            <h1 className="text-3xl font-black uppercase tracking-[0.05em] sm:text-4xl">Результаты интервью</h1>
            <p className="text-sm font-semibold leading-relaxed sm:text-base">
              {isComplete ? "Сессия завершена. Чеклист собран и готов к выгрузке." : "Сессия еще не завершена."}
            </p>
          </Card>

          <ChecklistPreview
            sessionId={sessionId}
            checklist={checklist}
            roundSummaries={roundSummaries}
            onDownload={() => {
              window.open(downloadResults(sessionId), "_blank");
            }}
          />

          <Button className="w-full sm:w-auto" variant="secondary" onClick={() => router.push("/")}>
            Новая сессия
          </Button>
        </div>
      </section>
    </main>
  );
}
