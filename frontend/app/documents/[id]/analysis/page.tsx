"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut, DocumentStatus } from "@/lib/types";

// What this screen does for every status the backend can report. The Record is
// exhaustive on purpose: adding a status to `DocumentStatus` forces a decision
// here instead of silently landing in the polling branch.
//   poll   — the backend is still working, ask again
//   report — terminal, the preflight report is what the user came for
//   failed — terminal, the document carries a processing error
type StatusMode = "poll" | "report" | "failed";

const STATUS_MODE: Record<DocumentStatus, StatusMode> = {
  uploaded: "poll",
  parsing: "poll",
  parsed: "report",
  parties_confirmed: "report",
  built: "report",
  exported: "report",
  failed: "failed",
};

// A status the frontend does not know is terminal too: keeping the poll alive
// would leave the user staring at the spinner forever.
const modeOf = (status: string): StatusMode | undefined =>
  Object.hasOwn(STATUS_MODE, status) ? STATUS_MODE[status as DocumentStatus] : undefined;

const POLL_INTERVAL_MS = 1000;

type PageError = { title: string; detail: string };

export default function AnalysisPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<PageError | null>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const a = await api.getAnalysis(params.id);
        if (cancelled) return;
        setAnalysis(a);
        const mode = modeOf(a.status);
        if (mode === "poll") {
          timer = setTimeout(tick, POLL_INTERVAL_MS);
          return;
        }
        if (mode === "failed") {
          setError({
            title: "Документ не удалось обработать",
            // An older backend omits error_message entirely.
            detail: a.error_message?.trim() || "Ошибка обработки документа",
          });
          return;
        }
        if (mode === undefined) {
          setError({
            title: "Неизвестный статус документа",
            detail: `Сервер вернул статус «${a.status}». Обновите страницу или загрузите документ заново.`,
          });
        }
      } catch (e) {
        if (!cancelled) {
          setError({
            title: "Не удалось загрузить анализ",
            detail: (e as Error).message,
          });
        }
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [params.id]);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-12">
        <div role="alert" className="space-y-2 rounded border border-red-200 bg-red-50 p-4">
          <h1 className="text-2xl font-semibold tracking-tight text-red-900">{error.title}</h1>
          <p className="text-red-800">{error.detail}</p>
        </div>
        <a
          href="/"
          className="inline-block text-sm text-blue-700 underline underline-offset-2 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          Загрузить другой документ
        </a>
      </main>
    );
  }

  if (!analysis || modeOf(analysis.status) === "poll") {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12" aria-busy="true">
        <p role="status" aria-live="polite" className="text-gray-600">
          Анализируем документ…
        </p>
      </main>
    );
  }

  const m = analysis.preflight_metrics;
  const diagnostics = analysis.preflight_diagnostics ?? [];
  return (
    <main className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <h1 className="text-2xl font-semibold">Предварительный отчёт</h1>
      {m && (
        <div className="bg-white border rounded p-4 space-y-1">
          <div>Правок всего: {m.revisions_total}</div>
          <div>Format-only: {m.format_only_count}</div>
          <div>Параграфов с нумерацией: {m.paragraphs_with_numbering}</div>
          <div>Уверенность нумерации: {(m.numbering_confidence_mean * 100).toFixed(0)}%</div>
        </div>
      )}
      {diagnostics.length > 0 && (
        <div className="bg-white border rounded p-4 space-y-2">
          <div className="font-medium">Диагностика</div>
          <ul className="space-y-1 text-sm">
            {diagnostics.map((d, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  aria-hidden
                  className={
                    d.level === "error"
                      ? "inline-block mt-0.5 text-red-600"
                      : "inline-block mt-0.5 text-yellow-600"
                  }
                  title={d.level}
                >
                  {d.level === "error" ? "⛔" : "⚠"}
                </span>
                <span>
                  <span className="font-mono text-gray-700">{d.component}</span>
                  {": "}
                  <span>{d.message}</span>
                  {d.block_id && (
                    <span className="text-gray-500"> ({d.block_id})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {!m && diagnostics.length === 0 && (
        <p className="text-gray-600">
          Метрики анализа для этого документа недоступны. Перейдите к сторонам договора.
        </p>
      )}
      <button
        onClick={() => router.push(`/documents/${params.id}/parties`)}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Дальше
      </button>
    </main>
  );
}
