"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { QuestionCard } from "@/components/question-card";
import { RoundIndicator } from "@/components/round-indicator";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getSession, submitRound, transcribeAudio } from "@/lib/api";
import { Question } from "@/lib/types";

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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
                  setIsLoading(true);
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
                    setIsLoading(false);
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

          <Card className="space-y-4 bg-[var(--card-2)]">
            <p className="text-sm font-semibold leading-relaxed sm:text-base">
              Когда все 3 ответа подтверждены, отправьте раунд. После 3-го раунда появится итоговое резюме.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button
                className="w-full sm:w-auto"
                disabled={!allConfirmed || isLoading}
                onClick={async () => {
                  setIsLoading(true);
                  setError(null);
                  try {
                    const questionIds = questions.map((q) => q.id);
                    const blobs = questionIds.map((id) => answers[id]?.blob).filter((item): item is Blob => item instanceof Blob);

                    if (blobs.length !== 3) {
                      throw new Error("three answers required");
                    }

                    const result = await submitRound(sessionId, questionIds, blobs);

                    if (result.round_summary) {
                      setRoundSummaries((prev) => [...prev, result.round_summary]);
                    }

                    if (result.is_complete) {
                      router.push(`/results/${sessionId}`);
                    } else {
                      setRound(result.round);
                      setQuestions(result.questions);
                      setAnswers({});
                    }
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Не удалось отправить ответы");
                  } finally {
                    setIsLoading(false);
                  }
                }}
              >
                {isLoading ? "Обрабатываю..." : "Отправить ответы"}
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
