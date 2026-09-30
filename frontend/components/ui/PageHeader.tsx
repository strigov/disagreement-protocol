import type { ReactNode } from "react";

/** Редакторская шапка страницы «Бюро»: моно-рубрика, serif-заголовок, описание, мета, действия. */
export function PageHeader({ rubric, title, description, meta, actions }: {
  rubric?: ReactNode; title: ReactNode; description?: ReactNode; meta?: ReactNode; actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-8">
      <div className="min-w-0">
        {rubric && <p className="rubric mb-3">{rubric}</p>}
        <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight text-ink md:text-5xl">{title}</h1>
        {description && <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-2">{description}</p>}
        {meta && <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-ink-2">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
