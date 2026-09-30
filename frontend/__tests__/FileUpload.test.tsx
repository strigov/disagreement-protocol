import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { FileUpload } from "@/components/FileUpload";
import { readRecentDocuments } from "@/lib/recent-documents";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockClear();
  window.localStorage.clear();
});

const docx = (name: string) =>
  new File(["docx"], name, {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });

test("uploads selected docx and navigates to analysis page", async () => {
  const seenFiles: string[] = [];
  server.use(
    http.post("/api/documents", async ({ request }) => {
      const form = await request.formData();
      const file = form.get("file");
      if (file instanceof File) {
        seenFiles.push(file.name);
      }
      return HttpResponse.json({ id: "doc-123", status: "uploaded" });
    }),
  );

  render(<FileUpload />);

  const input = screen.getByLabelText("Выбрать файл");
  const file = new File(["docx"], "contract.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  await userEvent.upload(input, file);

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-123/analysis"));
  expect(seenFiles).toEqual(["contract.docx"]);
});

test("uploads dropped docx and shows server errors", async () => {
  server.use(
    http.post("/api/documents", () => new HttpResponse("upload failed", { status: 500 })),
  );

  render(<FileUpload />);

  const dropZone = screen.getByText("Перетащите .docx сюда или выберите файл").closest("div");
  expect(dropZone).not.toBeNull();
  const file = new File(["docx"], "bad.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });

  fireEvent.drop(dropZone!, {
    dataTransfer: {
      files: [file],
    },
  });

  expect(await screen.findByText("500 upload failed")).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

test("shows only the FastAPI detail for a rejected upload", async () => {
  server.use(
    http.post("/api/documents", () =>
      HttpResponse.json(
        { detail: "Поддерживаются только файлы .docx без макросов" },
        { status: 400 },
      ),
    ),
  );

  render(<FileUpload />);
  await userEvent.upload(screen.getByLabelText("Выбрать файл"), docx("macros.docx"));

  expect(
    await screen.findByText("Поддерживаются только файлы .docx без макросов"),
  ).toBeInTheDocument();
  // The raw JSON envelope and the bare status code never reach the user.
  expect(screen.queryByText(/detail/)).not.toBeInTheDocument();
  expect(screen.queryByText(/400/)).not.toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

test("joins FastAPI validation messages into one line", async () => {
  server.use(
    http.post("/api/documents", () =>
      HttpResponse.json(
        {
          detail: [
            { loc: ["body", "file"], msg: "Field required", type: "missing" },
            { loc: ["body", "file"], msg: "Файл пустой", type: "value_error" },
          ],
        },
        { status: 422 },
      ),
    ),
  );

  render(<FileUpload />);
  await userEvent.upload(screen.getByLabelText("Выбрать файл"), docx("empty.docx"));

  expect(await screen.findByText("Field required; Файл пустой")).toBeInTheDocument();
});

test("falls back to a Russian message when the error body is empty", async () => {
  server.use(
    http.post("/api/documents", () => new HttpResponse(null, { status: 502 })),
  );

  render(<FileUpload />);
  await userEvent.upload(screen.getByLabelText("Выбрать файл"), docx("gateway.docx"));

  expect(await screen.findByText("Ошибка запроса (HTTP 502)")).toBeInTheDocument();
});

test("remembers a successfully uploaded document in the recent list", async () => {
  server.use(
    http.post("/api/documents", () => HttpResponse.json({ id: "doc-123", status: "uploaded" })),
  );

  render(<FileUpload />);
  await userEvent.upload(screen.getByLabelText("Выбрать файл"), docx("contract.docx"));

  await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-123/analysis"));
  expect(readRecentDocuments()).toEqual([
    { id: "doc-123", title: "contract", stage: "analysis", openedAt: expect.any(Number) },
  ]);
});

test("a failed or rejected upload is not added to the recent list", async () => {
  server.use(
    http.post("/api/documents", () => new HttpResponse("upload failed", { status: 500 })),
  );

  render(<FileUpload />);
  await userEvent.upload(screen.getByLabelText("Выбрать файл"), docx("broken.docx"));
  expect(await screen.findByText("500 upload failed")).toBeInTheDocument();

  fireEvent.drop(screen.getByText("Перетащите .docx сюда или выберите файл").closest("div")!, {
    dataTransfer: { files: [new File(["pdf"], "scan.pdf", { type: "application/pdf" })] },
  });
  expect(
    await screen.findByText("Выберите договор в формате .docx. Файлы .doc и .pdf не поддерживаются."),
  ).toBeInTheDocument();

  expect(readRecentDocuments()).toEqual([]);
});
