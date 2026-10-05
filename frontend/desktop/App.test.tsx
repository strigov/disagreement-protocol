import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { server } from "@/src/mocks/server";
import { FORM } from "@/__tests__/fixtures/protocol-form";
import { App } from "./App";

const protocol = {
  id: "proto-1", document_id: "doc-1", form: FORM,
  rows: [{
    id: "row-1", sort_order: 0, point_label: "1.1", party_1_text: "Было",
    party_2_text: "Стало", agreed_text: "Согласовано", source_clause_key: "clause-1",
    confidence: 1, flags: [], user_edited: false,
  }],
};

let built: boolean;
let builds: number;

beforeEach(() => {
  localStorage.clear();
  built = false;
  builds = 0;
  server.use(
    http.post("/api/documents", () => HttpResponse.json({ id: "doc-1", status: "uploaded" })),
    http.get("/api/documents/doc-1/analysis", () => HttpResponse.json({
      id: "doc-1", status: built ? "built" : "parsed", contract_name: "поставки № 12",
      drafting_party_id: "buyer", preflight_metrics: null, preflight_diagnostics: [], validation_report: null,
      parties: Object.entries(FORM.signatures).map(([id, value]) => ({ id, ...value, confidence: 1 })),
    })),
    http.patch("/api/documents/doc-1/parties", () => HttpResponse.json({ parties: [] })),
    http.get("/api/protocols", () => HttpResponse.json(built ? [protocol] : [])),
    http.post("/api/documents/doc-1/protocol", () => {
      built = true;
      builds++;
      return HttpResponse.json(protocol);
    }),
    http.get("/api/protocols/proto-1/rows", () => HttpResponse.json(protocol)),
  );
});

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

test("Electron routes take an upload through parties, protocol and export and resume without rebuilding", async () => {
  const user = userEvent.setup();
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:docx");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  let downloaded = "";
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    downloaded = this.download;
  });
  let exported: unknown;
  server.use(http.post("/api/documents/doc-1/protocol/export", async ({ request }) => {
    exported = await request.json();
    return new HttpResponse(new Blob(["docx"]), { status: 200 });
  }));

  render(<MemoryRouter><App /></MemoryRouter>);
  await user.upload(screen.getByLabelText("Выбрать файл"), new File(["docx"], "Договор.docx"));
  expect(await screen.findByDisplayValue("ООО Покупатель")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Построить протокол" }));
  expect(await screen.findByText("1.1")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Сохранить DOCX" }));
  await user.click(screen.getByRole("button", { name: "Сохранить" }));
  await screen.findByText("Выберите папку и подтвердите сохранение в открывшемся окне.");
  expect(exported).toEqual({ filename: "Протокол разногласий — поставки № 12" });
  expect(downloaded).toBe("Протокол разногласий — поставки № 12.docx");
  await user.click(screen.getByRole("button", { name: "Закрыть сохранение" }));
  await user.click(screen.getByRole("button", { name: /Strigov: Протокол разногласий/ }));
  await user.click(await screen.findByRole("link", { name: /Продолжить работу с договором/ }));
  expect(await screen.findByText("Согласовано")).toBeInTheDocument();
  expect(builds).toBe(1);
});

test("a saved export deep link uses its document id and returns to the existing protocol", async () => {
  built = true;
  render(<MemoryRouter initialEntries={["/documents/doc-1/export"]}><App /></MemoryRouter>);
  const back = screen.getByRole("link", { name: "Вернуться к протоколу" });
  expect(back).toHaveAttribute("href", "/documents/doc-1/protocol");
  await userEvent.click(back);
  expect(await screen.findByText("1.1")).toBeInTheDocument();
  expect(builds).toBe(0);
  await waitFor(() => expect(localStorage.getItem("disprot:last-document-route")).toBe("/documents/doc-1/protocol"));
});

test("an unknown route offers a working return to the upload screen", async () => {
  render(<MemoryRouter initialEntries={["/unknown"]}><App /></MemoryRouter>);
  expect(screen.getByRole("heading", { name: "Этот раздел недоступен" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("link", { name: "Открыть документ" }));
  expect(screen.getByLabelText("Выбрать файл")).toBeInTheDocument();
});
