import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import ProtocolTable from "@/components/ProtocolTable";
import { DiffText } from "@/components/DiffText";
import { AnalysisSummary } from "@/components/AnalysisSummary";
import type { ProtocolRow } from "@/lib/types";

const first: ProtocolRow = { id: "r1", sort_order: 0, point_label: "3.1", party_1_text: "Оплатить за 5 дней.\nБез комиссии.", party_2_text: "Оплатить за 10 дней.\nБез комиссии.", agreed_text: "Редакция Покупателя", source_clause_key: "c1", confidence: 1, flags: [], user_edited: false };
const second: ProtocolRow = { ...first, id: "r2", sort_order: 1, point_label: "4.2", party_1_text: "Доставка товара", party_2_text: "Доставка за счёт поставщика", confidence: 0.6 };
const props = { draftingRole: "Покупатель", counterpartyRole: "Поставщик", onDelete: vi.fn(), onMerge: vi.fn(), onAddRow: vi.fn(), onSwapParties: vi.fn() };

beforeEach(() => { window.localStorage.clear(); });

test("word comparison preserves exact Russian text, whitespace and punctuation on both sides", () => {
  const { container } = render(<><div data-testid="before"><DiffText before={first.party_1_text} after={first.party_2_text} side="before" /></div><div data-testid="after"><DiffText before={first.party_1_text} after={first.party_2_text} side="after" /></div></>);
  expect(screen.getByTestId("before").textContent).toBe(first.party_1_text);
  expect(screen.getByTestId("after").textContent).toBe(first.party_2_text);
  expect(container.querySelector("del")).toHaveTextContent("5");
  expect(container.querySelector("ins")).toHaveTextContent("10");
});

test("large-clause comparison falls back to the full unmodified text", () => {
  const before = "Очень длинный пункт. ".repeat(6000);
  const { container } = render(<DiffText before={before} after="Заменён" side="before" />);
  expect(container.textContent).toBe(before);
});

test("view switch awaits an active save and shows the saved text in table mode", async () => {
  let finish!: () => void;
  const gate = new Promise<void>((resolve) => { finish = resolve; });
  function Harness() {
    const [rows, setRows] = useState([first, second]);
    return <ProtocolTable {...props} initialMode="focus" rows={rows} onPatch={async (id, patch) => { await gate; setRows((current) => current.map((row) => row.id === id ? { ...row, ...patch } : row)); }} />;
  }
  render(<Harness />);
  await userEvent.click(screen.getByRole("textbox", { name: "Согласованная редакция" }));
  fireEvent.change(screen.getByDisplayValue(first.agreed_text), { target: { value: "Итоговая формулировка" } });
  fireEvent.click(screen.getByRole("button", { name: "Таблица" }));
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  await act(async () => finish());
  expect(await screen.findByRole("table")).toHaveTextContent("Итоговая формулировка");
});

test("failed save blocks both view switch and next-clause navigation and keeps the draft", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn().mockRejectedValue(new Error("offline"))} />);
  await userEvent.click(screen.getByRole("textbox", { name: "Согласованная редакция" }));
  fireEvent.change(screen.getByDisplayValue(first.agreed_text), { target: { value: "Несохранённый текст" } });
  fireEvent.click(screen.getByRole("button", { name: "Таблица" }));
  await screen.findByRole("alert");
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Открыть пункт 4.2" }));
  expect(screen.getByDisplayValue("Несохранённый текст")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Пункт 3.1" })).toBeInTheDocument();
});

test("search and attention filter locate the appropriate clause, and empty results can be reset", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn()} />);
  await userEvent.type(screen.getByRole("textbox", { name: "Поиск по пунктам" }), "доставка");
  expect(screen.getByRole("heading", { name: "Пункт 4.2" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Открыть пункт 3.1" })).not.toBeInTheDocument();
  await userEvent.clear(screen.getByRole("textbox", { name: "Поиск по пунктам" }));
  await userEvent.click(screen.getByRole("button", { name: /Требуют внимания/ }));
  expect(screen.queryByRole("button", { name: "Открыть пункт 3.1" })).not.toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox", { name: "Поиск по пунктам" }), "несуществующий пункт");
  await userEvent.click(screen.getByRole("button", { name: "Сбросить фильтры" }));
  expect(screen.getByRole("button", { name: "Открыть пункт 3.1" })).toBeInTheDocument();
});

test("a failed draft remains reachable after a search excludes its saved text", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn().mockRejectedValue(new Error("offline"))} />);
  await userEvent.click(screen.getByRole("textbox", { name: "Согласованная редакция" }));
  fireEvent.change(screen.getByDisplayValue(first.agreed_text), { target: { value: "Сохранить обязательно" } });
  fireEvent.blur(screen.getByDisplayValue("Сохранить обязательно"));
  await screen.findByRole("alert");
  fireEvent.change(screen.getByRole("textbox", { name: "Поиск по пунктам" }), { target: { value: "доставка" } });
  expect(screen.getByDisplayValue("Сохранить обязательно")).toBeInTheDocument();
});

test("review marks survive remount and are invalidated by text edits and a change of drafting party", async () => {
  const onPatch = vi.fn();
  const view = render(<ProtocolTable {...props} initialMode="focus" rows={[first]} storageKey="test-protocol" reviewContext="buyer" onPatch={onPatch} />);
  await userEvent.click(screen.getByRole("checkbox", { name: "Проверено мной" }));
  expect(screen.getByRole("checkbox", { name: "Проверено мной" })).toBeChecked();
  view.unmount();
  const restored = render(<ProtocolTable {...props} initialMode="focus" rows={[first]} storageKey="test-protocol" reviewContext="buyer" onPatch={onPatch} />);
  await waitFor(() => expect(screen.getByRole("checkbox", { name: "Проверено мной" })).toBeChecked());
  restored.rerender(<ProtocolTable {...props} initialMode="focus" rows={[{ ...first, agreed_text: "Новая редакция" }]} storageKey="test-protocol" reviewContext="buyer" onPatch={onPatch} />);
  expect(screen.getByRole("checkbox", { name: "Проверено мной" })).not.toBeChecked();
  restored.rerender(<ProtocolTable {...props} initialMode="focus" rows={[first]} storageKey="test-protocol" reviewContext="seller" onPatch={onPatch} />);
  expect(screen.getByRole("checkbox", { name: "Проверено мной" })).not.toBeChecked();
});

test("local storage failure does not prevent reviewing a clause", async () => {
  const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
  render(<ProtocolTable {...props} initialMode="focus" rows={[first]} storageKey="test" onPatch={vi.fn()} />);
  await userEvent.click(screen.getByRole("checkbox", { name: "Проверено мной" }));
  expect(screen.getByRole("checkbox", { name: "Проверено мной" })).toBeChecked();
  expect(screen.getByText("Не удалось сохранить отметки проверки. При повторном открытии договора они могут быть потеряны.")).toBeInTheDocument();
  spy.mockRestore();
});

test("warnings are attached to their row, not every clause", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} warnings={[{ kind: "check", scope: "row", row_id: "r2", message: "Проверьте номер пункта 4.2" }]} onPatch={vi.fn()} />);
  expect(screen.queryByText("Проверьте номер пункта 4.2")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Открыть пункт 4.2" }));
  expect(within(screen.getByRole("region", { name: "Выбранный пункт" })).getByText("Проверьте номер пункта 4.2")).toBeInTheDocument();
});

test("processing diagnostics and metrics remain available on the parties screen", () => {
  render(<AnalysisSummary analysis={{ id: "doc", status: "parsed", contract_name: null, error_message: null, drafting_party_id: null, parties: [], validation_report: null, preflight_metrics: { revisions_total: 60, format_only_count: 5, numbering_confidence_mean: .82, paragraphs_with_numbering: 17 }, preflight_diagnostics: [{ level: "warning", component: "parser", code: "MOVE", block_id: null, message: "Проверьте перемещение вручную" }] }} />);
  expect(screen.getByText(/Найдено правок/)).toHaveTextContent("60");
  expect(screen.getAllByText("Проверьте перемещение вручную")).toHaveLength(2);
  expect(screen.getByText("Уверенность нумерации: 82%")).toBeInTheDocument();
});
