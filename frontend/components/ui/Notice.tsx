import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/icons/Icon";

export type NoticeTone = "neutral" | "warn" | "danger" | "ok";

const TONES: Record<NoticeTone, { box: string; icon: IconName; iconClass: string; text: string }> = {
  neutral: { box: "bg-bg-sunk", icon: "info", iconClass: "text-ink-2", text: "text-ink-1" },
  warn: { box: "bg-warn-soft", icon: "triangle-alert", iconClass: "text-warn", text: "text-ink" },
  danger: { box: "bg-danger-soft", icon: "circle-alert", iconClass: "text-danger", text: "text-danger" },
  ok: { box: "bg-ok-soft", icon: "circle-check", iconClass: "text-ok", text: "text-ink" },
};

export function Notice({ tone = "neutral", title, children, role, id, className }: {
  tone?: NoticeTone; title?: ReactNode; children?: ReactNode;
  role?: "alert" | "status"; id?: string; className?: string;
}) {
  const t = TONES[tone];
  return (
    <div role={role} id={id} className={cn("flex gap-2.5 rounded-md border border-line-c p-3 text-sm leading-relaxed", t.box, t.text, className)}>
      <Icon name={t.icon} size={16} className={cn("mt-0.5", t.iconClass)} />
      <div className="min-w-0 flex-1 wrap-anywhere">
        {title && <p className="font-medium">{title}</p>}
        {children}
      </div>
    </div>
  );
}
