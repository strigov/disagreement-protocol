import { render } from "./render";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import PartiesPage from "@/pages/PartiesPage";
import { TestRoute, useTestParams } from "./route-context";
import { readRecentDocuments } from "@/lib/recent-documents";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("@/lib/navigation", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/navigation")>(),
  useRouter: () => ({ push }),
  useParams: () => useTestParams(),
}));

function RoutedPage({ params }: { params: { id: string } }) {
  return <TestRoute id={params.id}><PartiesPage /></TestRoute>;
}

beforeEach(() => {
  push.mockClear();
  window.localStorage.clear();
});

const analysisWithTwoParties = {
  id: "doc-1",
  status: "parsed",
  contract_name: null,
  preflight_metrics: null,
  preflight_diagnostics: [],
  validation_report: null,
  drafting_party_id: "p1",
  parties: [
    { id: "p1", name: "ООО А", role: "Арендодатель", confidence: 0.9 },
    { id: "p2", name: "АО Б", role: "Арендатор", confidence: 0.9 },
  ],
};

test("loads existing parties, builds protocol when none exists, navigates", async () => {
  let patchedPayload: unknown = null;
  let buildCalled = false;
  server.use(
    http.get("/api/documents/doc-1/analysis", () =>
      HttpResponse.json(analysisWithTwoParties),
    ),
    http.patch("/api/documents/doc-1/parties", async ({ request }) => {
      patchedPayload = await request.json();
      return HttpResponse.json(analysisWithTwoParties);
    }),
    http.get("/api/protocols", () => HttpResponse.json([])),
    http.post("/api/documents/doc-1/protocol", () => {
      buildCalled = true;
      return HttpResponse.json({ id: "proto-1", document_id: "doc-1", rows: [] });
    }),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);

  expect(screen.getByText("Читаем сведения о сторонах…")).toBeInTheDocument();

  expect(await screen.findByText("Стороны договора")).toBeInTheDocument();
  expect(screen.getByDisplayValue("ООО А")).toBeInTheDocument();
  expect(screen.getByDisplayValue("АО Б")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Построить протокол" }));

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-1/protocol"));
  expect(patchedPayload).toEqual({
    parties: [
      { id: "p1", name: "ООО А", role: "Арендодатель" },
      { id: "p2", name: "АО Б", role: "Арендатор" },
    ],
    drafting_party_id: "p1",
  });
  expect(buildCalled).toBe(true);
});

test("skips build if a protocol already exists", async () => {
  let buildCalled = false;
  server.use(
    http.get("/api/documents/doc-1/analysis", () =>
      HttpResponse.json(analysisWithTwoParties),
    ),
    http.patch("/api/documents/doc-1/parties", () =>
      HttpResponse.json(analysisWithTwoParties),
    ),
    http.get("/api/protocols", () =>
      HttpResponse.json([{ id: "proto-1", document_id: "doc-1", rows: [] }]),
    ),
    http.post("/api/documents/doc-1/protocol", () => {
      buildCalled = true;
      return HttpResponse.json({ id: "proto-1", document_id: "doc-1", rows: [] });
    }),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);
  await screen.findByText("Стороны договора");
  await userEvent.click(screen.getByRole("button", { name: "Построить протокол" }));

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-1/protocol"));
  expect(buildCalled).toBe(false);
});

test("disables submit when party count is not exactly two and shows warning", async () => {
  server.use(
    http.get("/api/documents/doc-9/analysis", () =>
      HttpResponse.json({
        ...analysisWithTwoParties,
        id: "doc-9",
        drafting_party_id: "p1",
        parties: [{ id: "p1", name: "Solo", role: "Сторона", confidence: 0.5 }],
      }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-9" }} />);
  await screen.findByText("Стороны договора");

  expect(screen.getByText("Для протокола нужны две стороны. Добавьте недостающую или удалите лишнюю.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Построить протокол" })).toBeDisabled();
});

test("surfaces fetch error", async () => {
  server.use(
    http.get("/api/documents/doc-err/analysis", () =>
      new HttpResponse("boom", { status: 500 }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-err" }} />);

  await waitFor(() => expect(screen.getByText(/500 boom/)).toBeInTheDocument());
});

const BUILD = "Построить протокол";
const PICK_SIDE = "Отметьте вашу сторону — от её имени будет составлен протокол.";
const FILL_IN = "Заполните наименование и роль каждой стороны.";

test("without a chosen side the requirements list explains why the button is disabled", async () => {
  server.use(
    http.get("/api/documents/doc-1/analysis", () =>
      HttpResponse.json({ ...analysisWithTwoParties, drafting_party_id: null }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);
  await screen.findByText("Стороны договора");

  const button = screen.getByRole("button", { name: BUILD });
  expect(button).toBeDisabled();
  expect(screen.getByText(PICK_SIDE)).toBeInTheDocument();
  expect(button).toHaveAccessibleDescription(/Отметьте вашу сторону/);

  await userEvent.click(screen.getByRole("radio", { name: "Составитель: ООО А" }));

  expect(screen.queryByText(PICK_SIDE)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: BUILD })).toBeEnabled();
});

test("a cleared name lists the missing fields until it is filled in again", async () => {
  server.use(
    http.get("/api/documents/doc-1/analysis", () => HttpResponse.json(analysisWithTwoParties)),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);
  await screen.findByText("Стороны договора");
  expect(screen.queryByText(FILL_IN)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: BUILD })).toBeEnabled();

  await userEvent.clear(screen.getByDisplayValue("ООО А"));

  expect(screen.getByText(FILL_IN)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: BUILD })).toBeDisabled();

  await userEvent.type(screen.getAllByPlaceholderText("Наименование")[0], "ООО Ромашка");

  expect(screen.queryByText(FILL_IN)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: BUILD })).toBeEnabled();
});

test("a failed load shows an error with «Повторить» that loads the parties on the second try", async () => {
  let calls = 0;
  server.use(
    http.get("/api/documents/doc-1/analysis", () => {
      calls += 1;
      return calls === 1 ? new HttpResponse("boom", { status: 500 }) : HttpResponse.json(analysisWithTwoParties);
    }),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось прочитать сведения о сторонах");
  expect(screen.getByRole("alert")).toHaveTextContent(/500 boom/);
  expect(screen.queryByText("Стороны договора")).not.toBeInTheDocument();
  expect(calls).toBe(1);

  await userEvent.click(screen.getByRole("button", { name: "Повторить" }));

  expect(await screen.findByText("Стороны договора")).toBeInTheDocument();
  expect(screen.getByDisplayValue("ООО А")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(calls).toBe(2);
});

test("does not show «Стороны договора» while the parties are still loading", async () => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  server.use(
    http.get("/api/documents/doc-1/analysis", async () => {
      await gate;
      return HttpResponse.json(analysisWithTwoParties);
    }),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);

  expect(screen.getByText("Читаем сведения о сторонах…")).toBeInTheDocument();
  expect(screen.queryByText("Стороны договора")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: BUILD })).not.toBeInTheDocument();

  release();
  expect(await screen.findByText("Стороны договора")).toBeInTheDocument();
  expect(screen.queryByText("Читаем сведения о сторонах…")).not.toBeInTheDocument();
});

test("a failed build keeps the form and shows the error next to it", async () => {
  server.use(
    http.get("/api/documents/doc-1/analysis", () => HttpResponse.json(analysisWithTwoParties)),
    http.patch("/api/documents/doc-1/parties", () => new HttpResponse("patch failed", { status: 500 })),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);
  await screen.findByText("Стороны договора");
  await userEvent.click(screen.getByRole("button", { name: BUILD }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/500 patch failed/);
  expect(screen.getByText("Стороны договора")).toBeInTheDocument();
  expect(screen.getByDisplayValue("ООО А")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: BUILD })).toBeEnabled();
  expect(push).not.toHaveBeenCalled();
});

test("remembers the document at the parties stage once it is loaded", async () => {
  server.use(
    http.get("/api/documents/doc-1/analysis", () =>
      HttpResponse.json({ ...analysisWithTwoParties, contract_name: "Договор аренды №7" }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);
  await screen.findByText("Стороны договора");

  expect(readRecentDocuments()).toEqual([
    { id: "doc-1", title: "Договор аренды №7", stage: "parties", openedAt: expect.any(Number) },
  ]);
});
