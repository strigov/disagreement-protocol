# Тестовые документы

Файлы генерируются скриптом `scripts/make_samples.py` (перегенерация: `cd backend && uv run python ../scripts/make_samples.py`).
Это настоящие OOXML-пакеты: Track Changes, автонумерация и стили лежат в `word/document.xml`,
`word/numbering.xml` и `word/styles.xml` в том же виде, в каком их пишет Word.

| Файл | Что проверяет | Ожидаемый результат |
| --- | --- | --- |
| `01_simple_manual_numbering.docx` | Ручная нумерация в тексте (`1.`, `1.1.`), вставка, удаление, замена | 3 строки протокола, стороны извлечены, номера из текста (уверенность 0.7) |
| `02_medium_auto_numbering.docx` | Автонумерация Word, новый пункт целиком, удалённый пункт целиком, таблица без правок | 4 строки, флаги `NEW_CLAUSE` и `DELETED_CLAUSE`, номера 1.1–3.1 |
| `03_complex_styles_annex_tables.docx` | Нумерация из стиля, `startOverride`, приложение, таблица с правкой в ячейке, format-only правка, вложенный `ins` в `del`, `w:sdt`, кавычки-ёлочки | 5 строк; стороны **не** извлекаются (ёлочки), `format_only_count == 1`, в «было» таблица `2026 год \| 1 200 \| 192 500`, в «стало» `2026 год \| 1 100 \| 192 500`, сохраняются `TABLE_CELL_CHANGE` и ручная проверка |
| `04_edge_no_revisions.docx` | Договор без правок | Пустой протокол, предупреждение `EMPTY_PROTOCOL` |
| `05_edge_with_macros.docx` | Документ с `vbaProject.bin` | Отказ 415 при загрузке |
| `06_edge_broken.docx` | Битый zip | Отказ 400 |
| `07_edge_plain.txt` | Не .docx | Отказ 400 |
| `08_edge_zip_without_document.docx` | Валидный zip без `word/document.xml` | Отказ 400 |
| `09_edge_xml_comment.docx` | XML-комментарий в `w:body` (так делают конвертеры) | Успешный разбор без `Invalid tag name` → статус `parsed` |
| `10_edge_renumbering.docx` | Новый пункт вставлен в середину раздела | Пункт, который в договоре был 1.2, в протоколе помечен как 1.3 |
