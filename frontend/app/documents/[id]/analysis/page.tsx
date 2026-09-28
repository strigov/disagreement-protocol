"use client";
import Link from "next/link";
import { LoaderCircle, ArrowRight } from "lucide-react";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
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

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<PageError | null>(null);
  const { push } = useRouter();

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
        if (mode === "report") {
          push(`/documents/${params.id}/${a.status === "built" || a.status === "exported" ? "protocol" : "parties"}`);
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
  }, [params.id, push]);

  if (error) return (
    <WorkspaceShell documentId={params.id}>
      <div role="alert" className="notice notice-error">
        <h1 className="text-xl font-semibold mb-3">{error.title}</h1>
        <p>{error.detail}</p>
      </div>
      <Link href="/" className="btn btn-secondary mt-6">Загрузить другой документ</Link>
    </WorkspaceShell>
  );
  const isPending = !analysis || modeOf(analysis.status) === "poll";
  return (
    <WorkspaceShell documentId={params.id}>
      <div className="loading-state" aria-busy={isPending}>
        {isPending && <LoaderCircle className="spinner mx-auto mb-6 text-blue-600" size={30} />}
        <h1 className="page-title" role="status" aria-live="polite">{isPending ? "Анализируем документ…" : "Документ готов к проверке"}</h1>
        <p className="page-description mx-auto">{isPending ? "Находим изменения, сопоставляем пункты и определяем стороны договора." : "Переходим в рабочее пространство договора."}</p>
        {!isPending && <button className="btn btn-primary mt-6" onClick={() => push(`/documents/${params.id}/${analysis?.status === "built" || analysis?.status === "exported" ? "protocol" : "parties"}`)}>Продолжить <ArrowRight size={14} /></button>}
      </div>
    </WorkspaceShell>
  );
}
