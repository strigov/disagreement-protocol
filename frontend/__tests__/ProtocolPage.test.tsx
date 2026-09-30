import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ProtocolPage from "@/app/documents/[id]/protocol/page";
import ProtocolTable from "@/components/ProtocolTable";
import { server } from "@/src/mocks/server";
import { readRecentDocuments } from "@/lib/recent-documents";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => ({ id: "doc1" }),
}));

beforeEach(() => {
  push.mockClear();
});

// BASE_ANALYSIS matches AnalysisOut (frontend/lib/types.ts):
//   id (not document_id), preflight_metrics (not preflight),
//   validation_report (not validation_summary), contract_name, drafting_party_id.
const BASE_ANALYSIS = {
  id: "doc1",
  status: "ready",
  contract_name: null,
  parties: [
    { id: "p1", name: "ООО Лесси", role: "Арендодатель", confidence: 0.9 },
    { id: "p2", name: "ООО Тетя", role: "Арендатор", confidence: 0.9 },
  ],
  preflight_metrics: null,
  preflight_diagnostics: [],
  validation_report: null,
  drafting_party_id: "p2",
};

const ROW = {
  id: "r1",
  sort_order: 0,
  point_label: "1.1",
  party_1_text: "Текст контрагента",
  party_2_text: "Текст drafting",
  agreed_text: "Редакция Арендатора",
  source_clause_key: null,
  confidence: 0.9,
  flags: [] as string[],
  user_edited: false,
};

test("first build: getAnalysis is called only AFTER buildProtocol resolves", async () => {
  // Deferred build: the POST handler does not resolve until we explicitly
  // release it. This lets us assert getAnalysis was NOT called while the
  // build was in flight — proving sequential ordering rather than mere
  // co-occurrence (a parallel implementation would call getAnalysis before
  // we release the build, and the assertion would catch it).
  let releaseBuild!: () => void;
  const buildGate = new Promise<void>((resolve) => {
    releaseBuild = resolve;
  });
  let analysisCallCount = 0;
  let analysisCallsBeforeBuildResolved = 0;
  let buildResolved = false;

  server.use(
    // No existing protocol — listProtocolsForDocument returns empty array.
    http.get("/api/protocols", () => HttpResponse.json([])),
    // buildProtocol awaits the gate before responding.
    http.post("/api/documents/doc1/protocol", async () => {
      await buildGate;
      buildResolved = true;
      return HttpResponse.json({
        id: "p1",
        document_id: "doc1",
        rows: [{ ...ROW, flags: ["LOW_NUMBERING_CONFIDENCE"] }],
      });
    }),
    http.get("/api/documents/doc1/analysis", () => {
      analysisCallCount += 1;
      if (!buildResolved) {
        analysisCallsBeforeBuildResolved += 1;
      }
      return HttpResponse.json({
        ...BASE_ANALYSIS,
        validation_report: {
          textual_revisions_total: 1,
          format_only_revisions: 0,
          covered_revisions: 0,
          numbering_confidence_mean: 0.9,
          warnings: [
            {
              kind: "LOW_NUMBERING_CONFIDENCE",
              scope: "row",
              clause_key: null,
              row_id: "r1",
              message: "Низкая уверенность нумерации",
              severity: "warning",
            },
          ],
        },
      });
    }),
  );

  render(<ProtocolPage />);

  // Loading state while build is still pending.
  expect(screen.getByText("Строим таблицу…")).toBeInTheDocument();

  // Give any (mis-ordered) parallel getAnalysis a chance to fire. If the page
  // ran build and analysis in parallel, this microtask flush would let the
  // analysis request hit the handler before we release the build below.
  await new Promise((r) => setTimeout(r, 20));
  expect(analysisCallCount).toBe(0);

  // Now release the build and verify analysis runs only afterwards.
  releaseBuild();

  await screen.findByText("1.1");
  await screen.findByText(/Низкая уверенность нумерации/);

  expect(analysisCallCount).toBeGreaterThanOrEqual(1);
  expect(analysisCallsBeforeBuildResolved).toBe(0);
});

test("loads existing protocol without rebuilding", async () => {
  let buildCalled = false;

  server.use(
    http.get("/api/protocols", () =>
      HttpResponse.json([{ id: "p1", document_id: "doc1", rows: [] }]),
    ),
    http.get("/api/protocols/p1/rows", () =>
      HttpResponse.json({ id: "p1", document_id: "doc1", rows: [ROW] }),
    ),
    http.post("/api/documents/doc1/protocol", () => {
      buildCalled = true;
      return HttpResponse.json({ id: "p1", document_id: "doc1", rows: [] });
    }),
    http.get("/api/documents/doc1/analysis", () => HttpResponse.json(BASE_ANALYSIS)),
  );

  render(<ProtocolPage />);
  await screen.findByText("1.1");
  expect(buildCalled).toBe(false);
});

test("loading state shown before protocol resolves", async () => {
  server.use(
    http.get("/api/protocols", () => HttpResponse.json([])),
    http.post("/api/documents/doc1/protocol", () =>
      HttpResponse.json({ id: "p1", document_id: "doc1", rows: [] }),
    ),
    http.get("/api/documents/doc1/analysis", () => HttpResponse.json(BASE_ANALYSIS)),
  );

  render(<ProtocolPage />);
  expect(screen.getByText("Строим таблицу…")).toBeInTheDocument();
  // Empty-rows state then renders.
  await screen.findByText(/В протоколе пока нет строк/);
});

test("surfaces error when build fails", async () => {
  server.use(
    http.get("/api/protocols", () => HttpResponse.json([])),
    http.post("/api/documents/doc1/protocol", () =>
      new HttpResponse("oops", { status: 500 }),
    ),
  );

  render(<ProtocolPage />);
  await waitFor(() =>
    expect(screen.getByText("Не удалось загрузить протокол")).toBeInTheDocument(),
  );
  expect(screen.getByText(/500 oops/)).toBeInTheDocument();
});

test("export opens a dialog without leaving the editor", async () => {
  server.use(
    http.get("/api/protocols", () =>
      HttpResponse.json([{ id: "p1", document_id: "doc1", rows: [] }]),
    ),
    http.get("/api/protocols/p1/rows", () =>
      HttpResponse.json({ id: "p1", document_id: "doc1", rows: [ROW] }),
    ),
    http.get("/api/documents/doc1/analysis", () => HttpResponse.json(BASE_ANALYSIS)),
  );

  render(<ProtocolPage />);
  await screen.findByText("1.1");

  await userEvent.click(screen.getByRole("button", { name: "Экспорт DOCX" }));
  expect(await screen.findByRole("dialog", { name: "Скачать протокол" })).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

// --- ProtocolTable in isolation -------------------------------------------------

const baseProps = {
  draftingRole: "Арендатор",
  counterpartyRole: "Арендодатель",
  onDelete: vi.fn(),
  onMerge: vi.fn(),
  onAddRow: vi.fn(),
  onSwapParties: vi.fn(),
};

test("blur without change does not call onPatch", async () => {
  const onPatch = vi.fn();
  render(<ProtocolTable {...baseProps} rows={[ROW]} onPatch={onPatch} />);

  await userEvent.click(screen.getByText("1.1"));
  // Edit input now visible — blur without typing.
  await userEvent.tab();
  expect(onPatch).not.toHaveBeenCalled();
});

test("editing a cell and blurring with new value calls onPatch", async () => {
  const onPatch = vi.fn().mockResolvedValue(undefined);
  render(<ProtocolTable {...baseProps} rows={[ROW]} onPatch={onPatch} />);

  await userEvent.click(screen.getByText("1.1"));
  const input = screen.getByDisplayValue("1.1");
  await userEvent.clear(input);
  await userEvent.type(input, "2.5");
  await userEvent.tab();

  await waitFor(() => expect(onPatch).toHaveBeenCalledTimes(1));
  expect(onPatch).toHaveBeenCalledWith("r1", { point_label: "2.5" });
});

test("escape cancels edit without calling onPatch", async () => {
  const onPatch = vi.fn();
  render(<ProtocolTable {...baseProps} rows={[ROW]} onPatch={onPatch} />);

  await userEvent.click(screen.getByText("1.1"));
  const input = screen.getByDisplayValue("1.1");
  await userEvent.clear(input);
  await userEvent.type(input, "999");
  await userEvent.keyboard("{Escape}");
  expect(onPatch).not.toHaveBeenCalled();
});

test("low-confidence row shows warning badge", () => {
  render(
    <ProtocolTable
      {...baseProps}
      rows={[{ ...ROW, confidence: 0.5 }]}
      onPatch={vi.fn()}
    />,
  );
  expect(screen.getByLabelText(/Низкая уверенность: 50%/)).toBeInTheDocument();
});

test("empty rows render explicit empty state", () => {
  render(<ProtocolTable {...baseProps} rows={[]} onPatch={vi.fn()} />);
  expect(screen.getByText(/В протоколе пока нет строк/)).toBeInTheDocument();
});

test("toolbar buttons dispatch add and swap", async () => {
  const onAddRow = vi.fn().mockResolvedValue(undefined);
  const onSwapParties = vi.fn().mockResolvedValue(undefined);
  render(
    <ProtocolTable
      {...baseProps}
      rows={[ROW]}
      onPatch={vi.fn()}
      onAddRow={onAddRow}
      onSwapParties={onSwapParties}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: /Добавить строку/ }));
  expect(onAddRow).toHaveBeenCalledTimes(1);

  await userEvent.click(screen.getByRole("button", { name: /Поменять стороны/ }));
  expect(onSwapParties).toHaveBeenCalledTimes(1);
});

test("failed onPatch preserves draft and keeps cell in edit mode", async () => {
  // Regression: a previous version exited edit mode synchronously on blur and
  // swallowed the rejection in setError, permanently losing the user's text.
  const onPatch = vi.fn().mockRejectedValue(new Error("network down"));
  render(<ProtocolTable {...baseProps} rows={[ROW]} onPatch={onPatch} />);

  await userEvent.click(screen.getByText("1.1"));
  const input = screen.getByDisplayValue("1.1");
  await userEvent.clear(input);
  await userEvent.type(input, "9.9");
  await userEvent.tab();

  await waitFor(() => expect(onPatch).toHaveBeenCalledTimes(1));
  // After the failed save, the draft is still visible AND the input is still
  // present (cell did not exit edit mode), so the user can retry.
  await screen.findByRole("alert");
  expect(screen.getByDisplayValue("9.9")).toBeInTheDocument();
});

test("merge and delete are disabled while a row save is in flight", async () => {
  // Regression: merge/delete on a row with an unsaved edit could clobber
  // the in-flight PATCH.
  let resolvePatch!: () => void;
  const patchGate = new Promise<void>((resolve) => {
    resolvePatch = resolve;
  });
  const onPatch = vi.fn().mockImplementation(() => patchGate);
  const onMerge = vi.fn();
  const onDelete = vi.fn();
  render(
    <ProtocolTable
      {...baseProps}
      rows={[ROW]}
      onPatch={onPatch}
      onMerge={onMerge}
      onDelete={onDelete}
    />,
  );

  await userEvent.click(screen.getByText("1.1"));
  const input = screen.getByDisplayValue("1.1");
  await userEvent.clear(input);
  await userEvent.type(input, "5.5");
  await userEvent.tab();

  // Save is in flight (gate not yet released).
  await waitFor(() => expect(onPatch).toHaveBeenCalledTimes(1));

  // Open the actions menu and confirm merge/delete are disabled.
  await userEvent.click(screen.getByLabelText("Действия со строкой"));
  const mergePrev = screen.getByRole("button", { name: /Объединить с предыдущей/ });
  const del = screen.getByRole("button", { name: /Исключить/ });
  expect(mergePrev).toBeDisabled();
  expect(del).toBeDisabled();

  // Releasing the save unblocks the row.
  resolvePatch();
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /Объединить с предыдущей/ }),
    ).not.toBeDisabled(),
  );
});

test("editing a second cell is blocked while the first cell's save is in flight", async () => {
  // Regression Ф17-R2-B1: two concurrent PATCHes on the same row would race —
  // whichever response arrived last would clobber the other cell's value
  // when state was set from a stale snapshot. Activation must be gated per
  // row until the in-flight save resolves.
  let resolvePatch!: () => void;
  const patchGate = new Promise<void>((resolve) => {
    resolvePatch = resolve;
  });
  const onPatch = vi.fn().mockImplementation(() => patchGate);
  render(<ProtocolTable {...baseProps} rows={[ROW]} onPatch={onPatch} />);

  // Begin editing cell 1 (point_label) and trigger a save.
  await userEvent.click(screen.getByText("1.1"));
  const input = screen.getByDisplayValue("1.1");
  await userEvent.clear(input);
  await userEvent.type(input, "5.5");
  await userEvent.tab();

  await waitFor(() => expect(onPatch).toHaveBeenCalledTimes(1));

  // While the first save is still pending, attempt to activate a different
  // cell of the same row. It must NOT enter edit mode (no input rendered).
  await userEvent.click(screen.getByText("Текст контрагента"));
  expect(screen.queryByDisplayValue("Текст контрагента")).not.toBeInTheDocument();

  // After the save resolves, that cell is editable again.
  resolvePatch();
  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  await userEvent.click(screen.getByText("Текст контрагента"));
  expect(screen.getByDisplayValue("Текст контрагента")).toBeInTheDocument();
});

test("row actions menu offers merge and delete", async () => {
  const onMerge = vi.fn().mockResolvedValue(undefined);
  const onDelete = vi.fn().mockResolvedValue(undefined);
  render(
    <ProtocolTable
      {...baseProps}
      rows={[ROW]}
      onPatch={vi.fn()}
      onMerge={onMerge}
      onDelete={onDelete}
    />,
  );

  // Choosing an item closes the menu, so it is reopened for the next action.
  await userEvent.click(screen.getByLabelText("Действия со строкой"));
  await userEvent.click(screen.getByRole("button", { name: /Объединить с предыдущей/ }));
  expect(onMerge).toHaveBeenCalledWith("r1", "previous");

  await userEvent.click(screen.getByLabelText("Действия со строкой"));
  await userEvent.click(screen.getByRole("button", { name: "Исключить из протокола" }));
  expect(onDelete).not.toHaveBeenCalled();
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Исключить" }));
  expect(onDelete).toHaveBeenCalledWith("r1");
});

test("load error offers a retry that reuses the existing protocol", async () => {
  let listCalls = 0;
  let buildCalled = false;
  server.use(
    http.get("/api/protocols", () => {
      listCalls += 1;
      return listCalls === 1
        ? new HttpResponse("offline", { status: 503 })
        : HttpResponse.json([{ id: "p1", document_id: "doc1", rows: [] }]);
    }),
    http.get("/api/protocols/p1/rows", () =>
      HttpResponse.json({ id: "p1", document_id: "doc1", rows: [ROW] }),
    ),
    http.post("/api/documents/doc1/protocol", () => {
      buildCalled = true;
      return HttpResponse.json({ id: "p1", document_id: "doc1", rows: [] });
    }),
    http.get("/api/documents/doc1/analysis", () => HttpResponse.json(BASE_ANALYSIS)),
  );

  render(<ProtocolPage />);
  expect(await screen.findByRole("heading", { name: "Не удалось загрузить протокол" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Повторить" }));
  await screen.findByText("1.1");
  expect(buildCalled).toBe(false);
  expect(listCalls).toBe(2);
});

test("opening the protocol remembers the document for the home page", async () => {
  window.localStorage.clear();
  server.use(
    http.get("/api/protocols", () =>
      HttpResponse.json([{ id: "p1", document_id: "doc1", rows: [] }]),
    ),
    http.get("/api/protocols/p1/rows", () =>
      HttpResponse.json({ id: "p1", document_id: "doc1", rows: [ROW] }),
    ),
    http.get("/api/documents/doc1/analysis", () =>
      HttpResponse.json({ ...BASE_ANALYSIS, contract_name: "Договор аренды" }),
    ),
  );

  render(<ProtocolPage />);
  await screen.findByText("1.1");
  await waitFor(() => expect(readRecentDocuments()).toEqual([
    expect.objectContaining({ id: "doc1", title: "Договор аренды", stage: "protocol" }),
  ]));
});
