"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, ArrowLeft, LoaderCircle } from "lucide-react";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import { api } from "@/lib/api";
import type { AnalysisOut } from "@/lib/types";
import { PartySelector, newPartyUid, type PartyDraft } from "@/components/PartySelector";

export default function PartiesPage() {
  const params = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [parties, setParties] = useState<PartyDraft[]>([]);
  // We track the drafting selection by the client-side _uid because newly-
  // added parties have no server id yet; on submit we resolve _uid → real
  // UUID after the PATCH response returns.
  const [draftingUid, setDraftingUid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
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
        setParties(drafts.length ? drafts : [0, 1].map(() => ({ id: null, name: "", role: "", _uid: newPartyUid() })));
        const draftingDraft = drafts.find((d) => d.id === a.drafting_party_id) ?? null;
        setDraftingUid(draftingDraft?._uid ?? null);
      })
      .catch((e) => setError((e as Error).message));
  }, [params.id]);

  const submit = async () => {
    if (!draftingUid || submitting.current || parties.length !== 2 || parties.some((p) => !p.name.trim() || !p.role.trim())) return;
    submitting.current = true;
    setBusy(true);
    setError(null);
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
      submitting.current = false;
      setBusy(false);
    }
  };

  if (!analysis) return <WorkspaceShell step={2} documentId={params.id}>
    {error ? <div className="notice notice-error" role="alert">{error}</div> : <div className="loading-state"><LoaderCircle className="spinner mx-auto mb-4" size={24} /><p>Загружаем…</p></div>}
  </WorkspaceShell>;

  return (
    <WorkspaceShell step={2} documentId={params.id}>
      <div className="eyebrow">Договор загружен</div>
      <h1 className="page-title">Стороны договора</h1>
      {analysis.contract_name && <p className="document-name">{analysis.contract_name}</p>}
      <p className="page-description">Проверьте названия и роли. Отметьте вашу сторону — от её имени будет составлен протокол разногласий.</p>
      <AnalysisSummary analysis={analysis} />
      {analysis.parties.length === 0 && <p className="notice mt-5">Стороны не удалось определить автоматически. Введите их названия и роли из договора.</p>}
      <PartySelector parties={parties} draftingUid={draftingUid} onChange={setParties} onDraftingChange={setDraftingUid} disabled={busy} />
      {parties.length !== 2 && <p className="notice mt-5">Для протокола нужны две стороны. Добавьте недостающую или удалите лишнюю.</p>}
      {error && <p className="notice notice-error mt-5" role="alert">{error}</p>}
      <div className="page-actions">
        <button className="btn btn-quiet" disabled={busy} onClick={() => router.push("/")}><ArrowLeft size={14} /> Другой документ</button>
        <button disabled={!draftingUid || busy || parties.length !== 2 || parties.some((p) => !p.name.trim() || !p.role.trim())}
          onClick={submit} className="btn btn-primary">
          {busy ? <><LoaderCircle size={15} className="spinner" /> Подготавливаем…</> : <>Построить протокол <ArrowRight size={15} /></>}
        </button>
      </div>
    </WorkspaceShell>
  );
}
