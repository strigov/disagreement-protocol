"use client";

import Link from "next/link";
import { Check, FileText, LockKeyhole, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  step?: 1 | 2 | 3;
  documentId?: string;
  wide?: boolean;
  onNavigate?: (href: string) => void;
}

export function WorkspaceShell({ children, step = 1, documentId, wide, onNavigate }: Props) {
  const navigate = (href: string, content: ReactNode, className?: string) => onNavigate
    ? <button type="button" className={className} onClick={() => onNavigate(href)}>{content}</button>
    : <Link className={className} href={href}>{content}</Link>;
  return (
    <div className="app-shell">
      <header className="app-header">
        {navigate("/", <><span className="brand-mark"><FileText size={19} strokeWidth={1.7} /></span><span>Протокол<span className="brand-subtitle">Работа с разногласиями</span></span></>, "brand")}
        <span className="local-badge"><LockKeyhole size={13} /> Документы остаются на вашем компьютере</span>
      </header>
      <nav className="workflow" aria-label="Этапы работы">
        {(["Документ", "Стороны", "Проверка протокола"] as const).map((label, index) => {
          const number = index + 1;
          const content = <><span className="step-number">{number < step ? <Check size={13} /> : `0${number}`}</span>{label}</>;
          const href = number === 1 ? "/" : `/documents/${documentId}/parties`;
          return <div className={`workflow-step ${number === step ? "current" : ""} ${number < step ? "complete" : ""}`} key={label} aria-current={number === step ? "step" : undefined}>
            {number < step ? navigate(href, content, "step-link") : <span className="step-link">{content}</span>}
            {number < 3 && <ChevronRight className="step-chevron" size={14} />}
          </div>;
        })}
      </nav>
      <main id="main-content" className={wide ? "workspace workspace-wide" : "workspace"}>{children}</main>
    </div>
  );
}
