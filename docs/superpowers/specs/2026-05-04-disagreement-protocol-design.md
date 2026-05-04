# Disagreement Protocol — Design Spec

**Версия:** 0.1
**Дата:** 2026-05-04
**Статус:** утверждён к реализации

---

## 1. Контекст и цели

### 1.1. Что делает продукт

Локальный инструмент для российских юристов: автоматическая генерация **протокола разногласий** из `.docx`-файлов с правками в режиме рецензирования (Track Changes).

**Протокол разногласий** — стандартный российский юридический документ в виде таблицы из 4 колонок:

| Пункт договора | Редакция Стороны 1 | Редакция Стороны 2 | Согласованная редакция |
|---|---|---|---|

Сейчас юристы составляют такие протоколы вручную копи-пейстом. Цель MVP — закрыть эту рутину.

### 1.2. Поток работы пользователя

1. Пользователь загружает один `.docx` с правками в Track Changes (входящий редлайн от контрагента или собственная правка).
2. Система извлекает изменённые пункты, восстанавливает исходную и предлагаемую редакции, парсит наименования сторон.
3. Пользователь подтверждает стороны и указывает drafting party (от чьего имени составляется протокол).
4. Система строит редактируемую таблицу протокола.
5. Пользователь правит таблицу в UI.
6. Система экспортирует результат в `.docx`.

### 1.3. Цели MVP

- Закрыть рутину копи-пейста для солиста-юриста.
- 5–6 недель solo-разработки.
- 80–90% строк протокола генерируются автоматически с понятными пометками для оставшегося.
- Конфиденциальность: никаких внешних сетевых вызовов, всё локально.
- Cross-platform: macOS, Linux, Windows.
- Только русский язык в MVP.

### 1.4. Не-цели MVP

- B2B SaaS, биллинг, multi-user, share-функции, audit trail.
- LLM/AI-функции в runtime (архитектурный порт зарезервирован).
- Поддержка `.doc` (Word 97–2003).
- English-language contracts (архитектурный порт зарезервирован).
- Two-version pipeline (две `.docx` без Track Changes → автогенерация redline).
- Word add-in.
- Подробная история проектов (сессии разовые, TTL 7 дней).
- Footnotes, endnotes, MoveFrom/MoveTo, non-native redlines (цветной текст без TC).
- Антивирусная проверка загружаемых файлов.
- Экспорт в XLSX/PDF.

---

## 2. Архитектура

### 2.1. Структура репозитория

Monorepo из трёх Python-пакетов на `uv` workspace:

```
disagreement-protocol/
├── packages/
│   ├── disprot-core/      # чистый Python, без web-зависимостей
│   ├── disprot-web/       # FastAPI + React/Vite (frontend pre-built в wheel)
│   └── disprot-cli/       # Click/Typer обёртка
├── pyproject.toml         # uv workspace
└── README.md
```

### 2.2. Правило слоёв

Жёсткое разделение:

- `disprot-core` ничего не знает про web/cli. Не возвращает HTTP-объекты, не пишет в SQLite напрямую (если SQLite вообще нужен на этом слое), не парсит CLI-аргументы.
- `disprot-web` и `disprot-cli` импортируют только из `disprot-core`.
- Между web и cli прямых зависимостей нет.

### 2.3. Distribution

Meta-пакет `disagreement-protocol` зависит от `disprot-web` (тянет `disprot-core` транзитивно) и `disprot-cli`.

Установка для конечного пользователя:

```
pipx install disagreement-protocol
disprot serve            # запускает localhost:8765 + открывает браузер
disprot convert input.docx \
    --party-1 "ООО \"Ромашка\":Арендодатель" \
    --party-2 "АО \"Василёк\":Арендатор" \
    --drafting-party "Арендатор" \
    -o protocol.docx
disprot --version
```

Frontend pre-built в `disprot-web/frontend/dist/` и копируется в Python wheel. На машине пользователя `npm` не требуется.

**Ограничения зависимостей:**

- Никаких runtime-зависимостей вне Python ecosystem: ни LibreOffice/`soffice`, ни .NET runtime, ни Microsoft Office, ни системных утилит сверх Python и `pip`.
- Никаких heavy ML stacks: PyTorch, TensorFlow, transformers — запрещены в runtime.
- Binary wheels допустимы, если они штатно публикуются на PyPI для macOS / Linux / Windows и не требуют ручной системной установки чего-либо. Примеры допустимых: `lxml`, `numpy`, `pydantic-core`.

---

## 3. Источники заимствования

В runtime НЕ тянутся как зависимости, но изучаются как референс. **Reference-only, no copying:** алгоритмы перепишутся в clean-room реализации. В исходниках адаптированных файлов указывается источник и оригинальная лицензия.

| Источник | Лицензия | Что берём | Куда кладём |
|---|---|---|---|
| `adeu` (https://github.com/dealfluence/adeu) | MIT | Алгоритм Run Coalescing (склейка фрагментированных `<w:r>`), обход XML-дерева | Адаптация в `disprot-core/.../parsing/ooxml.py` (`OOXMLReader`) |
| `Open-Xml-PowerTools` / `WmlComparer` (.NET) | MIT | Референсная логика revision tracking и сравнения DOCX | Учебный материал; полезно для будущего two-version pipeline (v2) |
| `dedoc` (ИСП РАН) | Apache 2.0 | Эвристики выявления иерархии пунктов в русских договорах | Адаптация в `disprot-core/.../parsing/segmentation.py` (`ClauseSegmenter`) |
| Anthropic skill `docx` (`docs/brainstorming/Materials/skill for docx/`) | Anthropic skill | `unpack.py`, `pack.py`, `validate.py` — **читаем как референс**, чтобы понять устройство DOCX. Свою реализацию пишем clean-room на `zipfile` (stdlib) + `lxml` + `python-docx`. Файлы из `docs/brainstorming/Materials/` НЕ переносятся в `packages/disprot-core/`. | reference-only |
| Anthropic skill `docx` — `accept_changes.py` через `soffice` | Anthropic skill | **Только** dev-time oracle для генерации expected snapshots в golden corpus (см. § 11). В runtime не входит, `soffice` не является зависимостью продакшен-инсталляции | `scripts/dev/` (dev-only) |

---

## 4. Доменная модель

Все доменные типы располагаются в `disprot-core/src/disprot/core/model/`. Реализуются как `@dataclass(frozen=True)` или pydantic-модели; immutable где возможно; коллекции в frozen-моделях — `tuple`, не `list`.

### 4.1. Ключевые типы

#### `Run`

Сегмент с одинаковым форматированием.

| Поле | Тип | Назначение |
|---|---|---|
| `text` | `str` | Текст |
| `formatting` | `Mapping[str, str \| int \| bool]` (immutable, через `types.MappingProxyType` либо frozen pydantic-модель) | Базовые атрибуты: bold, italic, underline, font, size |

**Run НЕ содержит revision-полей.** Revision-семантика (что было удалено / вставлено, кто автор, какой `revision_id`) принадлежит исключительно `RevisionResolver` и материализуется в `EnrichedParagraph.revisions` / `EnrichedParagraph.original_text` / `EnrichedParagraph.accepted_text`. Текст runs внутри `<w:ins>` или `<w:del>` сохраняется как обычный `Run.text` без интерпретации (см. § 5.1). Это исключает дублирование владения revision-данными.

#### `RawParagraph`

`@dataclass(frozen=True)`. Продукт `OOXMLReader`. Никаких revision/numbering-полей — только то, что прочитано из `document.xml`.

| Поле | Тип |
|---|---|
| `block_id` | `str` (стабильный идентификатор; присваивается `OOXMLReader` как монотонный индекс по порядку появления `<w:p>` в `document.xml`, например `p_0001`, `p_0002`) |
| `runs` | `tuple[Run, ...]` |
| `num_id` | `int \| None` |
| `ilvl` | `int \| None` |
| `style_id` | `str \| None` |
| `is_in_table` | `bool` |
| `table_ref` | `str \| None` (id таблицы, если параграф внутри ячейки) |

Метод `text(self) -> str: return ''.join(r.text for r in self.runs)` — derived строковое представление, используется fallback regex'ами в `NumberingResolver` / `ClauseSegmenter` и сериализацией в UI/превью.

#### `RawTable`

`@dataclass(frozen=True)`. Продукт `OOXMLReader`. Представляет `<w:tbl>` как блок верхнего уровня документа (не вложенный внутрь параграфа).

| Поле | Тип |
|---|---|
| `block_id` | `str` (например `t_0001`, `t_0002`; нумерация независима от `p_NNNN`) |
| `rows` | `tuple[RawTableRow, ...]` |
| `xml_path` | `str` (XPath-подобный путь до элемента в `document.xml` для отладки) |
| `has_revisions` | `bool` (выставлен `OOXMLReader` в `True`, если внутри поддерева `<w:tbl>` найден хотя бы один элемент `<w:ins>` или `<w:del>`. Структура самих revisions **не** извлекается — это лишь wiring-флаг для downstream-стадий) |

#### `RawTableRow` / `RawTableCell`

`@dataclass(frozen=True)`. Минимальные структуры для табличного содержимого.

- `RawTableRow` имеет одно поле `cells: tuple[RawTableCell, ...]`.
- `RawTableCell` имеет одно поле `paragraphs: tuple[RawParagraph, ...]` — параграфы внутри ячейки. У этих `RawParagraph` поле `is_in_table=True`, `table_ref=parent_table.block_id`. Они **не** попадают в `RawDocument.blocks` (которые содержат только top-level блоки `<w:body>`); они доступны только через `RawTable.rows[i].cells[j].paragraphs`.

В v1 revisions внутри ячеек не интерпретируются построчно — таблица рассматривается как единое целое. Однако сами параграфы внутри ячеек собираются в `RawTableRow` для целей сериализации в текст (см. `_serialize_table_to_text` в § 5.6).

#### `RawBlock`

Type alias: `RawBlock = RawParagraph | RawTable`. Используется в `RawDocument.blocks` для хранения интерливированной последовательности параграфов и таблиц в порядке их появления в `document.xml`.

#### `RawDocument`

`@dataclass(frozen=True)`. Контейнер всего, что прочитал `OOXMLReader`.

| Поле | Тип |
|---|---|
| `source_path` | `pathlib.Path` (абсолютный путь к загруженному `.docx` в `~/.disprot/sessions/<session_id>/input.docx`) |
| `blocks` | `tuple[RawBlock, ...]` (интерливированная последовательность `RawParagraph` и `RawTable` в порядке появления в `document.xml`) |
| `contract_name` | `str \| None` (опционально извлечённое имя договора из заголовка) |

#### `RevisionData`

`@dataclass(frozen=True)`. Продукт `RevisionResolver` для одного `block_id`.

| Поле | Тип |
|---|---|
| `original_text` | `str` (текст без принятых правок) |
| `accepted_text` | `str` (текст с принятыми правками) |
| `revisions` | `tuple[Revision, ...]` |

#### `NumberingData`

`@dataclass(frozen=True)`. Продукт `NumberingResolver` для одного `block_id`.

| Поле | Тип |
|---|---|
| `rendered_number` | `str \| None` (например `"2.1.3."`) |
| `confidence` | `float` (0.0–1.0) |
| `source` | `Literal["docx2python", "regex", "unmapped"]` |

#### `ResolverDiagnostic`

`@dataclass(frozen=True)`. Несёт диагностическое сообщение от resolver-стадий (`RevisionResolver`, `NumberingResolver`) в `ValidationEngine`.

```python
@dataclass(frozen=True)
class ResolverDiagnostic:
    code: Literal["REVISION_MAPPING_MISMATCH", "NUMBERING_MAPPING_MISMATCH"]
    severity: Literal["info", "warning"]
    message: str
    metadata: Mapping[str, Any]   # immutable; например {"unmapped_count": 3, "expected": 12, "actual": 9}
```

#### `RevisionResolveResult`

`@dataclass(frozen=True)`. Результат `RevisionResolver.extract`. Несёт map ревизий вместе с диагностиками — без этого `ValidationEngine` не сможет получить сообщение о mismatch'е.

```python
@dataclass(frozen=True)
class RevisionResolveResult:
    revision_map: Mapping[str, RevisionData]   # immutable; ключ — block_id
    diagnostics: tuple[ResolverDiagnostic, ...]
```

#### `NumberingResolveResult`

`@dataclass(frozen=True)`. Симметричный `RevisionResolveResult` тип для `NumberingResolver.resolve`.

```python
@dataclass(frozen=True)
class NumberingResolveResult:
    numbering_map: Mapping[str, NumberingData]   # immutable; ключ — block_id
    diagnostics: tuple[ResolverDiagnostic, ...]
```

#### `EnrichedParagraph`

`@dataclass(frozen=True)`. Расширяет `RawParagraph` revision/numbering-полями. Создаётся фабрикой `ParagraphEnricher.enrich(raw, revision_data, numbering_data)`. После создания не мутируется.

| Поле | Тип |
|---|---|
| `block_id` | `str` (наследуется из RawParagraph) |
| `runs` | `tuple[Run, ...]` |
| `num_id` | `int \| None` |
| `ilvl` | `int \| None` |
| `style_id` | `str \| None` |
| `is_in_table` | `bool` |
| `table_ref` | `str \| None` |
| `original_text` | `str` |
| `accepted_text` | `str` |
| `revisions` | `tuple[Revision, ...]` |
| `rendered_number` | `str \| None` |
| `numbering_confidence` | `float` |

Метод `text(self) -> str: return ''.join(r.text for r in self.runs)` — повторяет поведение `RawParagraph.text` для удобства downstream-кода (UI / сериализация). Семантически эквивалентен `accepted_text` для большинства параграфов, но физически читается из `runs` (что включает текст внутри `<w:ins>` / `<w:del>` без интерпретации revisions).

#### `EnrichedTable`

`@dataclass(frozen=True)`. Расширение `RawTable` для downstream-стадий. Revisions/numbering на уровне таблицы как блока не вычисляются — таблица обрабатывается как единый табличный контейнер. Поля совпадают с `RawTable` (`block_id`, `rows`, `xml_path`, `has_revisions`); значение `has_revisions` наследуется без изменений из соответствующего `RawTable`.

#### `EnrichedBlock`

Type alias: `EnrichedBlock = EnrichedParagraph | EnrichedTable`. Используется в `Clause.blocks` и в выходе `ParagraphEnricher.enrich_all` для сохранения порядка и interleaving параграфов и таблиц.

#### `Clause`

| Поле | Тип |
|---|---|
| `clause_id` | `str` |
| `label` | `str` (rendered_number или специальная метка: `"Преамбула"`, `"Реквизиты сторон"`, `"Приложение № 1, пункт 3"`) |
| `level` | `int` (0 — top-level) |
| `parent_id` | `str \| None` (ссылка на родительский `clause_id` при nested numbering) |
| `blocks` | `tuple[EnrichedBlock, ...]` (интерливированная последовательность параграфов и таблиц, принадлежащих этому пункту, в порядке документа) |
| `children` | `tuple[Clause, ...]` |
| `flags` | `frozenset[ClauseFlag]` |

#### `Revision`

| Поле | Тип |
|---|---|
| `revision_id` | `str` |
| `type` | `RevisionType` (`INS` / `DEL` / `MOVE_FROM` / `MOVE_TO` / `FORMAT_ONLY`) |
| `author` | `str` (парсится из `<w:author>`, **в бизнес-логику не включается**, см. § 6.7) |
| `date` | `datetime \| None` |

`PARAGRAPH_INSERTION` / `PARAGRAPH_DELETION` отдельным `RevisionType` не моделируются — выводятся из `ClauseFlag.NEW_CLAUSE` / `ClauseFlag.DELETED_CLAUSE`.

#### `Party`

| Поле | Тип |
|---|---|
| `party_id` | `str` |
| `name` | `str` (юр. наименование, например `"ООО \"Ромашка\""`) |
| `role` | `str` (например `"Арендатор"`, `"Исполнитель"`) |
| `confidence` | `float` (0.0–1.0) |

#### `ProtocolRow`

| Поле | Тип |
|---|---|
| `row_id` | `str` |
| `point_label` | `str` (`"2.1.3."`, `"Новый пункт 5"`, `"Преамбула"`, `"Реквизиты сторон"`) |
| `party_1_text` | `str` |
| `party_2_text` | `str` |
| `agreed_text` | `str` |
| `source_clause_id` | `str \| None` (`None` для строк, добавленных вручную) |
| `confidence` | `float` |
| `flags` | `frozenset[RowFlag]` |
| `user_edited` | `bool` |

### 4.2. Флаги

`ClauseFlag` (значения enum):

- `MULTI_PARAGRAPH` — пункт состоит из нескольких параграфов.
- `CONTAINS_TABLE` — внутри пункта есть таблица.
- `STANDALONE_TABLE` — Clause создан искусственно для таблицы, встретившейся вне любого numbered context (например таблица сразу после преамбулы, до первого numbered paragraph).
- `NEW_CLAUSE` — пункт целиком вставлен (`<w:ins>` обёртывает весь параграф).
- `DELETED_CLAUSE` — пункт целиком удалён.
- `LOW_CONFIDENCE_BOUNDARY` — segmenter не уверен в границах пункта.
- `LOW_NUMBERING_CONFIDENCE` — нумерация определена fallback-regex'ом или не определена.
- `TABLE_CELL_REVISIONS` — внутри как минимум одной из таблиц этого Clause найдены revisions на уровне ячеек (т.е. хотя бы один `EnrichedTable.has_revisions == True`). v1 не извлекает структуру этих правок; флаг — wiring для force-include в `ProtocolBuilder` и для row-level warning.

`RowFlag`:

- `LOW_CONFIDENCE`
- `MULTI_PARAGRAPH_SOURCE`
- `TABLE_CHANGE` — внутри Clause есть таблица (флаг `CONTAINS_TABLE`); пользовательский визуальный hint, что нужно проверить вручную.
- `TABLE_CELL_CHANGE` — Clause имеет флаг `TABLE_CELL_REVISIONS`; в v1 protocol row построен с `original == accepted` (текущий рендер таблицы), пользователь редактирует вручную.
- `MOVE_DETECTED`
- `MANUALLY_ADDED`
- `USER_EDITED`

`RevisionType`: `INS`, `DEL`, `MOVE_FROM`, `MOVE_TO`, `FORMAT_ONLY`.

---

## 5. Компоненты ядра

Все находятся в `disprot-core/src/disprot/core/`.

### 5.1. `parsing/ooxml.py` — `OOXMLReader`

Открывает DOCX как ZIP через stdlib `zipfile`, парсит `document.xml`, `numbering.xml`, `styles.xml` через `lxml`.

Делает Run Coalescing — склеивает фрагментированные соседние `<w:r>` с одинаковым форматированием в один логический `Run` (адаптация из `adeu`).

```python
class OOXMLReader:
    def read(self, path: pathlib.Path) -> RawDocument: ...
```

Отдаёт `RawDocument`, где `RawDocument.blocks` — интерливированная последовательность `RawParagraph` и `RawTable` в порядке появления в `document.xml` (top-level дети `<w:body>`). `RawDocument.source_path` сохраняет абсолютный путь, переданный в `read()` — нужен downstream (`RevisionResolver`) для повторного открытия файла независимой библиотекой. `block_id` для параграфов — `p_0001`, `p_0002`, …, монотонный по порядку среди только параграфов; для таблиц — `t_0001`, `t_0002`, …, монотонный по порядку среди только таблиц.

**На этом уровне нет семантики revisions, нумерации или сегментации.** В частности:

- `OOXMLReader` сохраняет ВЕСЬ текст из `<w:t>` внутри `<w:p>` независимо от того, обёрнут ли соответствующий `<w:r>` в `<w:ins>` или `<w:del>`. Каждый такой `<w:r>` (включая те, что внутри ins/del-обёрток) превращается в обычный `Run` без потери текста.
- `OOXMLReader` НЕ присваивает `revision_id`-ы, НЕ строит original/accepted view и НЕ конструирует `Revision`-объекты. Семантика правок (что было удалено, что добавлено, кто автор) делается в `RevisionResolver` (§ 5.2) поверх независимого чтения файла через `docx-revisions`.
- Единственная revision-aware операция на этом уровне — структурный обход поддерева `<w:tbl>` и выставление `RawTable.has_revisions = True`, если внутри найден хотя бы один элемент `<w:ins>` или `<w:del>`. Структура самих правок внутри таблицы НЕ извлекается; см. § 5.6 / § 6.5 для семантики force-include в `ProtocolBuilder`.

### 5.2. `parsing/revisions.py` — `RevisionResolver`

Фасад над библиотекой `docx-revisions`. **Единственный источник revision-семантики в системе.** Никакой другой компонент не интерпретирует `<w:ins>` / `<w:del>` структурно (за исключением boolean-флага `RawTable.has_revisions`, выставляемого в `OOXMLReader`).

```python
class RevisionResolver:
    def extract(self, raw_doc: RawDocument) -> RevisionResolveResult: ...
```

**Источник `.docx`:** `RevisionResolver` открывает `raw_doc.source_path` через `docx-revisions` — это вторая независимая read-операция над тем же файлом. Накладные расходы малы для документов ≤ 25 MB (см. § 6.1). Передавать сам ZIP-объект через `OOXMLReader` бессмысленно: `docx-revisions` ожидает путь и сам управляет жизненным циклом ресурсов.

**Маппинг `docx-revisions` paragraph results → `block_id`:**

- `docx-revisions` итерируется по своим paragraph-объектам в порядке их появления в `document.xml` — том же порядке, в котором `OOXMLReader` итерировал `<w:p>`.
- **Top-level only:** счёт ведётся только по `<w:p>`, являющимся прямыми детьми `<w:body>`. Параграфы внутри `<w:tc>` (ячеек таблиц) НЕ итерируются `docx-revisions` и НЕ становятся top-level `RawParagraph` (они хранятся внутри `RawTable.rows[i].cells[j].paragraphs`). Это значит, что счёт обоих стримов ведётся симметрично по top-level `RawParagraph` объектам в `raw_doc.blocks` (без захода в `RawTable.rows`).
- Соответствие позиционное 1:1 по индексу среди только top-level параграфов: `i_para`-й `RawParagraph` в `raw_doc.blocks` (счёт только среди `RawParagraph`, таблицы пропускаются и внутрь `RawTable` не залезаем) сопоставляется с `i_para`-м paragraph-объектом из `docx-revisions`. Данные конвертируются в `RevisionData(original_text, accepted_text, revisions)` и кладутся в результат под ключом `raw_paragraph.block_id`.
- При расхождении количеств (`docx-revisions` вернул больше или меньше paragraph-объектов, чем `OOXMLReader` нашёл top-level `RawParagraph`) расхождение **не падает**, но обрабатывается так:
  - **Безопасный fallback для unmapped `RawParagraph`:** для каждого `block_id`, для которого нет соответствия в выходе `docx-revisions`, в `revision_map` кладётся `RevisionData(original_text=raw.text(), accepted_text=raw.text(), revisions=())`. То есть в обеих колонках протокола пользователь увидит хотя бы plain-текст параграфа, а не пустую строку. Это явно снижает риск тихой потери текста (видимая потеря — это правки внутри параграфа, которые НЕ будут различимы; но сам текст останется виден).
  - Избыточные paragraph-объекты `docx-revisions` (без соответствующего `RawParagraph`) игнорируются.
  - В `diagnostics` добавляется `ResolverDiagnostic(code="REVISION_MAPPING_MISMATCH", severity="warning", message=..., metadata={"unmapped_count": N, "expected": E, "actual": A, ...})`. Сообщение содержит: количество unmapped `RawParagraph`, количество избыточных `docx-revisions`-объектов, и пометку «повышенный риск пропуска правок внутри указанных параграфов — проверьте таблицу вручную». В `ValidationEngine` (§ 5.7) этот diagnostic преобразуется в session-level `ValidationWarning` с `kind = REVISION_MAPPING_MISMATCH`.

Возвращает `RevisionResolveResult(revision_map, diagnostics)`. **Не мутирует `RawDocument`** — модели остаются frozen.

**Один файл — одна точка замены.** Если `docx-revisions` придётся форкать или менять реализацию, изменения локализованы здесь.

### 5.3. `parsing/numbering.py` — `NumberingResolver`

Фасад над `docx2python.list_position`.

```python
class NumberingResolver:
    def resolve(self, raw_doc: RawDocument) -> NumberingResolveResult: ...
```

**Маппинг `docx2python` → `block_id`:**

- `docx2python` открывает `raw_doc.source_path` (третья независимая read-операция; накладные расходы малы) и итерируется по `<w:p>` в порядке появления в `document.xml`. `OOXMLReader` итерирует те же `<w:p>` в том же порядке.
- **Top-level only (симметрично с `RevisionResolver`, § 5.2):** `docx2python` итерируется только по `<w:p>`, являющимся прямыми детьми `<w:body>`. Параграфы внутри `<w:tc>` не попадают в этот стрим (они доступны через `RawTable.rows[i].cells[j].paragraphs` и не имеют top-level позиции).
- Соответствие 1:1 по индексу среди только top-level параграфов: i-й `RawParagraph` в `raw_doc.blocks` (счёт только среди `RawParagraph`, таблицы пропускаются и внутрь `RawTable` не залезаем) соответствует i-му элементу в обходе `docx2python`.
- При расхождении количества **силой не маппим**: такие `block_id` получают `NumberingData(rendered_number=None, confidence=0.0, source="unmapped")` и не считаются ошибкой парсинга — на них поднимается row-level `LOW_NUMBERING_CONFIDENCE`. Если общее число unmapped блоков ненулевое — в `diagnostics` добавляется `ResolverDiagnostic(code="NUMBERING_MAPPING_MISMATCH", severity="warning", metadata={"unmapped_count": N, "expected": E, "actual": A})`. В `ValidationEngine` этот diagnostic преобразуется в session-level `ValidationWarning` с `kind = NUMBERING_MAPPING_MISMATCH`.

Возвращает `NumberingResolveResult(numbering_map, diagnostics)`. **Не мутирует `RawDocument`** — модели остаются frozen.

**Confidence:**

| Источник | Confidence | `source` |
|---|---|---|
| `docx2python` отдал номер | `1.0` | `"docx2python"` |
| Regex-fallback совпал | `0.7` | `"regex"` |
| Не определилось / unmapped | `0.0` | `"unmapped"` |

Regex fallback `^\s*(Статья\s+)?\d+(\.\d+)*\.?\s+` применяется **только** если `docx2python` для абзаца вернул `None` или сбросил счётчик неожиданным образом (предыдущий абзац имел номер `2.1`, текущий — `None` при наличии `numPr` в `RawParagraph`).

### 5.4. `parsing/segmentation.py` — `ClauseSegmenter`

Собственный код, цель ~250 строк, реализован как state-machine с явным стеком уровней.

```python
class ClauseSegmenter:
    def segment(self, blocks: tuple[EnrichedBlock, ...]) -> list[Clause]: ...
```

На вход поступает интерливированная последовательность `EnrichedParagraph` и `EnrichedTable` в порядке документа (выход `ParagraphEnricher.enrich_all`). Сегментер сохраняет порядок и interleaving — таблицы попадают в `Clause.blocks` рядом с параграфами в том же месте, где они физически находятся в документе.

**Определение `clause_level` для `EnrichedParagraph`:**

- Если есть `num_id` (`numPr` в OOXML) — `level = ilvl` (0-based).
- Если `num_id == None`, но `rendered_number` определился через regex — `level = len(rendered_number.rstrip(".").split(".")) - 1` (например `"2.1.3"` → level 2).
- Иначе — `None` (continuation paragraph).

**Алгоритм state-machine:**

- Стек `current_clauses: list[ClauseBuilder]` — открытые Clause от верхнего уровня к нижнему.
- Для каждого `EnrichedBlock` b в порядке документа:
  - **`b` — `EnrichedParagraph` p:**
    - **Whitespace-only** (`p.accepted_text.strip() == ""` и `p.original_text.strip() == ""`) — игнорируется.
    - **`p.level == N` (numbered):**
      - pop из стека все `ClauseBuilder` c уровнем ≥ N (закрываем их в готовые `Clause`).
      - создаём новый `ClauseBuilder` с `level = N`. `parent_id` = `clause_id` верхнего элемента стека после pop, либо `None`.
      - push в стек.
      - присоединяем p как первый блок текущего clause (через `ClauseBuilder.append_block(p)`).
    - **`p.level == None` (continuation):**
      - присоединяем к top of stack через `append_block(p)`.
      - если стек пуст — это часть преамбулы (см. ниже).
  - **`b` — `EnrichedTable` t:**
    - если стек непустой — присоединяем к top of stack через `append_block(t)`. Поднимаем `ClauseFlag.CONTAINS_TABLE` на этом clause; если `t.has_revisions == True` — дополнительно поднимаем `ClauseFlag.TABLE_CELL_REVISIONS`.
    - если стек пустой:
      - если ещё не было ни одного numbered paragraph (мы в преамбуле) — присоединяем к преамбульному `ClauseBuilder` (создаётся лениво при первом блоке); если `t.has_revisions == True` — поднимаем `TABLE_CELL_REVISIONS` на преамбульном clause.
      - иначе создаём «sibling» `Clause(label="Таблица", level=0, parent_id=None)` с единственным блоком t и флагами `{STANDALONE_TABLE, CONTAINS_TABLE}`; если `t.has_revisions == True` — добавляем `TABLE_CELL_REVISIONS`.
- В конце документа: pop всё содержимое стека и закрываем clauses.

**Иерархия:** `Clause.parent_id` ссылается на `clause_id` родителя, зафиксированного в момент создания. `Clause.children` собирается отдельным проходом по плоскому списку через `parent_id`.

**Специальные блоки:**

- **Преамбула** — всё ДО первого numbered paragraph упаковывается в `Clause(label="Преамбула", level=0, parent_id=None)`.
- **Приложения** — маркер `^\s*Приложение\s*№?\s*\d+` (case-insensitive) → закрытие текущего стека и открытие нового top-level Clause с `label = "Приложение № N"`. Дальнейшие numbered paragraphs становятся детьми этого clause; их `label = "Приложение № N, пункт X"`.
- **Реквизиты сторон** — эвристика **только по тексту параграфа** (стили `style_id` не используются: они называются по-разному в разных шаблонах и часто не совпадают с ожиданиями).
  - Берётся «хвост» документа: последние N параграфов (`N = 30`) среди top-level `EnrichedParagraph` в `RawDocument.blocks` (таблицы и параграфы внутри таблиц не считаются для целей выбора кандидатов; точкой отсчёта остаётся top-level paragraph stream).
  - Применяется case-insensitive substring match по `paragraph.text()` (см. `EnrichedParagraph.text`). Триггерные подстроки: `"реквизиты сторон"`, `"реквизиты"`, `"подписи сторон"`, `"подписи и реквизиты"`, `"адреса и реквизиты"`.
  - Если match найден хотя бы в одном из этих параграфов — все блоки от первого matched параграфа и до конца документа (в порядке появления, включая таблицы) объединяются в единый `Clause(label="Реквизиты сторон", level=0, parent_id=None)` независимо от того, какие numbered/unnumbered структуры там были иначе.
  - Если match не найден — последний пункт документа НЕ помечается как реквизиты автоматически; обрабатывается как обычный numbered/unnumbered Clause.

Ожидаемое поведение для multi-level / table-inside / continuation / NEW_CLAUSE / DELETED_CLAUSE задаётся фикстурами в § 11.

### 5.4a. `parsing/enrich.py` — `ParagraphEnricher`

Фабрика, собирающая `EnrichedParagraph` из `RawParagraph` + `RevisionData` + `NumberingData` и `EnrichedTable` из `RawTable`. Не имеет состояния; чистая функция.

```python
@dataclass(frozen=True)
class EnrichmentResult:
    blocks: tuple[EnrichedBlock, ...]
    diagnostics: tuple[ResolverDiagnostic, ...]   # конкатенация revision_result.diagnostics + numbering_result.diagnostics


class ParagraphEnricher:
    @staticmethod
    def enrich(
        raw: RawParagraph,
        revision_data: RevisionData,
        numbering_data: NumberingData,
    ) -> EnrichedParagraph: ...

    @staticmethod
    def enrich_table(raw: RawTable) -> EnrichedTable: ...

    @staticmethod
    def enrich_all(
        raw_doc: RawDocument,
        revision_result: RevisionResolveResult,
        numbering_result: NumberingResolveResult,
    ) -> EnrichmentResult: ...
```

`enrich_all` принимает оба resolve-результата, забирает map-ы для собственно enrichment и **прокидывает diagnostics дальше**: на выходе `EnrichmentResult.diagnostics` — конкатенация `revision_result.diagnostics + numbering_result.diagnostics` в исходном порядке. Этот tuple позже передаётся в `ValidationEngine.validate(...)` (см. § 5.7), где каждый `ResolverDiagnostic` превращается в session-level `ValidationWarning`.

Итерируется по `raw_doc.blocks` в порядке документа, **сохраняя interleaving** параграфов и таблиц:

- `RawParagraph` → `EnrichedParagraph`. Если `block_id` отсутствует в `revision_result.revision_map` — используется `RevisionData(original_text=raw.text(), accepted_text=raw.text(), revisions=())`; если нет в `numbering_result.numbering_map` — `NumberingData(rendered_number=None, confidence=0.0, source="unmapped")`.
- `RawTable` → `EnrichedTable` через `enrich_table` (без revisions/numbering — таблица как единый табличный контейнер).

Возвращает `EnrichmentResult(blocks, diagnostics)`. `EnrichmentResult.blocks` передаётся в `ClauseSegmenter.segment(blocks)`; `EnrichmentResult.diagnostics` передаётся в `ValidationEngine.validate(...)` как `resolver_diagnostics`.

### 5.5. `extraction/parties.py`

ABC `PartyExtractor` с фабрикой `for_language(lang: str) -> PartyExtractor`.

```python
class PartyExtractor(ABC):
    @abstractmethod
    def extract(self, clauses: list[Clause]) -> list[Party]: ...
```

v1 содержит:

- `RussianPartyExtractor` — Natasha `NewsNERTagger` + Yargy parser. Yargy-грамматики покрывают типовые формулы: `именуемое в дальнейшем "..."`, `далее — ...`, табличные преамбулы.

**`PartyExtractor.extract` НЕ возвращает revision_authors и НЕ делает author→party mapping.** Авторы правок не используются для определения сторон.

v2 (отложено): `EnglishPartyExtractor` через `spaCy`.

### 5.6. `building/builder.py` — `ProtocolBuilder`

Принимает `(clauses, drafting_party, counterparty)`.

**Критерий включения Clause в строки протокола (v1):** Clause включается, если выполнено **любое** из условий:

- (а) у одного из его `EnrichedParagraph` есть textual revisions (т.е. `len(p.revisions) > 0` и среди них есть `INS` / `DEL` — не только `FORMAT_ONLY`); ИЛИ
- (б) Clause имеет флаг `ClauseFlag.TABLE_CELL_REVISIONS` (в одной из вложенных таблиц обнаружены ячейные правки, которые v1 не извлекает структурно).

Format-only revisions при отсутствии (а) и (б) игнорируются (учитываются в `ValidationReport`, но строк не порождают).

В случае (б) без (а) — то есть Clause force-включается ТОЛЬКО из-за `TABLE_CELL_REVISIONS` — `original_text` и `accepted_text` колонок получаются через **общую сериализацию clause** через `_serialize_clause_to_text(clause, mode)`, где `mode` ∈ `{"original", "accepted"}`. Для табличных ячеек в v1 справедливо `original == accepted == текущий рендер таблицы` (т.е. pre-revision содержимое внутри ячеек не восстанавливается). Пользователь правит `party_1_text` / `party_2_text` вручную; row помечается флагом `RowFlag.TABLE_CELL_CHANGE`. См. также `ValidationEngine.TABLE_CELL_CHANGE` warning в § 5.7.

**Базовый инвариант (важно для swap-parties):** колонка 2 = `original_text` (документ ДО правок), колонка 3 = `accepted_text` (документ ПОСЛЕ правок). Этот маппинг не меняется никогда — `original_text` / `accepted_text` физически приходят из DOCX. При swap-parties меняется только assignment `drafting_party_id` (см. § 8.1) и пересчитывается `agreed_text`. Headers столбцов вычисляются из текущих `drafting_party` / `counterparty` (роль + fallback при пустой роли — см. § 5.8).

**Маппинг колонок:**

| Колонка | Поле | Содержимое |
|---|---|---|
| 1. Пункт договора | `point_label` | `rendered_number` или специальная строка (`"Преамбула"`, `"Новый пункт N"`, `"Реквизиты сторон"`) |
| 2. Редакция counterparty | `party_1_text` | `original_text` (документ до правок). Header колонки — «Редакция [роль counterparty]» |
| 3. Редакция drafting party | `party_2_text` | `accepted_text` (документ после правок). Header колонки — «Редакция [роль drafting party]» |
| 4. Согласованная редакция | `agreed_text` | `"Редакция [роль drafting party]"` (например `"Редакция Арендатора"`). Если роль drafting party не указана — `"Редакция Стороны 2"` |

**Семантика swap-parties:** swap — это **header-only relabel**. Содержимое `party_1_text` / `party_2_text` НЕ меняется (это `original_text` / `accepted_text` соответственно — физический факт). Меняется только: какой `Party` считается drafting (= editor / автор правок), какой counterparty. Реализация — единственный источник истины: `sessions.drafting_party_id`. Counterparty не хранится отдельной колонкой, а вычисляется во время чтения как «вторая `Party` из таблицы `parties` в этой сессии, не равная `drafting_party_id`» (см. § 7.2 / § 8.1). После swap пересчитывается `agreed_text` (по новой роли drafting party) для всех `protocol_rows` с `user_edited == False` (строки с `user_edited == True` НЕ трогаются — пользовательская правка приоритетнее). Headers колонок 2 и 3 в экспорте и UI отображаются с новыми ролями. Это переинтерпретирует «who edited», но физический документ и его revisions неизменны.

**Сериализация `Clause.blocks` в текст колонок (`_serialize_clause_to_text`):**

Текст обеих колонок получается через единый helper `_serialize_clause_to_text(clause, mode)`, где `mode` ∈ `{"original", "accepted"}`. Helper обходит `clause.blocks` в порядке появления и преобразует каждый блок:

- `EnrichedParagraph` → `p.original_text` если `mode == "original"`, иначе `p.accepted_text`.
- `EnrichedTable` → результат helper'а `_serialize_table_to_text(table) -> str`. Helper возвращает строку: каждая строка таблицы — отдельный `\n`-разделённый элемент; внутри строки ячейки разделены ` | ` (пробел, pipe, пробел). Многоабзацный текст внутри ячейки склеивается через одиночный пробел. Перед и после табличного фрагмента вставляется `\n` (чтобы таблица отделялась от соседних параграфов). **В v1 `_serialize_table_to_text` не различает `mode`** — для таблиц pre-revision и post-revision содержимое идентично (см. ниже).

Конкатенация всех элементов через `\n`. `party_1_text = _serialize_clause_to_text(clause, "original")`, `party_2_text = _serialize_clause_to_text(clause, "accepted")`.

Для таблиц в v1 не различаем pre/post-revision содержимое — таблица рассматривается как «единое целое»; если внутри неё были ячейные правки (`EnrichedTable.has_revisions == True`), Clause получит флаг `TABLE_CELL_REVISIONS` (см. § 5.4), `ProtocolBuilder` всё равно включит этот Clause в строки (см. критерий выше), а row будет помечен `TABLE_CELL_CHANGE` — пользователь правит колонки вручную.

**Спецслучаи:**

- **Multi-paragraph Clause:** тексты колонок склеиваются через `\n` с сохранением порядка блоков (см. выше).
- **Таблицы внутри пункта:** сериализуются через `_serialize_table_to_text`. Флаг `TABLE_CHANGE` поднимается на `ProtocolRow`, если `Clause.flags` содержит `CONTAINS_TABLE`. Дополнительно: если `Clause.flags` содержит `TABLE_CELL_REVISIONS` — на row поднимается флаг `TABLE_CELL_CHANGE` (warning «правки внутри ячеек таблицы не извлечены автоматически — отредактируйте строку вручную»).
- **`STANDALONE_TABLE` Clause:** строится единственная `ProtocolRow` с `point_label = "Таблица"`, `party_1_text` / `party_2_text` = результат `_serialize_clause_to_text(clause, "original")` / `_serialize_clause_to_text(clause, "accepted")` (которые в v1 совпадают для таблицы), `agreed_text` = по обычному правилу drafting party. Флаг `TABLE_CHANGE`; если есть `TABLE_CELL_REVISIONS` — также `TABLE_CELL_CHANGE`.
- **`NEW_CLAUSE`:** `party_1_text = "—"`, `party_2_text = текст нового пункта`, `point_label = "Новый пункт N"`, где `N` — порядковый счётчик новых пунктов (1, 2, 3, ...) в рамках сессии.
- **`DELETED_CLAUSE`:** `party_1_text = текст исходного пункта`, `party_2_text = "Исключить пункт N"`, `point_label = N`, где `N` — `rendered_number` исходного (удалённого) пункта.

### 5.7. `validation/engine.py` — `ValidationEngine`

Пробегает `(clauses, rows, resolver_diagnostics)`, выставляет flags на rows и возвращает `ValidationReport`:

```python
class ValidationEngine:
    def validate(
        self,
        clauses: list[Clause],
        rows: list[ProtocolRow],
        resolver_diagnostics: tuple[ResolverDiagnostic, ...],
    ) -> ValidationReport: ...


@dataclass(frozen=True)
class ValidationReport:
    textual_revisions_total: int
    covered_revisions: int
    format_only_revisions: int
    numbering_confidence_mean: float
    warnings: tuple[ValidationWarning, ...]
```

`resolver_diagnostics` приходит из `EnrichmentResult.diagnostics` (см. § 5.4a). Каждый `ResolverDiagnostic` преобразуется в session-level `ValidationWarning` по правилу:

- `code == "REVISION_MAPPING_MISMATCH"` → `ValidationWarning(kind="REVISION_MAPPING_MISMATCH", scope="session", severity=diagnostic.severity, message=diagnostic.message, metadata=diagnostic.metadata, clause_id=None, row_id=None)`.
- `code == "NUMBERING_MAPPING_MISMATCH"` → `ValidationWarning(kind="NUMBERING_MAPPING_MISMATCH", scope="session", severity=diagnostic.severity, message=diagnostic.message, metadata=diagnostic.metadata, clause_id=None, row_id=None)`.

Типы warning (`ValidationWarning.kind`):

- `LOW_NUMBERING_CONFIDENCE`
- `LOW_NUMBERING_CONFIDENCE_OVERALL` (session-level)
- `UNCOVERED_REVISIONS`
- `TABLE_CHANGE`
- `TABLE_CELL_CHANGE` — выпускается **row-level** для каждого Clause с флагом `TABLE_CELL_REVISIONS`. Сообщение: «правки внутри ячеек таблицы не извлечены автоматически — отредактируйте строку вручную». `scope = "row"`, `row_id` обязателен.
- `MULTI_PARAGRAPH`
- `MOVE_DETECTED`
- `FORMAT_ONLY_IGNORED`
- `REVISION_MAPPING_MISMATCH` (session-level) — `RevisionResolver` обнаружил расхождение в количестве top-level paragraph-объектов. Содержит количество unmapped блоков и пометку «повышенный риск пропуска правок». См. § 5.2.
- `NUMBERING_MAPPING_MISMATCH` (session-level) — `NumberingResolver` обнаружил расхождение в количестве top-level paragraph-объектов. См. § 5.3.
- `EMPTY_PROTOCOL` (session-level, severity = `"info"`) — выпускается, если итоговый список `ProtocolRow` пуст (см. edge case ниже). `scope = "session"`, без `clause_id` / `row_id`.

`ValidationWarning` несёт обязательные поля:

- `kind` — один из перечисленных типов выше.
- `scope: Literal["session", "clause", "row"]`.
- `severity: Literal["info", "warning"]` — `"info"` только для `EMPTY_PROTOCOL`; все остальные `kind` — `"warning"`. Поле дублирует семантику `ResolverDiagnostic.severity` (см. § 4.1) — это сознательное минимальное дублирование, общий type alias не вводится для простоты v1.
- `message` — человекочитаемая строка.

Дополнительно поддерживает опциональные поля:

- `metadata: Mapping[str, Any]` — машиночитаемые детали (например `{"unmapped_count": 3, "expected": 12, "actual": 9}` в `REVISION_MAPPING_MISMATCH`).
- `clause_id` / `row_id` — обязательность зависит от `scope` (см. ниже).

- `scope = "session"` — `clause_id is None` и `row_id is None`. Например `LOW_NUMBERING_CONFIDENCE_OVERALL`, `EMPTY_PROTOCOL`, `REVISION_MAPPING_MISMATCH`, `NUMBERING_MAPPING_MISMATCH`.
- `scope = "clause"` — `clause_id` обязателен, `row_id is None`.
- `scope = "row"` — `row_id` обязателен (`clause_id` опционален).

**Edge cases:**

- Если в документе нет ни одного параграфа с `rendered_number`, `numbering_confidence_mean = 0.0` (не NaN); поднимается warning `LOW_NUMBERING_CONFIDENCE_OVERALL` со `scope = "session"`.
- **Empty protocol:** `ProtocolBuilder` возвращает пустой список строк **только если** `textual_revisions_total == 0` **И** ни один Clause не имеет флаг `ClauseFlag.TABLE_CELL_REVISIONS`. Если хотя бы один Clause force-включается из-за `TABLE_CELL_REVISIONS` (см. § 5.6 / § 6.5), список не пустой даже при `textual_revisions_total == 0`. В случае пустого списка `ValidationReport.warnings` содержит session-level warning `EMPTY_PROTOCOL` (`scope = "session"`); UI показывает баннер «В документе не найдено правок».

### 5.8. `export/docx_export.py` — `ProtocolExporter`

Генерирует DOCX через `python-docx` и пишет в file-like объект (стрим). На диск ничего не сохраняет.

```python
class ProtocolExporter:
    def export(
        self,
        rows: list[ProtocolRow],
        drafting_party: Party,
        counterparty: Party,
        contract_name: str,
        output_stream: BinaryIO,
    ) -> None: ...
```

**Параметры:**

- `rows` — финальные `ProtocolRow` из БД (с user-edits, если они были).
- `drafting_party` — `Party` с подтверждённой ролью и наименованием (определяется backend по `sessions.drafting_party_id`).
- `counterparty` — вторая `Party` (вычисляется backend во время чтения как Party в этой session, не равная `drafting_party_id`; см. § 7.2 / § 8.1).
- `contract_name` — sanitized строка из § 6.4 (может быть пустой, если NULL в БД).
- `output_stream` — file-like объект, в который `python-docx` пишет байты DOCX (например `io.BytesIO()` со стороны backend).

**Никакого параметра `swap_state` нет.** `drafting_party_id` — единственный источник истины (см. § 7.2 / § 8.1). Backend передаёт уже-актуальные `drafting_party` / `counterparty`; exporter не делает никаких swap-операций сам.

**Шаблон:**

- A4, поля стандартные.
- Заголовок документа: `"Протокол разногласий к договору <contract_name>"` либо `"Протокол разногласий"`, если `contract_name` пустой.
- Таблица 4 колонки фиксированной ширины.
- Базовое форматирование: Times New Roman 11pt, выравнивание по ширине, границы ячеек.

**Шапка таблицы (4 заголовка):**

- Колонка 1 — `"Пункт договора"`.
- Колонка 2 — `"Редакция <counterparty.role>"`. Если `counterparty.role` пустая — `"Редакция Стороны 1"`.
- Колонка 3 — `"Редакция <drafting_party.role>"`. Если `drafting_party.role` пустая — `"Редакция Стороны 2"`.
- Колонка 4 — `"Согласованная редакция"`.

Headers всегда строятся из переданных `drafting_party` / `counterparty` без условных ветвлений. Если backend хочет «инвертировать» назначение сторон, он должен сначала переключить `sessions.drafting_party_id` (через `POST /api/sessions/{id}/swap-parties`, см. § 8.1) и затем вызвать exporter с уже-новой парой `drafting_party` / `counterparty`. Exporter не имеет состояния «swap».

**Поведение user-edited rows:** для row с `user_edited == True` тексты `party_1_text` / `party_2_text` / `agreed_text` берутся из БД дословно (пользовательская правка приоритетнее автоматической; никакого пересчёта exporter не делает).

**Тело:** многоабзацный текст в ячейках сохраняется через `\n` → отдельные параграфы внутри ячейки.

### 5.9. `llm/__init__.py` — `LLMAssistant`

`typing.Protocol`, архитектурный порт для будущего LLM-модуля.

```python
class LLMAssistant(Protocol):
    def assist_party_extraction(self, preamble_text: str) -> list[Party] | None: ...
    def suggest_clause_split(self, clause: Clause) -> list[Clause] | None: ...
    def explain_revision(self, revision: Revision, original: str, accepted: str) -> str | None: ...
```

v1 регистрирует и использует `NoopAssistant` — все методы возвращают `None`.

`LLMAssistant` передаётся через DI в конструкторы `ProtocolBuilder` / `PartyExtractor` / `ClauseSegmenter`. **Ядро не импортирует никаких LLM-клиентов** (anthropic SDK, openai SDK и т.п.).

---

## 6. Pipeline

Pipeline разделён на backend-стадии. Каждая стадия выполняется синхронно в своём request-handler (FastAPI sync). Между стадиями возможны **USER GATE-ы** — клиентский UI ждёт ввода пользователя, прежде чем триггерить следующий endpoint. Никакой одной длинной обработки в одном request нет:

- `POST /api/sessions` — **atomic stages 1–4** (Ingest → Parse → Segment → Extract Parties). Возвращает в одном response: `session_id`, `preflight_metrics`, `preflight_diagnostics`, `parties`, `contract_name`. `preflight_diagnostics` — диагностики от `RevisionResolver` / `NumberingResolver`, нужные Экрану 2 для показа предупреждений; в БД не сохраняются (см. § 6.2 / § 6.4). Auto-suggest drafting party в v1 не делается — пользователь выбирает на Экране 2 явно (см. § 14 Future scope: эвристика author→party mapping откладывается).
- USER GATE 1 — Экран 2 (подтверждение сторон + выбор drafting party).
- `PATCH /api/sessions/{id}/parties` — пользователь утверждает parties + drafting_party_id.
- `POST /api/sessions/{id}/build` — **atomic stages 5–6** (Build + Validate). Возвращает `{rows, validation_report}`.
- USER GATE 2 — Экран 3 (правка таблицы). Каждое редактирование auto-save через `PATCH /api/sessions/{id}/rows/{row_id}` и связанные endpoints.
- `POST /api/sessions/{id}/export` — стадия Export. Возвращает DOCX bytes напрямую (см. § 6.6 / § 8.1).

`GET /api/sessions/{id}` — **read-only** endpoint без побочных эффектов: отдаёт текущее состояние сессии (status, parties, drafting_party_id, contract_name, preflight_metrics, validation_report (если уже посчитан), timestamps `created_at` / `updated_at`). Counterparty явно не возвращается — фронтенд вычисляет его как «вторую Party в `parties`, не равную `drafting_party_id`» (это симметрично с backend resolve, см. § 7.2). Используется фронтендом для restore при reopen вкладки. Поля зеркалят колонки `sessions` из § 7.2.

DOCX-файлы малы; очередь / async внутри стадии не требуются.

### 6.1. Ingest

Multipart upload. Проверки выполняются **строго в указанном порядке**; первый fail возвращает соответствующий HTTP-код, дальнейшие проверки не запускаются.

1. **Расширение файла строго `.docx`** (case-insensitive). Если `.doc`, `.docm`, `.docx.zip`, `.rtf` или любое другое — **HTTP 400** с сообщением: «Поддерживаются только файлы .docx без макросов».
2. **Размер файла ≤ 25 MB**. Иначе — **HTTP 413** с сообщением: «Размер файла превышает 25 MB».
3. **Файл — валидный ZIP** (через `zipfile.is_zipfile`). Иначе — **HTTP 400** с сообщением: «Файл повреждён или не является документом Word».
4. **ZIP содержит `word/document.xml`**. Иначе — **HTTP 400** с сообщением: «В архиве отсутствует word/document.xml — это не Word-документ».
5. **Defensive macros check**: ZIP **не** содержит `word/vbaProject.bin`. (`.docm` уже отсечён по расширению на шаге 1, но проверяем структурно на случай, если файл с расширением `.docx` всё равно содержит макросы.) Иначе — **HTTP 415** с сообщением: «Документ содержит макросы (vbaProject.bin) — не поддерживается».

При прохождении всех пяти проверок: сохранение в `~/.disprot/sessions/<session_id>/input.docx` через `platformdirs`.

### 6.2. Parse

`OOXMLReader.read(path) -> raw_doc` → `RevisionResolver.extract(raw_doc) -> revision_result` → `NumberingResolver.resolve(raw_doc) -> numbering_result` → `ParagraphEnricher.enrich_all(raw_doc, revision_result, numbering_result) -> EnrichmentResult`.

`EnrichmentResult.blocks` — `tuple[EnrichedBlock, ...]` с `EnrichedParagraph` и `EnrichedTable`, интерливированными в порядке документа.

`EnrichmentResult.diagnostics` — `tuple[ResolverDiagnostic, ...]` с диагностиками от обоих resolver-стадий (mismatch'и количества paragraph-объектов и т.п.). Эти diagnostics **в БД не сохраняются**: они возвращаются в response `POST /api/sessions` под ключом `preflight_diagnostics` (см. § 6.4 / § 8.1) для отображения на Экране 2 (см. § 9.2). На стадии Build (§ 6.5) Parse + Segment **полностью пересчитываются** заново (поскольку clauses не персистятся, см. § 6.5), поэтому `EnrichmentResult.diagnostics` тоже пересчитываются на каждом `POST /build` и оттуда передаются в `ValidationEngine.validate(...)`. Нет in-memory session state, нет необходимости синхронизировать diagnostics между двумя request-handler'ами.

Preflight-метрики вычисляются и сохраняются в `sessions.preflight_metrics_json` (см. § 7.2):

- `revisions_total`
- `format_only_count`
- `paragraphs_with_numbering`
- `numbering_confidence_mean`

Это **только числовые метрики** — `ResolverDiagnostic`-объекты в `preflight_metrics_json` не попадают.

### 6.3. Segment

`ClauseSegmenter.segment(blocks) -> list[Clause]`, где `blocks: tuple[EnrichedBlock, ...]` — `EnrichmentResult.blocks` из § 6.2. Special-case для преамбулы, реквизитов, приложений и `STANDALONE_TABLE` (см. § 5.4).

### 6.4. Extract — последняя стадия внутри `POST /api/sessions`, перед USER GATE 1

В рамках обработки `POST /api/sessions` после Segment вызывается `PartyExtractor.for_language("ru").extract(clauses)`. Возвращает `list[Party]` без mapping авторов. **Auto-suggest drafting party в v1 не делается** — concept «определить editor по revision authors» концептуально требует устойчивого author→party mapping, который v1 не строит (см. § 6.7 — авторы правок игнорируются как класс; см. также § 14 Future scope). Пользователь выбирает drafting party вручную на Экране 2.

Дополнительно вычисляется `contract_name` через **deterministic filename-based sanitization**:

1. Берётся имя загруженного файла (например `Договор аренды_v3 (правки).docx`).
2. Удаляется расширение `.docx`.
3. Удаляется хвост в скобках, если он совпадает с `\s*\([^)]*\)\s*$` (для удаления хвостов вроде `(правки)` или `(v3)` в конце).
4. `_` заменяются на пробелы.
5. Повторяющиеся пробелы сжимаются в один.
6. Trim.

Для примера выше результат — `Договор аренды v3`. Если итоговая строка пустая — `contract_name = None` (UI показывает «Протокол разногласий» без хвоста).

В v1 НЕ используется попытка извлечь имя из первого параграфа документа (стиль Heading1 / жирный шрифт): шаблоны слишком разнятся, риск ошибочного распознавания выше, чем удобство. Future scope.

Результаты (`session_id`, `preflight_metrics`, `preflight_diagnostics`, `parties`, `contract_name`) возвращаются в ответе на `POST /api/sessions`. Здесь:

- `preflight_metrics` — числовые показатели из § 6.2 (`revisions_total`, `format_only_count`, `paragraphs_with_numbering`, `numbering_confidence_mean`); персистятся в `sessions.preflight_metrics_json`.
- `preflight_diagnostics: list[ResolverDiagnostic-shape]` — сериализованные диагностики из `EnrichmentResult.diagnostics` (см. § 5.4a / § 6.2). Каждый элемент имеет shape `{code, severity, message, metadata}`, где `code` — `"REVISION_MAPPING_MISMATCH"` или `"NUMBERING_MAPPING_MISMATCH"`. Используется фронтендом на Экране 2 (см. § 9.2) для показа предупреждений до Build. **В БД не сохраняется** (см. § 6.2): на стадии Build пересчитывается заново и попадает в `ValidationReport.warnings` через преобразование, описанное в § 5.7.
- `parties` — `list[Party]` от `RussianPartyExtractor`.
- `contract_name` — sanitized строка или `null`.

**Persistence в SQLite — минимальный**:

- `sessions.status = 'parsed'`, `sessions.input_path` (абсолютный путь к `~/.disprot/sessions/<session_id>/input.docx`), `sessions.contract_name`, `sessions.preflight_metrics_json` — заполняются.
- В таблицу `parties` пишутся записи извлечённых сторон.
- **Clauses в БД не хранятся.** Они материализуются in-memory из pipeline и используются для построения protocol rows на стадии Build. После завершения `POST /api/sessions` они остаются доступны только через rebuild на стадии Build (повторный парсинг `input.docx`). См. § 6.5 ниже.

**Пользователь на Экране 2 (USER GATE 1):**

1. Правит стороны (имя, роль), при необходимости добавляет/удаляет.
2. Выбирает **drafting party** — сторону, чьи правки содержатся в документе (входящий редлайн от контрагента или собственный исходящий редлайн — в обоих случаях drafting party = автор правок в этом DOCX). Counterparty определяется автоматически как вторая сторона.
3. Подтверждает через `PATCH /api/sessions/{id}/parties`.

**Допущение MVP:** в договоре ровно две стороны. Если пользователь оставил одну сторону или добавил третью, кнопка «Построить протокол» дисэйблится с сообщением «MVP поддерживает ровно две стороны».

### 6.5. Build + Validate — USER GATE 1 (стороны + drafting party) предшествует, USER GATE 2 (правка таблицы) следует

Триггер — `POST /api/sessions/{id}/build`. Внутри обработчика выполняется **полный re-run Parse + Segment**, потому что clauses не персистятся в БД (см. § 6.4):

1. Загрузка `input.docx` по `sessions.input_path` (абсолютный путь, заполненный на стадии Ingest).
2. `OOXMLReader.read(path) -> raw_doc` → `RevisionResolver.extract(raw_doc) -> revision_result` → `NumberingResolver.resolve(raw_doc) -> numbering_result` → `ParagraphEnricher.enrich_all(...) -> enrichment_result` → `ClauseSegmenter.segment(enrichment_result.blocks) -> clauses`.
3. Загрузка `parties` и `drafting_party_id` из БД (заполнены на стадии USER GATE 1 через `PATCH /api/sessions/{id}/parties`). Counterparty вычисляется как «вторая `Party` в `parties` для этой сессии, не равная `drafting_party_id`».
4. `ProtocolBuilder.build(clauses, drafting_party, counterparty) -> list[ProtocolRow]`.
5. `ValidationEngine.validate(clauses, rows, enrichment_result.diagnostics) -> ValidationReport`.

**Стоимость:** полный pipeline для документа ≤ 25 MB на typical Russian contract выполняется за единицы секунд. Для personal tool накладные расходы пренебрежимы; альтернатива (хранить frozen `Clause.blocks` с табличной структурой в SQLite через сериализацию dataclass'ов) создаёт дополнительные сложности с миграциями и верификацией, не оправданные в v1.

**Идемпотентность по входу:** `block_id` детерминированы (монотонные индексы по XML-позиции); `clause_id` детерминированы от `block_id` первого параграфа Clause. Поэтому повторный rebuild на том же `input.docx` даёт ту же структуру `Clause` с теми же `clause_id`. Это позволяет ссылке `protocol_rows.source_clause_id` оставаться валидной как трассировочный идентификатор (см. § 7.2).

**Критерий включения Clause в строки** (см. § 5.6): Clause включается, если у одного из его параграфов есть textual revisions ИЛИ если Clause имеет флаг `TABLE_CELL_REVISIONS` (force-include из-за правок внутри ячеек таблицы; в v1 не извлечены структурно). Format-only revisions при отсутствии обоих условий учитываются в `ValidationReport`, но строк не создают.

**Validation для table-cell revisions:** для каждого Clause с флагом `TABLE_CELL_REVISIONS` `ValidationEngine` выпускает row-level warning `TABLE_CELL_CHANGE` с сообщением «правки внутри ячеек таблицы не извлечены автоматически — отредактируйте строку вручную». На самой строке поднимается `RowFlag.TABLE_CELL_CHANGE`. Содержимое колонок — текущий рендер таблицы (одинаковый в `original` и `accepted`); пользователь правит руками.

**Empty-protocol edge case:** если итоговый `rows` пуст (`textual_revisions_total == 0` И ни один Clause не имеет `TABLE_CELL_REVISIONS`) — `ValidationEngine` добавляет в `ValidationReport.warnings` session-level warning `EMPTY_PROTOCOL`. UI показывает баннер «В документе не найдено правок».

**Persist:** `protocol_rows` (полный список перезаписывается `INSERT/REPLACE`-стилем) и `sessions.validation_report_json` (см. § 7.2). `sessions.status = 'built'`.

Пользователь правит таблицу в UI (USER GATE 2): inline-edit, merge / split, swap-parties (header-only relabel), добавление / удаление строк. Каждое изменение auto-save через `PATCH`-endpoints.

**Rebuild и user-edits:** в v1 UX **нет кнопки rebuild** (см. § 9.3 — также убрана кнопка «Сбросить»). Build выполняется автоматически ровно один раз — на запросе `POST /api/sessions/{id}/build` сразу после USER GATE 1. Если пользователь после первого build всё-таки делает повторный `PATCH /api/sessions/{id}/parties` (это не предусмотрено в v1 UX, но возможно через API напрямую) и затем триггерит `POST /api/sessions/{id}/build` ещё раз — повторный build **стирает старые `protocol_rows` целиком** (включая user-edits) и пересоздаёт их с новой ролью drafting party / counterparty. UI v1 не предлагает такой workflow, поэтому потеря user-edits через этот путь возможна только при ручной работе с API.

### 6.6. Export

Триггер — `POST /api/sessions/{id}/export` с request body `{filename: str}` (имя без расширения; backend санитизирует и добавляет `.docx` — см. § 8.1). Внутри обработчика:

1. Санитизация `filename` по правилам § 8.1 (trim, удаление path separators / control characters, truncate до 200 chars, fallback `"Протокол_разногласий"` при пустом результате).
2. Загрузка из БД: `protocol_rows` (полный список), `parties`, `drafting_party_id`, `contract_name` (см. § 7.2).
3. Резолвинг `drafting_party` как `Party` по `sessions.drafting_party_id` и `counterparty` как «вторая `Party` в session, не равная `drafting_party_id`».
4. Создание in-memory буфера `output = io.BytesIO()`.
5. Вызов `ProtocolExporter.export(rows, drafting_party, counterparty, contract_name, output)` — генерирует DOCX через `python-docx` и пишет байты в `output`. На диск backend ничего не пишет.
6. Возврат HTTP 200: `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition` с двумя параметрами (`filename="..."` ASCII-fallback и `filename*=UTF-8''...` percent-encoded — см. § 8.1), body — байты `output.getvalue()`. Никаких отдельных GET-endpoints, никаких временных download URL backend-side.
7. Перевод `sessions.status = 'exported'` и обновление `updated_at`.

См. сигнатуру `ProtocolExporter.export` в § 5.8 и описание endpoint-контракта в § 8.1.

### 6.7. Принципы

- Авторы правок (`<w:author>`) парсятся в `Revision.author`, но `ProtocolBuilder` их игнорирует. **Все правки в документе считаются правками drafting party**, независимо от автора.
- **Разделение error vs warning:**
  - `ParsingError` — фатальная ошибка этапа, прерывает pipeline и возвращает HTTP 4xx/5xx. Содержит понятное сообщение и ссылку на проблемный `block_id` или `paragraph_index`. Примеры: повреждённый ZIP, невалидный `document.xml`, отсутствие `word/document.xml`.
  - `ValidationWarning` — деградация, не прерывает pipeline; складывается в `ValidationReport`. Примеры: низкая уверенность сегментации (`LOW_CONFIDENCE_BOUNDARY`), неопознанная нумерация (`LOW_NUMBERING_CONFIDENCE`), неподдержанная конструкция (`MOVE_DETECTED`).
- В UI warnings показываются как баннер сверху Экрана 3 со списком и навигацией к проблемным строкам. UI не блокирует пользователя — он может править вручную.

---

## 7. Хранение и сессии

### 7.1. Расположение данных

| Что | Куда |
|---|---|
| SQLite | `~/.disprot/disprot.db` (через `platformdirs`) |
| Загруженный файл, рабочие артефакты | `~/.disprot/sessions/<session_id>/` |

Файлы DOCX в SQLite не хранятся — только в файловой системе.

### 7.2. Схема БД

Минимальный набор таблиц. **Нет таблиц `clauses` и `revisions`** — clauses материализуются in-memory из pipeline на стадии Build (см. § 6.5), revision-семантика выражается через `validation_report_json` (warnings, metrics) и через `protocol_rows.flags_json`. Это упрощает schema и снимает необходимость сериализации frozen-моделей в БД.

```
sessions(
    id PRIMARY KEY,
    status,                       -- enum: uploaded | parsed | parties_confirmed | built | exported
    created_at,
    updated_at,                   -- timestamp последней мутации; обновляется на каждом PATCH/POST
    input_path TEXT NOT NULL,     -- абсолютный путь к ~/.disprot/sessions/<session_id>/input.docx; заполняется на стадии Ingest; используется на стадии Build для re-run Parse pipeline (§ 6.5)
    drafting_party_id TEXT NULL REFERENCES parties.id,  -- FK на parties.id; NULL до USER GATE 1; ЕДИНСТВЕННЫЙ источник истины об ориентации drafting/counterparty
    contract_name TEXT,           -- извлечён в стадии Parse через filename-based sanitization (§ 6.4); immutable после стадии Parse; NULL если итог пустой
    preflight_metrics_json TEXT NOT NULL,   -- вычислен на стадии Parse, immutable после; зеркалит структуру preflight_metrics из API response
    validation_report_json TEXT   -- NULLABLE; вычислен на стадии Build, перезаписывается при rebuild; зеркалит ValidationReport (см. § 5.7)
)

-- Counterparty НЕ хранится отдельной колонкой. Это вычисляется во время чтения как «вторая Party
-- в таблице `parties` для этой session, не равная `drafting_party_id`». Допущение MVP — ровно две
-- стороны (см. § 6.4); если parties меньше двух или больше двух, UI ограничивает workflow и
-- swap-parties / build / export недоступны (см. § 6.4 / § 8.1).

parties(
    id PRIMARY KEY,
    session_id FK,
    name TEXT,
    role TEXT,
    confidence REAL
)

protocol_rows(
    id PRIMARY KEY,
    session_id FK,
    sort_order INT,
    point_label TEXT,
    party_1_text TEXT,
    party_2_text TEXT,
    agreed_text TEXT,
    source_clause_id TEXT,         -- NULLABLE; стабильный clause_id из ClauseSegmenter (детерминирован от block_id первого параграфа Clause), используется как трассировочный идентификатор для будущего jump-to-source (§ 14). NULL для ручных строк (RowFlag.MANUALLY_ADDED)
    confidence REAL,
    flags_json TEXT,
    user_edited BOOLEAN DEFAULT 0
)
```

`sessions.status` — enum: `uploaded`, `parsed`, `parties_confirmed`, `built`, `exported`.

**Семантика `protocol_rows.source_clause_id`:** это просто строковый идентификатор (`clause_id` из `ClauseSegmenter`) для трассировки, не FK. Поскольку `clause_id` детерминирован от XML-позиции первого параграфа Clause (через `block_id`), повторный rebuild на том же `input.docx` даёт те же значения, и трассировка остаётся валидной. Если документ переупорядочивается (что в v1 не предусмотрено — `input.docx` immutable после Ingest), идентификаторы могут разойтись; v1 это не покрывает.

**Семантика временны́х колонок и JSON-полей `sessions`:**

| Колонка | Когда заполняется | Когда мутируется |
|---|---|---|
| `created_at` | при `POST /api/sessions` (Ingest) | никогда |
| `updated_at` | при `POST /api/sessions` | каждым PATCH/POST, меняющим строку `sessions` или связанные таблицы (`parties`, `protocol_rows`, swap, build) |
| `input_path` | при Ingest (внутри `POST /api/sessions`) | никогда (immutable) |
| `contract_name` | в стадии Parse (внутри `POST /api/sessions`) | никогда (immutable) |
| `preflight_metrics_json` | в стадии Parse | никогда (immutable) |
| `validation_report_json` | в стадии Build (`POST /api/sessions/{id}/build`) | перезаписывается при каждом последующем `POST /api/sessions/{id}/build`. В v1 UX кнопка rebuild отсутствует (см. § 9.3 / § 14), поэтому фактически записывается один раз сразу после USER GATE 1; колонка остаётся `NULL` до первого build |
| `drafting_party_id` | при `PATCH /api/sessions/{id}/parties` (USER GATE 1) | каждым `POST /api/sessions/{id}/swap-parties` (становится id прежней counterparty); прочих путей мутации нет |

### 7.3. TTL и cleanup

При старте `disprot serve` выполняется cleanup всех session-папок и SQLite-записей старше **7 дней**.

Это **не** «история проектов» — это буфер на случай, если пользователь закрыл вкладку до экспорта. Сессии разовые.

### 7.4. Целостность

Cleanup сессии происходит **только** в трёх случаях:

- **TTL-based** на старте `disprot serve` — удаляются session-папки и SQLite-записи старше 7 дней (см. § 7.3). Это purge-only, никаких триггеров со стороны UI.
- **Явное удаление пользователем** — `DELETE /api/sessions/{id}` (например через кнопку «Закрыть и удалить» в UI, если она есть; в v1 такой кнопки нет — см. § 9.3, но endpoint существует) удаляет файлы и SQLite-записи немедленно и транзакционно.
- **Orphan-cleanup на startup** — записи в SQLite без соответствующих файлов на FS и файлы без записей в SQLite удаляются для снятия рассинхронизации.

При экспорте (`POST /api/sessions/{id}/export`) session **не удаляется**: backend стримит DOCX в response (см. § 6.6) и помечает `sessions.status = 'exported'`. Сессия остаётся доступной до TTL — пользователь может вернуться, повторить экспорт с другим именем файла, или довести правки. Это снимает race condition между browser download и backend cleanup.

Запись данных одной сессии всегда выполняется в рамках одной SQLite-транзакции, что снимает риск рассинхронизации БД и FS.

---

## 8. Web API

### 8.1. Endpoints

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/sessions` | Upload `.docx`. Atomic stages 1–4 (Ingest → Parse → Segment → Extract). Returns `{session_id, preflight_metrics, preflight_diagnostics, parties, contract_name}`. `preflight_diagnostics` — `list[{code, severity, message, metadata}]` от `RevisionResolver` / `NumberingResolver`; используется фронтендом на Экране 2 (см. § 6.4 / § 9.2). В БД не сохраняется — на стадии Build пересчитывается заново и попадает в `ValidationReport` |
| `GET` | `/api/sessions/{id}` | **Read-only.** Status + parties + drafting_party_id + contract_name + preflight_metrics + validation_report (nullable) + timestamps. Counterparty явно не возвращается (вычисляется фронтендом как «вторая Party, не равная drafting_party_id» — см. § 7.2). Без побочных эффектов |
| `GET` | `/api/sessions/{id}/input.docx` | Возвращает raw bytes исходного `.docx` с MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Используется фронтендом для рендеринга превью через `mammoth.js` (см. § 8.2 / § 9.2). Доступен пока сессия не удалена (запись в `sessions` существует и файл `input.docx` на FS не подчищен TTL'ом — см. § 7.3). Если файла больше нет — 404 |
| `PATCH` | `/api/sessions/{id}/parties` | Править стороны и установить `drafting_party_id` |
| `POST` | `/api/sessions/{id}/build` | Atomic stages 5–6 (Build + Validate). Returns `{rows, validation_report}` |
| `GET` | `/api/sessions/{id}/rows` | Таблица + `ValidationReport` |
| `PATCH` | `/api/sessions/{id}/rows/{row_id}` | Править строку |
| `POST` | `/api/sessions/{id}/rows` | Добавить ручную строку |
| `DELETE` | `/api/sessions/{id}/rows/{row_id}` | Удалить строку |
| `POST` | `/api/sessions/{id}/rows/merge` | Body: `{row_ids: [...]}`. Объединить строки |
| `POST` | `/api/sessions/{id}/rows/{row_id}/split` | Разбить строку |
| `POST` | `/api/sessions/{id}/swap-parties` | Header-only relabel: устанавливает `sessions.drafting_party_id = id прежней counterparty`. НЕ трогает `party_1_text` / `party_2_text` — они остаются `original_text` / `accepted_text`. Пересчитывает `agreed_text` для строк с `user_edited == False`. Повторный вызов возвращает в исходное состояние. Полный контракт см. ниже |
| `POST` | `/api/sessions/{id}/export` | Генерация `.docx`. Request body: `{filename: str}` (имя без расширения; backend санитизирует и добавляет `.docx`). Response: HTTP 200, `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition: attachment; filename="<ascii-fallback>.docx"; filename*=UTF-8''<percent-encoded>.docx`, body — DOCX bytes. Полный контракт санитизации и формата header'а см. ниже. Никаких отдельных GET endpoints, никакого `download_url` |
| `DELETE` | `/api/sessions/{id}` | Закрыть/удалить |

#### 8.1.1. `POST /api/sessions/{id}/swap-parties` — детальный контракт

Endpoint выполняет всю логику в **одной SQLite-транзакции**:

1. `SELECT drafting_party_id FROM sessions WHERE id = :session_id` — текущий `drafting_party_id`. Если NULL (USER GATE 1 ещё не пройден) — HTTP 409 с сообщением «Стороны не подтверждены».
2. `SELECT id, role FROM parties WHERE session_id = :session_id` — все стороны сессии. Если число записей ≠ 2 — HTTP 409 с сообщением «MVP поддерживает ровно две стороны» (см. § 6.4).
3. Найти counterparty: `Party`, чей `id != current_drafting_party_id`. Это новый drafting; прежний drafting становится новой counterparty.
4. `UPDATE sessions SET drafting_party_id = :new_drafting_id, updated_at = :now WHERE id = :session_id`.
5. Для всех `protocol_rows` этой сессии **с `user_edited = 0`** — пересчитать `agreed_text` по новой роли drafting party: `"Редакция " + new_drafting.role` (если `role` пустая — `"Редакция Стороны 2"`). `UPDATE protocol_rows SET agreed_text = :new_agreed WHERE session_id = :session_id AND user_edited = 0`.
6. Строки с `user_edited = 1` НЕ трогаются (пользовательская правка приоритетнее автоматической; см. также § 5.8).
7. Колонки `party_1_text` / `party_2_text` НЕ трогаются никогда (это физический `original_text` / `accepted_text` из DOCX, см. § 5.6).
8. Commit.

Response: HTTP 200, body — JSON-объект `{drafting_party_id: str, rows: list[ProtocolRow]}`. Поле `drafting_party_id` содержит новое (после swap) значение — это единственный авторитетный источник для frontend, **отдельный `GET /api/sessions/{id}` после swap делать не нужно и не следует**. Поле `rows` совпадает по shape с body `GET /api/sessions/{id}/rows` (обновлённый `agreed_text` для строк с `user_edited = False`; неизменённый — для строк с `user_edited = True`).

Идемпотентность: повторный вызов возвращает `drafting_party_id` к исходному значению (за вычетом строк с `user_edited = True`, чей `agreed_text` остался от предыдущего автоматического значения). Это сознательно: пересчёт никогда не перезатирает пользовательскую правку.

#### 8.1.2. `POST /api/sessions/{id}/export` — санитизация filename и формат `Content-Disposition`

Backend выполняет санитизацию `filename` из request body **строго в указанном порядке** (frontend дополнительно валидирует на client side, см. § 9.2 Экран 4 — но backend re-validate всегда):

1. Trim ведущего и хвостового whitespace.
2. Удаление path separators: `/`, `\`.
3. Удаление null-байтов (`\x00`) и control characters: `\x00`–`\x1F`, `\x7F`.
4. Замена всех остальных Unicode-категорий `C*` (control, format, unassigned, private use, surrogates) на `_`.
5. Truncate до 200 characters (по числу Unicode-codepoints, не байтов).
6. Если результат — пустая строка → fallback `"Протокол_разногласий"`.
7. Backend добавляет суффикс `.docx`.

`Content-Disposition` header собирается с **двумя параметрами**:

- `filename="<ascii-fallback>.docx"` — RFC 6266 fallback для legacy-клиентов. Получается транслитерацией кириллицы по простому mapping (`а→a`, `б→b`, `в→v`, ..., `я→ya`, `ё→yo`, для верхнего регистра аналогично; не-кириллические не-ASCII символы → `_`). Внутри значения параметра двойные кавычки, обратные слэши и control-байты дополнительно экранируются как `\"` / `\\` (в v1 после санитизации шага 3 такие байты в имени уже невозможны, но fallback-эскейпинг применяется на всякий случай). Если транслитерация дала пустую строку — `"protocol.docx"`.
- `filename*=UTF-8''<percent-encoded>.docx` — RFC 5987. Percent-encoding всех байтов UTF-8 кроме `[A-Za-z0-9!#$&+\-.^_`|~]`.

Полный пример при `filename = "Протокол разногласий"`:

```
Content-Disposition: attachment; filename="Protokol_raznoglasy.docx"; filename*=UTF-8''%D0%9F%D1%80%D0%BE%D1%82%D0%BE%D0%BA%D0%BE%D0%BB%20%D1%80%D0%B0%D0%B7%D0%BD%D0%BE%D0%B3%D0%BB%D0%B0%D1%81%D0%B8%D0%B9.docx
```

Современные браузеры (Chrome, Firefox, Safari, Edge) предпочитают `filename*` и показывают пользователю кириллическое имя; legacy-клиенты падают на ASCII-fallback.

### 8.2. Превью

Превью DOCX → HTML — **полностью клиентское** через `mammoth.js` (см. § 9). Backend renderer-endpoint в v1 нет.

**Поток данных в браузер:** на mount Экрана 3 фронтенд делает `GET /api/sessions/{id}/input.docx`, получает Blob с raw bytes исходного `.docx`, передаёт его в `mammoth.convertToHtml({ arrayBuffer })` и рендерит результат в правую панель split-pane. Сервер не делает DOCX → HTML преобразования; raw файл хранится на FS и отдаётся как байты (см. § 7.1).

**Read-only превью:** v1 не делает jump-to-source / scroll-to-clause из таблицы в превью. Для этого нужен server-side маппинг `clause_id` → anchor в HTML (через custom mammoth fork или собственный конвертер с inject'ом `data-block-id="..."`). Это вынесено во Future scope (§ 14).

Если по результатам dogfooding `mammoth.js` окажется неудовлетворительным — добавим backend renderer во v2.

### 8.3. DTO и стек

- DTOs через `pydantic`. OpenAPI-схема генерируется автоматически.
- Backend stack: **FastAPI + SQLAlchemy 2.0 sync + SQLite**.
- Никакого async / queue. DOCX мелкие, всё выполняется в request-handler.

---

## 9. Frontend

### 9.1. Стек

- **Vite + React 18 + TypeScript**
- **TanStack Table v8** (виртуализация, inline-edit)
- **TanStack Query v5** (data fetching, optimistic updates)
- **Zustand** (минимум, только локальное UI-state)
- **Tailwind CSS** + точечно компоненты из **shadcn/ui**
- **mammoth.js** (DOCX → HTML preview в браузере)

### 9.2. Flow

Линейный flow из четырёх экранов, без меню и навбара.

#### Экран 1 — Upload

- Drag-and-drop или file picker.
- Принимает `.docx`, ≤ 25 MB.
- На успех → переход к Экрану 2 со spinner на парсинг.

#### Экран 2 — Preflight + подтверждение сторон

- **Сверху** read-only сводка: `"Найдено X пунктов, Y правок, нумерация: Z%"` (числа из `preflight_metrics` в response `POST /api/sessions`).
- **Под сводкой** список предупреждений: фронтенд рендерит `preflight_diagnostics` из того же response (см. § 6.4 / § 8.1) — каждый элемент `{code, severity, message, metadata}` отображается строкой с иконкой по `severity` (`info` / `warning`) и текстом `message`. Если `preflight_diagnostics` пуст — секция скрыта. Эти предупреждения позже (на стадии Build) пересчитываются и попадают в `ValidationReport.warnings`, которые показываются на Экране 3 (см. § 9.2 Экран 3); пользователю это прозрачно — он видит обновлённый список после построения таблицы.
- **Снизу** форма «Стороны договора»: таблица сторон с inline-edit (роль + наименование), кнопки добавить/удалить.
- Radio-button **«От имени какой стороны составляется протокол»** = drafting party. **Обязательный** выбор; никаких suggested-вариантов / pre-selected опций / визуальных хайлайтов — система не подсказывает, какая из сторон editor (см. § 6.4: auto-suggest концептуально невозможен без author→party mapping).
- Кнопка «Построить протокол» дисэйблится, пока drafting party не выбрана.

#### Экран 3 — Редактируемая таблица протокола (главный)

Split-pane 65 / 35:

- **Слева** — TanStack Table (4 колонки + counter `#` + actions).
- **Справа** — read-only превью оригинального DOCX через `mammoth.js`. На mount экрана фронтенд делает `GET /api/sessions/{id}/input.docx`, получает Blob, передаёт в `mammoth.convertToHtml({ arrayBuffer })` и рендерит результат. См. § 8.2.

**Поведение:**

| Действие | Жест |
|---|---|
| Inline-edit ячейки | Двойной клик или Enter; сохранение по blur / Ctrl+Enter; Esc отменяет |
| Многоабзацный текст | Textarea с авторесайзом |
| Confidence-badge | Слева от номера: зелёный (≥ 0.85) / жёлтый (0.6 ≤ c < 0.85) / красный (< 0.6). Hover → причина (`MULTI_PARAGRAPH`, `LOW_NUMBERING_CONFIDENCE`, `TABLE_CHANGE`, ...) |
| Merge | Выделить 2+ соседних строк → «Объединить» → склейка через `\n`, `point_label` берётся от верхней |
| Split | Дублировать строку, обе редактируются |
| Swap parties (⇄) | Глобальный header-only relabel: кнопка триггерит `POST /api/sessions/{id}/swap-parties` (см. § 8.1.1). Backend меняет `drafting_party_id` на id прежней counterparty и пересчитывает `agreed_text` для строк с `user_edited == False`; в response — обновлённый список rows. Фронтенд обновляет UI store: новые headers («Редакция [роль counterparty]» / «Редакция [роль drafting]») и новые `agreed_text` рендерятся из server response. Содержимое колонок 2 и 3 (`original_text` / `accepted_text`) НЕ меняется — это физический факт. Никакого локального swap-state в frontend нет; единственный источник истины — `sessions.drafting_party_id`. Полезно, если NER неправильно угадал, кто из сторон editor — пользователь нажимает кнопку и получает корректное labeling без re-upload |
| Validation banner | Сверху страницы; ссылка раскрывает список предупреждений; клик скроллит к строке таблицы (НЕ к месту в превью) |
| Auto-save | Каждое редактирование → `PATCH` в API → SQLite; restore из SQLite при reopen вкладки |

Превью справа — **read-only**. Никаких navigation hooks из таблицы в превью; никаких inject'ов anchor'ов. Если пользователю нужно ориентироваться в исходном документе по номеру пункта — он скроллит превью вручную.

**Кнопки на странице:**

- «Добавить строку вручную»
- «Поменять стороны»
- «Экспорт DOCX»

#### Экран 4 — Export

Модал:

- Поле «Имя файла» (без расширения; backend санитизирует и добавляет `.docx`).
- Кнопки «Отмена» / «Сохранить».

**Client-side валидация** (применяется в onChange / onBlur поля «Имя файла», тем же набором правил, что у backend для дружелюбного UX, но **backend всё равно re-validate**, см. § 8.1.2):

1. Trim ведущего и хвостового whitespace.
2. Удаление path separators (`/`, `\`).
3. Удаление control characters (`\x00`–`\x1F`, `\x7F`).
4. Truncate до 200 characters.

Если результат пустой — submit-кнопка дисэйблится с подсказкой «Введите имя файла» (опционально UI может предложить дефолт «Протокол разногласий», который backend в любом случае подставит как fallback при пустой строке). Передача в backend — plain string (как ввёл пользователь, после client-side трима / удаления path-separators / control characters); backend применяет полную санитизацию из § 8.1.2.

Submit → фронтенд делает `fetch('POST /api/sessions/{id}/export', { body: JSON.stringify({filename}) })` → `await response.blob()` → `URL.createObjectURL(blob)` → создаётся скрытая `<a href={objectUrl} download={filename + '.docx'}>` и эмулируется клик → браузер скачивает файл через стандартный «Сохранить как…» / Downloads (`Content-Disposition` в response подсказывает имя; современные браузеры берут UTF-8 из `filename*`, см. § 8.1.2). Никаких временных download URL backend-side, никакого отдельного GET-endpoint — DOCX отдаётся напрямую в body POST-response (см. § 6.6 / § 8.1).

Откуда именно будет сохранён файл, backend не знает (browser download flow), поэтому никакой опции «открыть папку после сохранения» в v1 нет — см. § 14 Future scope.

### 9.3. Что НЕ в v1 UI

- Тёмная тема.
- Локализация (только русский).
- Undo / redo — отсутствует. Future scope (§ 14).
- Drag-and-drop reorder строк.
- Кнопка «Сбросить» / rebuild button — отсутствует. Если пользователь хочет начать заново — закрывает вкладку и делает re-upload. Future scope (§ 14).
- Jump-to-source / scroll-to-clause из таблицы в превью — отсутствует. Превью read-only. Future scope (§ 14).
- Чекбокс «Открыть папку после сохранения» в Export-модале. Future scope (§ 14): возможно через electron / tauri обёртку, в браузерном flow технически невозможно.

---

## 10. Распространение

### 10.1. CLI

Два режима — interactive (`serve`) и non-interactive batch (`convert`).

```
disprot serve            # localhost:8765 + open browser, full UI flow с USER GATE-ами
disprot --version
```

**`disprot convert` — non-interactive batch:**

```
disprot convert input.docx \
    --party-1 "ООО \"Ромашка\":Арендодатель" \
    --party-2 "АО \"Василёк\":Арендатор" \
    --drafting-party "Арендатор" \
    -o protocol.docx
```

Контракт:

- `--party-N "Имя:Роль"` — обе стороны задаются явно. Если оба `--party-1` и `--party-2` опущены — CLI запускает auto-extract (`RussianPartyExtractor`); если NER не уверен (любая `Party.confidence < 0.85`) — `convert` **fails fast** с exit code 2 и сообщением в stderr: `«Не удалось автоматически определить стороны. Используйте --party-1/--party-2 явно или запустите 'disprot serve' для интерактивного подтверждения.»`
- Если передан **ровно один** из `--party-1` / `--party-2` (а второй опущен) — `convert` **fails fast** с exit code 2 и сообщением в stderr: `«Параметры --party-1 и --party-2 должны быть указаны вместе или оба опущены (тогда стороны извлекаются автоматически).»`
- `--drafting-party "Роль"` — обязательный, указывает роль drafting party (одна из ролей, упомянутых в `--party-N` или авто-извлечённых). Если опущен — fail fast с exit code 2 и сообщением: `«Укажите --drafting-party "Роль" — по какой стороне формируется протокол.»`
- `-o, --output PATH` — путь выходного `.docx`.
- Exit code 0 — успех; exit code != 0 — ошибка с сообщением в stderr.
- **Никакого interactive prompt** в `convert`. Для интерактива — `disprot serve`.
- Обходит USER GATE 1 (стороны + drafting party) за счёт явных флагов; USER GATE 2 (правка таблицы) пропускается полностью — экспортируется автоматический результат `ProtocolBuilder` без редактирования.

### 10.2. Установка

```
pipx install disagreement-protocol
```

Требования: **Python ≥ 3.11**.

### 10.3. Release pipeline (GitHub Actions)

1. Tag `v0.x.y` → запускает workflow.
2. Билд React → `disprot-web/frontend/dist/`.
3. `uv build` для всех трёх пакетов → wheels.
4. `pytest` matrix: macOS / Linux / Windows × Python 3.11 / 3.12.
5. Upload to PyPI (trusted publishing).
6. GitHub Release с changelog.

### 10.4. Versioning

SemVer.

- `v0.x` — pre-stable.
- `v1.0.0` — после 50+ реальных договоров без критичных регрессий.

### 10.5. Лицензия

MIT. Репозиторий публичный.

---

## 11. Тестирование

### 11.1. Уровни

#### Unit

`disprot-core/tests/unit/`. Синтетические минимальные DOCX-фикстуры через `python-docx` builder.

| Компонент | Покрытие |
|---|---|
| `OOXMLReader` | Run Coalescing, table, empty paragraph, монотонность `block_id`; interleaved fixture (paragraph → table → paragraph) сохраняет порядок в `RawDocument.blocks`; `RawDocument.source_path` корректно возвращает абсолютный путь; **`RawTable.has_revisions = True`** для таблицы с `<w:ins>` / `<w:del>` внутри ячеек; `has_revisions = False` для таблицы без правок; `Run` НЕ содержит revision-полей (тексты внутри `<w:ins>` / `<w:del>` сохраняются как обычные `Run.text`); **параграфы внутри `<w:tc>` НЕ становятся top-level `RawParagraph`** (они доступны только через `RawTable.rows[i].cells[j].paragraphs`) |
| `RevisionResolver` | insert, delete, replace, format-only; **return type — `RevisionResolveResult` с непустым `revision_map` и пустым `diagnostics` для well-formed документа**; пустой `revision_map` для документа без правок; маппинг по `i_para`-индексу среди top-level параграфов при interleaving с таблицами; **fallback при расхождении количества top-level paragraph-объектов**: unmapped `RawParagraph` получает `RevisionData(original_text=raw.text(), accepted_text=raw.text(), revisions=())` (НЕ пустые строки), `diagnostics` содержит `ResolverDiagnostic(code="REVISION_MAPPING_MISMATCH", severity="warning", metadata={...})` с корректным count'ом unmapped/expected/actual |
| `NumberingResolver` | multi-level, restart, regex fallback, unmapped paragraph (расхождение docx2python ↔ OOXMLReader), confidence values; **return type — `NumberingResolveResult`**; `diagnostics` содержит `ResolverDiagnostic(code="NUMBERING_MAPPING_MISMATCH", ...)` при расхождении количества top-level paragraph-объектов |
| `ParagraphEnricher` | full enrichment, missing revision_map entry, missing numbering_map entry; interleaved input (paragraphs + tables) → output сохраняет порядок и тип `EnrichedParagraph` / `EnrichedTable`; `EnrichedTable.has_revisions` наследуется без изменений; **`EnrichmentResult.diagnostics` — корректная конкатенация `revision_result.diagnostics + numbering_result.diagnostics`** |
| `ClauseSegmenter` | numbered → new clause; multi-paragraph (continuation присоединяется к top of stack); nested numbering (2 → 2.1 → 2.1.3 — стек открывается, `parent_id` правильный); закрытие при возврате на меньший уровень (после 2.1.3 встретился 3 — стек pop'ается до уровня 0); **table внутри clause (interleaved)** — `EnrichedTable` попадает в `Clause.blocks` рядом с параграфами в правильной позиции, `CONTAINS_TABLE` поднимается; **TABLE_CELL_REVISIONS поднимается на Clause, если хотя бы один вложенный `EnrichedTable.has_revisions == True`** (для standalone, преамбульного и numbered Clause); **STANDALONE_TABLE** — таблица между numbered clauses без context оформляется в sibling Clause с `label="Таблица"` и флагами `{STANDALONE_TABLE, CONTAINS_TABLE}`; preamble; **requisites detection по тексту параграфа** (триггерные подстроки `"реквизиты сторон"`, `"реквизиты"`, `"подписи сторон"`, `"подписи и реквизиты"`, `"адреса и реквизиты"`; case-insensitive; стили `style_id` НЕ используются; window — последние 30 top-level параграфов); приложения (маркер `Приложение № N`); NEW_CLAUSE; DELETED_CLAUSE |
| `RussianPartyExtractor` | типовые преамбулы и edge cases |
| `ProtocolBuilder` | разные drafting parties, NEW_CLAUSE, DELETED_CLAUSE, multi-paragraph, **interleaved blocks (paragraph + table + paragraph) — `_serialize_clause_to_text` / `_serialize_table_to_text` корректно вставляют табличный фрагмент с `\n`-обвязкой между параграфами**; `STANDALONE_TABLE` Clause; **force-include для Clause с `TABLE_CELL_REVISIONS` без textual revisions** — row создаётся, `original == accepted`, флаг `TABLE_CELL_CHANGE` поднимается; **базовый инвариант** (вызов `build` с прежним drafting и с обменённым drafting/counterparty: `party_1_text` / `party_2_text` идентичны во обоих случаях; `agreed_text` пересчитан под новую роль drafting party). API-уровневый swap покрывается отдельным API-тестом (см. integration ниже) |
| `ValidationEngine` | все типы warning со всеми тремя `scope`-значениями, включая `TABLE_CELL_CHANGE` (row-level), `REVISION_MAPPING_MISMATCH` / `NUMBERING_MAPPING_MISMATCH` (session-level — преобразуются из `resolver_diagnostics` с прокидыванием `severity`), `EMPTY_PROTOCOL` (session-level, `severity="info"` — поднимается, если `rows` пуст ровно при условии `textual_revisions_total == 0` И отсутствии Clauses с `TABLE_CELL_REVISIONS`); НЕ поднимается, если хотя бы один Clause force-включён по `TABLE_CELL_REVISIONS`; все остальные warning kinds выпускаются с `severity="warning"` |
| `ProtocolExporter` | round-trip generate → re-parse через `io.BytesIO`-стрим (на диск ничего не пишется); сигнатура `export(rows, drafting_party, counterparty, contract_name, output_stream)` без параметра `swap_state`; headers колонок строятся из переданных `drafting_party` / `counterparty` (включая fallback `"Редакция Стороны 1"` / `"Редакция Стороны 2"` при пустых `Party.role`); вызов с прежним и обменённым drafting / counterparty даёт корректные headers и контент в обеих ориентациях без condition'ов внутри exporter; user-edited row сохраняет `agreed_text` из БД без пересчёта; заголовок документа корректен при пустом `contract_name` |

#### Integration

`disprot-core/tests/integration/`. Golden corpus, изначально пустой.

По мере встречи реальных багов: анонимизированный фрагмент → `tests/fixtures/golden/<case>/input.docx` + snapshot ожидаемого протокола → `tests/fixtures/golden/<case>/expected.json` (сериализованный `list[ProtocolRow]` + `ValidationReport`). Прогоняется в CI.

#### API

`disprot-web/tests/`. `pytest + httpx + FastAPI TestClient`. Полный flow: upload → parties → build → edit → export. Дополнительно покрывается:

- **Persistence shape:** после `POST /api/sessions` в БД присутствуют только записи в `sessions` (с заполненным `input_path`) и `parties`; таблиц `clauses` / `revisions` в schema нет.
- **Rebuild idempotency:** повторный `POST /api/sessions/{id}/build` для той же сессии (без изменения parties) даёт идентичный `protocol_rows.source_clause_id` для каждой строки (детерминизм `clause_id`).
- **Rebuild стирает user-edits:** если user отредактировал row через `PATCH /api/sessions/{id}/rows/{row_id}` и затем триггернул `POST /api/sessions/{id}/build` второй раз — `user_edited` сбрасывается (потому что `protocol_rows` пересоздаются).
- **Filename sanitization:** для имён файлов `Договор аренды_v3 (правки).docx`, `simple.docx`, `(только в скобках).docx`, `__multi___underscore.docx` — корректный `contract_name` после применения алгоритма из § 6.4.
- **Empty protocol:** для DOCX без Track Changes (`textual_revisions_total == 0`) и без table-cell revisions — `POST /api/sessions/{id}/build` возвращает `rows = []` и `validation_report.warnings` содержит `EMPTY_PROTOCOL` warning.
- **Preflight diagnostics:** response `POST /api/sessions` содержит ключ `preflight_diagnostics`; для well-formed DOCX он `[]`, для DOCX с искусственным расхождением количества paragraph-объектов — содержит элемент с `code="REVISION_MAPPING_MISMATCH"` или `"NUMBERING_MAPPING_MISMATCH"`. После `POST /api/sessions/{id}/build` соответствующие session-level warning'и присутствуют в `validation_report.warnings`.
- **Export contract:** `POST /api/sessions/{id}/export` с body `{filename: "test"}` возвращает HTTP 200, `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition` с двумя параметрами: `filename="test.docx"` (ASCII fallback) и `filename*=UTF-8''test.docx` (RFC 5987 percent-encoded). Body parses как валидный DOCX через `python-docx`; на диске backend файлы протокола не появляются. После export `sessions.status = 'exported'`, session-папка остаётся на FS (cleanup только по TTL / DELETE — см. § 7.4).
- **Filename sanitization:** покрывается набор edge cases для `filename`: пустая строка → fallback `"Протокол_разногласий"`; кириллица `"Протокол разногласий"` → `filename="Protokol_raznoglasy.docx"` + `filename*=UTF-8''%D0%9F...`; имена с path separators (`/`, `\`) и control characters удаляются (т.е. `"a/b\\c"` → `"abc"`); 250-character input усекается до 200 символов; смешанные ASCII + кириллица + emoji → emoji **сохраняется** в `filename*=UTF-8''...` параметре (категория Unicode `S*` (`Symbol`) не входит в `C*` (`Control`/`Format`/etc.), поэтому шаги 3–4 санитизации emoji не вычищают), но **в ASCII-fallback `filename="..."` emoji заменяется на `_`**, потому что транслитерационная таблица не имеет соответствия для symbol-категории.
- **Swap-parties contract:** `POST /api/sessions/{id}/swap-parties` (см. § 8.1.1) меняет `sessions.drafting_party_id` на id прежней counterparty в одной транзакции; `agreed_text` пересчитан для всех `protocol_rows.user_edited == 0`; `agreed_text` для `user_edited == 1` строк остаётся без изменений; `party_1_text` / `party_2_text` остаются неизменными во всех строках; повторный вызов возвращает `drafting_party_id` к исходному значению. Endpoint возвращает HTTP 409 если `parties` ≠ 2 или `drafting_party_id` IS NULL.

#### E2E smoke

`disprot-web/tests/e2e/` (опционально, последняя неделя). Playwright, один сценарий happy path.

### 11.2. Инфраструктура

- `pytest` + `pytest-snapshot` + `pytest-cov`. `pytest-asyncio` не используется — FastAPI sync, async-тесты не нужны.
- DOCX-builder фикстуры (fluent API): `build_docx(...).with_revision(...).build()`.
- Скрипт `scripts/anonymize_docx.py` — заменяет имена/реквизиты на placeholder'ы для подготовки golden-фикстур из реальных договоров.

### 11.3. Соглашения

- **TDD** для всех компонентов в `disprot-core` (test-first): сперва пишется fixture + ожидаемый результат, затем код.
- Покрытие `core` ≥ 80% через `pytest-cov`. Билд падает, если покрытие ниже порога.
- `disprot-web` и `disprot-cli` — без жёсткой цели по покрытию (smoke-уровень достаточен).

---

## 12. Реестр рисков

| # | Риск | Вероятность | Митигация |
|---|---|---|---|
| 1 | `docx-revisions` не справляется с экзотическими DOCX | Высокая | Спайк в первые 3 дня на 10 договорах. На fail — fork и патчим (MIT). Fallback-план: свой extractor через lxml (~2 недели) |
| 2 | `docx2python` ломается на нестандартной нумерации | Средняя | Regex fallback с пониженным confidence; UI помечает строки и пользователь правит |
| 3 | `ClauseSegmenter` не справляется с кривыми документами | Высокая | Делается простым и прозрачным. Каждый найденный косяк → fixture в golden corpus + правило в segmenter |
| 4 | `Natasha` плохо распознаёт стороны | Средняя | Ручная правка в UI всегда возможна. v2 — LLM-модуль через `LLMAssistant.assist_party_extraction` |
| 5 | `mammoth.js` некорректно рендерит TC | Средняя | Превью — secondary feature; на fail `mammoth.convertToHtml` правая панель скрывается, под таблицей появляется hint «Превью недоступно — таблица содержит весь нужный текст». Никаких внешних callout'ов в Word/файловую систему. Backend renderer как fallback — во v2 |
| 6 | Cross-platform path/encoding issues | Средняя | `pathlib.Path`, `platformdirs`, явный UTF-8 при IO; CI matrix для трёх OS |
| 7 | У пользователя нет Python 3.11+ | Низкая | README с инструкциями; v2 — рассмотреть PyInstaller standalone |
| 8 | SQLite и файлы могут разойтись | Низкая | Транзакционно: TTL-based purge на startup; явное `DELETE /api/sessions/{id}` транзакционно; orphan-cleanup на startup (см. § 7.3 / § 7.4) |
| 9 | Объёмные договоры тормозят UI | Низкая (для MVP) | TanStack Table v8 виртуализирует строки; превью lazy |

---

## 13. Timeline

| Неделя | Задачи |
|---|---|
| 1 | **Spike**: ставим `docx-revisions` + `docx2python` + Natasha, гоняем на 10 разных DOCX. Проверяем гипотезы. На fail — пересмотр scope. **Параллельно**: monorepo skeleton, CI базовый, README. |
| 2 | `disprot-core`: model (`RawParagraph` / `RawTable` / `RawDocument` / `RevisionData` / `NumberingData` / `ResolverDiagnostic` / `RevisionResolveResult` / `NumberingResolveResult` / `EnrichmentResult` / `EnrichedParagraph` / `EnrichedTable` / `EnrichedBlock` / `Clause`) + `OOXMLReader` + `RevisionResolver.extract` + `NumberingResolver.resolve` + `ParagraphEnricher.enrich_all`. Unit-тесты с синтетическими фикстурами. `scripts/anonymize_docx.py`. |
| 3 | `disprot-core`: `ClauseSegmenter`, `ProtocolBuilder`, `ValidationEngine`, `RussianPartyExtractor`, `ProtocolExporter`. End-to-end тест от DOCX до DOCX. |
| 4 | `disprot-web`: FastAPI endpoints + DTOs + SQLite. `disprot-cli`: batch-режим. API smoke-тесты. |
| 5 | React UI: 4 экрана. TanStack Table с inline-edit, merge/split, swap. mammoth.js preview. Validation banner. |
| 6 | Polish: edge cases по golden corpus (10–15 договоров уже накоплены), кросс-платформенный smoke на Win/Linux, README, первый pre-release `v0.1.0`. |

### Точки решения

- **Конец недели 1** — стоп-чек по библиотечной стратегии. Если `docx-revisions` непригоден и форк выглядит больше 2 недель — пересматривается scope.
- **Конец недели 3** — рабочее ядро без UI (CLI работает на тестовых файлах).
- **Конец недели 5** — готовый web UI; начало dogfooding на реальных договорах.

---

## 14. Future scope (НЕ в v1)

С обоснованием почему отложено.

| Фича | Обоснование отложенности |
|---|---|
| **LLM-модуль** через `LLMAssistant` port (Anthropic / Ollama / OpenAI) | Архитектурный порт уже есть в v1 (`disprot-core/llm/`). Само подключение клиента — отдельная итерация после dogfooding |
| **English NER** через spaCy и bilingual contracts | Архитектурный порт `PartyExtractor.for_language` уже есть. Клиентская база v1 — только русский |
| **Two-version pipeline** (две `.docx` без TC → автогенерация redline) | Используется редко; легко добавить как отдельный pipeline через WmlComparer-портирование или Python-Redlines |
| **Word add-in** через Office.js | Реалистично только если REST-обвязка стабилизируется и появится спрос |
| **Поддержка `.doc`** (Word 97–2003) через soffice | Юристу проще конвертировать в Word руками за секунду; добавление `soffice` как runtime-зависимости противоречит ограничениям зависимостей из § 2.3 (никаких системных runtime'ов вне Python ecosystem) |
| **Multi-user / shared server / Docker Compose** | Текущий продукт — solo tool |
| **Полная история проектов** (БД с поиском по сессиям) | Текущий v1 — разовые сессии с TTL 7 дней |
| **Footnotes/endnotes, MoveFrom/MoveTo, non-native redlines** (цветной текст без TC) | Редкие edge cases; v1 показывает warning и пропускает |
| **Экспорт в XLSX / PDF** | v1 — только DOCX как первичный формат протокола в российской практике |
| **Антивирусная проверка загружаемых файлов** | Локальный однопользовательский tool, low risk |
| **Undo / redo в редактируемой таблице** | В v1 есть auto-save после каждого редактирования. Полноценный undo-стек добавим после dogfooding |
| **Reset / rebuild button** (откат к авто-результату build с сохранением user-confirmed parties) | v1 опускает, чтобы избежать неоднозначности семантики (что именно сбрасывать — правки таблицы? сегментацию? стороны?). Если пользователю нужно начать заново, он закрывает вкладку и делает re-upload — TTL 7 дней оставляет старую сессию доступной. Прорабатывается после dogfooding |
| **Чекбокс «Открыть папку после сохранения»** | Browser download flow не позволяет backend узнать целевую папку (файл уходит через стандартный «Сохранить как...» / Downloads). Возможно через electron / tauri обёртку — отдельная итерация |
| **Backend DOCX → HTML renderer** | На случай, если `mammoth.js` не справляется с TC. В v1 превью полностью клиентское |
| **Jump-to-source / scroll-to-clause из таблицы в превью** | Требует server-side маппинга `clause_id` → anchor в HTML (через custom mammoth fork или собственный конвертер с inject'ом `data-block-id="..."`). v1 — read-only превью без navigation hooks |
| **Полноценная поддержка table-cell revisions** | v1 детектирует правки внутри ячеек таблицы (`EnrichedTable.has_revisions`, флаг `TABLE_CELL_REVISIONS` на Clause), force-включает соответствующий Clause в протокол, но НЕ извлекает структуру правок внутри ячеек. Колонки 2 и 3 заполняются текущим рендером таблицы (одинаковым), row помечается `TABLE_CELL_CHANGE`, пользователь правит вручную. Полноценный path: enrich ячейки revision-данными, отдельные protocol rows на уровень cell — отдельная итерация |
| **Auto-suggest drafting party** на основе revision authors | Эвристика типа `revision.author == party.name` или `revision.author == party.role` (с препроцессингом normalize). v1 не делает по двум причинам: (а) author-метаданные часто содержат шум (`"User"`, `"Microsoft Office User"`, не совпадает с юр. наименованием), (б) дизайн уже зафиксировал решение `--no-author-mapping` (§ 5.5, § 6.7) — авторы правок исключены из бизнес-логики как класс. Возможный возврат после dogfooding, если пользователи начнут жаловаться на неудобство выбора drafting party вручную |
| **Извлечение `contract_name` из заголовка документа** | v1 берёт имя только из имени файла через filename-based sanitization (§ 6.4). Heading-based detection (стиль Heading1, жирный текст крупного шрифта в первом параграфе) даёт более удобные результаты, но шаблоны слишком разнятся: ложно-положительные срабатывания на типовых преамбулах («АРЕНДНЫЙ ДОГОВОР № 5/2024 от ...») приведут к шумным contract_name. Включится после накопления golden corpus с реальными примерами |
