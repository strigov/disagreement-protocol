import { cleanup, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "./render";
import { ExportSettingsDialog } from "@/components/ExportSettingsDialog";
import { ExportForm } from "@/components/ExportForm";
import { DEFAULT_EXPORT_SETTINGS, EXPORT_SETTINGS_KEY, writeExportSettings } from "@/lib/export-settings";
import { api } from "@/lib/api";

beforeEach(() => { writeExportSettings(DEFAULT_EXPORT_SETTINGS); window.localStorage.clear(); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear(); });

test("highlighting is off by default, styles and enabled state survive remount", async () => {
  const user = userEvent.setup();
  const view = render(<ExportSettingsDialog onClose={() => {}} />);
  expect(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" })).not.toBeChecked();
  await user.click(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" }));
  const deletions = within(screen.getByRole("group", { name: "Удаления · исходная редакция" }));
  for (const name of ["Полужирный", "Курсив", "Подчёркнутый", "Зачёркнутый"]) await user.click(deletions.getByLabelText(name));
  await user.click(deletions.getByRole("button", { name: "Цвет текста: Фиолетовый" }));
  await user.click(deletions.getByRole("button", { name: "Маркер: Жёлтый" }));
  expect(within(screen.getByRole("group", { name: "Добавления · предлагаемая редакция" })).queryByLabelText("Зачёркнутый")).not.toBeInTheDocument();
  view.unmount();
  render(<ExportSettingsDialog onClose={() => {}} />);
  expect(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" })).toBeChecked();
  const stored = JSON.parse(window.localStorage.getItem(EXPORT_SETTINGS_KEY)!);
  expect(stored.deletions).toEqual({ color: "7030A0", highlight: "yellow", bold: true, italic: true, underline: true, strike: true });
  await user.click(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" }));
  cleanup();
  render(<ExportSettingsDialog onClose={() => {}} />);
  expect(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" })).not.toBeChecked();
  expect(within(screen.getByRole("group", { name: "Удаления · исходная редакция" })).getByLabelText("Зачёркнутый")).toBeChecked();
});

test("malformed stored settings fall back safely", () => {
  window.localStorage.setItem(EXPORT_SETTINGS_KEY, '{"enabled":"yes","deletions":{"color":"oops"},"additions":null}');
  render(<ExportSettingsDialog onClose={() => {}} />);
  expect(screen.getByRole("checkbox", { name: "Выделять изменения в DOCX" })).not.toBeChecked();
  expect(within(screen.getByRole("group", { name: "Удаления · исходная редакция" })).getByRole("button", { name: "Цвет текста: Красный" })).toHaveAttribute("aria-pressed", "true");
});

test("two-file export uses styles only for the marked copy; clean option starts unchecked", async () => {
  const user = userEvent.setup();
  URL.createObjectURL = vi.fn(() => "blob:test");
  URL.revokeObjectURL = vi.fn();
  const downloads: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) { downloads.push(this.download); });
  const exportSpy = vi.spyOn(api, "exportProtocol").mockResolvedValue(new Blob(["docx"]));
  render(<ExportForm documentId="doc1" />);
  const clean = screen.getByLabelText("Сохранить также версию без выделения изменений");
  expect(clean).not.toBeChecked();
  expect(clean).toBeDisabled();
  await user.click(screen.getByLabelText("Выделять изменения в DOCX"));
  expect(clean).toBeEnabled();
  expect(clean).not.toBeChecked();
  await user.click(clean);
  await user.click(screen.getByRole("button", { name: "Сохранить" }));
  await screen.findByText("Подтвердите сохранение каждого из двух файлов в открывшихся окнах.");
  expect(downloads).toEqual(["Протокол разногласий — с выделением изменений.docx", "Протокол разногласий — без выделения изменений.docx"]);
  expect(exportSpy).toHaveBeenNthCalledWith(1, "doc1", "Протокол разногласий — с выделением изменений", { ...DEFAULT_EXPORT_SETTINGS, enabled: true });
  expect(exportSpy).toHaveBeenNthCalledWith(2, "doc1", "Протокол разногласий — без выделения изменений", undefined);
});

test("a failed clean export does not start partial downloads and allows retry", async () => {
  writeExportSettings({ ...DEFAULT_EXPORT_SETTINGS, enabled: true });
  const download = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  vi.spyOn(api, "exportProtocol").mockResolvedValueOnce(new Blob(["docx"])).mockRejectedValueOnce(new Error("Ошибка чистой версии"));
  render(<ExportForm documentId="doc1" />);
  await userEvent.click(screen.getByLabelText("Сохранить также версию без выделения изменений"));
  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Ошибка чистой версии");
  expect(download).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled();
});
