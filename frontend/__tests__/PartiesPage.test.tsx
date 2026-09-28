import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import PartiesPage from "@/app/documents/[id]/parties/page";
import { TestRoute, useTestParams } from "./route-context";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => useTestParams(),
}));

function RoutedPage({ params }: { params: { id: string } }) {
  return <TestRoute id={params.id}><PartiesPage /></TestRoute>;
}

beforeEach(() => {
  push.mockClear();
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

  expect(screen.getByText("Загружаем…")).toBeInTheDocument();

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
