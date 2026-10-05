import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Notice } from "@/components/ui/Notice";

// eslint-disable-next-line no-control-regex -- File names must not contain control characters.
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
      // Let Electron start consuming the download before releasing the blob.
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDone(true);
    } catch (e) { setError((e as Error).message); }
    finally { pending.current = false; setBusy(false); onBusyChange?.(false); }
  };
  return <form className="space-y-4" onSubmit={submit}>
    <div className="flex items-center gap-3 rounded-md border border-line-c bg-bg-sunk p-3">
      <Icon name="file-text" size={20} className="text-accent" />
      <div className="min-w-0">
        <p className="font-serif text-lg font-semibold leading-tight text-ink">Протокол разногласий</p>
        <p className="mt-0.5 text-xs text-ink-2">Документ Word · .docx{rowCount !== undefined && ` · Строк: ${rowCount}`}</p>
      </div>
    </div>
    <Field label="Имя файла (без .docx)">
      <Input value={filename} onChange={(e) => { setFilename(e.target.value); setDone(false); }} disabled={busy} aria-invalid={!!error} aria-describedby={error ? "export-error" : undefined} />
    </Field>
    {cleaned && <p className="font-mono text-xs text-ink-2 wrap-anywhere">Файл: {cleaned}.docx</p>}
    {error && <Notice tone="danger" role="alert" id="export-error">{error}</Notice>}
    {done && !error && <Notice tone="ok" role="status">Выберите папку и подтвердите сохранение в открывшемся окне.</Notice>}
    <Button type="submit" variant="primary" disabled={busy || !cleaned} className="w-full" aria-busy={busy || undefined}>
      {busy ? <Icon name="loader-circle" size={16} className="motion-safe:animate-spin" /> : <Icon name="download" size={16} />}{busy ? "Сохраняем…" : "Сохранить"}
    </Button>
  </form>;
}
