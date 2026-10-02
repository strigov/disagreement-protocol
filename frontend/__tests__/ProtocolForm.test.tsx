import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ProtocolPage from "@/app/documents/[id]/protocol/page";
import { server } from "@/src/mocks/server";
import type { ProtocolForm, ProtocolFormPatch } from "@/lib/types";
import { FORM } from "./fixtures/protocol-form";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useParams: () => ({ id: "doc1" }) }));
const row = { id: "r1", sort_order: 0, point_label: "1.1", party_1_text: "Было", party_2_text: "Стало", agreed_text: "Согласовано", source_clause_key: null, confidence: 1, flags: [], user_edited: false };
let saved: ProtocolForm;
let patches: ProtocolFormPatch[];
let drafting = "buyer";
beforeEach(() => {
  saved = structuredClone(FORM); patches = []; drafting = "buyer"; push.mockClear();
  server.use(
    http.get("/api/protocols", () => HttpResponse.json([{ id: "p1", document_id: "doc1", rows: [row], form: saved }])),
    http.get("/api/protocols/p1/rows", () => HttpResponse.json({ id: "p1", document_id: "doc1", rows: [row], form: saved })),
    http.get("/api/documents/doc1/analysis", () => HttpResponse.json({
      id: "doc1", status: "built", contract_name: "поставки № 12", drafting_party_id: drafting,
      parties: Object.entries(FORM.signatures).map(([id, value]) => ({ id, ...value, confidence: 1 })),
      validation_report: null, preflight_diagnostics: [],
    })),
    http.patch("/api/protocols/p1/form", async ({ request }) => {
      const patch = await request.json() as ProtocolFormPatch;
      patches.push(patch);
      for (const [key, value] of Object.entries(patch)) {
        if (key === "signatures") {
          for (const [id, fields] of Object.entries(patch.signatures!)) saved.signatures[id] = { ...saved.signatures[id], ...fields };
        } else Object.assign(saved, { [key]: value === null ? FORM[key as keyof ProtocolForm] : value });
      }
      return HttpResponse.json(saved);
    }),
  );
});
async function openForm() {
  await screen.findByText("1.1");
  await userEvent.click(screen.getByRole("tab", { name: "Оформление" }));
  return screen.getByRole("region", { name: "Поля оформления" });
}

test("custom headers and pasted framing are saved on tab switch and survive reload", async () => {
  const view = render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("Колонка 2 · исходная редакция"), { target: { value: "Редакция клиента" } });
  fireEvent.change(screen.getByLabelText("Текст перед таблицей"), { target: { value: "Своя шапка\nВторая строка" } });
  expect(within(screen.getByRole("region", { name: "Предпросмотр оформления" })).getByText(/Своя шапка/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Правки договора" }));
  await waitFor(() => expect(screen.getByRole("tab", { name: "Правки договора" })).toHaveAttribute("aria-selected", "true"));
  expect(patches).toEqual([{ original_title: "Редакция клиента", opening_text: "Своя шапка\nВторая строка" }]);
  await userEvent.click(screen.getByRole("button", { name: "Таблица" }));
  expect(screen.getByRole("columnheader", { name: "Редакция клиента" })).toBeInTheDocument();
  view.unmount();
  render(<ProtocolPage />);
  await openForm();
  expect(screen.getByLabelText("Текст перед таблицей")).toHaveValue("Своя шапка\nВторая строка");
  await userEvent.click(screen.getByRole("button", { name: "Вернуть стандартные названия" }));
  await waitFor(() => expect(screen.getByLabelText("Колонка 2 · исходная редакция")).toHaveValue(FORM.original_title));
  expect(screen.getByLabelText("Текст перед таблицей")).toHaveValue("Своя шапка\nВторая строка");
});

test("failed save blocks export and navigation while preserving all draft fields for retry", async () => {
  server.use(http.patch("/api/protocols/p1/form", () => HttpResponse.json({ detail: "Нет связи" }, { status: 503 })));
  render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("Место составления"), { target: { value: "Казань" } });
  await userEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  await screen.findByText(/Не удалось сохранить оформление:/);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Место составления")).toHaveValue("Казань");
  await userEvent.click(screen.getByRole("tab", { name: "Правки договора" }));
  expect(screen.getByRole("tab", { name: "Оформление" })).toHaveAttribute("aria-selected", "true");
  expect(push).not.toHaveBeenCalled();
  server.use(http.patch("/api/protocols/p1/form", () => HttpResponse.json({ ...FORM, place: "Казань" })));
  await userEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
});

test("export waits for an already pending form save without issuing a second PATCH", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let calls = 0;
  server.use(http.patch("/api/protocols/p1/form", async () => { calls++; await gate; return HttpResponse.json({ ...FORM, date: "02.10.2026" }); }));
  render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("Дата протокола"), { target: { value: "02.10.2026" } });
  await userEvent.click(screen.getByRole("button", { name: "Сохранить оформление" }));
  await waitFor(() => expect(calls).toBe(1));
  await userEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await act(async () => release());
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
  expect(calls).toBe(1);
});

test("changing drafting party flushes signature edits and moves the note to the new party", async () => {
  server.use(http.post("/api/protocols/p1/swap-parties", () => {
    expect(saved.signatures.buyer.full_name).toBe("Петров");
    drafting = "supplier";
    saved.proposed_title = "Редакция Поставщика";
    return HttpResponse.json({ id: "p1", document_id: "doc1", rows: [row], form: saved });
  }));
  render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("ФИО подписанта · наша сторона"), { target: { value: "Петров" } });
  await userEvent.selectOptions(screen.getByLabelText("Протокол составляется от стороны"), "supplier");
  await waitFor(() => expect(screen.getByLabelText("ФИО подписанта · контрагент")).toHaveValue("Петров"));
  const preview = screen.getByRole("region", { name: "Предпросмотр оформления" });
  const note = within(preview).getByText("С учетом протокола разногласий");
  expect(note.parentElement).toHaveTextContent("ООО Поставщик");
  expect(note.parentElement).not.toHaveTextContent("Петров");
});

test("keyboard tab navigation and unload guard retain unsaved text", async () => {
  render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("Место составления"), { target: { value: "Москва" } });
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(true);
  fireEvent.keyDown(screen.getByRole("tab", { name: "Оформление" }), { key: "ArrowLeft" });
  await waitFor(() => expect(screen.getByRole("tab", { name: "Правки договора" })).toHaveAttribute("aria-selected", "true"));
  expect(saved.place).toBe("Москва");
  expect(screen.getByRole("tab", { name: "Правки договора" })).toHaveFocus();
});

test("discarding a failed draft restores the saved form and permits navigation", async () => {
  server.use(http.patch("/api/protocols/p1/form", () => HttpResponse.json({ detail: "Нет связи" }, { status: 503 })));
  render(<ProtocolPage />);
  await openForm();
  fireEvent.change(screen.getByLabelText("Место составления"), { target: { value: "Несохранённое" } });
  await userEvent.click(screen.getByRole("button", { name: "Сохранить оформление" }));
  await screen.findByText(/Не удалось сохранить оформление:/);
  await userEvent.click(screen.getByRole("button", { name: "Отменить изменения" }));
  expect(screen.getByLabelText("Место составления")).toHaveValue("");
  await userEvent.click(screen.getByRole("tab", { name: "Правки договора" }));
  await waitFor(() => expect(screen.getByRole("tab", { name: "Правки договора" })).toHaveAttribute("aria-selected", "true"));
});
