import {
  SessionResultsResponse,
  SessionStartResponse,
  SessionSubmitResponse
} from "@/lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://driopi-ai-checklist-agent-voice.hf.space";

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function extractErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const payload = (await res.json()) as { detail?: string };
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {
    // Ignore JSON parse errors and use fallback message.
  }
  return fallback;
}

export async function startSession(goal: string, topic: string): Promise<SessionStartResponse> {
  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, topic })
    }, 30000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Превышено время ожидания запуска сессии.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to start session"));
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionStartResponse> {
  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/${sessionId}`, { cache: "no-store" }, 20000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Превышено время ожидания загрузки сессии.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to get session"));
  return res.json();
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("audio_file", blob, "recording.webm");

  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/transcribe`, {
      method: "POST",
      body: formData
    }, 120000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Транскрипция заняла слишком много времени.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to transcribe audio"));
  const payload = await res.json();
  return payload.transcript as string;
}

export async function submitRound(
  sessionId: string,
  questionIds: string[],
  blobs: Blob[]
): Promise<SessionSubmitResponse> {
  const formData = new FormData();
  formData.append("question_ids", questionIds.join(","));

  blobs.forEach((blob, idx) => {
    formData.append("audio_files", blob, `answer-${idx + 1}.webm`);
  });

  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/${sessionId}/submit`, {
      method: "POST",
      body: formData
    }, 180000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Обработка ответов заняла слишком много времени.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to submit answers"));
  return res.json();
}

export async function getResults(sessionId: string): Promise<SessionResultsResponse> {
  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/${sessionId}/results`, { cache: "no-store" }, 30000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Превышено время ожидания загрузки результатов.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to fetch results"));
  return res.json();
}

export async function getSummaryAudio(sessionId: string): Promise<Blob> {
  let res: Response;
  try {
    res = await fetchWithTimeout(`${API_URL}/api/session/${sessionId}/summary-audio`, { cache: "no-store" }, 60000);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Озвучка заняла слишком много времени.");
    }
    throw err;
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, "Failed to generate summary audio"));
  return res.blob();
}

export function downloadResults(sessionId: string): string {
  return `${API_URL}/api/session/${sessionId}/download`;
}
