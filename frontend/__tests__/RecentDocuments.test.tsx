import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecentDocuments } from "@/components/RecentDocuments";
import { fmtDateTime } from "@/lib/format";
import { RECENT_DOCUMENTS_KEY, readRecentDocuments, rememberDocument } from "@/lib/recent-documents";

const DAY = 24 * 60 * 60 * 1000;

beforeEach(() => {
  window.localStorage.clear();
});

test("renders nothing when the store is empty", () => {
  const { container } = render(<RecentDocuments />);
  expect(container).toBeEmptyDOMElement();
});

test("renders nothing when the stored value is corrupt", () => {
  window.localStorage.setItem(RECENT_DOCUMENTS_KEY, "{oops");
  const { container } = render(<RecentDocuments />);
  expect(container).toBeEmptyDOMElement();
});

test("lists documents from the newest to the oldest with stage, date and a link to the analysis route", () => {
  const now = Date.now();
  rememberDocument({ id: "old", title: "Договор аренды", stage: "analysis" }, now - 3 * DAY);
  rememberDocument({ id: "new", title: "Договор поставки", stage: "protocol" }, now - 1000);
  rememberDocument({ id: "mid", title: null, stage: "parties" }, now - 2 * DAY);

  render(<RecentDocuments />);

  expect(screen.getByRole("heading", { level: 2, name: "недавние документы" })).toBeInTheDocument();

  const rows = screen.getAllByRole("listitem");
  expect(rows).toHaveLength(3);
  expect(within(rows[0]).getByRole("link")).toHaveAttribute("href", "/documents/new/analysis");
  expect(within(rows[0]).getByText("Договор поставки")).toBeInTheDocument();
  expect(within(rows[0]).getByText("Протокол")).toBeInTheDocument();
  expect(within(rows[0]).getByText(fmtDateTime(now - 1000))).toBeInTheDocument();

  expect(within(rows[1]).getByRole("link")).toHaveAttribute("href", "/documents/mid/analysis");
  expect(within(rows[1]).getByText("Документ без названия")).toBeInTheDocument();
  expect(within(rows[1]).getByText("Стороны")).toBeInTheDocument();

  expect(within(rows[2]).getByRole("link")).toHaveAttribute("href", "/documents/old/analysis");
  expect(within(rows[2]).getByText("Договор аренды")).toBeInTheDocument();
  expect(within(rows[2]).getByText("Обработка")).toBeInTheDocument();
});

test("the remove button drops the entry from the screen and from localStorage only", async () => {
  rememberDocument({ id: "a", title: "Договор аренды", stage: "analysis" }, 20);
  rememberDocument({ id: "b", title: "Договор поставки", stage: "parties" }, 10);
  render(<RecentDocuments />);

  await userEvent.click(screen.getByRole("button", { name: "Убрать «Договор аренды» из списка" }));

  expect(screen.queryByText("Договор аренды")).not.toBeInTheDocument();
  expect(screen.getByText("Договор поставки")).toBeInTheDocument();
  expect(readRecentDocuments().map((item) => item.id)).toEqual(["b"]);
});

test("removing the last entry hides the whole section", async () => {
  rememberDocument({ id: "a", title: "Единственный", stage: "analysis" }, 20);
  const { container } = render(<RecentDocuments />);

  await userEvent.click(screen.getByRole("button", { name: "Убрать «Единственный» из списка" }));

  expect(container).toBeEmptyDOMElement();
  expect(readRecentDocuments()).toEqual([]);
});

test("the remove button of an untitled entry names the placeholder title", () => {
  rememberDocument({ id: "a", title: null, stage: "analysis" }, 20);
  render(<RecentDocuments />);
  expect(screen.getByRole("button", { name: "Убрать «Документ без названия» из списка" })).toBeInTheDocument();
});
