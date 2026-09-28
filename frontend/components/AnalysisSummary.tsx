import { CircleCheck, TriangleAlert } from "lucide-react";
import type { AnalysisOut } from "@/lib/types";

export function AnalysisSummary({ analysis }: { analysis: AnalysisOut }) {
  const metrics = analysis.preflight_metrics;
  const diagnostics = analysis.preflight_diagnostics ?? [];
  return <div className="mt-6">
    <div className={`coverage-strip ${diagnostics.length ? "has-warnings" : ""}`}>
      {diagnostics.length ? <TriangleAlert size={16} className="shrink-0" /> : <CircleCheck size={16} className="shrink-0 text-emerald-600" />}
      <span>{metrics ? <>Найдено правок: <strong>{metrics.revisions_total}</strong>. Только оформление: {metrics.format_only_count}.</> : "Документ обработан. Проверьте распознанные стороны."}
        {diagnostics.length > 0 && <> Замечаний к обработке: <strong>{diagnostics.length}</strong>.</>}</span>
    </div>
    {diagnostics.length > 0 && <div className="notice"><strong>Обратите внимание</strong><ul className="list-disc pl-4 mt-2 space-y-1">{diagnostics.slice(0, 3).map((item, index) => <li key={index}>{item.message}</li>)}</ul>{diagnostics.length > 3 && <p className="mt-2">Остальные замечания — в подробностях обработки ниже.</p>}</div>}
    <details className="disclosure">
      <summary>Подробности обработки документа</summary>
      {metrics ? <div className="space-y-1 mb-4"><p>Правок всего: {metrics.revisions_total}</p><p>Изменений оформления: {metrics.format_only_count}</p><p>Абзацев с нумерацией: {metrics.paragraphs_with_numbering}</p><p>Уверенность нумерации: {(metrics.numbering_confidence_mean * 100).toFixed(0)}%</p></div> : <p>Метрики анализа для этого документа недоступны.</p>}
      <ul className="space-y-2">{diagnostics.map((item, index) => <li key={index}><span className="font-mono text-[10px]">{item.component} · {item.code}</span><p>{item.message}</p></li>)}</ul>
    </details>
  </div>;
}
