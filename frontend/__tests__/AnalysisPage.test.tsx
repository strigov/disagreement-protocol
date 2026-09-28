import { render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import AnalysisPage from "@/app/documents/[id]/analysis/page";
import { TestRoute, useTestParams } from "./route-context";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => useTestParams(),
}));

function RoutedPage({ params }: { params: { id: string } }) {
  return <TestRoute id={params.id}><AnalysisPage /></TestRoute>;
}

beforeEach(() => {
  push.mockClear();
});

// The page polls once a second. Sitting out a full interval (plus slack) is
// what turns "no second request yet" into "no second request was scheduled".
const POLL_INTERVAL_MS = 1000;
const waitPastPollInterval = () =>
  new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS + 250));

const baseAnalysis = {
  id: "doc-1",
  contract_name: null,
  parties: [],
  validation_report: null,
  drafting_party_id: null,
  preflight_metrics: null,
  preflight_diagnostics: [],
  error_message: null,
};

test("shows loading then goes directly to party confirmation", async () => {
  server.use(
    http.get("/api/documents/doc-1/analysis", () =>
      HttpResponse.json({
        ...baseAnalysis,
        status: "parsed",
        preflight_metrics: {
          revisions_total: 12,
          format_only_count: 3,
          paragraphs_with_numbering: 7,
          numbering_confidence_mean: 0.82,
        },
        preflight_diagnostics: [
          { level: "warning", component: "Numbering", code: "X1", message: "low confidence", block_id: "b1" },
          { level: "error", component: "Parser", code: "X2", message: "broken xml", block_id: null },
        ],
      }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-1" }} />);

  expect(screen.getByText("Анализируем документ…")).toBeInTheDocument();

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-1/parties"));
  expect(screen.queryByText("Анализируем документ…")).not.toBeInTheDocument();
});

test("already built document returns to the existing protocol", async () => {
  server.use(
    http.get("/api/documents/doc-empty/analysis", () =>
      HttpResponse.json({ ...baseAnalysis, id: "doc-empty", status: "built" }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-empty" }} />);

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-empty/protocol"));
});

// Every status that is not `uploaded`/`parsing` is terminal: the screen must
// settle on a final view and must not schedule another request. `quarantined`
// stands in for a status this frontend has never heard of — the failure mode
// being fixed here is exactly "unknown status keeps the spinner alive".
const REPORT_STATUSES = ["parsed", "parties_confirmed", "built", "exported"];
const TERMINAL_STATUSES = [...REPORT_STATUSES, "failed", "quarantined"];

test("every terminal status settles the screen and stops polling", async () => {
  // The document id doubles as the status the handler answers with.
  const calls: Record<string, number> = {};
  server.use(
    http.get("/api/documents/:id/analysis", ({ params }) => {
      const status = String(params.id);
      calls[status] = (calls[status] ?? 0) + 1;
      return HttpResponse.json({ ...baseAnalysis, id: status, status });
    }),
  );

  const views = TERMINAL_STATUSES.map((status) =>
    render(<RoutedPage params={{ id: status }} />),
  );

  await waitFor(() =>
    views.forEach((view) =>
      expect(
        within(view.container).queryByText("Анализируем документ…"),
      ).not.toBeInTheDocument(),
    ),
  );

  views.forEach((view, i) => {
    const scope = within(view.container);
    if (REPORT_STATUSES.includes(TERMINAL_STATUSES[i])) {
      expect(scope.getByRole("status")).toBeInTheDocument();
    } else {
      expect(scope.getByRole("alert")).toBeInTheDocument();
    }
  });

  await waitPastPollInterval();

  expect(calls).toEqual(
    Object.fromEntries(TERMINAL_STATUSES.map((status) => [status, 1])),
  );
});

test("polls while the backend is still working and stops once it settles", async () => {
  // Each document answers with its own non-terminal status once, then `parsed`.
  const calls: Record<string, number> = { uploaded: 0, parsing: 0 };
  server.use(
    http.get("/api/documents/:id/analysis", ({ params }) => {
      const pending = String(params.id);
      calls[pending] += 1;
      return HttpResponse.json({
        ...baseAnalysis,
        id: pending,
        status: calls[pending] === 1 ? pending : "parsed",
      });
    }),
  );

  const views = ["uploaded", "parsing"].map((id) =>
    render(<RoutedPage params={{ id }} />),
  );
  views.forEach((view) =>
    expect(within(view.container).getByText("Анализируем документ…")).toBeInTheDocument(),
  );

  await waitFor(
    () =>
      views.forEach((view) =>
        expect(
          within(view.container).getByRole("status"),
        ).toHaveTextContent("Документ готов к проверке"),
      ),
    { timeout: 3000 },
  );
  // Two requests each: the pending status, then the poll that found `parsed`.
  expect(calls).toEqual({ uploaded: 2, parsing: 2 });

  await waitPastPollInterval();
  expect(calls).toEqual({ uploaded: 2, parsing: 2 });
});

test("failed document shows the reason reported by the backend", async () => {
  server.use(
    http.get("/api/documents/doc-2/analysis", () =>
      HttpResponse.json({
        ...baseAnalysis,
        id: "doc-2",
        status: "failed",
        error_message: "Ошибка разбора OOXML: недопустимый XML-узел",
      }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-2" }} />);

  expect(
    await screen.findByText("Ошибка разбора OOXML: недопустимый XML-узел"),
  ).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("Документ не удалось обработать");
  expect(screen.queryByText("Ошибка обработки документа")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Загрузить другой документ" })).toHaveAttribute(
    "href",
    "/",
  );
});

test.each([
  ["null", null],
  ["blank", "   "],
  ["absent", undefined],
])("failed document falls back to a Russian reason when error_message is %s", async (_case, value) => {
  const payload: Record<string, unknown> = {
    ...baseAnalysis,
    id: "doc-3",
    status: "failed",
  };
  if (value === undefined) {
    delete payload.error_message;
  } else {
    payload.error_message = value;
  }
  server.use(
    http.get("/api/documents/doc-3/analysis", () => HttpResponse.json(payload)),
  );

  render(<RoutedPage params={{ id: "doc-3" }} />);

  expect(await screen.findByText("Ошибка обработки документа")).toBeInTheDocument();
});

test("unknown status names itself instead of spinning", async () => {
  server.use(
    http.get("/api/documents/doc-x/analysis", () =>
      HttpResponse.json({ ...baseAnalysis, id: "doc-x", status: "quarantined" }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-x" }} />);

  expect(await screen.findByText(/Сервер вернул статус «quarantined»/)).toBeInTheDocument();
  expect(screen.queryByText("Анализируем документ…")).not.toBeInTheDocument();
});

test("surfaces fetch error", async () => {
  server.use(
    http.get("/api/documents/doc-4/analysis", () =>
      new HttpResponse("nope", { status: 500 }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-4" }} />);

  await waitFor(() => expect(screen.getByText(/500 nope/)).toBeInTheDocument());
  expect(screen.getByRole("alert")).toHaveTextContent("Не удалось загрузить анализ");
});

test("shows only the FastAPI detail when the analysis request fails", async () => {
  server.use(
    http.get("/api/documents/doc-5/analysis", () =>
      HttpResponse.json({ detail: "Документ не найден" }, { status: 404 }),
    ),
  );

  render(<RoutedPage params={{ id: "doc-5" }} />);

  expect(await screen.findByText("Документ не найден")).toBeInTheDocument();
  expect(screen.queryByText(/detail/)).not.toBeInTheDocument();
  expect(screen.queryByText(/404/)).not.toBeInTheDocument();
});
