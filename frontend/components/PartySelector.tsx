"use client";

import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/cn";

export interface PartyDraft {
  id: string | null;
  name: string;
  role: string;
  _uid: string;
}

interface Props {
  parties: PartyDraft[];
  draftingUid: string | null;
  onChange: (parties: PartyDraft[]) => void;
  onDraftingChange: (uid: string | null) => void;
  disabled?: boolean;
}

let UID_SEQ = 0;
export const newPartyUid = () => `p${++UID_SEQ}_${Date.now()}`;

export function PartySelector({ parties, draftingUid, onChange, onDraftingChange, disabled = false }: Props) {
  const update = (idx: number, patch: Partial<PartyDraft>) => {
    const next = parties.map((p, i) => (i === idx ? { ...p, ...patch } : p));
    onChange(next);
  };
  const add = () => {
    const draft: PartyDraft = { id: null, name: "", role: "", _uid: newPartyUid() };
    onChange([...parties, draft]);
  };
  const remove = (idx: number) => {
    const removed = parties[idx];
    const next = parties.filter((_, i) => i !== idx);
    onChange(next);
    if (removed && removed._uid === draftingUid) onDraftingChange(null);
  };
  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className="sr-only">Выберите вашу сторону договора</legend>
      <div className="grid gap-4 md:grid-cols-2">
        {parties.map((p, idx) => {
          const selected = draftingUid === p._uid;
          return (
            <section
              key={p._uid}
              className={cn(
                "rounded-md border border-line-c bg-bg-elev p-4 shadow-sm",
                selected && "outline outline-2 -outline-offset-2 outline-accent",
              )}
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <label className="rubric flex cursor-pointer items-center gap-2 py-1">
                  <input type="radio" name="drafting" className="h-4 w-4 cursor-pointer accent-accent" aria-label={`Составитель: ${p.name || "новая сторона"}`}
                    checked={selected} onChange={() => onDraftingChange(p._uid)} />
                  {selected ? "Наша сторона" : `Сторона ${idx + 1}`}
                </label>
                <Button variant="ghost" size="xs" onClick={() => remove(idx)}>Удалить</Button>
              </div>
              <div className="space-y-3">
                <Field label="Наименование организации">
                  <Input value={p.name} onChange={(e) => update(idx, { name: e.target.value })} placeholder="Наименование" aria-label="Наименование стороны" />
                </Field>
                <Field label="Роль в договоре">
                  <Input value={p.role} onChange={(e) => update(idx, { role: e.target.value })} placeholder="Роль" aria-label="Роль стороны" />
                </Field>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-ink-2">{selected ? "Протокол будет составлен от имени этой стороны." : "Проверьте название и роль, распознанные в договоре."}</p>
            </section>
          );
        })}
      </div>
      {parties.length < 2 && <Button variant="ghost" onClick={add} className="mt-4"><Icon name="plus" /> Добавить сторону</Button>}
    </fieldset>
  );
}
