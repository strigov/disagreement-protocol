import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProtocolTable from "@/components/ProtocolTable";
import { rowFingerprint } from "@/lib/review";
import type { ProtocolRow } from "@/lib/types";

const first: ProtocolRow = { id: "r1", sort_order: 0, point_label: "3.1", party_1_text: "Оплата за 5 дней", party_2_text: "Оплата за 10 дней", agreed_text: "Редакция Покупателя", source_clause_key: "c1", confidence: 1, flags: [], user_edited: false };
const second: ProtocolRow = { ...first, id: "r2", sort_order: 1, point_label: "4.2", party_1_text: "Доставка товара", party_2_text: "Доставка за счёт поставщика", confidence: 0.6 };
const third: ProtocolRow = { ...first, id: "r3", sort_order: 2, point_label: "5.1", party_1_text: "Приёмка", party_2_text: "Приёмка в течение 3 дней" };
const props = { draftingRole: "Покупатель", counterpartyRole: "Поставщик", onAddRow: vi.fn(), onSwapParties: vi.fn() };

beforeEach(() => { window.localStorage.clear(); });

test("row menu moves focus inside, closes on Escape and returns focus to its trigger", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn()} onMerge={vi.fn()} onDelete={vi.fn()} />);
  const trigger = screen.getByRole("button", { name: "Действия со строкой" });
  await userEvent.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  await waitFor(() => expect(screen.getByRole("button", { name: "Объединить с предыдущей" })).toHaveFocus());
  await userEvent.keyboard("{ArrowDown}");
  expect(screen.getByRole("button", { name: "Объединить со следующей" })).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("button", { name: "Объединить со следующей" })).not.toBeInTheDocument();
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(trigger).toHaveFocus();
});

test("row menu closes on an outside click and after choosing an action", async () => {
  const onMerge = vi.fn().mockResolvedValue(undefined);
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn()} onMerge={onMerge} onDelete={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Действия со строкой" }));
  await userEvent.click(screen.getByRole("heading", { name: "Пункт 3.1" }));
  expect(screen.queryByRole("button", { name: "Объединить со следующей" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Действия со строкой" }));
  await userEvent.click(screen.getByRole("button", { name: "Объединить со следующей" }));
  expect(onMerge).toHaveBeenCalledWith("r1", "next");
  expect(screen.queryByRole("button", { name: "Объединить со следующей" })).not.toBeInTheDocument();
});

test("excluding a row asks for confirmation and cancel keeps the row", async () => {
  const onDelete = vi.fn().mockResolvedValue(undefined);
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn()} onMerge={vi.fn()} onDelete={onDelete} />);
  await userEvent.click(screen.getByRole("button", { name: "Действия со строкой" }));
  await userEvent.click(screen.getByRole("button", { name: "Исключить из протокола" }));
  const dialog = screen.getByRole("dialog", { name: "Исключить пункт 3.1 из протокола?" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Отмена" }));
  expect(onDelete).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Действия со строкой" }));
  await userEvent.click(screen.getByRole("button", { name: "Исключить из протокола" }));
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Исключить" }));
  expect(onDelete).toHaveBeenCalledTimes(1);
  expect(onDelete).toHaveBeenCalledWith("r1");
});

test("filter buttons show how much work is left and narrow the clause list", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} storageKey="k" onPatch={vi.fn()} onMerge={vi.fn()} onDelete={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Все пункты 2" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Требуют внимания 1" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Не проверены мной 2" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Требуют внимания/ }));
  expect(screen.queryByRole("button", { name: "Открыть пункт 3.1" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Все пункты/ }));
  await userEvent.click(screen.getByRole("checkbox", { name: "Проверено мной" }));
  expect(screen.getByRole("button", { name: "Не проверены мной 1" })).toBeInTheDocument();
});

test("«Проверено — дальше» marks the clause with the usual fingerprint and opens the next one", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second, third]} storageKey="k" reviewContext="ctx" onPatch={vi.fn()} onMerge={vi.fn()} onDelete={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Проверено — дальше" }));
  expect(JSON.parse(window.localStorage.getItem("protocol-review:k") || "{}").r1).toBe(rowFingerprint(first, "ctx"));
  expect(screen.getByRole("heading", { name: "Пункт 4.2" })).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Открыть пункт 3.1" }));
  expect(screen.getByRole("button", { name: "Проверено — дальше" })).toBeDisabled();

  await userEvent.click(screen.getByRole("button", { name: /Не проверены мной/ }));
  expect(screen.getByRole("heading", { name: "Пункт 4.2" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Проверено — дальше" }));
  expect(screen.getByRole("heading", { name: "Пункт 5.1" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Открыть пункт 4.2" })).not.toBeInTheDocument();
});

test("«Проверено — дальше» is unavailable while a draft is unsaved", async () => {
  render(<ProtocolTable {...props} initialMode="focus" rows={[first, second]} onPatch={vi.fn()} onMerge={vi.fn()} onDelete={vi.fn()} />);
  await userEvent.click(screen.getByRole("textbox", { name: "Согласованная редакция" }));
  await userEvent.type(screen.getByDisplayValue(first.agreed_text), " с уточнением");
  expect(screen.getByRole("button", { name: "Проверено — дальше" })).toBeDisabled();
});
