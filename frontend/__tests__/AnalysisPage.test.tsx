import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import AnalysisPage from "@/app/documents/[id]/analysis/page";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockClear();
});

const baseAnalysis = {
  id: "doc-1",
  contract_name: null,
  parties: [],
  validation_report: null,
  drafting_party_id: null,
  preflight_diagnostics: [],
};

test("shows loading state, then preflight metrics and diagnostics, navigates on Дальше", async () => {
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

  render(<AnalysisPage params={{ id: "doc-1" }} />);

  expect(screen.getByText("Анализируем документ…")).toBeInTheDocument();

  expect(await screen.findByText("Предварительный отчёт")).toBeInTheDocument();
  expect(screen.getByText("Правок всего: 12")).toBeInTheDocument();
  expect(screen.getByText("Format-only: 3")).toBeInTheDocument();
  expect(screen.getByText("Уверенность нумерации: 82%")).toBeInTheDocument();
  expect(screen.getByText("low confidence")).toBeInTheDocument();
  expect(screen.getByText("broken xml")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Дальше" }));
  expect(push).toHaveBeenCalledWith("/documents/doc-1/parties");
});

test("shows failure error when status=failed", async () => {
  server.use(
    http.get("/api/documents/doc-2/analysis", () =>
      HttpResponse.json({
        ...baseAnalysis,
        id: "doc-2",
        status: "failed",
        preflight_metrics: null,
      }),
    ),
  );

  render(<AnalysisPage params={{ id: "doc-2" }} />);

  expect(await screen.findByText("Ошибка обработки документа")).toBeInTheDocument();
});

test("surfaces fetch error", async () => {
  server.use(
    http.get("/api/documents/doc-3/analysis", () =>
      new HttpResponse("nope", { status: 500 }),
    ),
  );

  render(<AnalysisPage params={{ id: "doc-3" }} />);

  await waitFor(() => expect(screen.getByText(/500 nope/)).toBeInTheDocument());
});
