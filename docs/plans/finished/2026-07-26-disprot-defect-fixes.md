---
slug: disprot-defect-fixes
created: 2026-07-26
status: done
phases:
  - id: Ф1
    scope: "Безопасный разбор OOXML и реальные format-only правки"
    status: done
    commits: "c6d4ea6.."
  - id: Ф2
    scope: "Исходная и принятая редакции таблиц сквозь весь round-trip"
    status: done
    commits: "4e5da52.."
  - id: Ф3
    scope: "Нумерация исходного договора и достоверная confidence-метрика"
    status: done
    commits: "0d2d989.."
  - id: Ф4
    scope: "Backend: стороны, падежи и причина ошибки анализа"
    status: done
    parallel_group: G1
    commits: "054baed..491d05b"
  - id: Ф5
    scope: "Frontend: терминальные статусы и понятные ошибки API"
    status: done
    parallel_group: G1
    commits: "054baed..491d05b"
---

# Disagreement Protocol — план исправления 10 диагностированных находок

## Goal

Исправить все дефекты из завершённого диагностического прохода, из-за которых протокол может ссылаться не на тот пункт исходного договора, терять смысл табличной правки, пропускать стороны или скрывать причину сбоя. После изменений локальный pipeline должен одинаково корректно работать напрямую и после round-trip через SQLite.

Работа нужна сейчас, потому что находки воспроизводятся на уже подготовленных реальных OOXML-образцах и затрагивают основной юридический результат продукта. План сохраняет текущую локальную архитектуру FastAPI + SQLite + Next.js и не вводит новые сервисы или runtime-зависимости.

## Acceptance criteria

List 3–7 externally observable criteria that define "done" for the whole plan. Reviewers may block only on these criteria, stated user requirements, repo constraints, or high-materiality risks.

- На `samples/10_edge_renumbering.docx` изменённый исходный пункт имеет `point_label == "1.2."`, вставленный посередине пункт имеет `point_label == "Новый пункт 1"` и не сдвигает последующие номера; удалённые пункты в `samples/02_medium_auto_numbering.docx` сохраняют исходные номера, а стилевая нумерация и `startOverride` в `samples/03_complex_styles_annex_tables.docx` не регрессируют.
- `samples/09_edge_xml_comment.docx` доходит до `parsed`, а `samples/03_complex_styles_annex_tables.docx` сообщает одну format-only правку без отдельной строки протокола; табличная замена отображается как `1 200` в колонке «было» и `1 100` в колонке «стало», при этом флаг и предупреждение `TABLE_CELL_CHANGE` сохраняются.
- Для `samples/01_simple_manual_numbering.docx` ручная regex-нумерация больше не создаёт по одному `LOW_CONFIDENCE` на каждый нормальный пункт, а `numbering_confidence_mean` в preflight и validation report совпадает и отражает реальные сохранённые значения, а не `1.0`.
- Для преамбулы из `samples/03_complex_styles_annex_tables.docx` автоматически извлекаются ООО «Гамма» / «Арендодатель» и АО «Дельта» / «Арендатор»; экспортированные заголовки используют родительный падеж, например «Редакция Арендодателя» и «Редакция Арендатора».
- `GET /api/documents/{id}/analysis` возвращает сохранённый `error_message`; экран анализа показывает его при `failed`, перестаёт polling и показывает отчёт при `built`/`exported`, а FastAPI-ошибка загрузки отображается как её русское `detail` без сырого `400 {"detail": ...}`.
- После каждой фазы проходят `cd backend && uv run pytest`, `cd backend && uv run ruff check .`, `cd frontend && npm test`, `cd frontend && npx tsc --noEmit`; после frontend-фазы также проходит `npm run build`, а созданный Next.js diff в `frontend/tsconfig.json` не попадает в коммит.

## Non-goals / deferred

List explicit exclusions. Reviewers MUST classify requests for these as `REJECTED_BY_SCOPE` or `DEFER` unless the orchestrator authorizes scope expansion.

- Повторный диагностический проход, повторное создание набора из 10 `.docx` и переработка `scripts/make_samples.py`: образцы уже созданы и используются как regression fixtures; меняются только их ожидаемые результаты в `samples/README.md`.
- Автоматическое распределение правок по сторонам на основании `RevisionRecord.author` (finding 10c): отложено, потому что в текущем API/UI нет достоверного сопоставления произвольного имени автора Word с одной из двух подтверждённых сторон; эвристика могла бы бесшумно поменять юридический смысл колонок.
- Парсинг `headers`, `footers` и `footnotes` (finding 10d): отложен до отдельного контракта о том, какие правки из вспомогательных OOXML parts образуют пункты протокола и как они участвуют в нумерации; текущий scope остаётся `word/document.xml`.
- Удаление локальных `__pycache__` и пустых неотслеживаемых каталогов `backend/app/workers/` и `backend/alembic/` (finding 10e): это артефакты окружения без продуктового поведения и без отслеживаемых файлов.
- Добавление Alembic, автоматической миграции существующей SQLite-базы или сохранение уже обработанных локальных документов после изменения схемы: используется явно документированный сброс `backend/data` с повторной загрузкой исходных `.docx`.
- Якорь вида «после п. 1.1» для новой строки: `NEW_CLAUSE` продолжает получать стабильную метку «Новый пункт N»; исходный номер присваивается только пунктам, существовавшим до принятия Track Changes.
- Визуальное сравнение форматирования, вывод автора правки в UI/экспорт, морфологическая библиотека и изменения дизайна пяти экранов не входят в этот план.

## Global Constraints

List the spec's project-wide requirements — version floors, dependency limits, naming and copy rules, platform requirements — one line each, with exact values copied verbatim from the spec or user request. If the spec imposes none, write literally `None declared in the spec.`

- Scope: пользователь выбрал «Все 10 находок»; findings 1 и 7 включают реальную переработку, а допустимые deferred-решения по 10c/10d/10e перечислены выше явно.
- Продукт остаётся local-only: FastAPI background task выполняется in-process, SQLite и файловое хранилище остаются локальными; Docker / Postgres / Redis / S3 и новые внешние сервисы не добавляются.
- Backend остаётся на Python 3.12 с `requires-python = ">=3.12"`, FastAPI 0.115.0, Pydantic 2.9.2 + pydantic-settings, SQLAlchemy 2.0.35, lxml 5.3.0, python-docx 1.1.2 и SQLite.
- Frontend остаётся на Next.js 14.2.13 (app router), React 18.3, TypeScript 5.6 (`strict: true`), Tailwind 3.4, TanStack Table v8 + Query v5; рабочая среда использует Node 26.
- Новые runtime-зависимости не добавляются; если реализация обнаружит неизбежную потребность, фаза останавливается и риск выносится на согласование.
- Публичный HTTP API остаётся обратно совместимым; единственное изменение ответа — аддитивное nullable-поле `error_message` в `AnalysisOut`.
- Пользовательские строки — на русском; существующие машинные коды (`FORMAT_ONLY`, `LOW_CONFIDENCE`, `TABLE_CELL_CHANGE` и другие) не переименовываются.
- Сохраняются frozen dataclasses в `backend/app/processing/types.py`, возврат каждого resolver как `(data, list[ResolverDiagnostic])` и маршрутизация diagnostics по `code`, а не по `component`.
- Лимиты и отрицательные пути загрузки не меняются: максимум 25 MB, запрет `word/vbaProject.bin`, обязательный `.docx` и `word/document.xml`.
- Unit fixtures расширяются только в `backend/tests/fixtures/builders.py`; отдельная параллельная система конструкторов DOCX не создаётся.
- В конце каждой фазы обязательны `uv run pytest`, `uv run ruff check .`, `npm test`, `npx tsc --noEmit`.

## Files

### Ф1 — безопасный OOXML и format-only

- Modify `backend/app/processing/ooxml_parser.py` — игнорировать XML comments/processing instructions во всех обходах элементов.
- Modify `backend/app/processing/revision_resolver.py` — создавать production-записи `FORMAT_ONLY` для `w:rPrChange` и `w:pPrChange`.
- Modify `backend/app/processing/types.py` — уточнить документированный контракт format-only diagnostics без смены кодов.
- Modify `backend/tests/fixtures/builders.py` — добавить минимальные OOXML builders для non-element nodes и форматных правок.
- Modify `backend/tests/processing/test_ooxml_parser.py` — покрыть комментарии/PI в body, run и table cell.
- Modify `backend/tests/processing/test_revision_resolver.py` — покрыть `rPrChange`, `pPrChange`, автора и неизменность текстовых редакций.
- Modify `backend/tests/processing/test_changed_clause_detector.py` — закрепить отсутствие строки для реально распознанной format-only-only правки.
- Modify `backend/tests/integration/test_pipeline_e2e.py` — проверить production metric и неизменный набор changed clauses.
- Create `backend/tests/integration/test_sample_regressions.py` — проверки поведения на бинарных файлах из `samples/`.
- Modify `samples/README.md` — заменить ожидаемые падения/нулевую format-only метрику для samples 03 и 09.

### Ф2 — версии таблиц

- Modify `backend/app/processing/types.py` — хранить original/accepted/revisions в frozen `RawTableCell`.
- Modify `backend/app/processing/revision_resolver.py` — сопоставлять XML-параграфы внутри ячеек с их `block_id`.
- Modify `backend/app/services/ingestion.py` — собирать resolved `RawTable` и учитывать cell revisions в revision metrics.
- Modify `backend/app/services/processing.py` — сохранять версионные ячейки в `tables_json`.
- Modify `backend/app/api/protocols.py` — восстанавливать новую форму `tables_json` и читать legacy string-cells.
- Modify `backend/app/services/protocol_generator.py` — отдельно рендерить таблицу для исходной и принятой редакции.
- Modify `backend/app/processing/validation_engine.py` — учитывать сохранённые table-cell revisions в validation totals.
- Modify `backend/tests/fixtures/builders.py` — добавить DOCX с заменой внутри ячейки и неизменными соседними ячейками.
- Modify `backend/tests/processing/test_revision_resolver.py` — проверить original/accepted для cell paragraphs.
- Modify `backend/tests/processing/test_validation_engine.py` — проверить подсчёт table-cell revisions.
- Modify `backend/tests/services/test_protocol_generator.py` — проверить разные таблицы в двух колонках и прежний warning flag.
- Create `backend/tests/services/test_processing.py` — проверить фактическую запись versioned table cells сервисом `process_document`.
- Modify `backend/tests/api/test_protocols.py` — проверить JSON round-trip и legacy fallback.
- Modify `backend/tests/integration/test_pipeline_e2e.py` — проверить pipeline → row → export для табличной замены.
- Modify `backend/tests/integration/test_sample_regressions.py` — закрепить результат `samples/03_complex_styles_annex_tables.docx`.
- Modify `samples/README.md` — описать исправленные «было»/«стало» и сохранённую ручную проверку.

### Ф3 — исходная нумерация и confidence

- Modify `backend/app/processing/types.py` — добавить `RevisionData.exists_in_original`, структурный numbering level и полный paragraph round-trip.
- Modify `backend/app/processing/revision_resolver.py` — классифицировать вставленный/удалённый paragraph mark.
- Modify `backend/app/processing/numbering_resolver.py` — считать номера по состоянию «все правки отклонены» и убрать шум для regex.
- Modify `backend/app/processing/clause_segmenter.py` — сегментировать вставленные пункты по структурному уровню без присвоения исходного номера.
- Modify `backend/app/services/ingestion.py` — передавать revision map в numbering resolver и переносить новый level в `EnrichedParagraph`.
- Modify `backend/app/models/clause.py` — добавить JSON-колонку `paragraphs_json`, а `confidence` использовать как реальное агрегированное значение.
- Modify `backend/app/services/processing.py` — сохранять все paragraph fields и реальную confidence.
- Modify `backend/app/api/protocols.py` — восстанавливать точные paragraphs, numbers и confidences из БД.
- Modify `backend/tests/fixtures/builders.py` — добавить revision-aware native/style numbering cases.
- Modify `backend/tests/processing/test_numbering_resolver.py` — покрыть inserted/deleted paragraphs, regex policy, style chain и overrides.
- Modify `backend/tests/processing/test_clause_segmenter.py` — проверить отдельную вложенную clause без rendered number.
- Modify `backend/tests/processing/test_validation_engine.py` — закрепить точное среднее после восстановления paragraphs.
- Modify `backend/tests/services/test_processing.py` — проверить запись `paragraphs_json` и реальной clause confidence.
- Modify `backend/tests/api/test_protocols.py` — проверить `paragraphs_json`, annex label и validation report.
- Modify `backend/tests/integration/test_pipeline_e2e.py` — проверить new/deleted clause semantics.
- Modify `backend/tests/integration/test_sample_regressions.py` — проверить samples 01, 02, 03 и 10.
- Modify `backend/tests/test_bootstrap.py` — проверить новую SQLite-колонку.
- Modify `README.md` — явно связать изменение модели с локальным reset/re-upload.
- Modify `samples/README.md` — зафиксировать исправленную исходную нумерацию и отсутствие regex-шума.

### Ф4 — backend API, стороны и экспорт

- Modify `backend/app/schemas/document.py` — добавить nullable `AnalysisOut.error_message`.
- Modify `backend/app/api/documents.py` — вернуть сохранённую причину ошибки.
- Modify `backend/app/services/party_extractor.py` — поддержать русские типографские кавычки и полные организационно-правовые формы.
- Modify `backend/app/services/protocol_generator.py` — предоставить единый helper формирования «Редакция …» в родительном падеже.
- Modify `backend/app/services/exporter.py` — использовать общий helper для обоих заголовков.
- Modify `backend/tests/api/test_documents_analysis.py` — проверить аддитивное поле ошибки для failed/success состояний.
- Modify `backend/tests/services/test_party_extractor.py` — покрыть «ёлочки», „лапки“, curly quotes и полные формы.
- Modify `backend/tests/services/test_protocol_generator.py` — проверить известные роли, пустую и неизвестную роль.
- Modify `backend/tests/services/test_exporter.py` — проверить родительный падеж в итоговом DOCX.
- Modify `backend/tests/integration/test_sample_regressions.py` — проверить извлечение сторон sample 03.
- Modify `samples/README.md` — заменить ручной ввод сторон на успешное автоизвлечение.

### Ф5 — frontend статусы и ошибки

- Modify `frontend/lib/types.ts` — типизировать полный `DocumentStatus` и nullable `error_message`.
- Modify `frontend/lib/api.ts` — извлекать FastAPI `detail` и единообразно обрабатывать ошибки всех методов.
- Modify `frontend/app/documents/[id]/analysis/page.tsx` — завершать polling для `built`/`exported` и показывать backend reason при `failed`.
- Modify `frontend/__tests__/AnalysisPage.test.tsx` — покрыть все terminal statuses, backend reason и fallback.
- Modify `frontend/__tests__/FileUpload.test.tsx` — проверить чистый русский `detail` и прежний plain-text fallback.

## Contracts

### Revision semantics

В Ф3 основной тип получает новый флаг с default, поэтому существующие constructors не требуют позиционных изменений:

```python
@dataclass(frozen=True)
class RevisionData:
    original_text: str
    accepted_text: str
    revisions: tuple[RevisionRecord, ...]
    exists_in_original: bool = True
```

`RevisionResolver.resolve(data: bytes, raw_doc: RawDocument) -> tuple[dict[str, RevisionData], list[ResolverDiagnostic]]` сохраняет сигнатуру. После Ф2 map содержит данные для каждого top-level `RawParagraph` и каждого `RawParagraph` внутри table cell; ключом всегда остаётся существующий deterministic `block_id`.

Правила `exists_in_original`:

- Для параграфа с содержимым решающим сигналом служат его редакции текста: `False` тогда и только тогда, когда `original_text.strip() == ""`, а `accepted_text.strip() != ""`. Это тот же критерий новизны, который уже использует `ChangedClauseDetector` для `NEW_CLAUSE`; его семантика не меняется.
- Если `original_text.strip() != ""`, вернуть `True` независимо от `w:pPr/w:rPr/w:ins`: вставленный знак абзаца может завершать существующий предыдущий пункт и не доказывает, что сам этот пункт новый.
- Полностью удалённый paragraph имеет непустой `original_text` и поэтому получает `True`, в том числе при `w:pPr/w:rPr/w:del`.
- Только когда обе текстовые редакции пусты, paragraph-mark служит tie-break: `w:pPr/w:rPr/w:ins` подтверждает `False`, `w:pPr/w:rPr/w:del` подтверждает `True`; без такого marker действует безопасный fallback `True`.

Каждый отдельный `w:rPrChange` или `w:pPrChange` создаёт ровно один `RevisionRecord(type="FORMAT_ONLY", text=<затронутый текст>, author=<w:author или "">)`. Для run-change `text` — видимый текст текущего run, для paragraph-change и пустого paragraph-mark run — `accepted_text` всего параграфа. `original_text == accepted_text`; такой record считается метрикой, но сам по себе не делает clause changed.

### Table versions and persistence

Frozen cell API после Ф2:

```python
@dataclass(frozen=True)
class RawTableCell:
    paragraphs: tuple[RawParagraph, ...]
    original_text: str | None = None
    accepted_text: str | None = None
    revisions: tuple[RevisionRecord, ...] = ()

    def text(
        self,
        version: Literal["original", "accepted"] = "accepted",
    ) -> str: ...
```

Если resolved field равен `None`, `text()` возвращает прежний plain-text fallback из `paragraphs`; неизвестный `version` вызывает `ValueError`. `RawTable.cell_text(version: Literal["original", "accepted"] = "accepted") -> str` передаёт выбор версии каждой ячейке и сохраняет разделители ` | ` / `\n`.

Новая запись одной ячейки в `Clause.tables_json`:

```json
{
  "original_text": "1 200",
  "accepted_text": "1 100",
  "revisions": [
    {"type": "DEL", "text": "1 200", "author": "Юрист контрагента"},
    {"type": "INS", "text": "1 100", "author": "Юрист контрагента"}
  ]
}
```

Полная форма таблицы остаётся `{"block_id": str, "has_revisions": bool, "rows": [[cell, ...], ...]}`. Чтение старой string-cell обязательно: строка `"1 2001 100"` восстанавливается как одинаковый fallback для original/accepted и без revisions, чтобы Ф2 не ломала уже существующую БД; новые записи всегда используют object-cell.

`ProtocolRowBuilder._render_tables(clause: Clause, version: Literal["original", "accepted"]) -> str` вызывается отдельно для `party_1_text` и `party_2_text`. `TABLE_CELL_CHANGE` и предупреждение ручной проверки сохраняются. Для standalone table `party_1_text` получает original, `party_2_text` — accepted.

### Original numbering

После Ф3:

```python
@dataclass(frozen=True)
class NumberingData:
    rendered_number: str | None
    confidence: float
    source: str
    numbering_level: int | None = None

@dataclass(frozen=True)
class EnrichedParagraph:
    # существующие поля без переименований
    numbering_level: int | None = None
```

Новая обязательная внутренняя сигнатура:

```python
NumberingResolver.resolve(
    data: bytes,
    raw_doc: RawDocument,
    revision_map: dict[str, RevisionData],
) -> tuple[dict[str, NumberingData], list[ResolverDiagnostic]]
```

Resolver сначала определяет effective `num_id`/`ilvl`, включая `styles.xml`/`basedOn`, и сохраняет `numbering_level` независимо от наличия `rendered_number`. Затем применяются правила:

- `exists_in_original=True` + native numbering: вызвать `_advance_and_render` и сдвинуть counters;
- `exists_in_original=False`: не вызывать `_advance_and_render`, не применять `startOverride`, вернуть `rendered_number=None`, но сохранить native `numbering_level` и confidence/source распознавания;
- полностью удалённый paragraph имеет `exists_in_original=True`, поэтому получает и занимает исходный номер;
- regex для существующего paragraph ищется в `RevisionData.original_text`, а не в смешанном `RawParagraph.text()`;
- для inserted-only manual paragraph regex из `accepted_text` разрешён только как structural hint для `numbering_level`; номер всё равно `None`;
- `ClauseSegmenter._level_of` сначала использует `numbering_level`, затем существующие fallbacks, поэтому inserted native/style/manual clause остаётся отдельной clause правильной вложенности.

`LOW_CONFIDENCE` создаётся только при `source == "native"`, непустом `rendered_number` и `confidence < 0.85`; поэтому regex confidence `0.7` не даёт warning. Native mismatch продолжает выдавать конкретный `NUMBERING_TEXT_MISMATCH` и один `LOW_CONFIDENCE`; `UNKNOWN_NUMID` остаётся отдельным сигналом.

`NEW_CLAUSE` не получает выдуманный исходный номер: `ProtocolRowBuilder` продолжает нумеровать только строки как `"Новый пункт {N}"`. `DELETED_CLAUSE` использует исходный `Clause.label` и текст `"Исключить пункт {label}"`.

### Paragraph persistence and validation

Ф3 добавляет `Clause.paragraphs_json: Mapped[list[dict]] = mapped_column(JSON, default=list)`. Один элемент имеет точную форму:

```json
{
  "block_id": "p_0007",
  "text_runs": "Срок поставки — 147 календарных дней.",
  "num_id": 1,
  "ilvl": 1,
  "original_text": "Срок поставки — 14 календарных дней.",
  "accepted_text": "Срок поставки — 7 календарных дней.",
  "revisions": [
    {"type": "DEL", "text": "14", "author": "Юрист контрагента"},
    {"type": "INS", "text": "7", "author": "Юрист контрагента"}
  ],
  "rendered_number": "1.2.",
  "numbering_confidence": 0.95,
  "numbering_level": 1
}
```

`Clause.original_text`, `accepted_text` и `revisions` сохраняются для совместимости внутренних моделей, но build path восстанавливает `EnrichedParagraph` из `paragraphs_json`. `Clause.confidence` равен арифметическому среднему `numbering_confidence` её paragraphs либо `0.0`, если paragraphs нет. `ValidationEngine` получает восстановленный полный список paragraphs, поэтому его mean совпадает с in-memory preflight; `rendered_number` больше никогда не заполняется `Clause.label` (в частности, annex label не маскируется под номер).

Существующая SQLite schema не мигрируется автоматически: перед первым запуском версии Ф3 пользователь останавливает backend, выполняет документированный `rm -rf backend/data`, запускает backend заново и повторно загружает исходные `.docx`. Код не удаляет данные сам.

### Party roles and export labels

`PartyExtractor.extract(preamble_text: str) -> list[ExtractedParty]` сохраняет сигнатуру и confidence `0.9`/`0.85`. Quote grammar принимает `"..."`, `«...»`, `„...“`, `“...”` и `”...”` для названия и роли. `ENTITY_PREFIX` принимает прежние сокращения и полные формы:

- `Общество с ограниченной ответственностью`;
- `Акционерное общество`;
- `Публичное акционерное общество`;
- `Закрытое акционерное общество`;
- `Открытое акционерное общество`;
- `Индивидуальный предприниматель`;
- `Автономная некоммерческая организация`;
- `Некоммерческая организация`;
- `Федеральное государственное унитарное предприятие`;
- `Государственное унитарное предприятие`.

В `backend/app/services/protocol_generator.py` вводится единая публичная функция:

```python
def edition_label(role: str, empty_fallback: str) -> str: ...
```

Для известной роли она возвращает форму `"Редакция {родительный падеж}"`; словарь включает текущие семь ролей и как минимум `Продавец`, `Лицензиар`, `Лицензиат`, `Заёмщик`, `Займодавец`, `Агент`, `Принципал`, `Поручитель`, `Перевозчик`. Для неизвестной непустой роли fallback равен `"Редакция стороны «{role.strip()}»"`, для пустой — `"Редакция {empty_fallback}"`. `agreed_text_for_party(role)` делегирует `edition_label(role, "Стороны 2")`; exporter использует `edition_label(counterparty_role, "Стороны 1")` и `edition_label(drafting_role, "Стороны 2")`.

### Analysis API and frontend state machine

Единственное изменение HTTP shape:

```json
{
  "id": "uuid",
  "status": "failed",
  "error_message": "Ошибка разбора OOXML: недопустимый XML-узел",
  "...": "остальные существующие поля без изменений"
}
```

`AnalysisOut.error_message: str | None = None`; `GET /api/documents/{id}/analysis` и возвращающий тот же schema `PATCH /api/documents/{id}/parties` всегда включают поле (`null` без ошибки). Текст уже ограничен backend до 2000 символов.

Frontend фиксирует union:

```ts
type DocumentStatus =
  | "uploaded"
  | "parsing"
  | "parsed"
  | "parties_confirmed"
  | "built"
  | "exported"
  | "failed";
```

Polling продолжается только для `uploaded` и `parsing`. `parsed`, `parties_confirmed`, `built`, `exported` рендерят загруженный отчёт; `failed` останавливает polling и показывает `error_message.trim()` либо `"Ошибка обработки документа"`.

Общий frontend error parser читает response body ровно один раз:

- непустой FastAPI `detail: string` → только этот текст;
- `detail: array` → соединённые `msg` через `"; "`;
- plain text → `"{status} {text}"`, чтобы сохранить диагностический fallback;
- пустое тело → `"Ошибка запроса (HTTP {status})"`.

Эта логика используется `jsonOrThrow`, delete и export paths; JSON-тело больше не показывается пользователю целиком.

## Test strategy

### Общая проверка каждой фазы

Каждая фаза заканчивается полным обязательным циклом, даже если менялась только одна сторона приложения:

```bash
cd backend && uv run pytest
cd backend && uv run ruff check .
cd frontend && npm test
cd frontend && npx tsc --noEmit
```

Тесты уровня unit строят минимальный OOXML только через расширения `backend/tests/fixtures/builders.py`. Новый `backend/tests/integration/test_sample_regressions.py` не создаёт fixtures: он читает уже сгенерированные бинарные `samples/*.docx` и проверяет их публичные pipeline/build результаты.

### Ф1

- Unit: comments и processing instructions между body blocks, внутри `w:r` и внутри cell не попадают в `QName`; обычный текст до/после них сохраняется.
- Unit: один `w:rPrChange` и один `w:pPrChange` дают отдельные `FORMAT_ONLY` records с автором, но identical original/accepted.
- Integration: format-only-only clause не входит в `changed_clauses`; `format_only_count` на sample 03 становится `1`; sample 09 разбирается без exception.
- Не проверять пиксельное/стилевое различие Word: pipeline хранит факт format-only, а не визуальный diff.

### Ф2

- Unit: replacement в cell даёт old/new text без конкатенации; несколько paragraphs в cell соединяются прежним пробелом; неизменные cells одинаковы в обеих версиях.
- Service: attached и standalone tables попадают в разные party columns, но всегда сохраняют `TABLE_CELL_CHANGE`.
- API: новая object-cell форма переживает DB reconstruction; legacy string-cell читается без 500 и дублируется как безопасный fallback.
- Integration: sample 03 содержит строку `2026 год | 1 200 | 192 500` только в original и `2026 год | 1 100 | 192 500` только в accepted; экспорт открывается `python-docx`.
- Не тестировать сложную визуальную разметку/merged cells: формат текущего plain-text table rendering не меняется.

### Ф3

- Unit: существующий paragraph с неизменёнными runs и `w:pPr/w:rPr/w:ins` сохраняет исходный номер и advance counter; следующий wholly-ins paragraph номера не получает и counter не advance; wholly-del и deleted paragraph mark advance; обычная последовательность, style `basedOn`, annex `startOverride`, native mismatch и manual regex остаются покрыты.
- Unit: inserted paragraph с `rendered_number=None` и `numbering_level=1` образует отдельную дочернюю clause, а не continuation предыдущей.
- API/persistence: `paragraphs_json` точно восстанавливает per-paragraph values; annex `Clause.label` не становится `rendered_number`; validation mean совпадает с preflight mean.
- Samples: 10 даёт исходный `1.2.` и `"Новый пункт 1"`; 02 сохраняет номер deleted clause и new-clause semantics; 03 сохраняет style/override; 01 не содержит regex-generated `LOW_CONFIDENCE`.
- Bootstrap: новая schema создаётся in-memory; README содержит явный destructive reset warning и re-upload step.
- Не писать тест миграции существующей БД: migration framework явно вне scope, поддерживаемый путь — reset.

### Ф4

- Unit: прежние ASCII quotes не регрессируют; sample-подобная строка с полными ООО/АО и `«...»` даёт ровно две стороны; отдельно покрываются `„...“`, `“...”`, `”...”` и форма ИП.
- Unit: `edition_label` проверяется для известных, пустых и неизвестных ролей; exporter DOCX содержит грамматически корректные headers.
- API: `failed` response содержит точный сохранённый reason, обычный response содержит `error_message: null`.
- Sample integration: sample 03 извлекает ожидаемые names/roles.
- Не тестировать все возможные российские ОПФ и свободные морфологические формы: контракт ограничен перечисленным набором и безопасным fallback.

### Ф5

- Component: analysis page делает один terminal fetch и рендерит отчёт для `parsed`, `parties_confirmed`, `built`, `exported`; `failed` показывает backend reason или русский fallback.
- Component/API: upload `400 {"detail":"Поддерживаются только файлы .docx без макросов"}` показывает только detail; plain-text 500 сохраняет `500 внутренняя ошибка`; array-detail сворачивается в сообщения.
- Regression: существующие Parties/Protocol/Export tests продолжают проверять остальные API paths после общей error-функции.
- После тестов выполнить `cd frontend && npm run build`; затем проверить `git diff -- frontend/tsconfig.json` и восстановить только автоматически созданный Next.js churn, поскольку намеренных изменений этого файла в плане нет.
- Browser E2E не добавлять: state machine и error rendering полностью покрываются существующим Vitest + MSW уровнем.

## Risks / unknowns / assumptions

- **REGRESSION — numbering state machine.** Пропуск inserted item не должен ни увеличивать текущий level, ни сбрасывать deeper levels, ни отмечать `startOverride` применённым. Риск закрывают middle/end insertion, deletion, style chain и annex tests.
- **REGRESSION — inserted clause segmentation.** `rendered_number=None` раньше означал continuation; новый независимый `numbering_level` обязателен для explicit и style-based numbering. Без него finding 1 исправит label, но потеряет строку `NEW_CLAUSE`.
- **DATA_LOSS — SQLite reset.** `create_all` не добавит `paragraphs_json` в существующую таблицу. Поддерживаемый путь `rm -rf backend/data` удаляет локальные документы и uploads; команда не запускается автоматически, README обязан предупредить о потере и потребовать повторную загрузку исходников.
- **REGRESSION — JSON round-trip.** Новая table cell shape и `paragraphs_json` должны быть симметричны между `processing.py` и `protocols.py`; иначе in-memory tests пройдут, а HTTP build даст иные строки/metrics. API tests проверяют именно persisted shape.
- **REGRESSION — paragraph-mark ownership.** `w:pPr/w:rPr/w:ins` может завершать существующий предыдущий paragraph, поэтому marker не переопределяет непустой `original_text`. Обязательная unit-фикстура с marker на предыдущем неизменённом пункте проверяет, что он сохраняет номер и advance counter, а следующий wholly-ins paragraph — нет.
- **REGRESSION — quote regex.** Длинные полные ОПФ должны идти в alternation раньше коротких и spans должны разделяться по следующей entity, иначе первая сторона поглотит вторую. Тест sample 03 проверяет ровно две записи.
- **ASSUMPTION — unknown role grammar.** Без морфологической зависимости неизвестная роль не склоняется; конструкция «Редакция стороны «…»» выбрана как грамматически безопасный и юридически читаемый fallback.
- **REGRESSION — metric scope.** После Ф2 textual/format totals включают revisions из table cells; preflight и validation обязаны обходить один и тот же набор records, иначе возникнет новый разрыв метрик.
- **TOOLING — Next build.** Next.js 14 переписывает `frontend/tsconfig.json`; этот generated diff нельзя смешивать с функциональной фазой.
- **DEPENDENCIES.** Все исправления реализуемы стандартной библиотекой, lxml, SQLAlchemy, python-docx и текущим frontend stack; новых пакетов не предполагается.

## Phases

## Ф1: Безопасный OOXML и реальные format-only правки

**Files in this phase:**

- Modify: `backend/app/processing/ooxml_parser.py`
- Modify: `backend/app/processing/revision_resolver.py`
- Modify: `backend/app/processing/types.py`
- Test: `backend/tests/fixtures/builders.py`
- Test: `backend/tests/processing/test_ooxml_parser.py`
- Test: `backend/tests/processing/test_revision_resolver.py`
- Test: `backend/tests/processing/test_changed_clause_detector.py`
- Test: `backend/tests/integration/test_pipeline_e2e.py`
- Create: `backend/tests/integration/test_sample_regressions.py`
- Modify: `samples/README.md`

**Interfaces:**
- Consumes: nothing
- Produces: `RevisionResolver.resolve(data: bytes, raw_doc: RawDocument) -> tuple[dict[str, RevisionData], list[ResolverDiagnostic]]` с production `RevisionRecord(type="FORMAT_ONLY", ...)`; `RevisionResolver._paragraph_revision(p_elem: etree._Element) -> RevisionData`, который Ф2 повторно использует для cell paragraphs

- [ ] **Step 1: Написать failing unit fixtures/tests для non-element XML nodes**

  Расширить только `backend/tests/fixtures/builders.py`: уметь вставить `etree.Comment` и processing instruction между body blocks, внутрь run и внутрь cell. Тесты должны проверять не только отсутствие exception, но и сохранение соседнего текста/порядка blocks.

- [ ] **Step 2: Защитить все parser traversal points**

  В `_iter_block_children` и `_parse_paragraph` пропускать узлы, у которых `not isinstance(node.tag, str)`, до вызова `etree.QName`. Проверить `_parse_table`: direct `findall` оставляем, а вложенный обход cell идёт через уже защищённый `_iter_block_children`. Поддержку неизвестных element-wrappers и ошибку nested table не ослаблять.

- [ ] **Step 3: Написать failing tests для `w:rPrChange` / `w:pPrChange`**

  Проверить число records, `type`, `author`, затронутый `text`, identical original/accepted и diagnostic с прежним code `FORMAT_ONLY_MISMATCH`. Подать production output в `ChangedClauseDetector`, а не создавать record вручную.

- [ ] **Step 4: Реализовать format-only detection**

  После текстового INS/DEL walk найти каждый property-change element ровно один раз, не интерпретировать old property snapshot как текст и добавить `FORMAT_ONLY`. Русский diagnostic message описывает форматную правку без изменения текста; `ChangedClauseDetector` не менять, потому что его фильтр `INS`/`DEL` уже является нужным контрактом.

- [ ] **Step 5: Закрепить samples 03/09**

  В `test_sample_regressions.py` вызвать `run_pipeline` для обоих файлов: sample 09 не падает, sample 03 имеет `format_only_count == 1`, а clause с единственным format-only record отсутствует в `changed_clauses`. Обновить только соответствующие expected-result cells в `samples/README.md`.

- [ ] **Step 6: Выполнить phase gate**

  Запустить четыре обязательные команды из Test strategy. Не изменять и не перегенерировать samples или source code вне списка фазы.

## Ф2: Исходная и принятая редакции таблиц сквозь round-trip

**Files in this phase:**

- Modify: `backend/app/processing/types.py`
- Modify: `backend/app/processing/revision_resolver.py`
- Modify: `backend/app/services/ingestion.py`
- Modify: `backend/app/services/processing.py`
- Modify: `backend/app/api/protocols.py`
- Modify: `backend/app/services/protocol_generator.py`
- Modify: `backend/app/processing/validation_engine.py`
- Test: `backend/tests/fixtures/builders.py`
- Test: `backend/tests/processing/test_revision_resolver.py`
- Test: `backend/tests/processing/test_validation_engine.py`
- Test: `backend/tests/services/test_protocol_generator.py`
- Create: `backend/tests/services/test_processing.py`
- Test: `backend/tests/api/test_protocols.py`
- Test: `backend/tests/integration/test_pipeline_e2e.py`
- Test: `backend/tests/integration/test_sample_regressions.py`
- Modify: `samples/README.md`

**Interfaces:**
- Consumes: `RevisionResolver._paragraph_revision(p_elem: etree._Element) -> RevisionData` и format-only semantics из Ф1
- Produces: `RawTableCell.text(version: Literal["original", "accepted"] = "accepted") -> str`, `RawTable.cell_text(version=...) -> str` и persisted `tables_json.rows[][]` object-cell contract с обязательным legacy string-cell reader

- [ ] **Step 1: Сначала зафиксировать cell-level data contract тестами**

  Builder создаёт таблицу с unchanged header/neighbor cells и `DEL("1 200") + INS("1 100")` в одной cell. Resolver test ожидает два текста и два records под deterministic table paragraph `block_id`.

- [ ] **Step 2: Расширить frozen table types**

  Добавить optional resolved fields/revisions после существующего `paragraphs`, чтобы старые constructors оставались валидны. Реализовать versioned `text()`/`cell_text()` с безопасным fallback и прежними разделителями.

- [ ] **Step 3: Сопоставить XML и raw paragraphs внутри tables**

  `RevisionResolver.resolve` обходит body тем же порядком, что parser: flattened top-level blocks, затем direct rows/cells и cell block children. Для каждого raw cell paragraph вызвать уже проверенный `_paragraph_revision`; fallback при отсутствии XML-пары сохраняет plain text в обеих версиях.

- [ ] **Step 4: Материализовать resolved tables в ingestion**

  Поскольку dataclasses frozen, построить новые `RawTableCell`/`RawTableRow`/`RawTable` с original/accepted/revisions, не мутируя parser output. `has_revisions` остаётся textual INS/DEL сигналом: format-only cell не создаёт protocol row.

- [ ] **Step 5: Сделать persistence round-trip симметричным**

  `processing.py` пишет object-cells из Contracts; новый service test вызывает `process_document` с fake session/storage и проверяет реально добавленный `ClauseModel`. `protocols.py` восстанавливает fields/revisions; если cell — legacy string, присваивает её обеим версиям. API test строит protocol именно из `ClauseModel.tables_json`, чтобы исключить ложноположительный in-memory тест.

- [ ] **Step 6: Развести table rendering по колонкам**

  В attached и standalone paths вызывать `_render_tables` отдельно для `"original"` и `"accepted"`. Не менять порядок cells/rows, plain-text separators, `TABLE_CELL_CHANGE`, row confidence и warning message.

- [ ] **Step 7: Синхронизировать revision totals**

  Preflight и ValidationEngine считают INS/DEL/FORMAT_ONLY records как в clause paragraphs, так и в table cells. `covered_revisions` включает textual cell changes, поскольку их original/accepted уже представлены в protocol row.

- [ ] **Step 8: Закрепить sample 03 и экспорт**

  Проверить точные old/new table strings, отсутствие `1 2001 100`, сохранение warning и валидность экспортированного DOCX через `python-docx`. Обновить expected result в `samples/README.md`.

- [ ] **Step 9: Выполнить phase gate**

  Запустить четыре обязательные команды из Test strategy.

## Ф3: Нумерация исходного договора и достоверная confidence

**Files in this phase:**

- Modify: `backend/app/processing/types.py`
- Modify: `backend/app/processing/revision_resolver.py`
- Modify: `backend/app/processing/numbering_resolver.py`
- Modify: `backend/app/processing/clause_segmenter.py`
- Modify: `backend/app/services/ingestion.py`
- Modify: `backend/app/models/clause.py`
- Modify: `backend/app/services/processing.py`
- Modify: `backend/app/api/protocols.py`
- Test: `backend/tests/fixtures/builders.py`
- Test: `backend/tests/processing/test_numbering_resolver.py`
- Test: `backend/tests/processing/test_clause_segmenter.py`
- Test: `backend/tests/processing/test_validation_engine.py`
- Test: `backend/tests/services/test_processing.py`
- Test: `backend/tests/api/test_protocols.py`
- Test: `backend/tests/integration/test_pipeline_e2e.py`
- Test: `backend/tests/integration/test_sample_regressions.py`
- Test: `backend/tests/test_bootstrap.py`
- Modify: `README.md`
- Modify: `samples/README.md`

**Interfaces:**
- Consumes: versioned table types/JSON из Ф2 и полный `RevisionResolver.resolve(...)` map для body/table paragraphs
- Produces: `NumberingResolver.resolve(data: bytes, raw_doc: RawDocument, revision_map: dict[str, RevisionData]) -> tuple[dict[str, NumberingData], list[ResolverDiagnostic]]`; `Clause.paragraphs_json` shape и реальная `Clause.confidence`, на которые опирается последующий protocol build

- [ ] **Step 1: Написать revision-aware numbering fixtures**

  Расширить native builder возможностью пометить content и paragraph mark как INS/DEL и отдельно задать style-only numbering. Добавить обязательную unit-фикстуру обычного Word-жеста: предыдущий paragraph содержит неизменённые runs и вставленный `w:pPr/w:rPr/w:ins`, следующий paragraph содержит текст целиком в `w:ins`, затем идёт следующий исходный пункт. Тест утверждает, что первый paragraph сохраняет свой исходный номер и advance counter, wholly-ins paragraph получает `rendered_number=None` и counter не advance, а следующий исходный пункт получает ожидаемый номер. Остальные failing tests покрывают middle insertion, end insertion, whole deletion, paragraph-mark deletion и first-use `startOverride`.

- [ ] **Step 2: Вычислить `exists_in_original`**

  В `_paragraph_revision` сначала построить `original_text` и `accepted_text`. Для параграфа с содержимым выставить `exists_in_original=False` только при пустом original и непустом accepted; любой непустой original даёт `True`, даже если его paragraph mark содержит `pPr/rPr/ins`. Консультировать `pPr/rPr/ins|del` только как подтверждающий tie-break, когда обе текстовые редакции пусты. Не менять семантику `NEW_CLAUSE` / `DELETED_CLAUSE` и не смешивать этот флаг с обычной вставкой внутри существующего пункта.

- [ ] **Step 3: Передать revision map в numbering resolver**

  Изменить единственный production call в `run_pipeline` и все unit helpers. Для native paragraph вычислять effective numPr/level до решения об advance. Для regex брать original text; accepted regex inserted paragraph использовать только для level hint.

- [ ] **Step 4: Исправить counters и diagnostics**

  Inserted paragraph полностью пропускает `_advance_and_render`, включая restart и applied override state. Deleted paragraph идёт по обычной ветке. Не выдавать generic `LOW_CONFIDENCE` для валидного regex source; сохранить specific mismatch/unknown diagnostics.

- [ ] **Step 5: Отделить structural level от rendered number**

  Перенести `numbering_level` через `NumberingData` → `EnrichedParagraph`; обновить `_level_of`. Тест сегментирует inserted nested paragraph с `None` number как отдельную clause и затем получает `NEW_CLAUSE`/«Новый пункт 1».

- [ ] **Step 6: Добавить точный paragraph persistence**

  Добавить `paragraphs_json`, сериализовать все поля из Contracts и заменить `confidence=1.0` на mean реальных paragraph values. Расширить service test `process_document`, чтобы он проверял payload и агрегат на нескольких paragraphs. В `protocols.py` восстанавливать каждый paragraph; legacy/fake ClauseModel без payload получает один безопасный synthetic paragraph с `rendered_number=None`, но новые persisted documents всегда идут по точному path.

- [ ] **Step 7: Проверить validation report после БД**

  API test задаёт разные confidences нескольким paragraphs одной clause и нескольким clauses, строит protocol и сравнивает weighted paragraph mean. Отдельно проверить, что annex label остаётся только `Clause.label`, а paragraph number — числовым.

- [ ] **Step 8: Документировать schema reset**

  В README рядом с существующей reset-командой указать: остановить backend, сохранить исходные `.docx`, выполнить `rm -rf backend/data`, перезапустить, повторно загрузить документы. Не добавлять Alembic и не выполнять удаление из кода/tests.

- [ ] **Step 9: Закрепить четыре regression samples**

  Sample 10: последующий changed clause `1.2.`, inserted row «Новый пункт 1». Sample 02: deleted clause сохраняет исходный номер, inserted-at-end не расходует номер. Sample 03: basedOn/startOverride/annex без регрессии. Sample 01: preflight и persisted validation mean совпадают, per-regex LOW diagnostics отсутствуют. Обновить `samples/README.md`.

- [ ] **Step 10: Выполнить phase gate**

  Запустить четыре обязательные команды из Test strategy на чистой тестовой SQLite schema.

## Ф4: Backend — стороны, падежи и причина ошибки анализа

**Files in this phase:**

- Modify: `backend/app/schemas/document.py`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/services/party_extractor.py`
- Modify: `backend/app/services/protocol_generator.py`
- Modify: `backend/app/services/exporter.py`
- Test: `backend/tests/api/test_documents_analysis.py`
- Test: `backend/tests/services/test_party_extractor.py`
- Test: `backend/tests/services/test_protocol_generator.py`
- Test: `backend/tests/services/test_exporter.py`
- Test: `backend/tests/integration/test_sample_regressions.py`
- Modify: `samples/README.md`

**Interfaces:**
- Consumes: nothing
- Produces: additive `AnalysisOut.error_message: str | None`; `edition_label(role: str, empty_fallback: str) -> str`; неизменённую форму `PartyExtractor.extract(...) -> list[ExtractedParty]` с расширенной grammar

- [ ] **Step 1: Зафиксировать response contract ошибки**

  API tests создают `Document(status=FAILED, error_message="...")` и проверяют точное поле; parsed document возвращает `null`. Добавить default `None` в Pydantic schema и явно передать model value из `get_analysis`.

- [ ] **Step 2: Расширить quote/legal-form grammar тестами**

  Сохранить все старые ASCII cases. Добавить точную преамбулу sample 03, варианты `„...“`, `“...”`, `”...”`, полный ИП и dash-form. Проверять ровно две стороны, полные names и роли, а не внутренние regex groups.

- [ ] **Step 3: Реализовать PartyExtractor без новой NLP-зависимости**

  Вынести quote alternatives и full-form alternatives в читаемые constants, поставить длинные формы раньше сокращений, применить `IGNORECASE | DOTALL` к spans. Сохранить dedupe по role и confidence.

- [ ] **Step 4: Централизовать родительный падеж**

  Реализовать `edition_label` по Contracts, перевести на него `agreed_text_for_party`, затем импортировать тот же helper в exporter. Не копировать dictionary и не добавлять морфологический пакет.

- [ ] **Step 5: Проверить реальный export/sample**

  Открыть bytes через `python-docx` и сравнить все четыре headers. В sample regression проверить ООО «Гамма» и АО «Дельта»; обновить только expected result sample 03.

- [ ] **Step 6: Выполнить phase gate**

  Запустить четыре обязательные команды. Фаза не меняет frontend files и может выполняться параллельно с Ф5 только на frozen HTTP contract из Contracts.

## Ф5: Frontend — терминальные статусы и понятные ошибки API

**Files in this phase:**

- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/documents/[id]/analysis/page.tsx`
- Test: `frontend/__tests__/AnalysisPage.test.tsx`
- Test: `frontend/__tests__/FileUpload.test.tsx`

**Interfaces:**
- Consumes: frozen HTTP contract `AnalysisOut.error_message: string | null` и существующие status strings `uploaded|parsing|parsed|parties_confirmed|built|exported|failed`, определённые в `## Contracts`; реализация Ф4 не требуется для MSW tests
- Produces: nothing

- [ ] **Step 1: Типизировать status/error shape**

  Добавить `DocumentStatus` union, использовать его в `AnalysisOut.status`, добавить `error_message`. Обновить MSW payloads только там, где TypeScript требует поле; runtime fallback обязан переживать `undefined` от старого backend.

- [ ] **Step 2: Написать failing state-machine tests**

  Параметризовать loaded statuses `parsed`, `parties_confirmed`, `built`, `exported`; с fake timers/request counter доказать отсутствие следующего poll. Для failed проверить backend reason и fallback при `null`.

- [ ] **Step 3: Исправить polling/render guards**

  Вынести terminal loaded set, продолжать polling только для `uploaded`/`parsing`, показывать report для всех loaded statuses. При failed установить error из response и не планировать новый timeout.

- [ ] **Step 4: Централизовать разбор API errors**

  Реализовать single-read parser из Contracts и применить его в `jsonOrThrow`, `deleteRow` и `exportProtocol`. Не менять signatures методов `api`.

- [ ] **Step 5: Проверить пользовательский текст ошибки**

  FileUpload test отправляет FastAPI JSON detail и ожидает только «Поддерживаются только файлы .docx без макросов»; plain response с текстом «внутренняя ошибка» отображается как `500 внутренняя ошибка`. Добавить array-detail case на любом JSON endpoint без создания нового UI компонента.

- [ ] **Step 6: Выполнить финальный phase gate и production build**

  Запустить четыре обязательные команды, затем `cd frontend && npm run build`. Проверить и убрать только generated churn `frontend/tsconfig.json`; убедиться через `git status --short`, что plan/source/test changes ожидаемы и `.next`/cache artifacts не staged.
