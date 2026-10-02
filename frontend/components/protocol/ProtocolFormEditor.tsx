"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Party, ProtocolForm, ProtocolFormPatch, ProtocolRow, ProtocolSignature } from "@/lib/types";
import type { SaveState } from "@/components/ProtocolTable";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Notice } from "@/components/ui/Notice";

export interface ProtocolFormHandle { saveAll: () => Promise<boolean> }
type TextField = Exclude<keyof ProtocolForm, "signatures" | "mark_drafting_signature">;
const TITLES = [
  ["point_title", "Колонка 1 · пункт"],
  ["original_title", "Колонка 2 · исходная редакция"],
  ["proposed_title", "Колонка 3 · предлагаемая редакция"],
  ["agreed_title", "Колонка 4 · согласованная редакция"],
] as const;

function changes(before: ProtocolForm, after: ProtocolForm): ProtocolFormPatch {
  const patch: ProtocolFormPatch = {};
  for (const key of Object.keys(after) as (keyof ProtocolForm)[]) {
    if (key === "signatures") {
      for (const [id, signature] of Object.entries(after.signatures)) {
        for (const field of Object.keys(signature) as (keyof ProtocolSignature)[]) {
          if (signature[field] !== before.signatures[id]?.[field]) {
            patch.signatures ??= {};
            patch.signatures[id] ??= {};
            patch.signatures[id][field] = signature[field];
          }
        }
      }
    } else if (key === "mark_drafting_signature") {
      if (before[key] !== after[key]) patch[key] = after[key];
    } else if (before[key] !== after[key]) patch[key] = after[key];
  }
  return patch;
}

export const ProtocolFormEditor = forwardRef<ProtocolFormHandle, {
  form: ProtocolForm;
  rows: ProtocolRow[];
  parties: Party[];
  draftingPartyId: string | null;
  busy: boolean;
  active: boolean;
  onSave: (patch: ProtocolFormPatch) => Promise<ProtocolForm>;
  onSaveStateChange: (state: SaveState) => void;
  onSwapParties: () => Promise<void>;
}>(function ProtocolFormEditor({ form, rows, parties, draftingPartyId, busy, active, onSave, onSaveStateChange, onSwapParties }, ref) {
  const [draft, setDraft] = useState(form);
  const draftRef = useRef(form);
  const savedRef = useRef(form);
  const pending = useRef<Promise<boolean> | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = Object.keys(changes(savedRef.current, draft)).length > 0;
  const saveState: SaveState = saving ? "saving" : error ? "error" : dirty ? "dirty" : "saved";
  useEffect(() => { onSaveStateChange(saveState); }, [onSaveStateChange, saveState]);
  useEffect(() => {
    if (!pending.current && !Object.keys(changes(savedRef.current, draftRef.current)).length) {
      savedRef.current = form;
      draftRef.current = form;
      setDraft(form);
    }
  }, [form]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (pending.current || Object.keys(changes(savedRef.current, draftRef.current)).length) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  const saveAll = useCallback((reset?: ProtocolFormPatch): Promise<boolean> => {
    if (pending.current) return pending.current;
    const patch = { ...changes(savedRef.current, draftRef.current), ...reset };
    if (!Object.keys(patch).length) { setError(null); return Promise.resolve(true); }
    setSaving(true);
    setError(null);
    const request = Promise.resolve().then(async () => {
      try {
        const result = await onSave(patch);
        savedRef.current = result;
        draftRef.current = result;
        setDraft(result);
        return true;
      } catch (e) {
        setError((e as Error).message || "Не удалось сохранить оформление");
        return false;
      } finally {
        pending.current = null;
        setSaving(false);
      }
    });
    pending.current = request;
    return request;
  }, [onSave]);
  useImperativeHandle(ref, () => ({ saveAll }), [saveAll]);
  const update = (next: ProtocolForm) => { draftRef.current = next; setDraft(next); setError(null); };
  const textField = (key: TextField, label: string, multiline = false, placeholder?: string) => {
    const props = {
      value: draft[key], maxLength: multiline ? 20000 : 500, placeholder,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => update({ ...draftRef.current, [key]: e.target.value }),
    };
    return <Field label={label}>{multiline ? <Textarea {...props} rows={6} /> : <Input {...props} />}</Field>;
  };
  const signatureOrder = Object.entries(draft.signatures).sort(([a], [b]) => Number(a === draftingPartyId) - Number(b === draftingPartyId));

  return (
    <div className="grid items-start gap-6 xl:grid-cols-2">
      <section aria-label="Поля оформления" className="min-w-0 space-y-5">
        <div>
          <h2 className="font-serif text-2xl font-semibold text-ink">Оформление протокола</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-2">Заполните шапку и подписи или вставьте свой текст. Изменения сохраняются кнопкой ниже, при переходе к правкам и перед скачиванием DOCX.</p>
        </div>
        <fieldset disabled={busy || saving} className="space-y-5 disabled:opacity-60">
          <div className="space-y-4 rounded-lg border border-line-c bg-bg-elev p-5">
            <h3 className="rubric">Шапка документа</h3>
            {textField("title", "Название документа")}
            {textField("contract_reference", "Договор · название, номер и дата", false, "Например: поставки № 15 от 02.10.2026")}
            <div className="grid gap-4 sm:grid-cols-2">
              {textField("place", "Место составления", false, "г. Москва")}
              {textField("date", "Дата протокола", false, "Заполните дату")}
            </div>
            {textField("opening_text", "Текст перед таблицей", true)}
            <Button variant="ghost" size="sm" onClick={() => void saveAll({ opening_text: null })}>Восстановить типовую шапку</Button>
          </div>
          <div className="space-y-4 rounded-lg border border-line-c bg-bg-elev p-5">
            <h3 className="rubric">Названия колонок</h3>
            <div className="grid gap-4 sm:grid-cols-2">{TITLES.map(([key, label]) => <div key={key}>{textField(key, label)}</div>)}</div>
            <p className="text-xs leading-relaxed text-ink-2">Названия изменятся в редакторе и в DOCX. Содержание и порядок редакций останутся прежними.</p>
            <Button variant="ghost" size="sm" onClick={() => void saveAll({ point_title: null, original_title: null, proposed_title: null, agreed_title: null })}>Вернуть стандартные названия</Button>
          </div>
          <div className="space-y-4 rounded-lg border border-line-c bg-bg-elev p-5">
            <h3 className="rubric">После таблицы</h3>
            {textField("closing_text", "Заключительные положения", true)}
            <Button variant="ghost" size="sm" onClick={() => void saveAll({ closing_text: null })}>Восстановить типовые положения</Button>
          </div>
          <div className="space-y-4 rounded-lg border border-line-c bg-bg-elev p-5">
            <h3 className="rubric">Подписи сторон</h3>
            <Field label="Протокол составляется от стороны">
              <select value={draftingPartyId ?? ""} disabled={!draftingPartyId || parties.length !== 2} onChange={(e) => { if (e.target.value !== draftingPartyId) void onSwapParties(); }} className="h-9 w-full rounded-sm border border-line-c bg-bg px-3 text-sm text-ink">
                {parties.map((party) => <option key={party.id} value={party.id}>{party.name} · {party.role}</option>)}
              </select>
            </Field>
            <p className="text-xs leading-relaxed text-ink-2">Это та же «наша сторона», что и в таблице. При смене обновится автоматическая согласованная редакция.</p>
            <div className="grid gap-5 sm:grid-cols-2">
              {signatureOrder.map(([id, signature]) => (
                <div key={id} className="min-w-0 space-y-3">
                  <h4 className="text-sm font-medium text-ink">{id === draftingPartyId ? "Наша сторона" : "Контрагент"}</h4>
                  {([["name", "Наименование стороны"], ["role", "Роль в договоре"], ["position", "Должность подписанта"], ["full_name", "ФИО подписанта"]] as const).map(([key, label]) => (
                    <Field key={key} label={`${label} · ${id === draftingPartyId ? "наша сторона" : "контрагент"}`}>
                      <Input maxLength={500} value={signature[key]} onChange={(e) => update({ ...draftRef.current, signatures: { ...draftRef.current.signatures, [id]: { ...draftRef.current.signatures[id], [key]: e.target.value } } })} />
                    </Field>
                  ))}
                </div>
              ))}
            </div>
            <label className="flex items-start gap-2 text-sm leading-relaxed text-ink">
              <input type="checkbox" checked={draft.mark_drafting_signature} onChange={(e) => update({ ...draftRef.current, mark_drafting_signature: e.target.checked })} className="mt-1 h-4 w-4 accent-accent" />
              Отметка «С учетом протокола разногласий» под нашей подписью
            </label>
          </div>
        </fieldset>
        {error && <Notice tone="danger" role="alert">Не удалось сохранить оформление: {error}. Введённый текст сохранён в форме — повторите попытку.</Notice>}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" disabled={busy || saving || !dirty && !error} onClick={() => void saveAll()}>{saving ? "Сохраняем…" : "Сохранить оформление"}</Button>
          {(dirty || error) && <Button variant="ghost" disabled={busy || saving} onClick={() => update(savedRef.current)}>Отменить изменения</Button>}
          <span className="text-xs text-ink-2" role="status">{saving ? "Сохраняем оформление…" : dirty ? "Есть несохранённые изменения" : "Оформление сохранено"}</span>
        </div>
      </section>
      {active && <section aria-label="Предпросмотр оформления" className="min-w-0 rounded-lg border border-line-c bg-bg-elev p-5 shadow-sm md:p-7 xl:sticky xl:top-6 xl:max-h-protocol-table xl:overflow-y-auto">
        <p className="rubric mb-6">Предпросмотр · разбиение на страницы будет в DOCX</p>
        <h2 className="text-center font-serif text-2xl font-semibold text-ink wrap-anywhere">{draft.title}</h2>
        <p className="mt-2 text-center text-sm text-ink-1 wrap-anywhere">К договору: {draft.contract_reference || "№ __________ от __________________"}</p>
        <div className="my-5 flex justify-between gap-4 text-sm text-ink-1 wrap-anywhere"><span>{draft.place || "Место: __________________"}</span><span>{draft.date || "Дата: __________________"}</span></div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink wrap-anywhere">{draft.opening_text}</p>
        <div className="my-5 max-h-96 overflow-auto rounded-sm border border-line-c">
          <table className="w-full text-left text-xs leading-relaxed text-ink">
            <thead className="bg-bg-sunk"><tr>{TITLES.map(([key]) => <th key={key} className="border-b border-line-c p-2 align-top wrap-anywhere">{draft[key]}</th>)}</tr></thead>
            <tbody>{rows.map((row) => <tr key={row.id}>{[row.point_label, row.party_1_text, row.party_2_text, row.agreed_text].map((text, index) => <td key={index} className="border-b border-line-c p-2 align-top whitespace-pre-wrap wrap-anywhere">{text}</td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink wrap-anywhere">{draft.closing_text}</p>
        <h3 className="mb-4 mt-6 font-serif text-xl font-semibold text-ink">Подписи сторон</h3>
        <div className="grid gap-5 sm:grid-cols-2">
          {signatureOrder.map(([id, signature]) => <div key={id} className="min-w-0 space-y-2 text-sm text-ink wrap-anywhere">
            <p className="font-medium">{signature.role}</p><p>{signature.name}</p>
            <p>{signature.position || "Должность: __________________"}</p>
            <p>________________ / {signature.full_name || "________________"} /</p>
            {draft.mark_drafting_signature && id === draftingPartyId && <p className="text-xs">С учетом протокола разногласий</p>}
          </div>)}
        </div>
      </section>}
    </div>
  );
});
