import { useState } from "react";
import { Dialog } from "@/components/ui/Dialog";
import { ExportForm } from "./ExportForm";

export function ExportDialog({ documentId, contractName, rowCount, onClose }: {
  documentId: string; contractName?: string | null; rowCount: number; onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  // Пока файл готовится, закрыть диалог нельзя: Esc и крестик заблокированы.
  return <Dialog title="Сохранить протокол" closeLabel="Закрыть сохранение" dismissible={!busy} onClose={onClose}>
    <ExportForm documentId={documentId} contractName={contractName} rowCount={rowCount} onBusyChange={setBusy} />
  </Dialog>;
}
