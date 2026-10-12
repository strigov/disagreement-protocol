import { useMemo, useSyncExternalStore } from "react";

export const FONT_COLORS = [
  ["000000", "Чёрный"], ["FFFFFF", "Белый"], ["C00000", "Тёмно-красный"],
  ["FF0000", "Красный"], ["FFC000", "Оранжевый"], ["FFFF00", "Жёлтый"],
  ["92D050", "Светло-зелёный"], ["00B050", "Зелёный"], ["00B0F0", "Голубой"],
  ["0070C0", "Синий"], ["002060", "Тёмно-синий"], ["7030A0", "Фиолетовый"],
] as const;

// Native Word text-marker colors: https://learn.microsoft.com/office/vba/api/word.wdcolorindex
export const HIGHLIGHT_COLORS = [
  ["yellow", "Жёлтый", "FFFF00"], ["green", "Ярко-зелёный", "00FF00"],
  ["cyan", "Бирюзовый", "00FFFF"], ["magenta", "Розовый", "FF00FF"],
  ["blue", "Синий", "0000FF"], ["red", "Красный", "FF0000"],
  ["darkBlue", "Тёмно-синий", "000080"], ["darkCyan", "Тёмно-бирюзовый", "008080"],
  ["darkGreen", "Зелёный", "008000"], ["darkMagenta", "Фиолетовый", "800080"],
  ["darkRed", "Тёмно-красный", "800000"], ["darkYellow", "Тёмно-жёлтый", "808000"],
  ["darkGray", "Серый 50%", "808080"], ["lightGray", "Серый 25%", "C0C0C0"],
  ["black", "Чёрный", "000000"],
] as const;

export interface ChangeStyle {
  color: typeof FONT_COLORS[number][0] | null;
  highlight: typeof HIGHLIGHT_COLORS[number][0] | null;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strike?: boolean;
}
export interface ExportSettings {
  enabled: boolean;
  deletions: ChangeStyle;
  additions: ChangeStyle;
}

export const EXPORT_SETTINGS_KEY = "disprot.export-highlighting.v1";
export const DEFAULT_EXPORT_SETTINGS: ExportSettings = {
  enabled: false,
  deletions: { color: "FF0000", highlight: null, bold: false, italic: false, underline: false, strike: false },
  additions: { color: "00B050", highlight: null, bold: false, italic: false, underline: false },
};

const record = (value: unknown): Record<string, unknown> => value && typeof value === "object" ? value as Record<string, unknown> : {};
function parseStyle(value: unknown, fallback: ChangeStyle): ChangeStyle {
  const data = record(value);
  return {
    color: data.color === null ? null : FONT_COLORS.find(([color]) => color === data.color)?.[0] ?? fallback.color,
    highlight: HIGHLIGHT_COLORS.find(([color]) => color === data.highlight)?.[0] ?? null,
    bold: data.bold === true, italic: data.italic === true, underline: data.underline === true,
    ...(fallback.strike !== undefined ? { strike: data.strike === true } : {}),
  };
}
function parseSettings(raw: string | null): ExportSettings {
  try {
    const data = record(JSON.parse(raw || "null"));
    return { enabled: data.enabled === true, deletions: parseStyle(data.deletions, DEFAULT_EXPORT_SETTINGS.deletions), additions: parseStyle(data.additions, DEFAULT_EXPORT_SETTINGS.additions) };
  } catch { return DEFAULT_EXPORT_SETTINGS; }
}

let memory: string | null = null;
let memoryOnly = false;
const listeners = new Set<() => void>();
const snapshot = () => {
  if (memoryOnly) return memory;
  try { return window.localStorage.getItem(EXPORT_SETTINGS_KEY); } catch { return memory; }
};
function subscribe(listener: () => void) {
  listeners.add(listener);
  const changed = (event: StorageEvent) => { if (event.key === EXPORT_SETTINGS_KEY || event.key === null) listener(); };
  window.addEventListener("storage", changed);
  return () => { listeners.delete(listener); window.removeEventListener("storage", changed); };
}

export function writeExportSettings(settings: ExportSettings): boolean {
  memory = JSON.stringify(settings);
  let persisted = true;
  try { window.localStorage.setItem(EXPORT_SETTINGS_KEY, memory); } catch { persisted = false; }
  memoryOnly = !persisted;
  listeners.forEach((listener) => listener());
  return persisted;
}

export function useExportSettings() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => null);
  return useMemo(() => parseSettings(raw), [raw]);
}
