// Недавние документы этого браузера: единственный способ вернуться к договору
// после закрытия вкладки (backend не отдаёт список). Название договора не
// покидает браузер — та же граница доверия, что у отметок `protocol-review:*`.
export type RecentStage = "analysis" | "parties" | "protocol";

export interface RecentDocument {
  id: string;
  title: string | null;
  stage: RecentStage;
  openedAt: number;
}

export const RECENT_DOCUMENTS_KEY = "disprot.recent-documents";
export const RECENT_DOCUMENTS_LIMIT = 8;

const STAGES: readonly RecentStage[] = ["analysis", "parties", "protocol"];

const isRecentDocument = (value: unknown): value is RecentDocument => {
  if (typeof value !== "object" || value === null) return false;
  const entry = value as Record<string, unknown>;
  return typeof entry.id === "string" && entry.id !== ""
    && (entry.title === null || typeof entry.title === "string")
    && STAGES.includes(entry.stage as RecentStage)
    && typeof entry.openedAt === "number" && Number.isFinite(entry.openedAt);
};

export function readRecentDocuments(): RecentDocument[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(RECENT_DOCUMENTS_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isRecentDocument).sort((a, b) => b.openedAt - a.openedAt);
  } catch {
    return [];
  }
}

const write = (entries: RecentDocument[]) => {
  try {
    window.localStorage.setItem(RECENT_DOCUMENTS_KEY, JSON.stringify(entries));
  } catch {
    /* хранилище недоступно — список просто не обновится */
  }
};

export function rememberDocument(entry: { id: string; title?: string | null; stage: RecentStage }, now?: number): void {
  const current = readRecentDocuments();
  const previous = current.find((item) => item.id === entry.id);
  const title = entry.title?.trim() ? entry.title.trim() : previous?.title ?? null;
  const next: RecentDocument = { id: entry.id, title, stage: entry.stage, openedAt: now ?? Date.now() };
  write([next, ...current.filter((item) => item.id !== entry.id)]
    .sort((a, b) => b.openedAt - a.openedAt)
    .slice(0, RECENT_DOCUMENTS_LIMIT));
}

export function forgetDocument(id: string): void {
  write(readRecentDocuments().filter((item) => item.id !== id));
}
