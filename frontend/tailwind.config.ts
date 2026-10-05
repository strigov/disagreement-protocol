import type { Config } from "tailwindcss";

// Дизайн-система «Бюро» (strigov-crm): источник истины — CSS-переменные в
// styles/globals.css, здесь только их семантические имена для утилит.
const config: Config = {
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./desktop/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "bg-elev": "var(--bg-elev)",
        "bg-sunk": "var(--bg-sunk)",
        "bg-hover": "var(--bg-hover)",
        "bg-active": "var(--bg-active)",
        ink: "var(--ink)",
        "ink-1": "var(--ink-1)",
        "ink-2": "var(--ink-2)",
        "ink-3": "var(--ink-3)",
        "line-c": "var(--line-c)",
        "line-strong": "var(--line-strong)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        "accent-ink": "var(--accent-ink)",
        warn: "var(--warn)",
        "warn-soft": "var(--warn-soft)",
        danger: "var(--danger)",
        "danger-soft": "var(--danger-soft)",
        ok: "var(--ok)",
        "ok-soft": "var(--ok-soft)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
      letterSpacing: { rubric: "0.12em" },
      borderRadius: {
        xs: "var(--r-xs)",
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
        pill: "var(--r-pill)",
      },
      boxShadow: { sm: "var(--shadow-sm)", md: "var(--shadow-md)" },
      borderColor: { DEFAULT: "var(--line-c)" },
      // Именованные размеры рабочей области протокола — вместо произвольных [..px].
      gridTemplateColumns: {
        workbench: "16.5rem minmax(0, 1fr)",
        "workbench-narrow": "13.5rem minmax(0, 1fr)",
      },
      minWidth: { "protocol-table": "55rem" },
      maxHeight: { "protocol-table": "70vh", "clause-list": "40rem", "clause-strip": "8.5rem" },
      width: { "row-menu": "15rem" },
    },
  },
  plugins: [],
};

export default config;
