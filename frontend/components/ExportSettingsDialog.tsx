import { useState, type CSSProperties } from "react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { FONT_COLORS, HIGHLIGHT_COLORS, useExportSettings, writeExportSettings, type ChangeStyle, type ExportSettings } from "@/lib/export-settings";

function StyleEditor({ title, value, deletion, onChange }: {
  title: string; value: ChangeStyle; deletion?: boolean; onChange: (value: ChangeStyle) => void;
}) {
  const patch = (change: Partial<ChangeStyle>) => onChange({ ...value, ...change });
  const sample: CSSProperties = {
    color: value.color ? `#${value.color}` : "var(--paper-ink)",
    backgroundColor: value.highlight ? `#${HIGHLIGHT_COLORS.find(([color]) => color === value.highlight)?.[2]}` : undefined,
    fontWeight: value.bold ? 700 : 400,
    fontStyle: value.italic ? "italic" : "normal",
    textDecoration: [value.underline && "underline", value.strike && "line-through"].filter(Boolean).join(" ") || "none",
  };
  return <fieldset className="min-w-0 space-y-4 rounded-md border border-line-c p-4">
    <legend className="px-1 text-sm font-semibold">{title}</legend>
    <div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value.color !== null} onChange={(e) => patch({ color: e.target.checked ? deletion ? "FF0000" : "00B050" : null })} />Цвет текста</label>
      <div role="group" aria-label="Стандартные цвета Word" className="mt-2 flex flex-wrap gap-1.5">
        {FONT_COLORS.map(([color, label]) => <button key={color} type="button" title={label} aria-label={`Цвет текста: ${label}`} aria-pressed={value.color === color}
          className="grid h-7 w-7 place-items-center rounded-sm border border-line-strong outline-offset-2 focus-visible:outline focus-visible:outline-accent"
          style={{ backgroundColor: `#${color}`, color: ["000000", "C00000", "0070C0", "002060", "7030A0"].includes(color) ? "white" : "black" }}
          onClick={() => patch({ color })}>{value.color === color && <span aria-hidden="true">✓</span>}</button>)}
      </div>
    </div>
    <div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value.highlight !== null} onChange={(e) => patch({ highlight: e.target.checked ? "yellow" : null })} />Выделение маркером</label>
      <div role="group" aria-label="Цвета маркера Word" className="mt-2 flex flex-wrap gap-1.5">
        {HIGHLIGHT_COLORS.map(([color, label, hex]) => <button key={color} type="button" title={label} aria-label={`Маркер: ${label}`} aria-pressed={value.highlight === color}
          className="grid h-7 w-7 place-items-center rounded-sm border border-line-strong outline-offset-2 focus-visible:outline focus-visible:outline-accent"
          style={{ backgroundColor: `#${hex}`, color: color.startsWith("dark") || ["black", "blue"].includes(color) ? "white" : "black" }}
          onClick={() => patch({ highlight: color })}>{value.highlight === color && <span aria-hidden="true">✓</span>}</button>)}
      </div>
    </div>
    <div className="grid grid-cols-2 gap-2 text-sm">
      {([["bold", "Полужирный"], ["italic", "Курсив"], ["underline", "Подчёркнутый"], ...(deletion ? [["strike", "Зачёркнутый"]] : [])] as ["bold" | "italic" | "underline" | "strike", string][]).map(([key, label]) =>
        <label key={key} className="flex items-center gap-2"><input type="checkbox" checked={!!value[key]} onChange={(e) => patch({ [key]: e.target.checked })} />{label}</label>)}
    </div>
    <p className="rounded-sm border border-line-c bg-paper p-3 font-serif text-base text-paper-ink">Срок оплаты — <span style={sample}>{deletion ? "10" : "15"} дней</span>.</p>
  </fieldset>;
}

export function ExportSettingsDialog({ onClose }: { onClose: () => void }) {
  const settings = useExportSettings();
  const [storageError, setStorageError] = useState(false);
  const change = (value: ExportSettings) => setStorageError(!writeExportSettings(value));
  return <Dialog title="Настройки" description="Выделение изменений в DOCX" onClose={onClose} size="wide">
    <div className="space-y-5">
      <label className="flex items-center gap-3 text-sm font-medium"><input type="checkbox" checked={settings.enabled} onChange={(e) => change({ ...settings, enabled: e.target.checked })} />Выделять изменения в DOCX</label>
      <p className="text-sm text-ink-2">Выберите один или несколько способов для каждой редакции. Настройки сохраняются автоматически и применяются при следующем экспорте.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <StyleEditor title="Удаления · исходная редакция" value={settings.deletions} deletion onChange={(deletions) => change({ ...settings, deletions })} />
        <StyleEditor title="Добавления · предлагаемая редакция" value={settings.additions} onChange={(additions) => change({ ...settings, additions })} />
      </div>
      {storageError && <Notice tone="warn" role="alert">Не удалось сохранить настройки на устройстве. Они действуют до закрытия приложения.</Notice>}
      <div className="flex justify-end"><Button variant="primary" onClick={onClose}>Готово</Button></div>
    </div>
  </Dialog>;
}
