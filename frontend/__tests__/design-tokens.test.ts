import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

// Механическая проверка дисциплины токенов «Бюро»: цвет, размеры и эффекты
// приходят только из семантических токенов tailwind.config.ts / globals.css.
// Vitest запускается из frontend/ (vitest.config.ts).
const ROOT = process.cwd();

const FORBIDDEN_TSX: ReadonlyArray<[string, RegExp]> = [
  ["палитра Tailwind", /\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|decoration|divide|placeholder|accent|shadow|caret)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/],
  ["белый/чёрный из палитры", /\b(?:bg|text|border)-(?:white|black)\b/],
  ["произвольное значение [..]", /[a-z0-9]-\[[^\]]*\]/],
  ["произвольный вариант", /\[(?:@|&)[^\]]*\]:/],
  ["hex-цвет", /#[0-9a-fA-F]{3,8}\b/],
  ["модификатор dark:", /(?:^|[\s"'`])dark:[a-z!-]/],
  ["градиент или blur", /\bbackdrop-blur|\bblur-(?:none|sm|md|lg|xl|2xl|3xl)\b|\bbg-gradient-/],
  ["радиус больше 12px", /\brounded-(?:xl|2xl|3xl|full)\b/],
  ["тень вне шкалы", /\bshadow-(?:lg|xl|2xl|inner)\b/],
  ["три точки вместо «…»", /[А-Яа-яЁё]\.\.\./],
  ["lucide напрямую (только через Icon)", /from "lucide-react"/],
];

const ICON_REGISTRY = "components/icons/Icon.tsx";
const ALLOWED_CSS_CLASSES = new Set(["skip-link", "rubric", "wrap-anywhere"]);

const tsxFiles = ["app", "components"].flatMap((dir) =>
  (readdirSync(join(ROOT, dir), { recursive: true }) as string[])
    .filter((file) => file.endsWith(".tsx"))
    .map((file) => relative(ROOT, join(ROOT, dir, file))),
);

test.each(tsxFiles)("%s uses only design-system tokens", (file) => {
  const source = readFileSync(join(ROOT, file), "utf8");
  const violations = FORBIDDEN_TSX
    .filter(([name]) => !(file === ICON_REGISTRY && name.startsWith("lucide")))
    .filter(([, pattern]) => pattern.test(source))
    .map(([name]) => name);
  expect(violations).toEqual([]);
});

test("globals.css keeps colours inside the two theme blocks and defines only shared classes", () => {
  const css = readFileSync(join(ROOT, "app/globals.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const outsideThemes = css.replace(/\[data-concept='buro'\]\[data-theme='(?:light|dark)'\]\s*\{[^}]*\}/g, "");
  expect(outsideThemes).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
  expect(css).not.toMatch(/@import|https?:/);
  const classes = new Set([...css.replace(/url\([^)]*\)/g, "").matchAll(/\.([a-z][a-z0-9-]*)/g)].map((match) => match[1]));
  expect([...classes].filter((name) => !ALLOWED_CSS_CLASSES.has(name))).toEqual([]);
});
