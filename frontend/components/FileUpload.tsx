"use client";

import { useState, type ChangeEvent, type DragEvent } from "react";
import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function FileUpload() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <FileUploadForm />
    </QueryClientProvider>
  );
}

function FileUploadForm() {
  const router = useRouter();
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDocument(file),
    onSuccess: (res) => {
      router.push(`/documents/${res.id}/analysis`);
    },
  });

  const handle = (file: File) => {
    upload.reset();
    upload.mutate(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) handle(f);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handle(f);
  };

  const error = upload.error instanceof Error ? upload.error.message : null;

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center bg-white"
    >
      <p className="mb-4 text-lg">Перетащите .docx сюда или выберите файл</p>
      <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700">
        Выбрать файл
        <input type="file" accept=".docx" onChange={onPick} className="hidden" />
      </label>
      {upload.isPending && <p className="mt-4 text-gray-500">Загружаем...</p>}
      {error && <p className="mt-4 text-red-600">{error}</p>}
    </div>
  );
}
