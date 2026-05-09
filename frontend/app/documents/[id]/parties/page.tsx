"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut } from "@/lib/types";
import { PartySelector, newPartyUid, type PartyDraft } from "@/components/PartySelector";

export default function PartiesPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [parties, setParties] = useState<PartyDraft[]>([]);
  // We track the drafting selection by the client-side _uid because newly-
  // added parties have no server id yet; on submit we resolve _uid → real
  // UUID after the PATCH response returns.
  const [draftingUid, setDraftingUid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api
      .getAnalysis(params.id)
      .then((a) => {
        setAnalysis(a);
        const drafts: PartyDraft[] = a.parties.map((p) => ({
          id: p.id,
          name: p.name,
          role: p.role,
          _uid: newPartyUid(),
        }));
        setParties(drafts);
        const draftingDraft = drafts.find((d) => d.id === a.drafting_party_id) ?? null;
        setDraftingUid(draftingDraft?._uid ?? null);
      })
      .catch((e) => setError((e as Error).message));
  }, [params.id]);

  const submit = async () => {
    if (!draftingUid) return;
    setBusy(true);
    try {
      const payload = parties.map((p) => ({ id: p.id, name: p.name, role: p.role }));
      // First-pass PATCH: drafting may be a brand-new (id=null) party,
      // in which case we cannot send drafting_party_id yet — resolve it
      // from the response and PATCH a second time if needed.
      const draftingDraft = parties.find((p) => p._uid === draftingUid)!;
      const firstResp = await api.patchParties(
        params.id,
        payload,
        draftingDraft.id ?? null,
      );
      if (!draftingDraft.id) {
        // Locate the newly-created party by (name, role) and confirm drafting.
        const created = firstResp.parties.find(
          (p) => p.name === draftingDraft.name && p.role === draftingDraft.role,
        );
        if (created) {
          await api.patchParties(
            params.id,
            firstResp.parties.map((p) => ({ id: p.id, name: p.name, role: p.role })),
            created.id,
          );
        }
      }
      // Preserve existing edits on back-navigation: only build if no
      // protocol exists yet for this document.
      const existing = await api.listProtocolsForDocument(params.id);
      if (existing.length > 0) {
        router.push(`/documents/${params.id}/protocol`);
        return;
      }
      await api.buildProtocol(params.id);
      router.push(`/documents/${params.id}/protocol`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!analysis) return <main className="p-8">Загружаем…</main>;

  return (
    <main className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <h1 className="text-2xl font-semibold">Стороны договора</h1>
      <PartySelector
        parties={parties}
        draftingUid={draftingUid}
        onChange={setParties}
        onDraftingChange={setDraftingUid}
      />
      <p className="text-sm text-gray-600">
        Отметьте сторону, от чьего имени составляется протокол (drafting party).
      </p>
      <button
        disabled={!draftingUid || busy || parties.length !== 2}
        onClick={submit}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-gray-300"
      >
        Построить протокол
      </button>
      {parties.length !== 2 && (
        <p className="text-amber-700 text-sm">MVP поддерживает ровно две стороны.</p>
      )}
    </main>
  );
}
