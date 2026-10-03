import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

const KEY = "disprot:last-document-route";
const DOCUMENT_ROUTE = /^\/documents\/[a-zA-Z0-9-]+\/(analysis|parties|protocol|export)$/;

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
  let href: string | null = null;
  try { href = localStorage.getItem(KEY); } catch { /* The upload flow remains available. */ }
  return href && DOCUMENT_ROUTE.test(href) ? (
    <div className="mx-auto max-w-6xl px-6 pt-6">
      <Link className="inline-flex rounded-sm border border-line-c bg-bg-elev px-4 py-2 text-ink hover:bg-bg-hover" to={href}>Продолжить работу с последним договором</Link>
    </div>
  ) : null;
}
