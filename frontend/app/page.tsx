import { FileUpload } from "@/components/FileUpload";
import { RecentDocuments } from "@/components/RecentDocuments";
import { WorkspaceShell } from "@/components/WorkspaceShell";
import { PageHeader } from "@/components/ui/PageHeader";

const STEPS = [
  { rubric: "01 / Документ", title: "Загрузите договор", text: "Используйте файл с правками в режиме рецензирования Word." },
  { rubric: "02 / Стороны", title: "Укажите вашу сторону", text: "Проверьте названия и выберите, от чьего имени составить протокол." },
  { rubric: "03 / Протокол", title: "Проверьте и скачайте", text: "Сравните изменения по пунктам и сохраните итоговый документ." },
] as const;

export default function Home() {
  return (
    <WorkspaceShell>
      <PageHeader
        rubric="От правок — к готовому документу"
        title={<>Протокол разногласий.{" "}<br className="max-sm:hidden" />Каждая правка на своём месте.</>}
        description="Загрузите договор с исправлениями Word. Проверьте редакции сторон и получите готовый протокол в формате DOCX."
      />
      <div className="mt-10">
        <FileUpload />
      </div>
      <RecentDocuments />
      <section aria-labelledby="how-it-works-title" className="mt-16 md:mt-20">
        <h2 id="how-it-works-title" className="font-serif text-xl font-semibold text-ink">как это работает</h2>
        <ol className="mt-6 grid gap-8 md:grid-cols-3 md:gap-8">
          {STEPS.map((step) => (
            <li key={step.rubric} className="border-t border-line-strong pt-4">
              <p className="rubric">{step.rubric}</p>
              <h3 className="mt-3 font-serif text-xl font-semibold leading-snug text-ink">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </WorkspaceShell>
  );
}
