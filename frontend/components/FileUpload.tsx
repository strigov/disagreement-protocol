"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { FileUp, ArrowUpRight, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

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
    if (event.dataTransfer.files.length > 1) { setError("Загрузите один договор за раз."); return; }
    const file = event.dataTransfer.files[0];
    if (file) void handle(file);
  };
  const onPick = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) void handle(file);
    event.target.value = "";
  };
  return (
    <div className={`upload-surface ${dragging ? "dragging" : ""}`} aria-busy={busy}
      onDrop={onDrop} onDragOver={(e) => e.preventDefault()}
      onDragEnter={(e) => { e.preventDefault(); dragDepth.current++; setDragging(true); }}
      onDragLeave={() => { if (--dragDepth.current <= 0) setDragging(false); }}>
      <span className="upload-icon">{busy ? <LoaderCircle size={27} className="spinner" /> : <FileUp size={28} strokeWidth={1.5} />}</span>
      <p className="upload-title">Перетащите .docx сюда или выберите файл</p>
      <p className="upload-caption">Договор с исправлениями Word · до 25 МБ</p>
      <label className={`btn btn-primary relative ${busy ? "opacity-50" : "cursor-pointer"}`}>
        Выбрать файл <ArrowUpRight size={14} />
        <input className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" aria-label="Выбрать файл" type="file" accept=".docx" disabled={busy} onChange={onPick} />
      </label>
      {busy ? <p className="upload-note" role="status">Загружаем… {filename}</p> : <p className="upload-note">Обработка и хранение — только на вашем компьютере</p>}
      {error && <p className="notice notice-error mt-5 text-left" role="alert">{error}</p>}
    </div>
  );
}
