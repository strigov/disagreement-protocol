import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";

const MODES = [
  { value: "focus", label: "По пунктам", icon: "align-left" },
  { value: "table", label: "Таблица", icon: "table-2" },
] as const;

export function ProtocolToolbar({ mode, modeDisabled, actionsDisabled, onModeChange, onAddRow, onSwapParties }: {
  mode: "focus" | "table";
  modeDisabled: boolean;
  actionsDisabled: boolean;
  onModeChange: (mode: "focus" | "table") => void;
  onAddRow: () => void;
  onSwapParties: () => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div role="group" aria-label="Вид протокола" className="inline-flex gap-0.5 rounded-md border border-line-c bg-bg-sunk p-0.5">
        {MODES.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={modeDisabled}
            aria-pressed={mode === option.value}
            onClick={() => onModeChange(option.value)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-sm px-3 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              mode === option.value ? "bg-bg-elev text-ink shadow-sm" : "text-ink-2 hover:text-ink",
            )}
          >
            <Icon name={option.icon} />{option.label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" disabled={actionsDisabled} onClick={onAddRow}><Icon name="plus" />Добавить строку</Button>
        <Button variant="ghost" size="sm" disabled={actionsDisabled} onClick={onSwapParties}><Icon name="arrow-left-right" />Поменять стороны</Button>
      </div>
    </div>
  );
}
