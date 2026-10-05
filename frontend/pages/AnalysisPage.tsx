import Link from "@/lib/navigation";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "@/lib/navigation";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { Icon } from "@/components/icons/Icon";
import { Button, buttonClassName } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState } from "@/components/ui/States";
import { api } from "@/lib/api";
import { rememberDocument } from "@/lib/recent-documents";
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

// `retry`: whether asking the backend again can change the outcome. A document
// that failed processing stays failed, so it only offers "upload another".
type PageError = { title: string; detail: string; retry: boolean };

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<PageError | null>(null);
  // Bumped by "Повторить": re-runs the effect below without any automatic retry.
  const [attempt, setAttempt] = useState(0);
  // The recent-documents entry is written once per mount, and only when this
  // screen stays the final one (the redirect to parties/protocol writes its own).
  const remembered = useRef(false);
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
        if (mode !== "report" && !remembered.current) {
          remembered.current = true;
          rememberDocument({ id: params.id, title: a.contract_name, stage: "analysis" });
        }
        if (mode === "poll") {
          timer = setTimeout(tick, POLL_INTERVAL_MS);
          return;
        }
        if (mode === "failed") {
          setError({
            title: "Документ не удалось обработать",
            // An older backend omits error_message entirely.
            detail: a.error_message?.trim() || "Ошибка обработки документа",
            retry: false,
          });
          return;
        }
        if (mode === "report") {
          push(`/documents/${params.id}/${a.status === "built" || a.status === "exported" ? "protocol" : "parties"}`);
          return;
        }
        if (mode === undefined) {
          setError({
            title: "Не удалось определить этап обработки",
            detail: "Повторите попытку. Если ошибка повторится, откройте исходный файл заново.",
            retry: true,
          });
        }
      } catch (e) {
        if (!cancelled) {
          setError({
            title: "Не удалось получить результаты обработки",
            detail: (e as Error).message,
            retry: true,
          });
        }
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [params.id, push, attempt]);

  const retry = () => {
    setError(null);
    setAnalysis(null);
    setAttempt((n) => n + 1);
  };

  if (error) return (
    <WorkspaceShell documentId={params.id}>
      <ErrorState
        titleLevel={1}
        title={error.title}
        text={error.detail}
        onRetry={error.retry ? retry : undefined}
        actions={<Link href="/" className={buttonClassName({ variant: "ghost", size: "sm" })}>Открыть другой документ</Link>}
        className="max-w-2xl"
      />
    </WorkspaceShell>
  );
  const isPending = !analysis || modeOf(analysis.status) === "poll";
  return (
    <WorkspaceShell documentId={params.id}>
      <div aria-busy={isPending}>
        <PageHeader
          rubric={<span className="inline-flex items-center gap-2">
            {isPending && <Icon name="loader-circle" size={14} className="text-accent motion-safe:animate-spin" />}
            Анализ документа
          </span>}
          title={<span role="status" aria-live="polite">{isPending ? "Анализируем документ…" : "Документ готов к проверке"}</span>}
          description={isPending ? "Находим изменения, сопоставляем пункты и определяем стороны договора." : "Переходим в рабочее пространство договора."}
        />
        {!isPending && (
          <Button variant="primary" className="mt-8" onClick={() => push(`/documents/${params.id}/${analysis?.status === "built" || analysis?.status === "exported" ? "protocol" : "parties"}`)}>
            Продолжить <Icon name="arrow-right" />
          </Button>
        )}
      </div>
    </WorkspaceShell>
  );
}
