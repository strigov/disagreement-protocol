import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { readThemeMode, resolveTheme, THEME_INIT_SCRIPT, THEME_STORAGE_KEY } from "@/lib/theme";

type Listener = (event: MediaQueryListEvent) => void;

function stubMatchMedia(matches: boolean) {
  const listeners = new Set<Listener>();
  const query = {
    matches,
    addEventListener: (_: string, listener: Listener) => listeners.add(listener),
    removeEventListener: (_: string, listener: Listener) => listeners.delete(listener),
  };
  Object.defineProperty(window, "matchMedia", { configurable: true, writable: true, value: vi.fn(() => query) });
  return { emit: (dark: boolean) => { query.matches = dark; listeners.forEach((listener) => listener({ matches: dark } as MediaQueryListEvent)); } };
}

const html = document.documentElement;

beforeEach(() => {
  window.localStorage.clear();
  html.removeAttribute("data-theme");
  html.removeAttribute("data-concept");
  Reflect.deleteProperty(window, "matchMedia");
});

test("resolveTheme follows the explicit choice or the system preference", () => {
  expect(resolveTheme("light", true)).toBe("light");
  expect(resolveTheme("dark", false)).toBe("dark");
  expect(resolveTheme("system", true)).toBe("dark");
  expect(resolveTheme("system", false)).toBe("light");
});

test("readThemeMode falls back to system for missing, unknown or unreadable values", () => {
  expect(readThemeMode()).toBe("system");
  window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");
  expect(readThemeMode()).toBe("system");
  const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("denied"); });
  expect(readThemeMode()).toBe("system");
  spy.mockRestore();
});

test.each([
  ["dark", false, "dark"],
  ["light", true, "light"],
  [null, true, "dark"],
  [null, false, "light"],
] as const)("init script applies stored %s (system dark: %s) before paint", (stored, systemDark, expected) => {
  if (stored) window.localStorage.setItem(THEME_STORAGE_KEY, stored);
  stubMatchMedia(systemDark);
  new Function(THEME_INIT_SCRIPT)();
  expect(html).toHaveAttribute("data-theme", expected);
  expect(html).toHaveAttribute("data-concept", "buro");
});

test("init script never throws, even without matchMedia or storage", () => {
  const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("denied"); });
  expect(() => new Function(THEME_INIT_SCRIPT)()).not.toThrow();
  expect(html).toHaveAttribute("data-theme", "light");
  spy.mockRestore();
});

test("theme toggle stores the choice and follows the system in auto mode", async () => {
  const media = stubMatchMedia(false);
  render(<ThemeToggle />);
  await userEvent.click(screen.getByRole("button", { name: "Тёмная тема" }));
  expect(html).toHaveAttribute("data-theme", "dark");
  expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  expect(screen.getByRole("button", { name: "Тёмная тема" })).toHaveAttribute("aria-pressed", "true");

  await userEvent.click(screen.getByRole("button", { name: "Как в системе" }));
  expect(html).toHaveAttribute("data-theme", "light");
  media.emit(true);
  expect(html).toHaveAttribute("data-theme", "dark");
});
