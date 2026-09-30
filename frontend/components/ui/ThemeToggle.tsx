"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/icons/Icon";
import { applyTheme, readThemeMode, resolveTheme, systemPrefersDark, writeThemeMode, type ThemeMode } from "@/lib/theme";

const OPTIONS: ReadonlyArray<{ value: ThemeMode; label: string; icon: IconName }> = [
  { value: "light", label: "Светлая тема", icon: "sun" },
  { value: "dark", label: "Тёмная тема", icon: "moon" },
  { value: "system", label: "Как в системе", icon: "monitor" },
];

export function ThemeToggle() {
  // null до монтирования: на сервере выбор пользователя неизвестен.
  const [mode, setMode] = useState<ThemeMode | null>(null);

  useEffect(() => {
    const stored = readThemeMode();
    setMode(stored);
    applyTheme(resolveTheme(stored, systemPrefersDark()));
  }, []);

  useEffect(() => {
    if (mode !== "system" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = (event: MediaQueryListEvent) => applyTheme(event.matches ? "dark" : "light");
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, [mode]);

  const choose = (next: ThemeMode) => {
    writeThemeMode(next);
    applyTheme(resolveTheme(next, systemPrefersDark()));
    setMode(next);
  };

  return (
    <div role="group" aria-label="Тема оформления" className="inline-flex items-center gap-0.5 rounded-pill border border-line-c bg-bg p-0.5">
      {OPTIONS.map((option) => {
        const active = mode === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            aria-label={option.label}
            title={option.label}
            onClick={() => choose(option.value)}
            className={cn(
              "inline-grid h-7 w-7 place-items-center rounded-pill transition-colors",
              active ? "bg-accent-soft text-ink" : "text-ink-2 hover:bg-bg-hover hover:text-ink",
            )}
          >
            <Icon name={option.icon} />
          </button>
        );
      })}
    </div>
  );
}
