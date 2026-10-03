import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ExportPage from "@/app/documents/[id]/export/page";
import { server } from "@/src/mocks/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ id: "doc1" }),
}));

// jsdom does not implement these — stub them so the click-to-download
// flow can run end-to-end in tests.
const originalCreate = URL.createObjectURL;
const originalRevoke = URL.revokeObjectURL;

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => "blob:mock");
  URL.revokeObjectURL = vi.fn();
});

afterAll(() => {
  URL.createObjectURL = originalCreate;
  URL.revokeObjectURL = originalRevoke;
});

test("renders form with default filename and submit button", () => {
  render(<ExportPage />);
  expect(screen.getByRole("heading", { name: "Сохранение протокола" })).toBeInTheDocument();
  expect(screen.getByDisplayValue("Протокол разногласий")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled();
  expect(screen.getByText(/Протокол разногласий\.docx/)).toBeInTheDocument();
});

test("submits sanitized filename and triggers DOCX download", async () => {
  let received: { filename?: string } | null = null;
  server.use(
    http.post("/api/documents/doc1/protocol/export", async ({ request }) => {
      received = (await request.json()) as { filename?: string };
      return new HttpResponse(new Blob(["fake-docx"]), {
        status: 200,
        headers: {
          "Content-Type":
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
      });
    }),
  );

  // Spy on anchor click to verify the download attribute without leaving the page.
  const clickSpy = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(function (this: HTMLAnchorElement) {
      // Capture the download attribute the moment click fires.
      (clickSpy as unknown as { lastDownload?: string }).lastDownload =
        this.download;
    });

  render(<ExportPage />);

  const input = screen.getByLabelText(/Имя файла/);
  await userEvent.clear(input);
  // Path separators and control chars must be stripped.
  await userEvent.type(input, "report/v1");
  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

  await screen.findByText("Скачивание началось. Проверьте загрузки браузера.");

  expect(received).toEqual({ filename: "reportv1" });
  expect(
    (clickSpy as unknown as { lastDownload?: string }).lastDownload,
  ).toBe("reportv1.docx");

  clickSpy.mockRestore();
});

test("button disabled when filename sanitizes to empty", async () => {
  render(<ExportPage />);
  const input = screen.getByLabelText(/Имя файла/);
  await userEvent.clear(input);
  await userEvent.type(input, "   ");
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();
});

test("shows server error when export fails", async () => {
  server.use(
    http.post("/api/documents/doc1/protocol/export", () =>
      new HttpResponse("export blew up", { status: 500 }),
    ),
  );

  render(<ExportPage />);
  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

  await waitFor(() =>
    expect(screen.getByRole("alert")).toHaveTextContent(/500 export blew up/),
  );
  // Button is enabled again so the user can retry.
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled();
});

test("shows busy state while export is in flight", async () => {
  let release!: () => void;
  const gate = new Promise<void>((r) => {
    release = r;
  });

  server.use(
    http.post("/api/documents/doc1/protocol/export", async () => {
      await gate;
      return new HttpResponse(new Blob(["x"]), { status: 200 });
    }),
  );

  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

  render(<ExportPage />);
  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

  // Loading label visible, button disabled while in flight.
  const submitting = await screen.findByRole("button", { name: "Сохраняем…" });
  expect(submitting).toBeDisabled();
  expect(screen.getByLabelText(/Имя файла/)).toBeDisabled();

  release();
  await screen.findByText("Скачивание началось. Проверьте загрузки браузера.");
});
