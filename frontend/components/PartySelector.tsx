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
}

let UID_SEQ = 0;
export const newPartyUid = () => `p${++UID_SEQ}_${Date.now()}`;

export function PartySelector({ parties, draftingUid, onChange, onDraftingChange }: Props) {
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
    <div className="space-y-3">
      {parties.map((p, idx) => (
        <div key={p._uid} className="flex items-start gap-3 bg-white border rounded p-3">
          <input
            type="radio"
            name="drafting"
            aria-label={`Составитель: ${p.name || "новая сторона"}`}
            checked={draftingUid === p._uid}
            onChange={() => onDraftingChange(p._uid)}
            className="mt-2"
          />
          <div className="grid grid-cols-2 gap-2 flex-1">
            <input
              className="border rounded px-2 py-1"
              value={p.name}
              onChange={(e) => update(idx, { name: e.target.value })}
              placeholder="Наименование"
              aria-label="Наименование стороны"
            />
            <input
              className="border rounded px-2 py-1"
              value={p.role}
              onChange={(e) => update(idx, { role: e.target.value })}
              placeholder="Роль"
              aria-label="Роль стороны"
            />
          </div>
          <button
            type="button"
            onClick={() => remove(idx)}
            className="text-red-600 text-sm hover:underline"
          >
            Удалить
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="px-3 py-1 border border-dashed border-gray-400 rounded text-sm text-gray-700 hover:bg-gray-50"
      >
        + Добавить сторону
      </button>
    </div>
  );
}
