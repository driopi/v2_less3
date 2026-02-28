"use client";

import { useCallback, useRef, useState } from "react";

export function useAudioRecorder(maxDuration = 120) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stop = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];

        if (timerRef.current) clearTimeout(timerRef.current);
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        mediaRecorderRef.current = null;
        setIsRecording(false);
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  const start = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.start();
      setIsRecording(true);

      timerRef.current = setTimeout(() => {
        void stop();
      }, maxDuration * 1000);
    } catch {
      setError("Не удалось получить доступ к микрофону.");
    }
  }, [maxDuration, stop]);

  return { isRecording, error, start, stop };
}
