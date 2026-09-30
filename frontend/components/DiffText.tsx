import { memo, useMemo } from "react";
import { diffWordsWithSpace } from "diff";

export const DiffText = memo(function DiffText({ before, after, side }: { before: string; after: string; side: "before" | "after" }) {
  // Bound comparison work even for abnormally long or unrelated clauses. The
  // fallback always shows the original text in full, never an approximate diff.
  const changes = useMemo(() => before.length + after.length > 100_000 ? undefined : diffWordsWithSpace(before, after, { timeout: 35, maxEditLength: 1500 }), [before, after]);
  if (!changes) return <>{side === "before" ? before : after}</>;
  return <>{changes.filter((part) => side === "before" ? !part.added : !part.removed).map((part, index) =>
    part.removed ? <del className="rounded-xs bg-danger-soft text-danger line-through decoration-danger" key={index}>{part.value}</del> : part.added ? <ins className="rounded-xs bg-ok-soft text-ok no-underline" key={index}>{part.value}</ins> : <span key={index}>{part.value}</span>,
  )}</>;
});
