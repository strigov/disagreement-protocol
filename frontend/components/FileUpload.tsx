"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { rememberDocument } from "@/lib/recent-documents";
import { Icon } from "@/components/icons/Icon";
import { buttonClassName } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";

export function FileUpload() {
  const router = useRouter();
  const uploading = useRef(false);
  const dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState<string | null>(null);
  const handle = async (file: File) => {
    if (uploading.current) return;
    setError(null);
    if (!/\.docx$/i.test(file.name)) { setError("Выберите договор в формате .docx. Файлы .doc и .pdf не поддерживаются."); return; }
    if (file.size > 25 * 1024 * 1024) { setError("Файл слишком большой. Максимальный размер — 25 МБ."); return; }
    uploading.current = true;
    setBusy(true);
    setFilename(file.name);
    try {
      const result = await api.uploadDocument(file);
      rememberDocument({ id: result.id, title: file.name.replace(/\.docx$/i, ""), stage: "analysis" });
      router.push(`/documents/${result.id}/analysis`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      uploading.current = false;
      setBusy(false);
    }
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    if (event.dataTransfer.files.length > 1) { setError("Выберите один договор за раз."); return; }
    const file = event.dataTransfer.files[0];
    if (file) void handle(file);
  };
  const onPick = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) void handle(file);
    event.target.value = "";
  };
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-lg border border-dashed px-4 py-12 text-center transition-colors md:py-16",
        dragging ? "border-accent bg-accent-soft" : "border-line-strong bg-bg-elev",
      )}
      aria-busy={busy}
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      onDragEnter={(e) => { e.preventDefault(); dragDepth.current++; setDragging(true); }}
      onDragLeave={() => { if (--dragDepth.current <= 0) setDragging(false); }}
    >
      <span className="mb-5 grid h-12 w-12 place-items-center rounded-pill bg-bg-sunk text-ink-2">
        {busy ? <Icon name="loader-circle" size={20} className="motion-safe:animate-spin" /> : <Icon name="file-up" size={20} />}
      </span>
      <p className="max-w-md font-serif text-2xl font-semibold leading-snug text-ink">Перетащите .docx сюда или выберите файл</p>
      <p className="mt-2 text-sm text-ink-2">Договор с исправлениями Word · до 25 МБ</p>
      <label
        className={buttonClassName({
          variant: "primary",
          className: cn(
            "relative mt-6 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent",
            busy ? "pointer-events-none opacity-50" : "cursor-pointer",
          ),
        })}
      >
        Выбрать файл <Icon name="arrow-up-right" />
        <input className="absolute inset-0 h-full w-full cursor-pointer opacity-0" aria-label="Выбрать файл" type="file" accept=".docx" disabled={busy} onChange={onPick} />
      </label>
      {busy && <p className="mt-4 max-w-full text-xs text-ink-2 wrap-anywhere" role="status">Открываем… {filename}</p>}
      {error && <Notice tone="danger" role="alert" className="mt-6 w-full max-w-xl text-left">{error}</Notice>}
    </div>
  );
}
