import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/src/mocks/server";
import { rememberDocument } from "@/lib/recent-documents";
import { RememberDocument, ResumeDocument } from "./session";

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

test("last document shows its title and resumes the saved stage after reopening home", async () => {
  rememberDocument({ id: "abc-123", title: "Договор поставки", stage: "protocol" });
  const editor = render(<MemoryRouter initialEntries={["/documents/abc-123/protocol"]}><RememberDocument /></MemoryRouter>);
  editor.unmount();
  render(<MemoryRouter><RememberDocument /><Routes>
    <Route path="/" element={<ResumeDocument />} />
    <Route path="/documents/abc-123/protocol" element={<h1>Редактор протокола</h1>} />
  </Routes></MemoryRouter>);
  const resume = screen.getByRole("link", { name: /Продолжить работу с договором «Договор поставки»/ });
  expect(resume).toHaveAttribute("href", "/documents/abc-123/protocol");
  expect(screen.getByText("Этап: Проверка протокола")).toBeInTheDocument();
  await userEvent.click(resume);
  expect(screen.getByRole("heading", { name: "Редактор протокола" })).toBeInTheDocument();
});

test("an older installation resolves the saved document title from the local engine", async () => {
  localStorage.setItem("disprot:last-document-route", "/documents/legacy-123/parties");
  server.use(http.get("/api/documents/legacy-123/analysis", () => HttpResponse.json({ contract_name: "Договор аренды" })));
  render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(await screen.findByText("Договор аренды")).toBeInTheDocument();
  expect(screen.getByText("Этап: Стороны договора")).toBeInTheDocument();
});

test("a failed title lookup keeps the saved route available", async () => {
  localStorage.setItem("disprot:last-document-route", "/documents/legacy-123/export");
  server.use(http.get("/api/documents/legacy-123/analysis", () => new HttpResponse(null, { status: 500 })));
  render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(screen.getByRole("link", { name: /Сохранённый договор/ })).toHaveAttribute("href", "/documents/legacy-123/export");
});

test("no saved document or unavailable storage leaves the upload screen without a card", () => {
  const { container, unmount } = render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(container).toBeEmptyDOMElement();
  unmount();
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("Unavailable storage"); });
  const blocked = render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(blocked.container).toBeEmptyDOMElement();
});

test("a modified stored value cannot navigate outside the app", () => {
  localStorage.setItem("disprot:last-document-route", "https://example.com");
  render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
