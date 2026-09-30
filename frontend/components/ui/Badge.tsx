import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "ok" | "warn" | "danger" | "accent";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-bg-sunk text-ink-2 border-line-c",
  ok: "bg-ok-soft text-ok border-line-c",
  warn: "bg-warn-soft text-ink-1 border-line-c",
  danger: "bg-danger-soft text-danger border-line-c",
  accent: "bg-accent-soft text-ink-1 border-line-c",
};

export function Badge({ tone = "neutral", className, ...rest }: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      {...rest}
      className={cn("inline-flex items-center rounded-pill border px-2 py-0.5 text-xs font-medium", TONES[tone], className)}
    />
  );
}
