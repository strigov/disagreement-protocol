"use client";

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
    <fieldset disabled={disabled}>
      <legend className="sr-only">Выберите вашу сторону договора</legend>
      <div className="party-grid">
        {parties.map((p, idx) => (
          <section key={p._uid} className={`party-card ${draftingUid === p._uid ? "selected" : ""}`}>
            <div className="party-card-top">
              <label className="party-choice">
                <input type="radio" name="drafting" aria-label={`Составитель: ${p.name || "новая сторона"}`}
                  checked={draftingUid === p._uid} onChange={() => onDraftingChange(p._uid)} />
                {draftingUid === p._uid ? "Наша сторона" : `Сторона ${idx + 1}`}
              </label>
              <button type="button" onClick={() => remove(idx)} className="text-xs text-slate-500 hover:text-red-600">Удалить</button>
            </div>
            <label><span className="field-label">Наименование организации</span>
              <input className="field" value={p.name} onChange={(e) => update(idx, { name: e.target.value })} placeholder="Наименование" aria-label="Наименование стороны" />
            </label>
            <label><span className="field-label">Роль в договоре</span>
              <input className="field" value={p.role} onChange={(e) => update(idx, { role: e.target.value })} placeholder="Роль" aria-label="Роль стороны" />
            </label>
            <p className="party-caption">{draftingUid === p._uid ? "Протокол будет составлен от имени этой стороны." : "Проверьте название и роль, распознанные в договоре."}</p>
          </section>
        ))}
      </div>
      {parties.length < 2 && <button type="button" onClick={add} className="btn btn-secondary mt-4">+ Добавить сторону</button>}
    </fieldset>
  );
}
