// Тема «Бюро»: data-theme на <html> выставляет inline-скрипт до первой
// отрисовки, дальше им управляет ThemeToggle. Модуль не трогает window при импорте.
export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "disprot.theme";

const MODES: readonly ThemeMode[] = ["light", "dark", "system"];

export function readThemeMode(): ThemeMode {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return MODES.includes(value as ThemeMode) ? (value as ThemeMode) : "system";
  } catch {
    return "system";
  }
}

export function writeThemeMode(mode: ThemeMode): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    /* хранилище недоступно — выбор действует до перезагрузки */
  }
}

export function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(mode: ThemeMode, prefersDark: boolean): ResolvedTheme {
  if (mode === "system") return prefersDark ? "dark" : "light";
  return mode;
}

export function applyTheme(theme: ResolvedTheme): void {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-concept", "buro");
}

// Статическая строка без пользовательских данных; никогда не бросает исключение.
export const THEME_INIT_SCRIPT = `(function () {
  var theme = "light";
  try {
    var mode = window.localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
    var dark = mode === "dark" || (mode !== "light" && typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-color-scheme: dark)").matches);
    theme = dark ? "dark" : "light";
  } catch (e) {}
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-concept", "buro");
})();`;
