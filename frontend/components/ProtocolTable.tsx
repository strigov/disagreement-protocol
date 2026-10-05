import {
  forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState,
  type KeyboardEvent,
} from "react";
import type { ProtocolForm, ProtocolRow, ValidationWarning } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { EmptyState } from "@/components/ui/States";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DiffText } from "./DiffText";
import { ClauseFilter } from "./protocol/ClauseFilter";
import { ClauseFocusView } from "./protocol/ClauseFocusView";
import { ClauseSidebar } from "./protocol/ClauseSidebar";
import { ProtocolGrid } from "./protocol/ProtocolGrid";
import { ProtocolToolbar } from "./protocol/ProtocolToolbar";
import { RowActions } from "./protocol/RowActions";
import type { ClauseFilterValue, EditableField, ProtocolColumn } from "./protocol/types";
import { needsAttention, rowFingerprint, warningsForRow } from "@/lib/review";

export type SaveState = "saved" | "dirty" | "saving" | "error";

interface ProtocolTableProps {
  rows: ProtocolRow[];
  draftingRole: string;
  counterpartyRole: string;
  form?: ProtocolForm;
  busy?: boolean;
  initialMode?: "focus" | "table";
  storageKey?: string;
  reviewContext?: string;
  warnings?: ValidationWarning[];
  onSaveStateChange?: (state: SaveState) => void;
  onPatch: (rowId: string, patch: Partial<ProtocolRow>) => Promise<void>;
  onDelete: (rowId: string) => Promise<void>;
  onMerge: (rowId: string, direction: "previous" | "next") => Promise<void>;
  onAddRow: () => Promise<void>;
  onSwapParties: () => Promise<void>;
}

export interface ProtocolTableHandle {
  saveAll: () => Promise<boolean>;
  revealRow: (id: string) => void;
}

type EditingCell = { rowId: string; field: EditableField } | null;
type DraftMap = Record<string, string>;
const cellKey = (rowId: string, field: EditableField) => `${rowId}:${field}`;
const withoutKey = <T,>(map: Record<string, T>, key: string): Record<string, T> => {
  const next = { ...map };
  delete next[key];
  return next;
};

// Контейнер держит всё состояние редактирования и сохранения; вынесенные
// компоненты в ./protocol получают готовые элементы ячеек и колбэки.
const ProtocolTable = forwardRef<ProtocolTableHandle, ProtocolTableProps>(function ProtocolTable({
  rows, draftingRole, counterpartyRole, form, busy = false,
  onPatch, onDelete, onMerge, onAddRow, onSwapParties,
  initialMode = "table", storageKey, reviewContext = "", warnings = [], onSaveStateChange,
}, ref) {
  const [mode, setMode] = useState(initialMode);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ClauseFilterValue>("all");
  const [showDiff, setShowDiff] = useState(true);
  const [reviewed, setReviewed] = useState<Record<string, string>>({});
  const [storageNotice, setStorageNotice] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<ProtocolRow | null>(null);
  const transition = useRef(false);
  const [switching, setSwitching] = useState(false);
  useEffect(() => {
    if (!storageKey) return;
    try {
      const stored: unknown = JSON.parse(window.localStorage.getItem(`protocol-review:${storageKey}`) || "{}");
      setReviewed(stored && typeof stored === "object" && !Array.isArray(stored)
        ? Object.fromEntries(Object.entries(stored).filter(([, value]) => typeof value === "string")) : {});
    } catch { setStorageNotice(true); }
  }, [storageKey]);
  const [editingCell, setEditingCell] = useState<EditingCell>(null);
  const [drafts, setDrafts] = useState<DraftMap>({});
  const [saving, setSaving] = useState<Record<string, true>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const saveState: SaveState = Object.keys(saving).length ? "saving" : Object.keys(errors).length ? "error" : Object.keys(drafts).length ? "dirty" : "saved";
  useEffect(() => { onSaveStateChange?.(saveState); }, [onSaveStateChange, saveState]);
  // Refs close the blur -> button-click window before React renders new state.
  const draftsRef = useRef<DraftMap>({});
  const pending = useRef(new Map<string, Promise<boolean>>());
  const cancelled = useRef(new Set<string>());
  const updateDrafts = useCallback((update: (current: DraftMap) => DraftMap) => {
    draftsRef.current = update(draftsRef.current);
    setDrafts(draftsRef.current);
  }, []);

  useEffect(() => {
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      if (Object.keys(draftsRef.current).length || pending.current.size) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, []);

  const commit = useCallback((rowId: string, field: EditableField, original: string, value: string): Promise<boolean> => {
    const key = cellKey(rowId, field);
    const existing = pending.current.get(key);
    if (existing) return existing;
    if (value === original) {
      setEditingCell((cell) => cell?.rowId === rowId && cell.field === field ? null : cell);
      updateDrafts((current) => withoutKey(current, key));
      setErrors((current) => withoutKey(current, key));
      return Promise.resolve(true);
    }
    updateDrafts((current) => ({ ...current, [key]: value }));
    setSaving((current) => ({ ...current, [key]: true }));
    setErrors((current) => withoutKey(current, key));
    const request = Promise.resolve().then(async () => {
      try {
        await onPatch(rowId, { [field]: value });
        updateDrafts((current) => withoutKey(current, key));
        setEditingCell((cell) => cell?.rowId === rowId && cell.field === field ? null : cell);
        return true;
      } catch (error) {
        setErrors((current) => ({ ...current, [key]: (error as Error).message || "Ошибка сохранения" }));
        setEditingCell({ rowId, field });
        return false;
      } finally {
        pending.current.delete(key);
        setSaving((current) => withoutKey(current, key));
      }
    });
    pending.current.set(key, request);
    return request;
  }, [onPatch, updateDrafts]);

  const saveAll = useCallback(async () => {
    // Await saves already started by blur; a failure must prevent navigation.
    if ((await Promise.all([...pending.current.values()])).some((ok) => !ok)) return false;
    for (const [key, value] of Object.entries(draftsRef.current)) {
      const [rowId, field] = key.split(":") as [string, EditableField];
      const row = rows.find((candidate) => candidate.id === rowId);
      if (!row || !await commit(rowId, field, row[field], value)) return false;
    }
    return true;
  }, [commit, rows]);
  useImperativeHandle(ref, () => ({ saveAll, revealRow: (id: string) => { setSelectedId(id); setQuery(""); setFilter("all"); } }), [saveAll]);

  const handleEditKey = (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>, multiline: boolean) => {
    if (event.key === "Escape") {
      event.preventDefault();
      const key = `${event.currentTarget.dataset.rowId}:${event.currentTarget.dataset.field}`;
      cancelled.current.add(key);
      updateDrafts((current) => withoutKey(current, key));
      setErrors((current) => withoutKey(current, key));
      setEditingCell(null);
    } else if (event.key === "Enter" && (!multiline || event.shiftKey || event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      event.currentTarget.blur();
    }
  };

  const rowHasPendingSave = (rowId: string) => [...pending.current.keys()].some((key) => key.startsWith(`${rowId}:`));

  // These helpers return elements directly, not freshly-created React component
  // types. The keyed <tr>/<td> and input DOM nodes survive each draft keystroke.
  const renderEditableText = (row: ProtocolRow, field: EditableField, label: string) => {
    const key = cellKey(row.id, field);
    const multiline = field !== "point_label";
    const isEditing = editingCell?.rowId === row.id && editingCell.field === field;
    const isSaving = !!saving[key];
    const error = errors[key];
    if (isEditing || key in drafts || error) {
      const value = drafts[key] ?? row[field];
      const common = {
        autoFocus: isEditing,
        value,
        "aria-label": label,
        "aria-invalid": error ? true : undefined,
        "data-row-id": row.id,
        "data-field": field,
        disabled: isSaving || busy,
        onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
          const next = event.currentTarget.value;
          updateDrafts((current) => ({ ...current, [key]: next }));
        },
        onBlur: (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
          if (!cancelled.current.has(key)) void commit(row.id, field, row[field], event.currentTarget.value);
        },
        onKeyDown: (event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => handleEditKey(event, multiline),
      };
      return (
        <div className="w-full space-y-1 font-sans text-sm font-normal leading-relaxed">
          {multiline
            ? <Textarea {...common} rows={Math.max(3, value.split("\n").length)} className="min-h-36" />
            : <Input {...common} className="max-w-xs" />}
          {isSaving && <span className="flex items-center gap-1.5 text-xs text-ink-2" role="status"><Icon name="loader-circle" className="motion-safe:animate-spin" />Сохраняем…</span>}
          {error && !isSaving && (
            <span className="block text-xs text-danger" role="alert">
              Не удалось сохранить: {error}. Enter (Ctrl+Enter для текста) — повтор, Esc — отмена.
            </span>
          )}
        </div>
      );
    }
    const blocked = busy || rowHasPendingSave(row.id);
    const activate = () => {
      if (blocked || rowHasPendingSave(row.id)) return;
      cancelled.current.delete(key);
      setEditingCell({ rowId: row.id, field });
    };
    return (
      <span
        role="textbox" tabIndex={0} aria-label={label} aria-disabled={blocked || undefined}
        title={blocked ? "Дождитесь сохранения изменений" : undefined}
        onClick={activate}
        onKeyDown={(event) => {
          if (["Enter", " ", "F2"].includes(event.key)) { event.preventDefault(); activate(); }
        }}
        className={cn(
          "block min-h-6 cursor-text whitespace-pre-wrap rounded-xs px-1 py-0.5 transition-colors wrap-anywhere hover:bg-bg-hover focus-visible:bg-bg-hover",
          field === "point_label" && "inline-block min-w-8",
          blocked && "cursor-wait opacity-60",
        )}
      >
        {row[field] ? (mode === "focus" && showDiff && (field === "party_1_text" || field === "party_2_text")
          ? <DiffText before={row.party_1_text} after={row.party_2_text} side={field === "party_1_text" ? "before" : "after"} />
          : row[field]) : <span className="text-ink-2">{field === "point_label" ? "Без номера" : "Нажмите, чтобы добавить текст"}</span>}
      </span>
    );
  };

  const columns: ProtocolColumn[] = [
    { field: "point_label", header: "Пункт договора", label: "Пункт договора" },
    { field: "party_1_text", header: `Редакция: ${counterpartyRole || "контрагент"}`, label: `Редакция ${counterpartyRole || "контрагента"}` },
    { field: "party_2_text", header: `Редакция: ${draftingRole || "наша сторона"}`, label: `Редакция ${draftingRole || "нашей стороны"}` },
    { field: "agreed_text", header: "Согласованная редакция", label: "Согласованная редакция" },
  ];
  if (form) {
    [form.point_title, form.original_title, form.proposed_title, form.agreed_title].forEach((title, index) => {
      columns[index].header = title;
      columns[index].label = title;
    });
  }
  const isReviewed = (row: ProtocolRow) => reviewed[row.id] === rowFingerprint(row, reviewContext);
  const isAttention = (row: ProtocolRow) => needsAttention(row, warnings);
  const reviewedCount = rows.filter(isReviewed).length;
  const counts: Record<ClauseFilterValue, number> = {
    all: rows.length,
    attention: rows.filter(isAttention).length,
    unreviewed: rows.length - reviewedCount,
  };
  const filtered = rows.filter((row) => {
    // A failed draft must remain reachable even if a search/filter changes.
    if (Object.keys(drafts).some((key) => key.startsWith(`${row.id}:`))) return true;
    return (filter === "all" || (filter === "attention" ? isAttention(row) : !isReviewed(row))) &&
      `${row.point_label} ${row.party_1_text} ${row.party_2_text} ${row.agreed_text}`.toLocaleLowerCase("ru").includes(query.toLocaleLowerCase("ru").trim());
  });
  const active = filtered.find((row) => row.id === selectedId) ?? filtered[0];
  const activeIndex = active ? filtered.indexOf(active) : -1;
  const changeView = async (action: () => void) => {
    if (busy || transition.current) return;
    transition.current = true;
    setSwitching(true);
    try { if (await saveAll()) { setEditingCell(null); action(); } }
    finally { transition.current = false; setSwitching(false); }
  };
  const setReviewMark = async (row: ProtocolRow, mark: boolean, after?: () => void) => {
    // Capture exactly the visible draft before flushing it. A later edit or a
    // side swap invalidates the mark because its content fingerprint changes.
    const snapshot = { ...row };
    for (const field of ["point_label", "party_1_text", "party_2_text", "agreed_text"] as const) {
      snapshot[field] = draftsRef.current[cellKey(row.id, field)] ?? row[field];
    }
    await changeView(() => {
      const next = { ...reviewed };
      if (mark) next[row.id] = rowFingerprint(snapshot, reviewContext);
      else delete next[row.id];
      setReviewed(next);
      if (storageKey) {
        try { window.localStorage.setItem(`protocol-review:${storageKey}`, JSON.stringify(next)); }
        catch { setStorageNotice(true); }
      }
      after?.();
    });
  };
  const toggleReviewed = (row: ProtocolRow) => setReviewMark(row, !isReviewed(row));
  const reviewAndNext = (row: ProtocolRow) => {
    const nextId = filtered[activeIndex + 1]?.id;
    return setReviewMark(row, true, () => { if (nextId) setSelectedId(nextId); });
  };
  const renderActions = (row: ProtocolRow) => (
    <RowActions
      disabled={busy || rowHasPendingSave(row.id)}
      onMergePrevious={() => { void onMerge(row.id, "previous"); }}
      onMergeNext={() => { void onMerge(row.id, "next"); }}
      onRequestDelete={() => setPendingDelete(row)}
    />
  );
  const search = (
    <label className="relative block">
      <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-2" />
      <Input aria-label="Поиск по пунктам" placeholder="Номер пункта или текст" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-8" />
    </label>
  );
  const clauseFilter = (layout: "stack" | "inline") => <ClauseFilter value={filter} counts={counts} layout={layout} onChange={setFilter} />;
  const empty = rows.length
    ? <EmptyState icon="search" text="Ничего не найдено." cta={<Button variant="ghost" size="sm" onClick={() => { setQuery(""); setFilter("all"); }}>Сбросить фильтры</Button>} />
    : <EmptyState icon="file-text" text={<>В протоколе пока нет строк.<br />Нажмите «Добавить строку», чтобы начать.</>} />;
  const navDisabled = busy || switching;
  return (
    <div aria-busy={busy || switching}>
      <ProtocolToolbar
        mode={mode} modeDisabled={navDisabled} actionsDisabled={busy}
        onModeChange={(next) => void changeView(() => setMode(next))}
        onAddRow={onAddRow} onSwapParties={onSwapParties}
      />
      {mode === "focus" ? (
        <div className="grid overflow-hidden rounded-lg border border-line-c bg-bg-elev shadow-sm md:grid-cols-workbench-narrow lg:grid-cols-workbench">
          <ClauseSidebar
            rows={filtered} totalCount={rows.length} activeId={active?.id} navDisabled={navDisabled}
            isReviewed={isReviewed} isAttention={isAttention}
            onSelect={(rowId) => void changeView(() => setSelectedId(rowId))}
            search={search} filter={clauseFilter("stack")} reviewedCount={reviewedCount} storageNotice={storageNotice}
          />
          {active ? (
            <ClauseFocusView
              row={active} position={activeIndex + 1} total={filtered.length} navDisabled={navDisabled}
              onPrevious={activeIndex > 0 ? () => void changeView(() => setSelectedId(filtered[activeIndex - 1].id)) : null}
              onNext={activeIndex < filtered.length - 1 ? () => void changeView(() => setSelectedId(filtered[activeIndex + 1].id)) : null}
              actions={renderActions(active)}
              attention={isAttention(active)} rowWarnings={warningsForRow(active, warnings)}
              showDiff={showDiff} onShowDiffChange={setShowDiff}
              counterpartyRole={form?.original_title ?? counterpartyRole} draftingRole={form?.proposed_title ?? draftingRole}
              pointLabel={columns[0].label} agreedLabel={columns[3].label}
              counterpartyLabel={columns[1].label} draftingLabel={columns[2].label}
              renderCell={renderEditableText}
              reviewed={isReviewed(active)} reviewDisabled={navDisabled || saveState !== "saved"}
              onToggleReviewed={() => void toggleReviewed(active)}
              onReviewAndNext={() => void reviewAndNext(active)}
              reviewAndNextDisabled={navDisabled || saveState !== "saved" || isReviewed(active)}
            />
          ) : <div className="grid place-items-center">{empty}</div>}
        </div>
      ) : (
        <ProtocolGrid
          rows={filtered} columns={columns} isAttention={isAttention}
          renderCell={renderEditableText} renderActions={renderActions}
          empty={empty} search={search} filter={clauseFilter("inline")}
        />
      )}
      {pendingDelete && (
        <ConfirmDialog
          title={`Исключить пункт ${pendingDelete.point_label || "без номера"} из протокола?`}
          description="Строка и все её редакции будут удалены из протокола. Отменить это действие нельзя."
          confirmLabel="Исключить"
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => { const id = pendingDelete.id; setPendingDelete(null); void onDelete(id); }}
        />
      )}
    </div>
  );
});

export default ProtocolTable;
