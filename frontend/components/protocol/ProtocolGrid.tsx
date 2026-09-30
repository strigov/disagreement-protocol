import type { ReactNode } from "react";
import type { ProtocolRow } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/icons/Icon";
import type { ProtocolColumn, RenderCell } from "./types";

export function ProtocolGrid({ rows, columns, isAttention, renderCell, renderActions, empty, search, filter }: {
  rows: ProtocolRow[];
  columns: ProtocolColumn[];
  isAttention: (row: ProtocolRow) => boolean;
  renderCell: RenderCell;
  renderActions: (row: ProtocolRow) => ReactNode;
  empty: ReactNode;
  search: ReactNode;
  filter: ReactNode;
}) {
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="w-full max-w-sm">{search}</div>
        {filter}
      </div>
      <div className="max-h-protocol-table overflow-auto rounded-lg border border-line-c bg-bg-elev shadow-sm">
        <table className="w-full min-w-protocol-table table-fixed border-separate border-spacing-0 text-sm leading-relaxed">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th
                  key={column.field}
                  scope="col"
                  className={cn(
                    "sticky top-0 z-10 border-b border-line-c bg-bg-sunk px-3 py-3 text-left text-xs font-medium text-ink-1",
                    index === 0 && "w-36",
                  )}
                >
                  {column.header}
                </th>
              ))}
              <th scope="col" className="sticky top-0 z-10 w-14 border-b border-line-c bg-bg-sunk"><span className="sr-only">Действия</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0
              ? <tr><td colSpan={5}>{empty}</td></tr>
              : rows.map((row) => {
                const attention = isAttention(row);
                return (
                  <tr key={row.id} className="group">
                    {columns.map((column, index) => (
                      <td
                        key={column.field}
                        className={cn(
                          "border-b border-line-c px-3 py-3 align-top wrap-anywhere group-last:border-b-0",
                          index > 0 && "border-l",
                          index === 0 && attention && "border-l-2 border-l-warn",
                        )}
                      >
                        {renderCell(row, column.field, column.label)}
                        {column.field === "point_label" && row.confidence < 0.85 && (
                          <span className="mt-2 inline-flex text-warn" aria-label={`Низкая уверенность: ${(row.confidence * 100).toFixed(0)}%`}>
                            <Icon name="triangle-alert" />
                          </span>
                        )}
                      </td>
                    ))}
                    <td className="border-b border-l border-line-c px-2 py-2 align-top group-last:border-b-0">{renderActions(row)}</td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-ink-2">Нажмите на ячейку, чтобы изменить её. Изменения сохраняются при выходе из ячейки.</p>
    </>
  );
}
