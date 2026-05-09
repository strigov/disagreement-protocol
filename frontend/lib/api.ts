import type { AnalysisOut, Protocol, ProtocolRow, UUID } from "./types";

const BASE = "";

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export const api = {
  uploadDocument: async (file: File): Promise<{ id: UUID; status: string }> => {
    const fd = new FormData();
    fd.append("file", file);
    return jsonOrThrow(await fetch(`${BASE}/api/documents`, { method: "POST", body: fd }));
  },

  getAnalysis: async (id: UUID): Promise<AnalysisOut> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/analysis`)),

  // PartiesPatchItem mirrors the backend `PartyUpdateItem` schema (Task 11):
  //   id: existing party UUID, or null to create a new party.
  // Omitting an existing party id from the list deletes that party.
  patchParties: async (
    id: UUID,
    parties: { id: UUID | null; name: string; role: string }[],
    drafting: UUID | null,
  ): Promise<AnalysisOut> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/parties`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parties, drafting_party_id: drafting }),
    })),

  buildProtocol: async (id: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/protocol`, { method: "POST" })),

  listProtocolsForDocument: async (documentId: UUID): Promise<Protocol[]> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols?document_id=${documentId}`)),

  getProtocolRows: async (protocolId: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows`)),

  patchRow: async (
    protocolId: UUID,
    rowId: UUID,
    patch: Partial<ProtocolRow> & { merge_with?: "previous" | "next" },
  ): Promise<ProtocolRow> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows/${rowId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    })),

  addRow: async (protocolId: UUID, sortOrder?: number): Promise<ProtocolRow> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sort_order: sortOrder ?? null }),
    })),

  deleteRow: async (protocolId: UUID, rowId: UUID): Promise<void> => {
    const resp = await fetch(`${BASE}/api/protocols/${protocolId}/rows/${rowId}`, {
      method: "DELETE",
    });
    if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  },

  swapParties: async (protocolId: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/swap-parties`, {
      method: "POST",
    })),

  exportProtocol: async (documentId: UUID, filename: string): Promise<Blob> => {
    const r = await fetch(`${BASE}/api/documents/${documentId}/protocol/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.blob();
  },
};
