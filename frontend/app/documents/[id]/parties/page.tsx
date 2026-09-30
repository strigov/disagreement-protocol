"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { api } from "@/lib/api";
import { rememberDocument } from "@/lib/recent-documents";
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
  // Two independent failures: the screen cannot load (nothing to show, retry
  // reloads it) vs. building the protocol failed (the form stays, edits kept).
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Bumped by "Повторить": re-runs the load effect.
  const [attempt, setAttempt] = useState(0);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    api
      .getAnalysis(params.id)
      .then((a) => {
        if (cancelled) return;
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
        rememberDocument({ id: params.id, title: a.contract_name, stage: "parties" });
      })
      .catch((e) => { if (!cancelled) setLoadError((e as Error).message); });
    return () => { cancelled = true; };
  }, [params.id, attempt]);

  const submit = async () => {
    if (!draftingUid || submitting.current || parties.length !== 2 || parties.some((p) => !p.name.trim() || !p.role.trim())) return;
    submitting.current = true;
    setBusy(true);
    setSubmitError(null);
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
      setSubmitError((e as Error).message);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  if (loadError) return (
    <WorkspaceShell step={2} documentId={params.id}>
      <ErrorState
        titleLevel={1}
        title="Не удалось загрузить стороны"
        text={loadError}
        onRetry={() => { setLoadError(null); setAttempt((n) => n + 1); }}
        className="max-w-2xl"
      />
    </WorkspaceShell>
  );

  if (!analysis) return (
    <WorkspaceShell step={2} documentId={params.id}>
      <div aria-busy="true">
        <p className="mb-6 text-sm text-ink-2">Загружаем…</p>
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((key) => (
            <div key={key} className="rounded-md border border-line-c bg-bg-elev p-4 shadow-sm">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-5 h-3 w-40" />
              <Skeleton className="mt-2 h-9 w-full" />
              <Skeleton className="mt-4 h-3 w-32" />
              <Skeleton className="mt-2 h-9 w-full" />
            </div>
          ))}
        </div>
      </div>
    </WorkspaceShell>
  );

  // Everything that still blocks "Построить протокол", in the order the user
  // is most likely to fix it. Shown as a list next to the disabled button.
  const blockers: string[] = [];
  if (parties.length !== 2) blockers.push("Для протокола нужны две стороны. Добавьте недостающую или удалите лишнюю.");
  if (parties.some((p) => !p.name.trim() || !p.role.trim())) blockers.push("Заполните наименование и роль каждой стороны.");
  if (!draftingUid) blockers.push("Отметьте вашу сторону — от её имени будет составлен протокол.");

  return (
    <WorkspaceShell step={2} documentId={params.id}>
      <PageHeader
        rubric="Договор загружен"
        title="Стороны договора"
        description="Проверьте названия и роли. Отметьте вашу сторону — от её имени будет составлен протокол разногласий."
        meta={analysis.contract_name ? <span className="font-serif text-base font-medium text-ink-1 wrap-anywhere">{analysis.contract_name}</span> : undefined}
      />
      <div className="mt-8 space-y-6">
        <AnalysisSummary analysis={analysis} />
        {analysis.parties.length === 0 && <Notice tone="warn">Стороны не удалось определить автоматически. Введите их названия и роли из договора.</Notice>}
        <PartySelector parties={parties} draftingUid={draftingUid} onChange={setParties} onDraftingChange={setDraftingUid} disabled={busy} />
        {submitError && <Notice tone="danger" role="alert">{submitError}</Notice>}
      </div>
      <div className="mt-10 flex flex-col-reverse gap-4 border-t border-line-c pt-6 sm:flex-row sm:items-start sm:justify-between">
        <Button variant="ghost" disabled={busy} onClick={() => router.push("/")}><Icon name="arrow-left" /> Другой документ</Button>
        <div className="flex flex-col gap-3 sm:items-end">
          {blockers.length > 0 && (
            <div id="build-requirements" className="rounded-md border border-line-c bg-bg-sunk px-3 py-2.5 text-sm text-ink-1">
              <p className="rubric">Чтобы построить протокол:</p>
              <ul className="mt-1.5 list-disc space-y-1 pl-4 marker:text-ink-2">
                {blockers.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}
          <Button
            variant="primary"
            disabled={blockers.length > 0 || busy}
            aria-describedby={blockers.length > 0 ? "build-requirements" : undefined}
            onClick={submit}
          >
            {busy
              ? <><Icon name="loader-circle" className="motion-safe:animate-spin" /> Подготавливаем…</>
              : <>Построить протокол <Icon name="arrow-right" /></>}
          </Button>
        </div>
      </div>
    </WorkspaceShell>
  );
}
