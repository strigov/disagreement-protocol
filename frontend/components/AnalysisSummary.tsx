import { Notice } from "@/components/ui/Notice";
import type { AnalysisOut } from "@/lib/types";

export function AnalysisSummary({ analysis }: { analysis: AnalysisOut }) {
  const metrics = analysis.preflight_metrics;
  const diagnostics = analysis.preflight_diagnostics ?? [];
  return <div className="space-y-4">
    <Notice tone={diagnostics.length ? "warn" : "ok"}>
      {metrics ? <>Найдено правок: <strong>{metrics.revisions_total}</strong>. Только оформление: {metrics.format_only_count}.</> : "Документ обработан. Проверьте распознанные стороны."}
      {diagnostics.length > 0 && <> Замечаний к обработке: <strong>{diagnostics.length}</strong>.</>}
    </Notice>
    {diagnostics.length > 0 && (
      <Notice tone="warn" title="Обратите внимание">
        <ul className="mt-2 list-disc space-y-1 pl-4 marker:text-ink-2">{diagnostics.slice(0, 3).map((item, index) => <li key={index}>{item.message}</li>)}</ul>
        {diagnostics.length > 3 && <p className="mt-2">Остальные замечания — в подробностях обработки ниже.</p>}
      </Notice>
    )}
    <details className="rounded-md border border-line-c bg-bg-elev text-sm text-ink-1 shadow-sm">
      <summary className="cursor-pointer rounded-md px-4 py-3 font-medium text-ink transition-colors hover:bg-bg-hover focus-visible:-outline-offset-2">Подробности обработки документа</summary>
      <div className="space-y-4 border-t border-line-c px-4 py-4">
        {metrics ? <div className="space-y-1"><p>Правок всего: {metrics.revisions_total}</p><p>Изменений оформления: {metrics.format_only_count}</p><p>Абзацев с нумерацией: {metrics.paragraphs_with_numbering}</p><p>Уверенность нумерации: {(metrics.numbering_confidence_mean * 100).toFixed(0)}%</p></div> : <p>Метрики анализа для этого документа недоступны.</p>}
        {diagnostics.length > 0 && <ul className="space-y-3">{diagnostics.map((item, index) => <li key={index}><span className="block font-mono text-2xs text-ink-2">{item.component} · {item.code}</span><p className="mt-0.5">{item.message}</p></li>)}</ul>}
      </div>
    </details>
  </div>;
}
