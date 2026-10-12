import Link from "@/lib/navigation";
import { useState, type ReactNode } from "react";
import { ExportSettingsDialog } from "@/components/ExportSettingsDialog";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

interface Props {
  children: ReactNode;
  step?: 1 | 2 | 3;
  documentId?: string;
  wide?: boolean;
  onNavigate?: (href: string) => void;
}

const STEPS = ["Документ", "Стороны", "Проверка протокола"] as const;

export function WorkspaceShell({ children, step = 1, documentId, wide, onNavigate }: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const navigate = (href: string, content: ReactNode, className?: string) => onNavigate
    ? <button type="button" className={className} onClick={() => onNavigate(href)}>{content}</button>
    : <Link className={className} href={href}>{content}</Link>;
  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="border-b border-line-c bg-bg-elev">
        <div className="mx-auto flex min-h-20 max-w-screen-2xl items-center justify-between gap-3 px-4 py-3 md:gap-4 md:px-9">
          {navigate("/", <>
            <span className="font-serif text-xl font-semibold leading-tight text-ink sm:text-2xl">Strigov: Протокол разногласий</span>
            <span className="font-serif text-sm leading-tight text-ink-2">{"It's just Strigov's"}</span>
          </>, "-mx-2 flex min-w-0 flex-col items-start gap-0.5 rounded-sm px-2 py-1 text-left transition-colors hover:bg-bg-hover")}
          <div className="flex shrink-0 items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => setSettingsOpen(true)}>Настройки</Button>
            <ThemeToggle />
          </div>
        </div>
        <nav aria-label="Этапы работы" className="border-t border-line-c">
          <ol className="mx-auto flex h-12 max-w-screen-2xl items-center gap-1 overflow-x-auto px-4 md:justify-center md:gap-3 md:px-9">
            {STEPS.map((label, index) => {
              const number = index + 1;
              const current = number === step;
              const complete = number < step;
              const href = number === 1 ? "/" : `/documents/${documentId}/parties`;
              const content = <>
                <span className={cn(
                  "grid h-6 w-6 shrink-0 place-items-center rounded-pill font-mono text-2xs",
                  current && "bg-accent text-accent-ink",
                  complete && "bg-ok-soft text-ok",
                  !current && !complete && "border border-line-strong text-ink-2",
                )}>
                  {complete ? <Icon name="check" size={12} /> : `0${number}`}
                </span>
                <span className={cn(!current && "max-sm:sr-only")}>{label}</span>
              </>;
              return (
                <li key={label} className="flex shrink-0 items-center gap-1 md:gap-3" aria-current={current ? "step" : undefined}>
                  {complete
                    ? navigate(href, content, "flex items-center gap-2 rounded-sm px-2 py-1 text-xs text-ink-1 transition-colors hover:bg-bg-hover hover:text-ink")
                    : <span className={cn("flex items-center gap-2 px-2 py-1 text-xs", current ? "font-medium text-ink" : "text-ink-2")}>{content}</span>}
                  {number < STEPS.length && <Icon name="chevron-right" size={12} className="text-ink-3" />}
                </li>
              );
            })}
          </ol>
        </nav>
      </header>
      <main id="main-content" className={cn("w-full flex-1", wide
        ? "mx-auto max-w-screen-2xl px-4 py-6 md:px-9 md:py-8"
        : "mx-auto max-w-4xl px-4 py-10 md:px-8 md:py-14")}>
        {children}
      </main>
      {settingsOpen && <ExportSettingsDialog onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
