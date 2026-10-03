import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/icons/Icon";
import { Button } from "./Button";

// Единые состояния блоков данных «Бюро»: loading (Skeleton), empty, error с повтором.
const CARD = "rounded-md border border-line-c bg-bg-elev p-6 shadow-sm";

export function EmptyState({ icon, text, cta, card = false, className }: {
  icon?: IconName; text: ReactNode; cta?: ReactNode; card?: boolean; className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-4 py-10 text-center", card && CARD, className)}>
      {icon && (
        <div className="mb-3 grid h-10 w-10 place-items-center rounded-pill bg-bg-sunk text-ink-2">
          <Icon name={icon} size={18} />
        </div>
      )}
      <div className="max-w-md text-sm leading-relaxed text-ink-2">{text}</div>
      {cta && <div className="mt-3">{cta}</div>}
    </div>
  );
}

export function ErrorState({
  title, titleLevel = 2, text = "Не удалось прочитать данные. Попробуйте ещё раз.",
  onRetry, retryLabel = "Повторить", actions, card = true, className,
}: {
  title?: ReactNode; titleLevel?: 1 | 2; text?: ReactNode;
  onRetry?: () => void; retryLabel?: string; actions?: ReactNode; card?: boolean; className?: string;
}) {
  const Heading = titleLevel === 1 ? "h1" : "h2";
  return (
    <div role="alert" className={cn("flex flex-col items-start gap-3", card && CARD, className)}>
      <div className="flex items-start gap-3">
        <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-pill bg-danger-soft text-danger">
          <Icon name="circle-alert" size={16} />
        </span>
        <div className="min-w-0">
          {title && (
            <Heading className={titleLevel === 1 ? "font-serif text-3xl font-semibold leading-tight text-ink" : "text-base font-medium text-ink"}>
              {title}
            </Heading>
          )}
          <p className="mt-1 text-sm leading-relaxed text-ink-1 wrap-anywhere">{text}</p>
        </div>
      </div>
      {(onRetry || actions) && (
        <div className="flex flex-wrap items-center gap-2 pl-11">
          {onRetry && <Button variant="ghost" size="sm" onClick={onRetry}><Icon name="history" />{retryLabel}</Button>}
          {actions}
        </div>
      )}
    </div>
  );
}
