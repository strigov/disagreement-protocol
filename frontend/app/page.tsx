import { FileUpload } from "@/components/FileUpload";
import { WorkspaceShell } from "@/components/WorkspaceShell";

export default function Home() {
  return (
    <WorkspaceShell>
      <div className="eyebrow">От правок — к готовому документу</div>
      <h1 className="page-title">Протокол разногласий.<br />Каждая правка на своём месте.</h1>
      <p className="page-description">Загрузите договор с исправлениями Word. Проверьте редакции сторон и получите готовый протокол в формате DOCX.</p>
      <FileUpload />
      <div className="intro-steps">
        <section><span className="intro-number">01 / ДОКУМЕНТ</span><h2>Загрузите договор</h2><p>Используйте файл с правками в режиме рецензирования Word.</p></section>
        <section><span className="intro-number">02 / СТОРОНЫ</span><h2>Укажите вашу сторону</h2><p>Проверьте названия и выберите, от чьего имени составить протокол.</p></section>
        <section><span className="intro-number">03 / ПРОТОКОЛ</span><h2>Проверьте и скачайте</h2><p>Сравните изменения по пунктам и сохраните итоговый документ.</p></section>
      </div>
    </WorkspaceShell>
  );
}
