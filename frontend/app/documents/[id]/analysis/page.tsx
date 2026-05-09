"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut } from "@/lib/types";

export default function AnalysisPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const a = await api.getAnalysis(params.id);
        if (cancelled) return;
        setAnalysis(a);
        if (a.status === "parsed" || a.status === "parties_confirmed") return;
        if (a.status === "failed") {
          setError("Ошибка обработки документа");
          return;
        }
        setTimeout(tick, 1000);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!analysis) return <main className="p-8">Анализируем документ…</main>;
  if (analysis.status !== "parsed" && analysis.status !== "parties_confirmed") {
    return <main className="p-8">Анализируем документ…</main>;
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
      <button
        onClick={() => router.push(`/documents/${params.id}/parties`)}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Дальше
      </button>
    </main>
  );
}
