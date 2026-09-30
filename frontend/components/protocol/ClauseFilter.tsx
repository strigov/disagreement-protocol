import { cn } from "@/lib/cn";
import type { ClauseFilterValue } from "./types";

const OPTIONS: ReadonlyArray<{ value: ClauseFilterValue; label: string }> = [
  { value: "all", label: "Все пункты" },
  { value: "attention", label: "Требуют внимания" },
  { value: "unreviewed", label: "Не проверены мной" },
];

export function ClauseFilter({ value, counts, layout, onChange }: {
  value: ClauseFilterValue;
  counts: Record<ClauseFilterValue, number>;
  layout: "stack" | "inline";
  onChange: (value: ClauseFilterValue) => void;
}) {
  return (
    <div role="group" aria-label="Фильтр пунктов" className={cn("flex gap-1", layout === "stack" ? "flex-col" : "flex-wrap")}>
      {OPTIONS.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              "flex items-center justify-between gap-3 rounded-sm px-2.5 text-left text-xs transition-colors",
              layout === "stack" ? "h-8 w-full" : "h-8 border",
              active
                ? "bg-bg-active font-medium text-ink"
                : "text-ink-1 hover:bg-bg-hover hover:text-ink",
              layout === "inline" && (active ? "border-line-strong" : "border-line-c"),
            )}
          >
            {option.label}
            <span className="rounded-pill bg-bg-elev px-1.5 font-mono text-2xs text-ink-2">{counts[option.value]}</span>
          </button>
        );
      })}
    </div>
  );
}
