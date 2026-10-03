import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Icon } from "@/components/icons/Icon";
import { api } from "@/lib/api";
import { readRecentDocuments } from "@/lib/recent-documents";

const KEY = "disprot:last-document-route";
const DOCUMENT_ROUTE = /^\/documents\/([a-zA-Z0-9-]+)\/(analysis|parties|protocol|export)$/;

const STAGE_LABEL: Record<string, string> = {
  analysis: "Обработка документа",
  parties: "Стороны договора",
  protocol: "Проверка протокола",
  export: "Сохранение протокола",
};

function readLastDocument() {
  try {
    const href = localStorage.getItem(KEY);
    const match = href?.match(DOCUMENT_ROUTE);
    if (!href || !match) return null;
    const [, id, stage] = match;
    const title = readRecentDocuments().find((item) => item.id === id)?.title?.trim() || null;
    return { href, id, stage, title };
  } catch {
    return null;
  }
}

export function RememberDocument() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (DOCUMENT_ROUTE.test(pathname)) {
      try { localStorage.setItem(KEY, pathname); } catch { /* Storage may be unavailable. */ }
    }
  }, [pathname]);
  return null;
}

export function ResumeDocument() {
  const [document] = useState(readLastDocument);
  const [title, setTitle] = useState(document?.title ?? null);

  useEffect(() => {
    if (!document || document.title) return;
    let cancelled = false;
    // Older installations remember only the route. Resolve its title locally.
    api.getAnalysis(document.id).then((analysis) => {
      if (!cancelled) setTitle(analysis.contract_name?.trim() || null);
    }).catch(() => { /* A missing title must not block returning to the document. */ });
    return () => { cancelled = true; };
  }, [document]);

  if (!document) return null;
  const name = title || "Сохранённый договор";

  return (
    <Link
      to={document.href}
      aria-label={`Продолжить работу с договором «${name}»`}
      className="group flex items-center gap-4 rounded-lg border border-line-c bg-bg-elev p-4 transition-colors hover:border-line-strong hover:bg-bg-hover sm:px-5"
    >
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-bg-sunk text-ink-2 max-sm:hidden">
        <Icon name="file-text" size={20} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="rubric">Последний договор</span>
        <span className="font-serif text-xl font-semibold leading-snug text-ink wrap-anywhere">{name}</span>
        <span className="text-xs text-ink-2">Этап: {STAGE_LABEL[document.stage]}</span>
      </span>
      <span className="flex shrink-0 items-center gap-2 text-sm font-medium text-ink-1 group-hover:text-ink">
        Продолжить <Icon name="arrow-right" size={16} />
      </span>
    </Link>
  );
}
