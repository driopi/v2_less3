"use client";

import { AudioRecorder } from "@/components/audio-recorder";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Question } from "@/lib/types";

interface QuestionCardProps {
  question: Question;
  index: number;
  transcript?: string;
  isAnswered: boolean;
  isConfirmed: boolean;
  hideRecorder?: boolean;
  onAnswer: (audioBlob: Blob) => Promise<void>;
  onConfirm: () => void;
}

export function QuestionCard({
  question,
  index,
  transcript,
  isAnswered,
  isConfirmed,
  hideRecorder = false,
  onAnswer,
  onConfirm
}: QuestionCardProps) {
  return (
    <Card className="space-y-5 bg-[var(--card-2)]">
      <div className="space-y-3">
        <p className="inline-flex rounded-md border-4 border-[var(--line)] bg-[var(--card)] px-3 py-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">
          Вопрос {index + 1}
        </p>
        <h3 className="text-2xl font-black leading-tight sm:text-3xl">{question.text}</h3>
      </div>

      {hideRecorder ? (
        <div className="rounded-lg border-4 border-[var(--line)] bg-[var(--card)] px-4 py-3">
          <p className="text-sm font-bold uppercase tracking-[0.08em] text-[var(--muted)]">Mock режим: запись отключена</p>
          <p className="mt-2 text-sm font-semibold">Ответ будет сгенерирован автоматически и подставлен как транскрипт.</p>
        </div>
      ) : (
        <AudioRecorder questionId={question.id} onRecordingComplete={onAnswer} />
      )}

      {isAnswered ? (
        <div className="space-y-3 rounded-lg border-4 border-[var(--line)] bg-[var(--card)] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">Превью транскрипции</p>
          <p className="whitespace-pre-wrap text-sm font-semibold leading-relaxed sm:text-base">{transcript || "..."}</p>
          <Button className="w-full sm:w-auto" variant={isConfirmed ? "secondary" : "primary"} onClick={onConfirm}>
            {isConfirmed ? "Подтверждено" : "Подтвердить ответ"}
          </Button>
        </div>
      ) : null}
    </Card>
  );
}
