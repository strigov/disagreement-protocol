"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut, Protocol, ProtocolRow, ValidationReport } from "@/lib/types";
import { Download, CircleCheck, TriangleAlert, LoaderCircle, Check, FileText } from "lucide-react";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { ExportDialog } from "@/components/ExportDialog";
import ProtocolTable, { type ProtocolTableHandle, type SaveState } from "@/components/ProtocolTable";

export default function ProtocolPage() {
  const params = useParams<{ id: string }>();
  const tableRef = useRef<ProtocolTableHandle>(null);
  const operation = useRef(false);
  const analysisVersion = useRef(0);
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [exportOpen, setExportOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

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
        } catch {
          if (!cancelled) setOperationError("Не удалось получить проверку полноты. Повторите действие после восстановления связи.");
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  const refreshAnalysis = async () => {
    const version = ++analysisVersion.current;
    try {
      const a = await api.getAnalysis(params.id);
      if (version === analysisVersion.current) setAnalysis(a);
    } catch {
      if (version === analysisVersion.current) {
        setAnalysis((current) => current && ({ ...current, validation_report: null }));
        setOperationError("Строки сохранены, но проверка полноты недоступна. Повторите действие после восстановления связи.");
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
      if (!await tableRef.current?.saveAll()) {
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

  if (error) return <WorkspaceShell step={3} documentId={params.id}><div className="notice notice-error" role="alert"><h1 className="text-xl font-semibold mb-2">Не удалось загрузить протокол</h1><p>{error}</p></div></WorkspaceShell>;
  if (!protocol) return <WorkspaceShell step={3} documentId={params.id}><div className="loading-state" aria-busy="true"><LoaderCircle className="spinner mx-auto mb-5 text-blue-600" size={28} /><p>Строим таблицу…</p></div></WorkspaceShell>;

  const report: ValidationReport | null = analysis?.validation_report ?? null;
  const uncovered = report ? Math.max(0, report.textual_revisions_total - report.covered_revisions) : 0;
  const diagnostics = analysis?.preflight_diagnostics ?? [];
  const warningCount = (report?.warnings.length ?? 0) + diagnostics.length;
  const draftingParty = analysis?.parties.find((p) => p.id === analysis?.drafting_party_id);
  const counterparty = analysis?.parties.find((p) => p.id !== analysis?.drafting_party_id);
  const saveLabel = { saved: "Все изменения сохранены", dirty: "Есть несохранённые изменения", saving: "Сохраняем изменения…", error: "Не удалось сохранить изменения" }[saveState];
  return (
    <WorkspaceShell wide step={3} documentId={params.id} onNavigate={(href) => { void perform(async () => { router.push(href); }, false); }}>
      <header className="document-heading">
        <div><div className="eyebrow">Рабочее пространство договора</div><h1>Протокол разногласий</h1>
          {analysis?.contract_name && <p className="document-name flex gap-1.5"><FileText size={14} className="shrink-0 mt-0.5" />{analysis.contract_name}</p>}
          <div className="document-meta"><span>Наша сторона: <strong className="font-medium">{draftingParty?.name || draftingParty?.role || "загружаем…"}</strong></span><span className="meta-separator" /><span className={`save-indicator ${saveState === "error" ? "!text-red-600" : saveState === "dirty" ? "!text-amber-700" : ""}`} aria-live="polite">{saveState === "saving" ? <LoaderCircle size={12} className="spinner" /> : saveState === "saved" ? <Check size={12} /> : <TriangleAlert size={12} />}{saveLabel}</span></div>
        </div>
        <button type="button" className="btn btn-primary" disabled={busy} aria-busy={busy || undefined} aria-label="Экспорт DOCX" onClick={() => { void perform(async () => { setExportOpen(true); }, false); }}><Download size={15} /> Скачать DOCX</button>
      </header>
      <section className={`coverage-strip ${uncovered > 0 || warningCount > 0 ? "has-warnings" : ""}`} aria-label="Проверка полноты">
        {uncovered > 0 || warningCount > 0 ? <TriangleAlert size={16} className="shrink-0" /> : <CircleCheck size={16} className="shrink-0" />}
        <span>{report ? <>{uncovered > 0 ? <>Не покрыто правок: <strong>{uncovered}</strong> из {report.textual_revisions_total}.</> : <>Все текстовые правки учтены: <strong>{report.covered_revisions}</strong> из {report.textual_revisions_total}.</>}{warningCount > 0 && <> Замечаний: <strong>{warningCount}</strong>.</>}</> : "Проверка полноты пока недоступна."}</span>
        <button type="button" onClick={() => setDetailsOpen(!detailsOpen)} aria-expanded={detailsOpen} aria-controls="validation-details">{detailsOpen ? "Скрыть" : "Подробнее"}</button>
      </section>
      {detailsOpen && <div id="validation-details" className="notice mb-5"><p>Проверка полноты показывает, учтены ли исходные правки. Юридическую корректность редакций вы проверяете самостоятельно.</p>{report?.warnings.length ? <ul className="list-disc pl-4 mt-3 space-y-1">{report.warnings.map((warning, index) => <li key={index}>{warning.message}</li>)}</ul> : null}{diagnostics.length > 0 && <ul className="list-disc pl-4 mt-3 space-y-1">{diagnostics.map((item, index) => <li key={index}>{item.message}</li>)}</ul>}{!report && <button className="btn btn-secondary mt-3" onClick={() => void refreshAnalysis()}>Повторить проверку</button>}</div>}
      {operationError && <p role="alert" className="notice notice-error mb-5">{operationError}</p>}
      <ProtocolTable ref={tableRef} busy={busy} rows={protocol.rows} initialMode="focus" storageKey={protocol.id}
        reviewContext={analysis?.drafting_party_id ?? ""} warnings={report?.warnings ?? []} onSaveStateChange={setSaveState}
        counterpartyRole={counterparty?.role ?? ""} draftingRole={draftingParty?.role ?? ""}
        onPatch={patch} onMerge={merge} onDelete={remove} onAddRow={addRow} onSwapParties={swap} />
      {exportOpen && <ExportDialog documentId={params.id} contractName={analysis?.contract_name} rowCount={protocol.rows.length} onClose={() => setExportOpen(false)} />}
    </WorkspaceShell>
  );
}
