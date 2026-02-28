"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";

interface AudioRecorderProps {
  questionId: string;
  onRecordingComplete: (audioBlob: Blob) => Promise<void> | void;
  maxDuration?: number;
}

export function AudioRecorder({ onRecordingComplete, maxDuration = 120 }: AudioRecorderProps) {
  const [isSaving, setIsSaving] = useState(false);
  const { isRecording, error, start, stop } = useAudioRecorder(maxDuration);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        {!isRecording ? (
          <Button
            className="w-full sm:w-auto"
            onClick={async () => {
              await start();
            }}
          >
            Начать запись
          </Button>
        ) : (
          <Button
            className="w-full sm:w-auto"
            variant="secondary"
            onClick={async () => {
              const blob = await stop();
              if (!blob) return;
              setIsSaving(true);
              try {
                await onRecordingComplete(blob);
              } finally {
                setIsSaving(false);
              }
            }}
            disabled={isSaving}
          >
            {isSaving ? "Сохраняю..." : "Остановить"}
          </Button>
        )}
      </div>

      <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">Максимум 120 секунд</p>

      {error ? (
        <p className="rounded-lg border-4 border-[#601b1b] bg-[#cfa18f] px-4 py-3 text-sm font-semibold text-[#2d0c0c]">{error}</p>
      ) : null}
    </div>
  );
}
