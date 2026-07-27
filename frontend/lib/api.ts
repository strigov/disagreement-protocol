import type { AnalysisOut, Protocol, ProtocolRow, UUID } from "./types";

const BASE = "";

// Turns a failed Response into the sentence we put in front of the user.
// FastAPI answers with {"detail": "..."} for handled errors and with a
// {"detail": [{"msg": ...}]} list for request-validation errors; anything else
// (a proxy, a crash page) arrives as plain text and keeps its diagnostic
// "<status> <body>" shape. The body is read exactly once — a Response stream
// cannot be consumed twice.
async function apiErrorMessage(resp: Response): Promise<string> {
  let body = "";
  try {
    body = (await resp.text()).trim();
  } catch {
    return `Ошибка запроса (HTTP ${resp.status})`;
  }
  if (!body) return `Ошибка запроса (HTTP ${resp.status})`;

  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return `${resp.status} ${body}`;
  }
  if (typeof parsed !== "object" || parsed === null) {
    return `${resp.status} ${body}`;
  }

  const detail = (parsed as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        typeof item === "object" && item !== null
          ? (item as { msg?: unknown }).msg
          : undefined,
      )
      .filter((msg): msg is string => typeof msg === "string" && msg.trim() !== "")
      .map((msg) => msg.trim());
    if (messages.length > 0) return messages.join("; ");
  }
  // Never dump a raw JSON body at the user.
  return `Ошибка запроса (HTTP ${resp.status})`;
}

async function throwApiError(resp: Response): Promise<never> {
  throw new Error(await apiErrorMessage(resp));
}

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) await throwApiError(resp);
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
    if (!resp.ok) await throwApiError(resp);
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
    if (!r.ok) await throwApiError(r);
    return r.blob();
  },
};
