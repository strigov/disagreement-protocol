import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { PartySelector, type PartyDraft, newPartyUid } from "@/components/PartySelector";

function Harness({
  initial,
  onSubmit,
}: {
  initial: PartyDraft[];
  onSubmit: (p: PartyDraft[]) => void;
}) {
  const [parties, setParties] = useState<PartyDraft[]>(initial);
  const [drafting, setDrafting] = useState<string | null>(null);
  return (
    <>
      <PartySelector
        parties={parties}
        draftingUid={drafting}
        onChange={setParties}
        onDraftingChange={setDrafting}
      />
      <button onClick={() => onSubmit(parties)}>submit</button>
    </>
  );
}

test("add new party then remove existing produces correct PATCH shape", () => {
  const existing: PartyDraft = {
    id: "uuid-existing",
    name: "ООО А",
    role: "Арендодатель",
    _uid: newPartyUid(),
  };
  const captured: PartyDraft[][] = [];
  render(<Harness initial={[existing]} onSubmit={(p) => captured.push(p)} />);
  fireEvent.click(screen.getByText("+ Добавить сторону"));
  // Two name inputs now visible (existing + new).
  const nameInputs = screen.getAllByPlaceholderText("Наименование");
  fireEvent.change(nameInputs[1], { target: { value: "АО Б" } });
  const roleInputs = screen.getAllByPlaceholderText("Роль");
  fireEvent.change(roleInputs[1], { target: { value: "Арендатор" } });
  // Remove the original existing party.
  fireEvent.click(screen.getAllByText("Удалить")[0]);
  fireEvent.click(screen.getByText("submit"));
  const final = captured.at(-1)!;
  expect(final).toHaveLength(1);
  expect(final[0].id).toBeNull();
  expect(final[0].name).toBe("АО Б");
  expect(final[0].role).toBe("Арендатор");
  // Mapping to PATCH payload (mirrors PartiesPage.submit):
  const payload = final.map((p) => ({ id: p.id, name: p.name, role: p.role }));
  expect(payload).toEqual([{ id: null, name: "АО Б", role: "Арендатор" }]);
});
