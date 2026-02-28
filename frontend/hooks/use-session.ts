"use client";

import { useMemo, useState } from "react";

import { Question } from "@/lib/types";

interface AnswerState {
  blob?: Blob;
  transcript?: string;
  confirmed: boolean;
}

export function useSessionState(initialQuestions: Question[]) {
  const [questions, setQuestions] = useState<Question[]>(initialQuestions);
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({});
  const [roundSummaries, setRoundSummaries] = useState<string[]>([]);

  const allConfirmed = useMemo(
    () =>
      questions.length === 3 &&
      questions.every((q) => Boolean(answers[q.id]?.blob) && Boolean(answers[q.id]?.confirmed)),
    [answers, questions]
  );

  return {
    questions,
    setQuestions,
    answers,
    setAnswers,
    roundSummaries,
    setRoundSummaries,
    allConfirmed
  };
}
