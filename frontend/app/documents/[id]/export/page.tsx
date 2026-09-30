"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { ExportForm } from "@/components/ExportForm";
import { Icon } from "@/components/icons/Icon";
import { buttonClassName } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ExportPage() {
  const params = useParams<{ id: string }>();
  return <WorkspaceShell step={3} documentId={params.id}>
    <div className="mx-auto max-w-lg">
      <Link className={buttonClassName({ variant: "ghost", size: "sm", className: "mb-8" })} href={`/documents/${params.id}/protocol`}>
        <Icon name="arrow-left" /> Вернуться к протоколу
      </Link>
      <PageHeader rubric="Экспорт DOCX" title="Экспорт" description="Сохраните протокол разногласий в формате DOCX." />
      <div className="mt-8 rounded-md border border-line-c bg-bg-elev p-6 shadow-sm">
        <ExportForm documentId={params.id} />
      </div>
    </div>
  </WorkspaceShell>;
}
