"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { ExportForm } from "@/components/ExportForm";

export default function ExportPage() {
  const params = useParams<{ id: string }>();
  return <WorkspaceShell step={3} documentId={params.id}>
    <div className="max-w-lg mx-auto">
      <Link className="btn btn-quiet mb-5" href={`/documents/${params.id}/protocol`}><ArrowLeft size={14} /> Вернуться к протоколу</Link>
      <h1 className="page-title">Экспорт</h1>
      <p className="page-description mb-6">Сохраните протокол разногласий в формате DOCX.</p>
      <div className="surface !p-0"><ExportForm documentId={params.id} /></div>
    </div>
  </WorkspaceShell>;
}
