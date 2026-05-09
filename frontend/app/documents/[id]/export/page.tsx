"use client";

import { useState } from "react";
import { api } from "@/lib/api";

// Strip path separators and control characters; cap length so the resulting
// download attribute can never exceed filesystem limits on common OSes.
const sanitize = (raw: string) =>
  raw
    .trim()
    // eslint-disable-next-line no-control-regex
    .replace(/[\\/]/g, "")
    // eslint-disable-next-line no-control-regex
    .replace(/[\x00-\x1f\x7f]/g, "")
    .slice(0, 200);

export default function ExportPage({ params }: { params: { id: string } }) {
  const [filename, setFilename] = useState("Протокол разногласий");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const cleaned = sanitize(filename);
  const canSubmit = !busy && cleaned.length > 0;

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!cleaned) {
      setError("Введите имя файла");
      return;
    }
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      const blob = await api.exportProtocol(params.id, cleaned);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = cleaned + ".docx";
      // Element must be in the DOM in some browsers for the click to take.
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-md space-y-6 px-4 py-12">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Экспорт</h1>
        <p className="text-sm text-gray-500">
          Сохраните протокол разногласий в формате DOCX.
        </p>
      </header>

      <form onSubmit={submit} className="space-y-4" noValidate>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-gray-700">
            Имя файла (без .docx)
          </span>
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            disabled={busy}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "export-error" : undefined}
            className="w-full rounded border border-gray-300 px-3 py-2 text-base focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:bg-gray-100"
          />
          {cleaned && (
            <span className="mt-1 block text-xs text-gray-500">
              Файл: <span className="font-mono">{cleaned}.docx</span>
            </span>
          )}
        </label>

        {error && (
          <p
            id="export-error"
            role="alert"
            className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </p>
        )}

        {done && !error && (
          <p
            role="status"
            aria-live="polite"
            className="rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
          >
            Файл сохранён.
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          aria-busy={busy || undefined}
          className="inline-flex items-center justify-center rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {busy ? "Сохраняем…" : "Сохранить"}
        </button>
      </form>
    </main>
  );
}
