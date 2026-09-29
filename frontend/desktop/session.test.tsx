import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { RememberDocument, ResumeDocument } from "./session";

afterEach(() => { cleanup(); localStorage.clear(); });

test("last document remains available after reopening the home screen", () => {
  const editor = render(<MemoryRouter initialEntries={["/documents/abc-123/protocol"]}><RememberDocument /></MemoryRouter>);
  editor.unmount();
  render(<MemoryRouter><RememberDocument /><ResumeDocument /></MemoryRouter>);
  expect(screen.getByRole("link", { name: /Продолжить работу/ })).toHaveAttribute("href", "/documents/abc-123/protocol");
});

test("a modified stored value cannot navigate outside the app", () => {
  localStorage.setItem("disprot:last-document-route", "https://example.com");
  render(<MemoryRouter><ResumeDocument /></MemoryRouter>);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
