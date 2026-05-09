import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { FileUpload } from "@/components/FileUpload";
import { server } from "@/src/mocks/server";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockClear();
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
