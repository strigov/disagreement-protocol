"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut, Protocol, ProtocolRow, ValidationReport } from "@/lib/types";
import ProtocolTable from "@/components/ProtocolTable";

export default function ProtocolPage({ params }: { params: { id: string } }) {
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Decide between loading existing rows vs first-time build.
    // POST /documents/{id}/protocol wipes-and-rebuilds, which would discard
    // manual edits — so we only call it the first time (no protocol yet).
    //
    // Analysis is fetched AFTER the protocol is built/loaded (not in
    // parallel) so that the validation banner reflects the
    // `validation_report` written by the just-completed build. If we ran
    // them in parallel, the first-build path would render with a stale
    // analysis snapshot and the banner would only appear on a manual
    // refresh.
    let cancelled = false;
    (async () => {
      try {
        const existing = await api.listProtocolsForDocument(params.id);
        const proto =
          existing.length > 0
            ? await api.getProtocolRows(existing[0].id)
            : await api.buildProtocol(params.id);
        if (cancelled) return;
        setProtocol(proto);
        // Fetch analysis AFTER the protocol settles so the validation
        // report (written during build) is visible on first paint.
        try {
          const a = await api.getAnalysis(params.id);
          if (!cancelled) setAnalysis(a);
        } catch {
          /* non-fatal — banner just won't render */
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  const refreshAnalysis = async () => {
    try {
      const a = await api.getAnalysis(params.id);
      setAnalysis(a);
    } catch {
      /* ignore */
    }
  };

  const patch = async (rowId: string, body: Partial<ProtocolRow>) => {
    if (!protocol) return;
    // Rethrow on failure so ProtocolTable can keep the user's pending draft
    // visible (data-loss prevention: a swallowed error here would discard
    // edited text the moment the cell exits edit mode). We deliberately do
    // NOT call setError() — promoting a single-cell PATCH failure to the
    // page-level error UI would unmount the table and lose every other
    // unsaved draft along with it.
    const updated = await api.patchRow(protocol.id, rowId, body);
    // Functional update: two PATCHes on different cells of the same row can be
    // in flight simultaneously. Using a snapshot-based setState here would let
    // whichever response lands last clobber the other cell's just-saved value
    // with a stale row from before the concurrent edit. Merging from the
    // freshest state and only overriding the field(s) actually patched keeps
    // both writes visible.
    setProtocol((cur) => {
      if (!cur) return cur;
      return {
        ...cur,
        rows: cur.rows.map((r) => (r.id === rowId ? { ...r, ...updated } : r)),
      };
    });
  };

  const merge = async (rowId: string, direction: "previous" | "next") => {
    if (!protocol) return;
    try {
      await api.patchRow(protocol.id, rowId, { merge_with: direction });
      // Reload rows after merge — use the read endpoint, NOT buildProtocol,
      // to avoid wiping the just-merged state.
      const fresh = await api.getProtocolRows(protocol.id);
      setProtocol(fresh);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (rowId: string) => {
    if (!protocol) return;
    try {
      await api.deleteRow(protocol.id, rowId);
      setProtocol({ ...protocol, rows: protocol.rows.filter((r) => r.id !== rowId) });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const addRow = async () => {
    if (!protocol) return;
    try {
      const created = await api.addRow(protocol.id);
      setProtocol({ ...protocol, rows: [...protocol.rows, created] });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const swap = async () => {
    if (!protocol) return;
    try {
      const updated = await api.swapParties(protocol.id);
      setProtocol(updated);
      await refreshAnalysis();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8" role="alert">
        <h1 className="mb-2 text-2xl font-semibold">Не удалось загрузить протокол</h1>
        <p className="text-red-600">{error}</p>
      </main>
    );
  }

  if (!protocol) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8" aria-busy="true">
        <p className="text-gray-600">Строим таблицу…</p>
      </main>
    );
  }

  const report: ValidationReport | null = analysis?.validation_report ?? null;
  const uncovered = report
    ? Math.max(0, report.textual_revisions_total - report.covered_revisions)
    : 0;
  const warningCount = report?.warnings.length ?? 0;

  const draftingParty = analysis?.parties.find((p) => p.id === analysis?.drafting_party_id);
  const counterparty = analysis?.parties.find((p) => p.id !== analysis?.drafting_party_id);

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Протокол разногласий</h1>
        {analysis?.contract_name && (
          <p className="text-sm text-gray-500">{analysis.contract_name}</p>
        )}
      </header>

      {(uncovered > 0 || warningCount > 0) && report && (
        <section
          role="status"
          aria-live="polite"
          className="space-y-2 rounded border border-yellow-300 bg-yellow-50 p-4 text-sm text-yellow-900"
        >
          <div className="font-medium">Проверьте перед экспортом:</div>
          {uncovered > 0 && (
            <div>
              Не покрыто правок: <strong>{uncovered}</strong> из {report.textual_revisions_total}.
            </div>
          )}
          {warningCount > 0 && (
            <ul className="list-inside list-disc">
              {report.warnings.slice(0, 5).map((w, i) => (
                <li key={i}>{w.message}</li>
              ))}
              {warningCount > 5 && <li>и ещё {warningCount - 5}…</li>}
            </ul>
          )}
        </section>
      )}

      <ProtocolTable
        rows={protocol.rows}
        counterpartyRole={counterparty?.role ?? ""}
        draftingRole={draftingParty?.role ?? ""}
        onPatch={patch}
        onMerge={merge}
        onDelete={remove}
        onAddRow={addRow}
        onSwapParties={swap}
      />

      <div className="flex justify-end pt-2">
        <button
          type="button"
          onClick={() => router.push(`/documents/${params.id}/export`)}
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          Экспорт DOCX
        </button>
      </div>
    </main>
  );
}
