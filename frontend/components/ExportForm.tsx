"use client";

import { useRef, useState } from "react";
import { Download, FileText, LoaderCircle } from "lucide-react";
import { api } from "@/lib/api";

const sanitize = (raw: string) => raw.trim().replace(/\.docx$/i, "").replace(/[\\/]/g, "").replace(/[\x00-\x1f\x7f]/g, "").slice(0, 200).trim();

export function ExportForm({ documentId, contractName, rowCount, onBusyChange }: {
  documentId: string; contractName?: string | null; rowCount?: number; onBusyChange?: (busy: boolean) => void;
}) {
  const [filename, setFilename] = useState(contractName ? `Протокол разногласий — ${contractName.replace(/\.docx$/i, "").slice(0, 100)}` : "Протокол разногласий");
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const cleaned = sanitize(filename);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (pending.current || !cleaned) return;
    pending.current = true;
    setBusy(true);
    onBusyChange?.(true);
    setError(null);
    setDone(false);
    try {
      const blob = await api.exportProtocol(documentId, cleaned);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = cleaned + ".docx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      // Give the browser a chance to start consuming the download URL.
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDone(true);
    } catch (e) { setError((e as Error).message); }
    finally { pending.current = false; setBusy(false); onBusyChange?.(false); }
  };
  return <form className="export-form" onSubmit={submit}>
    <div className="export-preview"><FileText size={29} className="text-blue-600" strokeWidth={1.5} /><div><strong>Протокол разногласий</strong><span>Документ Word · .docx{rowCount !== undefined && ` · Строк: ${rowCount}`}</span></div></div>
    <label><span className="field-label">Имя файла (без .docx)</span><input className="field" value={filename} onChange={(e) => { setFilename(e.target.value); setDone(false); }} disabled={busy} aria-invalid={!!error} aria-describedby={error ? "export-error" : undefined} /></label>
    {cleaned && <p className="export-filename">Файл: {cleaned}.docx</p>}
    {error && <p className="notice notice-error" id="export-error" role="alert">{error}</p>}
    {done && !error && <p className="notice notice-success" role="status">Скачивание началось. Проверьте загрузки браузера.</p>}
    <button type="submit" disabled={busy || !cleaned} className="btn btn-primary" aria-busy={busy || undefined}>
      {busy ? <LoaderCircle size={15} className="spinner" /> : <Download size={15} />}{busy ? "Сохраняем…" : "Сохранить"}
    </button>
    <p className="edit-hint text-center mt-3">Все сохранённые изменения войдут в документ.</p>
  </form>;
}
