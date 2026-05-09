import { FileUpload } from "@/components/FileUpload";

export default function Home() {
  return (
    <main className="max-w-3xl mx-auto py-16 px-4">
      <h1 className="text-3xl font-semibold mb-8">Протокол разногласий</h1>
      <FileUpload />
    </main>
  );
}
