"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useCallback, useState, type KeyboardEvent } from "react";
import type { ProtocolRow } from "@/lib/types";

interface ProtocolTableProps {
  rows: ProtocolRow[];
  draftingRole: string;
  counterpartyRole: string;
  onPatch: (rowId: string, patch: Partial<ProtocolRow>) => Promise<void>;
  onDelete: (rowId: string) => Promise<void>;
  onMerge: (rowId: string, direction: "previous" | "next") => Promise<void>;
  onAddRow: () => Promise<void>;
  onSwapParties: () => Promise<void>;
}

type EditingCell = { rowId: string; field: keyof ProtocolRow } | null;
// Per-cell draft state. Lives outside `editingCell` so that a failed save can
// keep the user's typed value visible (and the cell in edit mode) until the
// retry succeeds — preventing data loss when PATCH errors mid-blur.
type DraftMap = Record<string, string>; // key = `${rowId}:${field}`
type SavingMap = Record<string, true>; // key = `${rowId}:${field}`
type ErrorMap = Record<string, string>; // key = `${rowId}:${field}`

const columnHelper = createColumnHelper<ProtocolRow>();

const editableInputClass =
  "w-full rounded-sm border border-blue-400 bg-white px-1 py-0.5 outline-none focus:ring-2 focus:ring-blue-300";
const editableInputErrorClass =
  "w-full rounded-sm border border-red-500 bg-white px-1 py-0.5 outline-none focus:ring-2 focus:ring-red-300";
const editableTextareaClass =
  "w-full min-h-[3rem] rounded-sm border border-blue-400 bg-white px-1 py-0.5 outline-none resize-y focus:ring-2 focus:ring-blue-300";
const editableTextareaErrorClass =
  "w-full min-h-[3rem] rounded-sm border border-red-500 bg-white px-1 py-0.5 outline-none resize-y focus:ring-2 focus:ring-red-300";
const cellViewClass =
  "block min-h-[1.5rem] cursor-text rounded-sm px-1 py-0.5 hover:bg-blue-50 focus:bg-blue-50 focus:outline focus:outline-2 focus:outline-blue-300";

const cellKey = (rowId: string, field: keyof ProtocolRow) => `${rowId}:${String(field)}`;

export default function ProtocolTable({
  rows,
  draftingRole,
  counterpartyRole,
  onPatch,
  onDelete,
  onMerge,
  onAddRow,
  onSwapParties,
}: ProtocolTableProps) {
  const [editingCell, setEditingCell] = useState<EditingCell>(null);
  const [drafts, setDrafts] = useState<DraftMap>({});
  const [saving, setSaving] = useState<SavingMap>({});
  const [errors, setErrors] = useState<ErrorMap>({});

  const rowHasPendingSave = useCallback(
    (rowId: string) => Object.keys(saving).some((k) => k.startsWith(`${rowId}:`)),
    [saving],
  );

  const commit = useCallback(
    async (rowId: string, field: keyof ProtocolRow, originalValue: string, newValue: string) => {
      const key = cellKey(rowId, field);
      if (newValue === originalValue) {
        // No-op: don't mark user_edited. Exit edit mode and clear any draft/error.
        setEditingCell((cur) =>
          cur && cur.rowId === rowId && cur.field === field ? null : cur,
        );
        setDrafts((d) => {
          if (!(key in d)) return d;
          const { [key]: _drop, ...rest } = d;
          return rest;
        });
        setErrors((e) => {
          if (!(key in e)) return e;
          const { [key]: _drop, ...rest } = e;
          return rest;
        });
        return;
      }
      // Hold draft, mark saving, keep cell in edit mode until PATCH resolves.
      setDrafts((d) => ({ ...d, [key]: newValue }));
      setSaving((s) => ({ ...s, [key]: true }));
      setErrors((e) => {
        if (!(key in e)) return e;
        const { [key]: _drop, ...rest } = e;
        return rest;
      });
      try {
        await onPatch(rowId, { [field]: newValue } as Partial<ProtocolRow>);
        // Success: exit edit mode, drop draft.
        setEditingCell((cur) =>
          cur && cur.rowId === rowId && cur.field === field ? null : cur,
        );
        setDrafts((d) => {
          const { [key]: _drop, ...rest } = d;
          return rest;
        });
      } catch (err) {
        // Failure: keep draft + edit mode so the user can retry without losing text.
        setErrors((e) => ({
          ...e,
          [key]: (err as Error)?.message ?? "Не удалось сохранить",
        }));
        setEditingCell({ rowId, field });
      } finally {
        setSaving((s) => {
          const { [key]: _drop, ...rest } = s;
          return rest;
        });
      }
    },
    [onPatch],
  );

  const handleEditKey = (
    e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>,
    options: { allowNewline: boolean },
  ) => {
    if (e.key === "Escape") {
      e.preventDefault();
      // Cancel: drop draft and exit edit mode without firing PATCH.
      const target = e.currentTarget;
      const rowId = target.dataset.rowId;
      const field = target.dataset.field;
      if (rowId && field) {
        const key = `${rowId}:${field}`;
        setDrafts((d) => {
          if (!(key in d)) return d;
          const { [key]: _drop, ...rest } = d;
          return rest;
        });
        setErrors((e2) => {
          if (!(key in e2)) return e2;
          const { [key]: _drop, ...rest } = e2;
          return rest;
        });
      }
      setEditingCell(null);
      return;
    }
    if (e.key === "Enter" && (!options.allowNewline || (!e.shiftKey && !e.ctrlKey && !e.metaKey))) {
      // For single-line inputs Enter commits.
      // For textareas Enter inserts a newline; Shift/Ctrl/Cmd+Enter commits.
      if (!options.allowNewline) {
        e.preventDefault();
        e.currentTarget.blur();
      }
    } else if (e.key === "Enter" && options.allowNewline && (e.shiftKey || e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      e.currentTarget.blur();
    }
  };

  const renderEditableText = (
    rowId: string,
    field: keyof ProtocolRow,
    value: string,
    multiline: boolean,
    label: string,
  ) => {
    const key = cellKey(rowId, field);
    const isEditing = editingCell?.rowId === rowId && editingCell.field === field;
    const isSaving = !!saving[key];
    const errMsg = errors[key];
    if (isEditing) {
      // Controlled value: prefer pending draft so a failed save keeps the user's text.
      const draft = drafts[key];
      const currentValue = draft !== undefined ? draft : value;
      const inputClass = errMsg ? editableInputErrorClass : editableInputClass;
      const textareaClass = errMsg ? editableTextareaErrorClass : editableTextareaClass;
      const common = {
        autoFocus: true,
        value: currentValue,
        "aria-label": label,
        "aria-invalid": errMsg ? true : undefined,
        "data-row-id": rowId,
        "data-field": String(field),
        disabled: isSaving,
        onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
          const v = e.currentTarget.value;
          setDrafts((d) => ({ ...d, [key]: v }));
        },
        onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
          if (isSaving) return; // ignore blur while a save is already in flight
          commit(rowId, field, value, e.currentTarget.value);
        },
        onKeyDown: (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) =>
          handleEditKey(e, { allowNewline: multiline }),
      };
      return (
        <div className="space-y-1">
          {multiline ? (
            <textarea
              {...common}
              className={textareaClass}
              rows={Math.max(2, currentValue.split("\n").length)}
            />
          ) : (
            <input {...common} className={inputClass} />
          )}
          {isSaving && (
            <span className="text-xs text-gray-500" role="status">
              Сохраняем…
            </span>
          )}
          {errMsg && !isSaving && (
            <span className="text-xs text-red-600" role="alert">
              Не удалось сохранить: {errMsg}. Нажмите Enter для повтора или Esc для отмены.
            </span>
          )}
        </div>
      );
    }
    // Block entering edit mode on any cell of a row that already has a PATCH
    // in flight. Two concurrent PATCHes on the same row would race in the
    // server response order: whichever lands last would overwrite the other
    // cell's just-saved value with a snapshot taken before the concurrent
    // edit. Disabling activation until the in-flight save resolves serialises
    // edits per row and prevents that data-loss window.
    const rowBusy = rowHasPendingSave(rowId);
    const activate = () => {
      if (rowBusy) return;
      setEditingCell({ rowId, field });
    };
    const busyTitle = rowBusy ? "Дождитесь сохранения изменений" : undefined;
    const viewClass = `${cellViewClass} ${multiline ? "whitespace-pre-wrap" : ""} ${
      rowBusy ? "cursor-wait opacity-60" : ""
    }`;
    return (
      <span
        role="textbox"
        tabIndex={0}
        aria-label={label}
        aria-disabled={rowBusy ? true : undefined}
        title={busyTitle}
        onClick={activate}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " " || e.key === "F2") {
            e.preventDefault();
            activate();
          }
        }}
        className={viewClass}
      >
        {value || <span className="text-gray-300">—</span>}
      </span>
    );
  };

  const columns = [
    columnHelper.accessor("point_label", {
      header: "Пункт договора",
      cell: ({ row, getValue }) =>
        renderEditableText(row.original.id, "point_label", getValue(), false, "Пункт договора"),
    }),
    columnHelper.accessor("party_1_text", {
      header: `Редакция: ${counterpartyRole || "контрагент"}`,
      cell: ({ row, getValue }) =>
        renderEditableText(
          row.original.id,
          "party_1_text",
          getValue(),
          true,
          `Редакция ${counterpartyRole || "контрагента"}`,
        ),
    }),
    columnHelper.accessor("party_2_text", {
      header: `Редакция: ${draftingRole || "наша сторона"}`,
      cell: ({ row, getValue }) =>
        renderEditableText(
          row.original.id,
          "party_2_text",
          getValue(),
          true,
          `Редакция ${draftingRole || "нашей стороны"}`,
        ),
    }),
    columnHelper.accessor("agreed_text", {
      header: "Согласованная редакция",
      cell: ({ row, getValue }) =>
        renderEditableText(row.original.id, "agreed_text", getValue(), true, "Согласованная редакция"),
    }),
    columnHelper.display({
      id: "actions",
      header: () => <span className="sr-only">Действия</span>,
      cell: ({ row }) => {
        // Disable merge/delete while any cell of this row has a pending save —
        // otherwise a structural mutation could clobber an in-flight edit.
        const rowBusy = rowHasPendingSave(row.original.id);
        const disabledTitle = rowBusy ? "Дождитесь сохранения изменений" : undefined;
        return (
          <div className="flex items-center justify-end gap-1">
            {row.original.confidence < 0.85 && (
              <span
                className="inline-flex items-center rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-800"
                title={`Низкая уверенность: ${(row.original.confidence * 100).toFixed(0)}%`}
                aria-label={`Низкая уверенность: ${(row.original.confidence * 100).toFixed(0)}%`}
              >
                !
              </span>
            )}
            <details className="relative">
              <summary
                aria-label="Действия со строкой"
                className="cursor-pointer list-none rounded px-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                ⋯
              </summary>
              <div className="absolute right-0 z-10 mt-1 flex min-w-[14rem] flex-col rounded border border-gray-200 bg-white p-1 text-sm shadow-lg">
                <button
                  type="button"
                  onClick={() => onMerge(row.original.id, "previous")}
                  disabled={rowBusy}
                  title={disabledTitle}
                  className="rounded px-2 py-1 text-left hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
                >
                  ↑ Объединить с предыдущей
                </button>
                <button
                  type="button"
                  onClick={() => onMerge(row.original.id, "next")}
                  disabled={rowBusy}
                  title={disabledTitle}
                  className="rounded px-2 py-1 text-left hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
                >
                  ↓ Объединить со следующей
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(row.original.id)}
                  disabled={rowBusy}
                  title={disabledTitle}
                  className="rounded px-2 py-1 text-left text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
                >
                  ✕ Исключить
                </button>
              </div>
            </details>
          </div>
        );
      },
    }),
  ];

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  });

  const toolbarBtn =
    "rounded border border-gray-300 bg-white px-3 py-1 text-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={onAddRow} className={toolbarBtn}>
          + Добавить строку
        </button>
        <button type="button" onClick={onSwapParties} className={toolbarBtn}>
          ⇄ Поменять стороны
        </button>
      </div>
      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="w-full border-collapse text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="bg-gray-50">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    scope="col"
                    className="border-b border-gray-200 px-2 py-2 text-left align-bottom font-semibold text-gray-700"
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-sm text-gray-500"
                >
                  В протоколе пока нет строк. Нажмите «Добавить строку», чтобы начать.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={
                    row.original.flags.includes("manual_review")
                      ? "bg-yellow-50/60"
                      : "odd:bg-white even:bg-gray-50/40"
                  }
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="border-t border-gray-100 px-2 py-1 align-top"
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
