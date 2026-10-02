import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProtocolPage from "@/app/documents/[id]/protocol/page";
import ProtocolTable from "@/components/ProtocolTable";
import { api } from "@/lib/api";
import { FORM } from "./fixtures/protocol-form";
import type { ProtocolRow } from "@/lib/types";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useParams: () => ({ id: "doc1" }) }));
vi.mock("@/lib/api", () => ({ api: {
  listProtocolsForDocument: vi.fn(), getProtocolRows: vi.fn(), getAnalysis: vi.fn(),
  patchRow: vi.fn(), addRow: vi.fn(), deleteRow: vi.fn(), swapParties: vi.fn(), buildProtocol: vi.fn(),
} }));

const ROW: ProtocolRow = { id: "r1", sort_order: 0, point_label: "1.1", party_1_text: "ABCD", party_2_text: "Наш текст", agreed_text: "Согласовано", source_clause_key: "c1", confidence: 1, flags: [], user_edited: false };
const ROW2: ProtocolRow = { ...ROW, id: "r2", sort_order: 1, point_label: "2.2" };
const ANALYSIS = { id: "doc1", status: "built" as const, error_message: null, contract_name: "Тест", preflight_metrics: null, preflight_diagnostics: [], parties: [], validation_report: null, drafting_party_id: null };
const PROTO = { id: "p1", document_id: "doc1", rows: [ROW], form: FORM };
const props = { draftingRole: "Автор", counterpartyRole: "Контрагент", onDelete: vi.fn(), onMerge: vi.fn(), onAddRow: vi.fn(), onSwapParties: vi.fn() };
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listProtocolsForDocument).mockResolvedValue([PROTO]);
  vi.mocked(api.getProtocolRows).mockResolvedValue(PROTO);
  vi.mocked(api.getAnalysis).mockResolvedValue(ANALYSIS);
});

test.each(["party_1_text", "point_label"] as const)("typing in the middle of %s keeps DOM identity and caret", async (field) => {
  const row = { ...ROW, [field]: "ABCD" };
  if (field === "point_label") row.party_1_text = "other";
  const onPatch = vi.fn().mockResolvedValue(undefined);
  render(<ProtocolTable {...props} rows={[row]} onPatch={onPatch} />);
  await userEvent.click(screen.getByText("ABCD"));
  const input = screen.getByDisplayValue("ABCD") as HTMLTextAreaElement;
  input.setSelectionRange(2, 2);
  await userEvent.keyboard("xy");
  expect(screen.getByDisplayValue("ABxyCD")).toBe(input);
  expect(input.selectionStart).toBe(4);
  await userEvent.tab();
  expect(onPatch).toHaveBeenCalledWith("r1", { [field]: "ABxyCD" });
});

async function editPoint() {
  await screen.findByText("1.1");
  await userEvent.click(screen.getByText("1.1"));
  fireEvent.change(screen.getByDisplayValue("1.1"), { target: { value: "9.9" } });
}

test("export waits for pending save then opens the download dialog", async () => {
  const gate = deferred<ProtocolRow>();
  vi.mocked(api.patchRow).mockReturnValue(gate.promise);
  render(<ProtocolPage />);
  await editPoint();
  fireEvent.blur(screen.getByDisplayValue("9.9"));
  await waitFor(() => expect(api.patchRow).toHaveBeenCalledOnce());
  await userEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(push).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Экспорт DOCX" })).toBeDisabled();
  await act(async () => { gate.resolve({ ...ROW, point_label: "9.9" }); });
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
  expect(api.patchRow).toHaveBeenCalledTimes(1);
});

test("export flushes active draft even when no blur event occurs", async () => {
  vi.mocked(api.patchRow).mockResolvedValue({ ...ROW, point_label: "9.9" });
  render(<ProtocolPage />);
  await editPoint();
  fireEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
  expect(api.patchRow).toHaveBeenCalledWith("p1", "r1", { point_label: "9.9" });
});

test("failed save prevents export and keeps draft for retry", async () => {
  const gate = deferred<ProtocolRow>();
  vi.mocked(api.patchRow).mockReturnValue(gate.promise);
  render(<ProtocolPage />);
  await editPoint();
  fireEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  await waitFor(() => expect(api.patchRow).toHaveBeenCalledOnce());
  await act(async () => { gate.reject(new Error("offline")); });
  expect(push).not.toHaveBeenCalled();
  expect(screen.getByDisplayValue("9.9")).toBeInTheDocument();
  vi.mocked(api.patchRow).mockResolvedValue({ ...ROW, point_label: "9.9" });
  fireEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

test("double add is gated and sequential adds preserve both returned rows", async () => {
  const first = deferred<ProtocolRow>();
  vi.mocked(api.addRow).mockReturnValueOnce(first.promise).mockResolvedValueOnce({ ...ROW, id: "new2", point_label: "4.4", sort_order: 2 });
  const { container } = render(<ProtocolPage />);
  await screen.findByText("1.1");
  await userEvent.click(screen.getByRole("button", { name: "Таблица" }));
  const button = screen.getByRole("button", { name: /Добавить строку/ });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(api.addRow).toHaveBeenCalledTimes(1));
  expect(button).toBeDisabled();
  await act(async () => { first.resolve({ ...ROW, id: "new1", point_label: "3.3", sort_order: 1 }); });
  await waitFor(() => expect(button).not.toBeDisabled());
  await userEvent.click(button);
  await screen.findByText("4.4");
  expect(container.querySelectorAll("tbody tr")).toHaveLength(3);
  expect(screen.getByText("3.3")).toBeInTheDocument();
});

test("delete waits for another row's save and preserves its new text", async () => {
  const saved = deferred<ProtocolRow>(), removed = deferred<void>();
  vi.mocked(api.getProtocolRows).mockResolvedValue({ ...PROTO, rows: [ROW, ROW2] });
  vi.mocked(api.patchRow).mockReturnValue(saved.promise);
  vi.mocked(api.deleteRow).mockReturnValue(removed.promise);
  render(<ProtocolPage />);
  await screen.findByText("1.1");
  await userEvent.click(screen.getByRole("button", { name: "Таблица" }));
  await editPoint();
  fireEvent.blur(screen.getByDisplayValue("9.9"));
  await waitFor(() => expect(api.patchRow).toHaveBeenCalledOnce());
  await userEvent.click(screen.getAllByLabelText("Действия со строкой")[1]);
  await userEvent.click(screen.getByRole("button", { name: "Исключить из протокола" }));
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Исключить" }));
  expect(api.deleteRow).not.toHaveBeenCalled();
  await act(async () => { saved.resolve({ ...ROW, point_label: "9.9" }); });
  await waitFor(() => expect(api.deleteRow).toHaveBeenCalledOnce());
  await act(async () => { removed.resolve(); });
  expect(screen.getByText("9.9")).toBeInTheDocument();
  expect(screen.queryByText("2.2")).not.toBeInTheDocument();
});

test("structural request failure leaves editor mounted", async () => {
  vi.mocked(api.deleteRow).mockRejectedValue(new Error("delete failed"));
  render(<ProtocolPage />);
  await screen.findByText("1.1");
  await userEvent.click(screen.getByLabelText("Действия со строкой"));
  await userEvent.click(screen.getByRole("button", { name: "Исключить из протокола" }));
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Исключить" }));
  await screen.findByText("delete failed");
  expect(screen.getByText("1.1")).toBeInTheDocument();
  await userEvent.click(screen.getByText("ABCD"));
  expect(screen.getByDisplayValue("ABCD")).toBeInTheDocument();
});

test("closing tab warns only while unsaved changes exist", async () => {
  render(<ProtocolTable {...props} rows={[ROW]} onPatch={vi.fn()} />);
  await userEvent.click(screen.getByText("1.1"));
  fireEvent.change(screen.getByDisplayValue("1.1"), { target: { value: "draft" } });
  const dirtyEvent = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(dirtyEvent);
  expect(dirtyEvent.defaultPrevented).toBe(true);
  await userEvent.keyboard("{Escape}");
  const cleanEvent = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(cleanEvent);
  expect(cleanEvent.defaultPrevented).toBe(false);
});
