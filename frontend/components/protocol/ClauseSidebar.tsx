import type { ReactNode } from "react";
import type { ProtocolRow } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";

export function ClauseSidebar({
  rows, totalCount, activeId, navDisabled, isReviewed, isAttention, onSelect, search, filter, reviewedCount, storageNotice,
}: {
  rows: ProtocolRow[];
  totalCount: number;
  activeId: string | undefined;
  navDisabled: boolean;
  isReviewed: (row: ProtocolRow) => boolean;
  isAttention: (row: ProtocolRow) => boolean;
  onSelect: (rowId: string) => void;
  search: ReactNode;
  filter: ReactNode;
  reviewedCount: number;
  storageNotice: boolean;
}) {
  const percent = totalCount ? Math.round((reviewedCount / totalCount) * 100) : 0;
  return (
    <aside aria-label="Навигация по пунктам" className="flex min-w-0 flex-col border-line-c bg-bg-sunk max-md:border-b md:border-r">
      <div className="space-y-3 border-b border-line-c p-4">
        <div className="flex items-center justify-between">
          <h2 className="rubric">Пункты договора</h2>
          <span className="rounded-pill bg-bg-elev px-2 font-mono text-2xs text-ink-2">{totalCount}</span>
        </div>
        {search}
        {filter}
      </div>
      <nav aria-label="Пункты договора" className="flex gap-1 overflow-auto p-2 max-md:max-h-clause-strip md:max-h-clause-list md:flex-1 md:flex-col">
        {rows.map((row) => {
          const active = row.id === activeId;
          const reviewed = isReviewed(row);
          return (
            <button
              key={row.id}
              type="button"
              aria-current={active}
              aria-label={`Открыть пункт ${row.point_label || "без номера"}`}
              disabled={navDisabled}
              onClick={() => onSelect(row.id)}
              className={cn(
                "block w-full rounded-sm border px-3 py-2.5 text-left transition-colors disabled:cursor-wait max-md:w-40 max-md:shrink-0",
                active ? "border-line-c bg-bg-elev shadow-sm" : "border-transparent hover:bg-bg-hover",
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className={cn("text-xs font-medium", active ? "text-ink" : "text-ink-1")}>Пункт {row.point_label || "без номера"}</span>
                {reviewed
                  ? <Icon name="check" className="text-ok" label="Проверен вами" />
                  : isAttention(row) ? <Icon name="triangle-alert" className="text-warn" label="Требует внимания" /> : null}
              </span>
              <span className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-2 wrap-anywhere">
                {row.party_2_text || row.party_1_text || "Новая строка протокола"}
              </span>
            </button>
          );
        })}
      </nav>
      <div className="mt-auto border-t border-line-c p-4 text-xs text-ink-2">
        <div className="flex items-baseline justify-between gap-2">
          <span>Проверено вами: {reviewedCount} из {totalCount}</span>
          <span className="font-mono text-2xs">{percent}%</span>
        </div>
        <progress value={reviewedCount} max={Math.max(1, totalCount)} aria-label="Прогресс вашей проверки" className="sr-only" />
        <div aria-hidden="true" className="my-2 h-1 overflow-hidden rounded-pill bg-bg-active max-md:hidden">
          <div className="h-full rounded-pill bg-ok transition-all" style={{ width: `${percent}%` }} />
        </div>
        <p className="leading-relaxed">{storageNotice ? "Отметки доступны только до закрытия страницы." : "Отметки сохраняются в этом браузере."}</p>
      </div>
    </aside>
  );
}
