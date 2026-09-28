import { memo, useMemo } from "react";
import { diffWordsWithSpace } from "diff";

export const DiffText = memo(function DiffText({ before, after, side }: { before: string; after: string; side: "before" | "after" }) {
  // Bound comparison work even for abnormally long or unrelated clauses. The
  // fallback always shows the original text in full, never an approximate diff.
  const changes = useMemo(() => before.length + after.length > 100_000 ? undefined : diffWordsWithSpace(before, after, { timeout: 35, maxEditLength: 1500 }), [before, after]);
  if (!changes) return <>{side === "before" ? before : after}</>;
  return <>{changes.filter((part) => side === "before" ? !part.added : !part.removed).map((part, index) =>
    part.removed ? <del className="diff-removed" key={index}>{part.value}</del> : part.added ? <ins className="diff-added" key={index}>{part.value}</ins> : <span key={index}>{part.value}</span>,
  )}</>;
});
