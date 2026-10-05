import type { ReactNode } from "react";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

export function ConfirmDialog({ title, description, confirmLabel, cancelLabel = "Отмена", onConfirm, onCancel }: {
  title: string; description?: ReactNode; confirmLabel: string; cancelLabel?: string;
  onConfirm: () => void; onCancel: () => void;
}) {
  return (
    <Dialog title={title} description={description} onClose={onCancel}>
      <div className="flex flex-wrap justify-end gap-2">
        {/* Безопасное действие получает фокус первым. */}
        <Button variant="ghost" autoFocus onClick={onCancel}>{cancelLabel}</Button>
        <Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Dialog>
  );
}
