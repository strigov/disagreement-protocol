import { useEffect, useId, useRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { IconButton } from "./Button";

// Смонтирован = открыт. Нативный <dialog> даёт focus trap и Esc без зависимостей.
export function Dialog({
  title, description, onClose, dismissible = true, closeLabel = "Закрыть", children, className,
}: {
  title: ReactNode; description?: ReactNode; onClose: () => void;
  dismissible?: boolean; closeLabel?: string; children: ReactNode; className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = ref.current;
    if (typeof element?.showModal === "function") element.showModal();
    else element?.setAttribute("open", "");
    return () => { element?.close?.(); previous?.focus?.(); };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      aria-modal="true"
      onCancel={(event) => { event.preventDefault(); if (dismissible) onClose(); }}
      className={cn("w-full max-w-md rounded-lg border border-line-c bg-bg-elev p-0 text-ink shadow-md max-sm:max-w-none", className)}
    >
      <div className="flex items-start justify-between gap-4 px-6 pt-5">
        <div className="min-w-0">
          <h2 id={titleId} className="text-lg font-semibold text-ink">{title}</h2>
          {description && <p id={descriptionId} className="mt-1 text-sm leading-relaxed text-ink-2">{description}</p>}
        </div>
        <IconButton icon="x" label={closeLabel} size="sm" disabled={!dismissible} onClick={onClose} className="-mr-2" />
      </div>
      <div className="px-6 pb-6 pt-4">{children}</div>
    </dialog>
  );
}
