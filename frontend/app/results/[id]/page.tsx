"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ChecklistPreview } from "@/components/checklist-preview";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { downloadResults, getResults, getSummaryAudio } from "@/lib/api";
import { ChecklistItem, PortraitCard } from "@/lib/types";

export default function ResultsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);
  const [portrait, setPortrait] = useState<PortraitCard | undefined>(undefined);
  const [isComplete, setIsComplete] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [narrationMode, setNarrationMode] = useState<"audio" | "browser" | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const buildNarrationText = () => {
    const confirmed = checklist.filter((item) => item.status === "confirmed").length;
    const needsClarification = checklist.filter((item) => item.status === "needs_clarification").length;
    const topItems = checklist
      .slice(0, 3)
      .map((item) => item.item)
      .filter(Boolean)
      .join(". ");

    const sections = [
      "Интервью завершено.",
      ...roundSummaries.map((summary, idx) => `Раунд ${idx + 1}. ${summary}`),
      `Подтвержденных пунктов: ${confirmed}. Требуют уточнения: ${needsClarification}.`,
      topItems ? `Ключевые пункты: ${topItems}.` : ""
    ].filter(Boolean);
    return sections.join(" ");
  };

  const stopPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsPlaying(false);
  };

  const playBrowserNarration = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setAudioError("В этом браузере нет встроенной озвучки. Откройте страницу в Chrome.");
      return;
    }

    const utterance = new SpeechSynthesisUtterance(buildNarrationText());
    utterance.lang = "ru-RU";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    const voices = window.speechSynthesis.getVoices();
    const ruVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("ru"));
    if (ruVoice) {
      utterance.voice = ruVoice;
    }

    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => {
      setIsPlaying(false);
      setAudioError("Не удалось воспроизвести озвучку через браузер.");
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setNarrationMode("browser");
    setIsPlaying(true);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getResults(sessionId);
        if (!cancelled) {
          setChecklist(res.checklist);
          setRoundSummaries(res.round_summaries);
          setPortrait(res.portrait);
          setIsComplete(res.is_complete);
        }
      } catch {
        if (!cancelled) {
          setChecklist([]);
          setPortrait(undefined);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    return () => {
      stopPlayback();
      utteranceRef.current = null;
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]); // eslint-disable-line react-hooks/exhaustive-deps

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
            portrait={portrait}
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
                  if (isPlaying) {
                    stopPlayback();
                    return;
                  }

                  let currentUrl = audioUrl;
                  if (!currentUrl) {
                    setIsAudioLoading(true);
                    try {
                      const { blob, source } = await getSummaryAudio(sessionId);
                      if (source !== "huggingface") {
                        setAudioUrl(null);
                        setNarrationMode("browser");
                        playBrowserNarration();
                        return;
                      }
                      currentUrl = URL.createObjectURL(blob);
                      setAudioUrl(currentUrl);
                      setNarrationMode("audio");
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
                      setNarrationMode("audio");
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

            {narrationMode === "browser" ? (
              <p className="text-sm font-semibold text-[var(--muted)]">
                Используется встроенная озвучка браузера (fallback), так как серверный TTS недоступен или не подтвердил источник.
              </p>
            ) : null}

            {audioError ? (
              <p className="rounded-lg border-4 border-[#601b1b] bg-[#cfa18f] px-4 py-3 text-sm font-semibold text-[#2d0c0c]">{audioError}</p>
            ) : null}
          </Card>
        </div>
      </section>
    </main>
  );
}
