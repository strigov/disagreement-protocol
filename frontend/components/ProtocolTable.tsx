"use client";

import {
  forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState,
  type KeyboardEvent,
} from "react";
import type { ProtocolRow, ValidationWarning } from "@/lib/types";
import { AlignLeft, Table2, Search, Plus, ArrowLeftRight, ChevronLeft, ChevronRight, MoreHorizontal, Check, TriangleAlert } from "lucide-react";
import { DiffText } from "./DiffText";
import { needsAttention, rowFingerprint, warningsForRow } from "@/lib/review";

export type SaveState = "saved" | "dirty" | "saving" | "error";

interface ProtocolTableProps {
  rows: ProtocolRow[];
  draftingRole: string;
  counterpartyRole: string;
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

type EditableField = "point_label" | "party_1_text" | "party_2_text" | "agreed_text";
type EditingCell = { rowId: string; field: EditableField } | null;
type DraftMap = Record<string, string>;
const cellKey = (rowId: string, field: EditableField) => `${rowId}:${field}`;
const withoutKey = <T,>(map: Record<string, T>, key: string): Record<string, T> => {
  const next = { ...map };
  delete next[key];
  return next;
};

const ProtocolTable = forwardRef<ProtocolTableHandle, ProtocolTableProps>(function ProtocolTable({
  rows, draftingRole, counterpartyRole, busy = false,
  onPatch, onDelete, onMerge, onAddRow, onSwapParties,
  initialMode = "table", storageKey, reviewContext = "", warnings = [], onSaveStateChange,
}, ref) {
  const [mode, setMode] = useState(initialMode);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [showDiff, setShowDiff] = useState(true);
  const [reviewed, setReviewed] = useState<Record<string, string>>({});
  const [storageNotice, setStorageNotice] = useState(false);
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
        className: `edit-input ${error ? "border-red-400" : ""}`,
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
        <div className="space-y-1">
          {multiline ? <textarea {...common} rows={Math.max(2, value.split("\n").length)} /> : <input {...common} />}
          {isSaving && <span className="text-xs text-gray-500" role="status">Сохраняем…</span>}
          {error && !isSaving && (
            <span className="text-xs text-red-600" role="alert">
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
        className={`editable ${blocked ? "cursor-wait opacity-60" : ""}`}
      >
        {row[field] ? (mode === "focus" && showDiff && (field === "party_1_text" || field === "party_2_text")
          ? <DiffText before={row.party_1_text} after={row.party_2_text} side={field === "party_1_text" ? "before" : "after"} />
          : row[field]) : <span className="text-slate-400">{field === "point_label" ? "Без номера" : "Нажмите, чтобы добавить текст"}</span>}
      </span>
    );
  };

  const columns: { field: EditableField; header: string; label: string }[] = [
    { field: "point_label", header: "Пункт договора", label: "Пункт договора" },
    { field: "party_1_text", header: `Редакция: ${counterpartyRole || "контрагент"}`, label: `Редакция ${counterpartyRole || "контрагента"}` },
    { field: "party_2_text", header: `Редакция: ${draftingRole || "наша сторона"}`, label: `Редакция ${draftingRole || "нашей стороны"}` },
    { field: "agreed_text", header: "Согласованная редакция", label: "Согласованная редакция" },
  ];
  const isReviewed = (row: ProtocolRow) => reviewed[row.id] === rowFingerprint(row, reviewContext);
  const reviewedCount = rows.filter(isReviewed).length;
  const filtered = rows.filter((row) => {
    // A failed draft must remain reachable even if a search/filter changes.
    if (Object.keys(drafts).some((key) => key.startsWith(`${row.id}:`))) return true;
    return (filter === "all" || (filter === "attention" ? needsAttention(row, warnings) : !isReviewed(row))) &&
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
  const toggleReviewed = async (row: ProtocolRow) => {
    // Capture exactly the visible draft before flushing it. A later edit or a
    // side swap invalidates the mark because its content fingerprint changes.
    const snapshot = { ...row };
    for (const field of ["point_label", "party_1_text", "party_2_text", "agreed_text"] as const) {
      snapshot[field] = draftsRef.current[cellKey(row.id, field)] ?? row[field];
    }
    await changeView(() => {
      const next = { ...reviewed };
      if (isReviewed(row)) delete next[row.id];
      else next[row.id] = rowFingerprint(snapshot, reviewContext);
      setReviewed(next);
      if (storageKey) {
        try { window.localStorage.setItem(`protocol-review:${storageKey}`, JSON.stringify(next)); }
        catch { setStorageNotice(true); }
      }
    });
  };
  const renderActions = (row: ProtocolRow) => {
    const blocked = busy || rowHasPendingSave(row.id);
    return <details className="row-actions">
      <summary className="icon-button" aria-label="Действия со строкой"><MoreHorizontal size={16} /></summary>
      <div className="row-menu">
        <button type="button" disabled={blocked} onClick={() => onMerge(row.id, "previous")}>Объединить с предыдущей</button>
        <button type="button" disabled={blocked} onClick={() => onMerge(row.id, "next")}>Объединить со следующей</button>
        <button type="button" disabled={blocked} onClick={() => onDelete(row.id)} className="text-red-600">Исключить из протокола</button>
      </div>
    </details>;
  };
  const search = <label className="search-field"><Search size={14} /><input aria-label="Поиск по пунктам" placeholder="Номер пункта или текст" value={query} onChange={(e) => setQuery(e.target.value)} /></label>;
  const filters = <select className="filter-select" aria-label="Фильтр пунктов" value={filter} onChange={(e) => setFilter(e.target.value)}>
    <option value="all">Все пункты</option><option value="attention">Требуют внимания</option><option value="unreviewed">Не проверены мной</option>
  </select>;
  const empty = <div className="empty-state">{rows.length ? <>Ничего не найдено.<br /><button className="btn btn-quiet mt-2" onClick={() => { setQuery(""); setFilter("all"); }}>Сбросить фильтры</button></> : <>В протоколе пока нет строк.<br />Нажмите «Добавить строку», чтобы начать.</>}</div>;
  const rowWarnings = active ? warningsForRow(active, warnings) : [];
  return (
    <div aria-busy={busy || switching}>
      <div className="editor-toolbar">
        <div className="segmented" role="group" aria-label="Вид протокола">
          <button type="button" disabled={busy || switching} aria-pressed={mode === "focus"} onClick={() => void changeView(() => setMode("focus"))}><AlignLeft size={14} /> По пунктам</button>
          <button type="button" disabled={busy || switching} aria-pressed={mode === "table"} onClick={() => void changeView(() => setMode("table"))}><Table2 size={14} /> Таблица</button>
        </div>
        <div className="toolbar-actions">
          <button type="button" disabled={busy} onClick={onAddRow} className="btn btn-secondary"><Plus size={14} /> Добавить строку</button>
          <button type="button" disabled={busy} onClick={onSwapParties} className="btn btn-quiet"><ArrowLeftRight size={14} /> Поменять стороны</button>
        </div>
      </div>
      {mode === "focus" ? <div className="editor-workbench">
        <aside className="clause-sidebar" aria-label="Навигация по пунктам">
          <div className="sidebar-top"><div className="sidebar-title">Пункты договора <span className="count">{rows.length}</span></div>{search}{filters}</div>
          <nav className="clause-list" aria-label="Пункты договора">
            {filtered.map((row) => <button key={row.id} className="clause-nav-item" aria-current={row.id === active?.id} disabled={busy || switching}
              onClick={() => void changeView(() => setSelectedId(row.id))} aria-label={`Открыть пункт ${row.point_label || "без номера"}`}>
              <span className="clause-nav-top"><span>Пункт {row.point_label || "без номера"}</span>{isReviewed(row) ? <Check size={13} className="text-emerald-600" aria-label="Проверен вами" /> : needsAttention(row, warnings) ? <TriangleAlert size={13} className="text-amber-600" aria-label="Требует внимания" /> : null}</span>
              <span className="clause-preview">{row.party_2_text || row.party_1_text || "Новая строка протокола"}</span>
            </button>)}
          </nav>
          <div className="review-progress"><span>Проверено вами: {reviewedCount} из {rows.length}</span><progress value={reviewedCount} max={Math.max(1, rows.length)} aria-label="Прогресс вашей проверки" /><p>{storageNotice ? "Отметки доступны только до закрытия страницы." : "Отметки сохраняются в этом браузере."}</p></div>
        </aside>
        {active ? <section className="clause-content" aria-label="Выбранный пункт">
          <header className="clause-heading">
            <div><h2>Пункт {renderEditableText(active, "point_label", "Пункт договора")}</h2><p>{activeIndex + 1} из {filtered.length} · {active.user_edited ? "Отредактирован вручную" : "Сформирован из правок договора"}</p></div>
            <div className="flex items-center gap-2">
              <button className="icon-button" aria-label="Предыдущий пункт" disabled={busy || switching || activeIndex <= 0} onClick={() => void changeView(() => setSelectedId(filtered[activeIndex - 1].id))}><ChevronLeft size={16} /></button>
              <button className="icon-button" aria-label="Следующий пункт" disabled={busy || switching || activeIndex >= filtered.length - 1} onClick={() => void changeView(() => setSelectedId(filtered[activeIndex + 1].id))}><ChevronRight size={16} /></button>
              {renderActions(active)}
            </div>
          </header>
          <div className="clause-body">
            {needsAttention(active, warnings) && <div className="notice mb-5"><strong>Проверьте этот пункт</strong>{rowWarnings.length ? <ul className="mt-1 space-y-1">{rowWarnings.map((warning, index) => <li key={index}>{warning.message}</li>)}</ul> : <p>Сверьте номер и содержание с исходным договором.</p>}</div>}
            <div className="comparison-label">Редакции сторон<label className="diff-toggle"><input type="checkbox" checked={showDiff} onChange={(e) => setShowDiff(e.target.checked)} /> Подсветить различия</label></div>
            <div className="comparison-grid">
              <section className="comparison-pane"><div className="comparison-pane-header"><span>Контрагент</span><h3>{counterpartyRole || "Редакция контрагента"}</h3></div><div className="comparison-text">{renderEditableText(active, "party_1_text", columns[1].label)}</div></section>
              <section className="comparison-pane ours"><div className="comparison-pane-header"><span>Наша сторона</span><h3>{draftingRole || "Наша редакция"}</h3></div><div className="comparison-text">{renderEditableText(active, "party_2_text", columns[2].label)}</div></section>
            </div>
            <div className="agreed-section"><div className="agreed-heading"><h3>Согласованная редакция</h3><span>Войдёт в итоговый протокол</span></div><div className="agreed-text">{renderEditableText(active, "agreed_text", "Согласованная редакция")}</div><p className="edit-hint">Нажмите на текст для редактирования. Ctrl / ⌘ + Enter — сохранить, Esc — отменить.</p></div>
          </div>
          <footer className="clause-footer">
            <label className="review-check"><input type="checkbox" checked={isReviewed(active)} disabled={busy || switching || saveState !== "saved"} onChange={() => void toggleReviewed(active)} /> Проверено мной</label>
            <button className="btn btn-secondary" disabled={busy || switching || activeIndex >= filtered.length - 1} onClick={() => void changeView(() => setSelectedId(filtered[activeIndex + 1].id))}>Следующий пункт <ChevronRight size={14} /></button>
          </footer>
        </section> : empty}
      </div> : <>
        <div className="table-search">{search}{filters}</div>
        <div className="protocol-table-wrap">
          <table className="protocol-table">
            <thead><tr>{columns.map((column) => <th key={column.field} scope="col">{column.header}</th>)}<th scope="col"><span className="sr-only">Действия</span></th></tr></thead>
            <tbody>{filtered.length === 0 ? <tr><td colSpan={5}>{empty}</td></tr> : filtered.map((row) => <tr key={row.id} className={needsAttention(row, warnings) ? "needs-attention" : ""}>
              {columns.map((column) => <td key={column.field}>{renderEditableText(row, column.field, column.label)}{column.field === "point_label" && row.confidence < 0.85 && <span className="inline-flex text-amber-600 mt-2" aria-label={`Низкая уверенность: ${(row.confidence * 100).toFixed(0)}%`}><TriangleAlert size={13} /></span>}</td>)}
              <td>{renderActions(row)}</td>
            </tr>)}</tbody>
          </table>
        </div>
        <p className="edit-hint">Нажмите на ячейку для редактирования. Изменения сохраняются при выходе из ячейки.</p>
      </>}
    </div>
  );
});

export default ProtocolTable;
