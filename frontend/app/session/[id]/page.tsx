"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { JobProgressPanel } from "@/components/job-progress-panel";
import { QuestionCard } from "@/components/question-card";
import { RoundIndicator } from "@/components/round-indicator";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getSession, getSubmitJobStatus, submitRound, transcribeAudio } from "@/lib/api";
import { Question, SubmitJobStatusResponse } from "@/lib/types";

interface AnswerState {
  blob?: Blob;
  transcript?: string;
  confirmed: boolean;
}

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [round, setRound] = useState(1);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({});
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSubmittingRound, setIsSubmittingRound] = useState(false);
  const [submitJob, setSubmitJob] = useState<SubmitJobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSession(sessionId);
        if (!cancelled) {
          setRound(data.round);
          setQuestions(data.questions);
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
        }

        if (result.is_complete) {
          setIsSubmittingRound(false);
          stopPolling();
          router.push(`/results/${sessionId}`);
          return;
        }

        setRound(result.round);
        setQuestions(result.questions);
        setAnswers({});
        setSubmitJob(null);
        setIsSubmittingRound(false);
        stopPolling();
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

  const allConfirmed = useMemo(
    () => questions.length === 3 && questions.every((q) => Boolean(answers[q.id]?.blob) && answers[q.id]?.confirmed),
    [answers, questions]
  );

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-5 px-4 py-8 sm:px-6 md:py-10">
      <section className="crt-shell w-full">
        <div className="space-y-5 rounded-[28px] border-4 border-[var(--line)] bg-[var(--card)] p-4 sm:p-6">
          <RoundIndicator currentRound={round} totalRounds={3} roundSummaries={roundSummaries} />

          <section className="grid gap-4">
            {questions.map((question, idx) => (
              <QuestionCard
                key={question.id}
                question={question}
                index={idx}
                transcript={answers[question.id]?.transcript}
                isAnswered={Boolean(answers[question.id]?.blob)}
                isConfirmed={Boolean(answers[question.id]?.confirmed)}
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

          <Card className="space-y-4 bg-[var(--card-2)]">
            <p className="text-sm font-semibold leading-relaxed sm:text-base">
              Когда все 3 ответа подтверждены, отправьте раунд. Пока идет обработка, можно оставаться на странице: прогресс, ETA и этапы обновляются автоматически.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button
                className="w-full sm:w-auto"
                disabled={!allConfirmed || isTranscribing || isSubmittingRound}
                onClick={async () => {
                  setIsSubmittingRound(true);
                  setSubmitJob(null);
                  setError(null);
                  try {
                    const questionIds = questions.map((q) => q.id);
                    const blobs = questionIds.map((id) => answers[id]?.blob).filter((item): item is Blob => item instanceof Blob);

                    if (blobs.length !== 3) {
                      throw new Error("three answers required");
                    }

                    const accepted = await submitRound(sessionId, questionIds, blobs);
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
