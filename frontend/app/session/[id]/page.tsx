"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { JobProgressPanel } from "@/components/job-progress-panel";
import { MockLogEntry, MockLogPanel } from "@/components/mock-log-panel";
import { QuestionCard } from "@/components/question-card";
import { RoundIndicator } from "@/components/round-indicator";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchMockAnswers, getSession, getSubmitJobStatus, submitRound, submitRoundMock, transcribeAudio } from "@/lib/api";
import { Question, SessionLogEntry, SubmitJobStatusResponse } from "@/lib/types";

interface AnswerState {
  blob?: Blob;
  transcript?: string;
  confirmed: boolean;
}

const timestamp = () =>
  new Date().toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });

const toLogId = (at: string, source: string, message: string) => `${at}|${source}|${message}`;

const buildLocalMockTranscript = (questionText: string, index: number, roundNumber: number): string =>
  `Раунд ${roundNumber}, автоответ ${index + 1}: по вопросу "${questionText}" приоритет — зафиксировать измеримые критерии, риски и следующий шаг запуска.`;

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [round, setRound] = useState(1);
  const [mockMode, setMockMode] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({});
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSubmittingRound, setIsSubmittingRound] = useState(false);
  const [isMockHydrating, setIsMockHydrating] = useState(false);
  const [submitJob, setSubmitJob] = useState<SubmitJobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<MockLogEntry[]>([]);
  const [mockPreparedRound, setMockPreparedRound] = useState<number | null>(null);

  const pollTimerRef = useRef<number | null>(null);
  const lastJobLogRef = useRef<string>("");

  const addLog = (source: MockLogEntry["source"], message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        at: timestamp(),
        source,
        message
      }
    ]);
  };

  const mergeServerLogs = (serverLogs: SessionLogEntry[]) => {
    setLogs((prev) => {
      const seen = new Set(prev.map((item) => item.id));
      const next = [...prev];
      serverLogs.forEach((entry) => {
        const id = toLogId(entry.at, entry.source, entry.message);
        if (seen.has(id)) return;
        seen.add(id);
        next.push({
          id,
          at: entry.at,
          source: entry.source,
          message: entry.message
        });
      });
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSession(sessionId);
        if (!cancelled) {
          setRound(data.round);
          setMockMode(data.mock_mode);
          setQuestions(data.questions);
          mergeServerLogs(data.logs || []);
          if (data.mock_mode) {
            addLog("ui", "Сессия загружена в mock режиме");
          } else {
            addLog("ui", "Сессия загружена в обычном режиме");
          }
        }
      } catch {
        if (!cancelled) setError("Не удалось загрузить сессию");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const stopPolling = () => {
    if (pollTimerRef.current !== null) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const pollSubmitJob = async (jobId: string) => {
    try {
      const status = await getSubmitJobStatus(jobId);
      setSubmitJob(status);

      const marker = `${status.status}|${status.current_step || ""}|${status.progress_pct}`;
      if (marker !== lastJobLogRef.current) {
        lastJobLogRef.current = marker;
        const stepText = status.current_step ? `, шаг: ${status.current_step}` : "";
        addLog("job", `Статус ${status.status}${stepText}, прогресс ${status.progress_pct}%`);
      }

      if (status.status === "failed") {
        setError(status.error || "Ошибка обработки раунда");
        setIsSubmittingRound(false);
        stopPolling();
        return;
      }

      if (status.status === "completed") {
        const result = status.result;
        if (!result) {
          setError("Результат обработки не получен");
          setIsSubmittingRound(false);
          stopPolling();
          return;
        }

        if (result.round_summary) {
          setRoundSummaries((prev) => [...prev, result.round_summary]);
          addLog("job", `Раунд завершен: ${result.round_summary}`);
        }

        if (result.is_complete) {
          addLog("job", "Интервью завершено, переход на страницу результатов");
          setIsSubmittingRound(false);
          stopPolling();
          router.push(`/results/${sessionId}`);
          return;
        }

        setRound(result.round);
        setQuestions(result.questions);
        setAnswers({});
        setMockPreparedRound(null);
        setSubmitJob(null);
        setIsSubmittingRound(false);
        try {
          const snapshot = await getSession(sessionId);
          mergeServerLogs(snapshot.logs || []);
        } catch {
          // ignore snapshot fetch errors here
        }
        stopPolling();
        addLog("job", `Переход к раунду ${result.round}`);
        return;
      }

      stopPolling();
      pollTimerRef.current = window.setTimeout(() => {
        void pollSubmitJob(jobId);
      }, 900);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось получить статус обработки");
      setIsSubmittingRound(false);
      stopPolling();
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  useEffect(() => {
    if (!mockMode) return;
    if (questions.length !== 3) return;
    if (isSubmittingRound || isMockHydrating) return;
    if (mockPreparedRound === round) return;

    let cancelled = false;
    (async () => {
      setIsMockHydrating(true);
      setError(null);
      addLog("mock", `Запрос mock-ответов для раунда ${round}`);
      try {
        const generated = await fetchMockAnswers(sessionId);
        if (cancelled) return;
        if (!generated.answers || generated.answers.length < 3) {
          throw new Error("Сервис mock-ответов вернул неполные данные");
        }
        const mapped: Record<string, AnswerState> = {};
        generated.answers.forEach((item) => {
          mapped[item.question_id] = {
            transcript: item.transcript,
            confirmed: true
          };
        });
        setAnswers(mapped);
        setMockPreparedRound(round);
        generated.logs.forEach((line) => addLog("mock", line));
      } catch (err) {
        if (!cancelled) {
          const mapped: Record<string, AnswerState> = {};
          questions.forEach((question, idx) => {
            mapped[question.id] = {
              transcript: buildLocalMockTranscript(question.text, idx, round),
              confirmed: true
            };
          });
          setAnswers(mapped);
          setMockPreparedRound(round);
          addLog("mock", "Серверные mock-ответы недоступны, применен локальный fallback");
          setError(null);
        }
      } finally {
        if (!cancelled) {
          setIsMockHydrating(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [mockMode, questions, round, isSubmittingRound, mockPreparedRound, sessionId]);

  const allConfirmed = useMemo(
    () => questions.length === 3 && questions.every((q) => Boolean(answers[q.id]?.transcript) && answers[q.id]?.confirmed),
    [answers, questions]
  );

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-5 px-4 py-8 sm:px-6 md:py-10">
      <section className="crt-shell w-full">
        <div className="space-y-5 rounded-[28px] border-4 border-[var(--line)] bg-[var(--card)] p-4 sm:p-6">
          <RoundIndicator currentRound={round} totalRounds={3} roundSummaries={roundSummaries} />

          {mockMode ? (
            <Card className="space-y-2 bg-[var(--card-2)]">
              <p className="crt-kicker">Mock Data Mode</p>
              <p className="text-sm font-semibold leading-relaxed sm:text-base">
                Микрофон не нужен: ответы генерируются автоматически и сразу подставляются как транскрипты.
              </p>
              {isMockHydrating ? (
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">Генерируем mock-ответы...</p>
              ) : null}
            </Card>
          ) : null}

          <section className="grid gap-4">
            {questions.map((question, idx) => (
              <QuestionCard
                key={question.id}
                question={question}
                index={idx}
                transcript={answers[question.id]?.transcript}
                isAnswered={Boolean(answers[question.id]?.transcript)}
                isConfirmed={Boolean(answers[question.id]?.confirmed)}
                hideRecorder={mockMode}
                onAnswer={async (blob) => {
                  setIsTranscribing(true);
                  setError(null);
                  try {
                    const transcript = await transcribeAudio(blob);
                    setAnswers((prev) => ({
                      ...prev,
                      [question.id]: {
                        blob,
                        transcript,
                        confirmed: false
                      }
                    }));
                    addLog("ui", `Получена транскрипция для вопроса ${idx + 1}`);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Не удалось транскрибировать аудио");
                  } finally {
                    setIsTranscribing(false);
                  }
                }}
                onConfirm={() => {
                  setAnswers((prev) => ({
                    ...prev,
                    [question.id]: {
                      ...prev[question.id],
                      confirmed: !prev[question.id]?.confirmed
                    }
                  }));
                }}
              />
            ))}
          </section>

          {submitJob ? (
            <JobProgressPanel
              etaSecondsLeft={submitJob.eta_seconds_left}
              progressPct={submitJob.progress_pct}
              steps={submitJob.steps}
              currentStep={submitJob.current_step}
            />
          ) : null}

          {mockMode ? <MockLogPanel entries={logs} title="Логи интервью" /> : null}

          <Card className="space-y-4 bg-[var(--card-2)]">
            <p className="text-sm font-semibold leading-relaxed sm:text-base">
              Когда все 3 ответа подтверждены, отправьте раунд. Пока идет обработка, можно оставаться на странице: прогресс, ETA и этапы обновляются автоматически.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button
                className="w-full sm:w-auto"
                disabled={!allConfirmed || isTranscribing || isSubmittingRound || isMockHydrating}
                onClick={async () => {
                  setIsSubmittingRound(true);
                  setSubmitJob(null);
                  setError(null);
                  addLog("ui", `Отправка ответов раунда ${round}`);
                  try {
                    const questionIds = questions.map((q) => q.id);
                    if (!mockMode) {
                      const blobCount = questionIds
                        .map((id) => answers[id]?.blob)
                        .filter((item): item is Blob => item instanceof Blob).length;
                      if (blobCount !== 3) {
                        throw new Error("Для обычного режима нужны 3 аудио-ответа.");
                      }
                    }
                    const accepted = mockMode
                      ? await submitRoundMock(
                          sessionId,
                          questionIds,
                          questionIds.map((id) => (answers[id]?.transcript || "").trim())
                        )
                      : await submitRound(
                          sessionId,
                          questionIds,
                          questionIds.map((id) => answers[id]?.blob).filter((item): item is Blob => item instanceof Blob)
                        );

                    const initialStatus: SubmitJobStatusResponse = {
                      job_id: accepted.job_id,
                      session_id: sessionId,
                      status: accepted.status,
                      current_step: accepted.current_step,
                      steps: [],
                      eta_seconds_left: accepted.eta_seconds_left,
                      progress_pct: accepted.progress_pct
                    };
                    setSubmitJob(initialStatus);
                    addLog("job", `Запущена фоновая обработка: job ${accepted.job_id.slice(0, 8)}`);
                    await pollSubmitJob(accepted.job_id);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Не удалось отправить ответы");
                    setIsSubmittingRound(false);
                  }
                }}
              >
                {isSubmittingRound ? "Обрабатываю..." : "Отправить ответы"}
              </Button>

              <Button className="w-full sm:w-auto" variant="secondary" onClick={() => router.push("/")}>
                Начать заново
              </Button>
            </div>

            {error ? (
              <p className="rounded-lg border-4 border-[#601b1b] bg-[#cfa18f] px-4 py-3 text-sm font-semibold text-[#2d0c0c]">{error}</p>
            ) : null}
          </Card>
        </div>
      </section>
    </main>
  );
}
