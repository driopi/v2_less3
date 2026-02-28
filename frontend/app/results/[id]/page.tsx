"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ChecklistPreview } from "@/components/checklist-preview";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { downloadResults, getResults, getSummaryAudio } from "@/lib/api";
import { ChecklistItem } from "@/lib/types";

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

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

          <Card className="space-y-4 bg-[var(--card-2)]">
            <div className="flex flex-wrap gap-3">
              <Button
                className="w-full sm:w-auto"
                disabled={!isComplete || isAudioLoading}
                onClick={async () => {
                  setAudioError(null);
                  const currentAudio = audioRef.current;
                  if (currentAudio && isPlaying) {
                    currentAudio.pause();
                    currentAudio.currentTime = 0;
                    setIsPlaying(false);
                    return;
                  }

                  let currentUrl = audioUrl;
                  if (!currentUrl) {
                    setIsAudioLoading(true);
                    try {
                      const blob = await getSummaryAudio(sessionId);
                      currentUrl = URL.createObjectURL(blob);
                      setAudioUrl(currentUrl);
                    } catch (err) {
                      setAudioError(err instanceof Error ? err.message : "Не удалось озвучить выводы");
                    } finally {
                      setIsAudioLoading(false);
                    }
                  }

                  if (currentUrl && audioRef.current) {
                    try {
                      audioRef.current.src = currentUrl;
                      await audioRef.current.play();
                      setIsPlaying(true);
                    } catch {
                      setAudioError("Браузер заблокировал воспроизведение. Нажмите Play в плеере ниже.");
                    }
                  }
                }}
              >
                {isAudioLoading ? "Готовлю озвучку..." : isPlaying ? "Остановить озвучку" : "Озвучить выводы"}
              </Button>

              <Button className="w-full sm:w-auto" variant="secondary" onClick={() => router.push("/")}>
                Новая сессия
              </Button>
            </div>

            <audio
              ref={audioRef}
              className="w-full"
              controls
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
            />

            {audioError ? (
              <p className="rounded-lg border-4 border-[#601b1b] bg-[#cfa18f] px-4 py-3 text-sm font-semibold text-[#2d0c0c]">{audioError}</p>
            ) : null}
          </Card>
        </div>
      </section>
    </main>
  );
}
