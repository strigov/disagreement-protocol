"use client";

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { ExportForm } from "./ExportForm";

export function ExportDialog({ documentId, contractName, rowCount, onClose }: {
  documentId: string; contractName?: string | null; rowCount: number; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    if (typeof element?.showModal === "function") element.showModal();
    else element?.setAttribute("open", "");
    return () => { element?.close?.(); previous?.focus(); };
  }, []);
  return <dialog ref={dialog} className="export-dialog" aria-labelledby="export-title" aria-modal="true"
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
    <div className="export-dialog-header"><h2 id="export-title">Скачать протокол</h2><button className="icon-button" aria-label="Закрыть экспорт" disabled={busy} onClick={onClose}><X size={16} /></button></div>
    <ExportForm documentId={documentId} contractName={contractName} rowCount={rowCount} onBusyChange={setBusy} />
  </dialog>;
}
