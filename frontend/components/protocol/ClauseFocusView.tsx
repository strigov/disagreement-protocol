import type { ReactNode } from "react";
import type { ProtocolRow, ValidationWarning } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";
import { Button, IconButton } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import type { RenderCell } from "./types";

export function ClauseFocusView({
  row, position, total, navDisabled, onPrevious, onNext, actions, attention, rowWarnings, showDiff, onShowDiffChange,
  counterpartyRole, draftingRole, counterpartyLabel, draftingLabel, renderCell,
  pointLabel = "Пункт договора", agreedLabel = "Согласованная редакция",
  reviewed, reviewDisabled, onToggleReviewed, onReviewAndNext, reviewAndNextDisabled,
}: {
  row: ProtocolRow;
  position: number;
  total: number;
  navDisabled: boolean;
  onPrevious: (() => void) | null;
  onNext: (() => void) | null;
  actions: ReactNode;
  attention: boolean;
  rowWarnings: ValidationWarning[];
  showDiff: boolean;
  onShowDiffChange: (value: boolean) => void;
  counterpartyRole: string;
  draftingRole: string;
  counterpartyLabel: string;
  draftingLabel: string;
  pointLabel?: string;
  agreedLabel?: string;
  renderCell: RenderCell;
  reviewed: boolean;
  reviewDisabled: boolean;
  onToggleReviewed: () => void;
  onReviewAndNext: () => void;
  reviewAndNextDisabled: boolean;
}) {
  const panes = [
    { field: "party_1_text" as const, rubric: "Контрагент", role: counterpartyRole || "Редакция контрагента", label: counterpartyLabel, ours: false },
    { field: "party_2_text" as const, rubric: "Наша сторона", role: draftingRole || "Наша редакция", label: draftingLabel, ours: true },
  ];
  return (
    <section aria-label="Выбранный пункт" className="flex min-w-0 flex-col">
      <header className="flex items-start justify-between gap-4 border-b border-line-c px-5 py-4 md:px-7 md:py-5">
        <div className="min-w-0">
          <p className="rubric" aria-live="polite">
            {position} из {total} · {row.user_edited ? "Отредактирован вручную" : "Сформирован из правок договора"}
          </p>
          <h2 className="mt-1 flex items-baseline gap-2 font-serif text-3xl font-semibold leading-tight text-ink">
            Пункт {renderCell(row, "point_label", pointLabel)}
          </h2>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton icon="chevron-left" label="Предыдущий пункт" disabled={navDisabled || !onPrevious} onClick={onPrevious ?? undefined} />
          <IconButton icon="chevron-right" label="Следующий пункт" disabled={navDisabled || !onNext} onClick={onNext ?? undefined} />
          {actions}
        </div>
      </header>

      <div className="space-y-6 px-5 py-5 md:px-7 md:py-6">
        {attention && (
          <Notice tone="warn" title="Проверьте этот пункт">
            {rowWarnings.length
              ? <ul className="mt-1 space-y-1">{rowWarnings.map((warning, index) => <li key={index}>{warning.message}</li>)}</ul>
              : <p>Сверьте номер и содержание с исходным договором.</p>}
          </Notice>
        )}

        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h3 className="rubric">Редакции сторон</h3>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-1">
              <input type="checkbox" className="h-4 w-4 accent-accent" checked={showDiff} onChange={(event) => onShowDiffChange(event.target.checked)} />
              Подсветить различия
            </label>
          </div>
          <div className="grid overflow-hidden rounded-md border border-line-c lg:grid-cols-2">
            {panes.map((pane) => (
              <section key={pane.field} className={cn("min-w-0", pane.ours && "border-line-c max-lg:border-t lg:border-l")}>
                <div className={cn("border-b border-line-c px-4 py-3", pane.ours ? "bg-accent-soft" : "bg-bg-sunk")}>
                  <span className="rubric block">{pane.rubric}</span>
                  <h4 className="mt-0.5 text-sm font-medium text-ink wrap-anywhere">{pane.role}</h4>
                </div>
                <div className="p-3 text-sm leading-7 text-ink">{renderCell(row, pane.field, pane.label)}</div>
              </section>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-serif text-xl font-semibold text-ink">{agreedLabel}</h3>
            <span className="text-xs text-ink-2">Войдёт в итоговый протокол</span>
          </div>
          <div className="rounded-md border border-line-strong bg-bg p-3 text-sm leading-7 text-ink">
            {renderCell(row, "agreed_text", agreedLabel)}
          </div>
          <p className="mt-2 text-xs text-ink-2">
            Нажмите на текст, чтобы изменить его. <kbd className="rounded-xs border border-line-c bg-bg-sunk px-1 text-2xs">Ctrl</kbd> / <kbd className="rounded-xs border border-line-c bg-bg-sunk px-1 text-2xs">⌘</kbd> + <kbd className="rounded-xs border border-line-c bg-bg-sunk px-1 text-2xs">Enter</kbd> — сохранить, <kbd className="rounded-xs border border-line-c bg-bg-sunk px-1 text-2xs">Esc</kbd> — отменить.
          </p>
        </div>
      </div>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-line-c bg-bg-sunk px-5 py-3 md:px-7">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
          <input type="checkbox" className="h-4 w-4 accent-ok" checked={reviewed} disabled={reviewDisabled} onChange={onToggleReviewed} />
          Проверено мной
        </label>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={reviewAndNextDisabled} onClick={onReviewAndNext}>
            <Icon name="check-check" className="text-ok" />Проверено — дальше
          </Button>
          <Button variant="ghost" size="sm" disabled={navDisabled || !onNext} onClick={onNext ?? undefined}>
            Следующий пункт<Icon name="chevron-right" />
          </Button>
        </div>
      </footer>
    </section>
  );
}
