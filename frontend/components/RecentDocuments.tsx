"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { fmtDateTime } from "@/lib/format";
import { forgetDocument, readRecentDocuments, type RecentDocument, type RecentStage } from "@/lib/recent-documents";

const STAGE_LABEL: Record<RecentStage, string> = {
  analysis: "Обработка",
  parties: "Стороны",
  protocol: "Протокол",
};

const UNTITLED = "Документ без названия";

// Список живёт в localStorage этого браузера: backend не отдаёт список документов.
// До монтирования (SSR и первый render клиента) хранилище недоступно — рендерим ничего,
// чтобы разметка совпала при гидрации.
export function RecentDocuments() {
  const [items, setItems] = useState<RecentDocument[]>([]);

  useEffect(() => {
    setItems(readRecentDocuments());
  }, []);

  if (items.length === 0) return null;

  const forget = (id: string) => {
    forgetDocument(id);
    setItems(readRecentDocuments());
  };

  return (
    <section aria-labelledby="recent-documents-title" className="mt-14">
      <h2 id="recent-documents-title" className="font-serif text-xl font-semibold text-ink">Недавние документы</h2>
      <ul className="mt-4 overflow-hidden rounded-md border border-line-c bg-bg-elev shadow-sm">
        {items.map((item) => {
          const title = item.title ?? UNTITLED;
          return (
            <li key={item.id} className="flex items-center border-b border-dashed border-line-c last:border-b-0">
              <Link
                href={`/documents/${item.id}/analysis`}
                className="flex min-w-0 flex-1 flex-col gap-1 px-4 py-3.5 transition-colors hover:bg-bg-hover focus-visible:-outline-offset-2 sm:flex-row sm:items-center sm:justify-between sm:gap-6"
              >
                <span className="min-w-0 font-serif text-lg font-semibold leading-snug text-ink wrap-anywhere">{title}</span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="rubric">{STAGE_LABEL[item.stage]}</span>
                  <span className="font-mono text-xs text-ink-2">{fmtDateTime(item.openedAt)}</span>
                </span>
              </Link>
              <IconButton
                icon="x"
                size="sm"
                label={`Убрать «${title}» из списка`}
                onClick={() => forget(item.id)}
                className="mx-2 focus-visible:-outline-offset-2"
              />
            </li>
          );
        })}
      </ul>
    </section>
  );
}
