import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "@/lib/navigation";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { rememberDocument } from "@/lib/recent-documents";
import type { AnalysisOut, Protocol, ProtocolFormPatch, ProtocolRow, ValidationReport } from "@/lib/types";
import { Icon, type IconName } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { ExportDialog } from "@/components/ExportDialog";
import ProtocolTable, { type ProtocolTableHandle, type SaveState } from "@/components/ProtocolTable";
import { ProtocolFormEditor, type ProtocolFormHandle } from "@/components/protocol/ProtocolFormEditor";

const SAVE_STATUS: Record<SaveState, { label: string; icon: IconName; className: string }> = {
  saved: { label: "Все изменения сохранены", icon: "check", className: "text-ok" },
  dirty: { label: "Есть несохранённые изменения", icon: "triangle-alert", className: "text-warn" },
  saving: { label: "Сохраняем изменения…", icon: "loader-circle", className: "text-ink-2 motion-safe:animate-spin" },
  error: { label: "Не удалось сохранить изменения", icon: "circle-alert", className: "text-danger" },
};

export default function ProtocolPage() {
  const params = useParams<{ id: string }>();
  const tableRef = useRef<ProtocolTableHandle>(null);
  const formRef = useRef<ProtocolFormHandle>(null);
  const focusTab = useRef<string | null>(null);
  const operation = useRef(false);
  const analysisVersion = useRef(0);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [formSaveState, setFormSaveState] = useState<SaveState>("saved");
  const [tab, setTab] = useState<"clauses" | "form">("clauses");
  const [exportOpen, setExportOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!busy && focusTab.current) {
      document.getElementById(`tab-${focusTab.current}`)?.focus();
      focusTab.current = null;
    }
  }, [busy, tab]);

  useEffect(() => {
    // Decide between loading existing rows vs first-time build.
    // POST /documents/{id}/protocol wipes-and-rebuilds, which would discard
    // manual edits — so we only call it the first time (no protocol yet).
    //
    // Analysis is fetched AFTER the protocol is built/loaded (not in
    // parallel) so that the validation banner reflects the
    // `validation_report` written by the just-completed build. If we ran
    // them in parallel, the first-build path would render with a stale
    // analysis snapshot and the banner would only appear on a manual
    // refresh.
    let cancelled = false;
    (async () => {
      try {
        const existing = await api.listProtocolsForDocument(params.id);
        if (cancelled) return;
        const proto =
          existing.length > 0
            ? await api.getProtocolRows(existing[0].id)
            : await api.buildProtocol(params.id);
        if (cancelled) return;
        setProtocol(proto);
        // Fetch analysis AFTER the protocol settles so the validation
        // report (written during build) is visible on first paint.
        try {
          const version = ++analysisVersion.current;
          const a = await api.getAnalysis(params.id);
          if (!cancelled && version === analysisVersion.current) setAnalysis(a);
          if (!cancelled) rememberDocument({ id: params.id, title: a.contract_name, stage: "protocol" });
        } catch {
          if (!cancelled) setOperationError("Не удалось проверить полноту протокола. Повторите проверку.");
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id, attempt]);

  const refreshAnalysis = async () => {
    const version = ++analysisVersion.current;
    try {
      const a = await api.getAnalysis(params.id);
      if (version === analysisVersion.current) setAnalysis(a);
    } catch {
      if (version === analysisVersion.current) {
        setAnalysis((current) => current && ({ ...current, validation_report: null }));
        setOperationError("Строки сохранены, но не удалось проверить полноту протокола. Повторите проверку.");
      }
    }
  };

  const patch = async (rowId: string, body: Partial<ProtocolRow>) => {
    if (!protocol) return;
    const updated = await api.patchRow(protocol.id, rowId, body);
    setProtocol((cur) => {
      if (!cur) return cur;
      return {
        ...cur,
        rows: cur.rows.map((r) => (r.id === rowId ? { ...r, ...body, flags: updated.flags, user_edited: updated.user_edited } : r)),
      };
    });
    await refreshAnalysis();
  };

  // Structural operations and navigation wait for every draft and pending PATCH.
  // The synchronous gate also covers double clicks before React disables buttons.
  const perform = async (action: () => Promise<void>, refresh = true) => {
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setOperationError(null);
    try {
      if (!await tableRef.current?.saveAll() || (formRef.current && !await formRef.current.saveAll())) {
        setOperationError("Изменения не сохранены. Исправьте ошибку или отмените правку перед продолжением.");
        return;
      }
      await action();
      if (refresh) await refreshAnalysis();
    } catch (error) {
      setOperationError((error as Error).message);
    } finally {
      operation.current = false;
      setBusy(false);
    }
  };

  const merge = (rowId: string, direction: "previous" | "next") => perform(async () => {
    if (!protocol) return;
    const updated = await api.patchRow(protocol.id, rowId, { merge_with: direction });
    setProtocol((current) => current && ({
      ...current,
      rows: current.rows.filter((row) => row.id !== rowId)
        .map((row, index) => ({ ...(row.id === updated.id ? updated : row), sort_order: index })),
    }));
    tableRef.current?.revealRow(updated.id);
  });

  const remove = (rowId: string) => perform(async () => {
    if (!protocol) return;
    await api.deleteRow(protocol.id, rowId);
    setProtocol((current) => current && ({
      ...current,
      rows: current.rows.filter((row) => row.id !== rowId).map((row, index) => ({ ...row, sort_order: index })),
    }));
  });

  const addRow = () => perform(async () => {
    if (!protocol) return;
    const created = await api.addRow(protocol.id);
    setProtocol((current) => current && ({ ...current, rows: [...current.rows, created] }));
    tableRef.current?.revealRow(created.id);
  });

  const swap = () => perform(async () => {
    if (!protocol) return;
    const updated = await api.swapParties(protocol.id);
    setProtocol(updated);
    setAnalysis(null);
  });

  const saveForm = async (patch: ProtocolFormPatch) => {
    if (!protocol) throw new Error("Протокол не загружен");
    const form = await api.patchProtocolForm(protocol.id, patch);
    setProtocol((current) => current && ({ ...current, form }));
    return form;
  };

  const retry = () => {
    setError(null);
    setOperationError(null);
    setAttempt((value) => value + 1);
  };

  if (error) return (
    <WorkspaceShell step={3} documentId={params.id}>
      <ErrorState titleLevel={1} title="Не удалось открыть протокол" text={error} onRetry={retry} />
    </WorkspaceShell>
  );
  if (!protocol) return (
    <WorkspaceShell wide step={3} documentId={params.id}>
      <div aria-busy="true" className="space-y-6">
        <div className="space-y-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-10 w-80 max-w-full" />
          <Skeleton className="h-3 w-64 max-w-full" />
        </div>
        <p className="flex items-center gap-2 text-sm text-ink-2"><Icon name="loader-circle" className="motion-safe:animate-spin" />Строим таблицу…</p>
        <div className="grid gap-4 rounded-lg border border-line-c bg-bg-elev p-4 shadow-sm md:grid-cols-workbench-narrow lg:grid-cols-workbench">
          <div className="space-y-2">{[0, 1, 2, 3].map((index) => <Skeleton key={index} className="h-14 w-full" />)}</div>
          <div className="space-y-3"><Skeleton className="h-8 w-40" /><Skeleton className="h-32 w-full" /><Skeleton className="h-20 w-full" /></div>
        </div>
      </div>
    </WorkspaceShell>
  );

  const report: ValidationReport | null = analysis?.validation_report ?? null;
  const uncovered = report ? Math.max(0, report.textual_revisions_total - report.covered_revisions) : 0;
  const diagnostics = analysis?.preflight_diagnostics ?? [];
  const warningCount = (report?.warnings.length ?? 0) + diagnostics.length;
  const hasIssues = uncovered > 0 || warningCount > 0;
  const draftingParty = analysis?.parties.find((p) => p.id === analysis?.drafting_party_id);
  const counterparty = analysis?.parties.find((p) => p.id !== analysis?.drafting_party_id);
  const combinedSaveState = (["saving", "error", "dirty", "saved"] as SaveState[])
    .find((state) => state === saveState || state === formSaveState)!;
  const save = SAVE_STATUS[combinedSaveState];
  return (
    <WorkspaceShell wide step={3} documentId={params.id} onNavigate={(href) => { void perform(async () => { router.push(href); }, false); }}>
      <PageHeader
        rubric="Проверка протокола"
        title="Протокол разногласий"
        meta={<>
          {analysis?.contract_name && <span className="flex min-w-0 items-center gap-1.5 text-ink-1"><Icon name="file-text" className="text-ink-2" /><span className="wrap-anywhere">{analysis.contract_name}</span></span>}
          <span className="flex items-center gap-1.5"><span className="rubric">Наша сторона</span><strong className="font-medium text-ink">{draftingParty?.name || draftingParty?.role || "Определяем…"}</strong></span>
          <span className="flex items-center gap-1.5 text-ink-1" aria-live="polite"><Icon name={save.icon} className={save.className} />{save.label}</span>
        </>}
        actions={
          <Button variant="primary" disabled={busy} aria-busy={busy || undefined}
            onClick={() => { void perform(async () => { setExportOpen(true); }, false); }}>
            <Icon name="download" size={16} />Сохранить DOCX
          </Button>
        }
      />
      <section aria-label="Проверка полноты" className={cn("mb-4 mt-6 rounded-md border border-line-c", hasIssues ? "bg-warn-soft" : "bg-ok-soft")}>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm text-ink">
          <Icon name={hasIssues ? "triangle-alert" : "circle-check"} size={16} className={hasIssues ? "text-warn" : "text-ok"} />
          <span className="min-w-0 flex-1">{report ? <>{uncovered > 0 ? <>Не покрыто правок: <strong>{uncovered}</strong> из {report.textual_revisions_total}.</> : <>Все текстовые правки учтены: <strong>{report.covered_revisions}</strong> из {report.textual_revisions_total}.</>}{warningCount > 0 && <> Замечаний: <strong>{warningCount}</strong>.</>}</> : "Проверка полноты пока недоступна."}</span>
          <button type="button" onClick={() => setDetailsOpen(!detailsOpen)} aria-expanded={detailsOpen} aria-controls="validation-details"
            className="flex items-center gap-1 rounded-xs text-xs font-medium text-ink-1 underline decoration-line-strong underline-offset-4 hover:text-ink">
            {detailsOpen ? "Скрыть" : "Подробнее"}<Icon name="chevron-down" className={cn("transition-transform", detailsOpen && "rotate-180")} />
          </button>
        </div>
        {detailsOpen && (
          <div id="validation-details" className="space-y-3 border-t border-line-c px-4 py-3 text-sm leading-relaxed text-ink-1">
            <p>Проверка полноты показывает, учтены ли исходные правки. Юридическую корректность редакций вы проверяете самостоятельно.</p>
            {report?.warnings.length ? <ul className="list-disc space-y-1 pl-5">{report.warnings.map((warning, index) => <li key={index}>{warning.message}</li>)}</ul> : null}
            {diagnostics.length > 0 && <ul className="list-disc space-y-1 pl-5">{diagnostics.map((item, index) => <li key={index}>{item.message}</li>)}</ul>}
            {!report && <Button variant="ghost" size="sm" onClick={() => void refreshAnalysis()}><Icon name="history" />Повторить проверку</Button>}
          </div>
        )}
      </section>
      {operationError && <Notice tone="danger" role="alert" className="mb-4">{operationError}</Notice>}
      <div role="tablist" aria-label="Раздел протокола" className="mb-5 flex gap-1 border-b border-line-c">
        {([{ value: "clauses", label: "Правки договора" }, { value: "form", label: "Оформление" }] as const).map((item) => (
          <button key={item.value} type="button" role="tab" id={`tab-${item.value}`} aria-selected={tab === item.value}
            aria-controls={`panel-${item.value}`} tabIndex={tab === item.value ? 0 : -1} disabled={busy}
            onKeyDown={(event) => {
              if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                event.preventDefault();
                const next = event.key === "Home" ? "clauses" : event.key === "End" ? "form" : tab === "clauses" ? "form" : "clauses";
                void perform(async () => { focusTab.current = next; setTab(next); }, false);
              }
            }}
            onClick={() => void perform(async () => { setTab(item.value); }, false)}
            className={cn("border-b-2 px-4 py-3 text-sm font-medium transition-colors", tab === item.value ? "border-accent text-ink" : "border-transparent text-ink-2 hover:text-ink")}>
            {item.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="panel-clauses" aria-labelledby="tab-clauses" hidden={tab !== "clauses"}>
        <ProtocolTable ref={tableRef} busy={busy} rows={protocol.rows} form={protocol.form} initialMode="focus" storageKey={protocol.id}
          reviewContext={analysis?.drafting_party_id ?? ""} warnings={report?.warnings ?? []} onSaveStateChange={setSaveState}
          counterpartyRole={counterparty?.role ?? ""} draftingRole={draftingParty?.role ?? ""}
          onPatch={patch} onMerge={merge} onDelete={remove} onAddRow={addRow} onSwapParties={swap} />
      </div>
      <div role="tabpanel" id="panel-form" aria-labelledby="tab-form" hidden={tab !== "form"}>
        {protocol.form && <ProtocolFormEditor ref={formRef} form={protocol.form} rows={protocol.rows}
          parties={analysis?.parties ?? []} draftingPartyId={analysis?.drafting_party_id ?? null}
          busy={busy} active={tab === "form"} onSave={saveForm} onSaveStateChange={setFormSaveState} onSwapParties={swap} />}
      </div>
      {exportOpen && <ExportDialog documentId={params.id} contractName={analysis?.contract_name} rowCount={protocol.rows.length} onClose={() => setExportOpen(false)} />}
    </WorkspaceShell>
  );
}
