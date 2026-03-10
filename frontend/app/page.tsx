"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { startSession } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [goal, setGoal] = useState("Заполнить чеклист с клиентом");
  const [topic, setTopic] = useState("Турнир по теннису");
  const [mockMode, setMockMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-8 sm:px-6 md:py-12">
      <section className="crt-shell w-full">
        <div className="grid gap-5 rounded-[28px] border-4 border-[var(--line)] bg-[var(--card)] p-5 sm:p-8 lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
          <div className="space-y-6">
            <div className="rounded-xl border-4 border-[var(--line)] bg-[var(--card-2)] px-4 py-3 sm:px-5">
              <p className="crt-kicker">protocol: v-link</p>
              <h1 className="mt-2 text-3xl font-black uppercase leading-none tracking-[0.04em] sm:text-5xl">
                Голосовой бриф созвона
              </h1>
              <p className="mt-4 text-base font-semibold text-[var(--muted)] sm:text-lg">
                3 раунда по 3 вопроса. Записывайте голосом, подтверждайте транскрипцию и получайте структурированный итог.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ["9", "вопросов"],
                ["Whisper", "локальная транскрипция"],
                ["AI", "итоговый чеклист"]
              ].map(([title, subtitle]) => (
                <div key={title} className="rounded-lg border-4 border-[var(--line)] bg-[var(--card-2)] px-4 py-3">
                  <p className="text-2xl font-black leading-none">{title}</p>
                  <p className="mt-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted)]">{subtitle}</p>
                </div>
              ))}
            </div>
          </div>

          <Card className="space-y-5 bg-[var(--card-2)]">
            <h2 className="text-2xl font-black uppercase tracking-[0.05em] sm:text-3xl">Новая сессия</h2>

            <label className="block space-y-2">
              <span className="crt-kicker">Цель интервью</span>
              <input className="crt-input" value={goal} onChange={(e) => setGoal(e.target.value)} />
            </label>

            <label className="block space-y-2">
              <span className="crt-kicker">Тема</span>
              <input className="crt-input" value={topic} onChange={(e) => setTopic(e.target.value)} />
            </label>

            <label className="flex items-center justify-between gap-4 rounded-lg border-4 border-[var(--line)] bg-[var(--card)] px-4 py-3">
              <div>
                <p className="text-sm font-black uppercase tracking-[0.07em]">Mock Data Mode</p>
                <p className="mt-1 text-xs font-semibold text-[var(--muted)]">
                  Автогенерация транскриптов и быстрый прогон без микрофона
                </p>
              </div>
              <button
                type="button"
                aria-pressed={mockMode}
                onClick={() => setMockMode((prev) => !prev)}
                className={`inline-flex h-11 w-24 appearance-none items-center rounded-full border-4 border-[var(--line)] p-1 transition focus:outline-none focus-visible:ring-4 focus-visible:ring-[#6f8d62] ${
                  mockMode ? "justify-end" : "justify-start"
                } ${
                  mockMode ? "bg-[#86a977]" : "bg-[#a8be90]"
                }`}
              >
                <span className="h-7 w-7 rounded-full border-4 border-[var(--line)] bg-[var(--card)]" />
                <span className="sr-only">{mockMode ? "Mock mode on" : "Mock mode off"}</span>
              </button>
            </label>

            <Button
              className="w-full"
              disabled={loading}
              onClick={async () => {
                try {
                  setLoading(true);
                  setError(null);
                  const started = await startSession(goal, topic, mockMode);
                  router.push(`/session/${started.session_id}`);
                } catch {
                  setError("Не удалось создать сессию. Проверьте backend URL.");
                } finally {
                  setLoading(false);
                }
              }}
            >
              {loading ? "Запускаю..." : "Начать сессию"}
            </Button>

            {error ? (
              <p className="rounded-lg border-4 border-[#601b1b] bg-[#cfa18f] px-4 py-3 text-sm font-semibold text-[#2d0c0c]">{error}</p>
            ) : null}
          </Card>
        </div>
      </section>
    </main>
  );
}
