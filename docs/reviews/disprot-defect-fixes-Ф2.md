# Review: disprot-defect-fixes — Ф2

- **Date**: 2026-07-26
- **Phase scope**: Исходная и принятая редакции таблиц сквозь весь round-trip
- **Base commit**: 4e5da5275214863f651f992efa5318bbfd95ebc1
- **Rounds**: 1 (Opus 4.1 + Codex xhigh 4.2 control)
- **Outcome**: ACCEPTED AT ESCALATION

## Findings history

| id | reviewer | finding (one line) | decision | final status |
|---|---|---|---|---|
| F1-B1-Ф2 | opus | `tables_json` docstring в `backend/app/models/clause.py:24-26` описывает дофазную форму ячейки (`"rows": [[cell_text, ...], ...]`), хотя фаза сделала персистируемую ячейку объектом; файл вне списка Ф2 (он в Ф3) | DEFER | deferred |
| F1-B2-Ф2 | opus | `block_index=table.get("block_index", 0)` в `backend/app/api/protocols.py:199` читает ключ, который ни один writer не пишет (`backend/app/services/processing.py:57-81`); безвредный no-op, выглядит как незавершённое намерение | DEFER | deferred |
| F1-B3-Ф2 | opus | `samples/README.md:11` — новая ячейка содержит неэкранированные `\|` внутри inline-кода, GFM не защищает пайпы код-спаном внутри таблицы, строка парсится как 7 колонок вместо 3, таблица рендерится сломанной | NIT-AUTHORIZED | fixed |
| F1-B4-Ф2 | opus | Test-strategy строка плана «несколько paragraphs в cell соединяются прежним пробелом» проверена только для неразрешённого fallback-пути, но не для разрешённого пути в `backend/app/services/ingestion.py:78-79`; поведение эмпирически корректно, не хватает покрытия | NIT | deferred |
| F1-B5-Ф2 | opus | `backend/tests/integration/test_pipeline_e2e.py:15` — `build_docx_with_table_cell_replacement` вставлен в блок импортов не по алфавиту (isort в ruff не включён, линт чист) | NIT | deferred |
| F1-B6-Ф2 | opus | `backend/app/processing/types.py:85-92` — `RawTable.cell_text` валидирует `version` и делегирует в `RawTableCell.text`, которая валидирует его повторно; обе проверки предписаны планом, дублирование только стилистическое | NIT | deferred |
| F1-B7-Ф2 | opus | `backend/tests/processing/test_validation_engine.py:206` — утверждение `covered_revisions == 2` пустое, так как `ValidationEngine` безусловно возвращает `covered_revisions=textual` | NIT | deferred |
| F1-B8-Ф2 | codex-control | BLOCKING, label plan-mandated: `STANDALONE_TABLE` в `backend/app/processing/changed_clause_detector.py:16-18` и `backend/app/api/protocols.py:206-212` безусловно включает строку протокола даже когда единственная revision в ячейке — FORMAT_ONLY и `table.has_revisions == False`; конфликт с шагом 4 плана Ф2 | ESCALATED_TO_HUMAN | resolved-by-user |
| F1-B9-Ф2 | codex-control | `backend/app/api/protocols.py:96-126,188-195` — reader не защищён от повреждённого `tables_json` (`null`, non-dict object-cell, non-list `rows`/`revisions` дают `AttributeError`/`TypeError`); hardening, не нарушение обратной совместимости | DEFER | deferred |
| F1-B10-Ф2 | codex-control | `backend/tests/api/test_protocols.py:202-224` — API-фикстура дублирует табличные `INS`/`DEL` одновременно в `ClauseModel.revisions` и в revisions object-ячейки, хотя production writer хранит их только в ячейке | NIT | deferred |
| F1-B11-Ф2 | codex-control | Пакет diff был усечён инструментом посреди хунка; контролёр дочитал оборванные production-функции и round-trip тесты отдельно | NIT | deferred |

## Deferred

- **F1-B1-Ф2** (NONE, информационное): `tables_json` docstring в `backend/app/models/clause.py:24-26` описывает дофазную форму ячейки (`"rows": [[cell_text, ...], ...]`), хотя фаза сделала персистируемую ячейку объектом. Файл не входит в список файлов Ф2 (он в списке Ф3) — исправить там, где файл и так меняется.
- **F1-B2-Ф2** (NONE, информационное): `block_index=table.get("block_index", 0)` в `backend/app/api/protocols.py:199` читает ключ, который ни один writer не пишет (`backend/app/services/processing.py:57-81`). `## Contracts` фиксирует персистируемую форму таблицы как `{block_id, has_revisions, rows}`, поэтому не сохранять ключ правильно, а чтение навсегда остаётся no-op. Безвредно, но выглядит как незавершённое намерение.
- **F1-B4-Ф2** (NICE_TO_HAVE): строка test-strategy плана «несколько paragraphs в cell соединяются прежним пробелом» проверена только для неразрешённого fallback-пути (`backend/tests/services/test_protocol_generator.py:356-378`), не для разрешённого пути в `backend/app/services/ingestion.py:78-79`. Поведение верно эмпирически, не хватает покрытия одной ветки.
- **F1-B9-Ф2** (NONE, hardening): `backend/app/api/protocols.py:96-126,188-195` — защитить reader от повреждённого `tables_json`: `null`, non-dict object-cell и non-list `rows`/`revisions` сейчас дают `AttributeError`/`TypeError`. Валидный до-Ф2 writer сохранял строки, поэтому это hardening, а не нарушение обратной совместимости.

## Nits (informational)

- **F1-B3-Ф2** (fixed, authorized by orchestrator): `samples/README.md:11` — новая ячейка содержала неэкранированные `|` внутри inline-кода; GFM не защищает пайпы код-спаном внутри таблицы, строка парсилась как 7 колонок против 3 у остальных, таблица рендерилась сломанной. Оркестратор авторизовал точечную правку (экранирование как `\|`) как единственный диспатченный quickfix фазы — выполнен Sonnet quickfix-субагентом до коммита фазы, кода не касался.
- **F1-B5-Ф2**: `backend/tests/integration/test_pipeline_e2e.py:15` — `build_docx_with_table_cell_replacement` вставлен в блок импортов не по алфавиту (isort в ruff не включён, линт чист).
- **F1-B6-Ф2**: `backend/app/processing/types.py:85-92` — `RawTable.cell_text` валидирует `version` и делегирует в `RawTableCell.text`, которая валидирует его повторно. Дублирующая проверка; обе предписаны планом, поэтому это только стиль.
- **F1-B7-Ф2**: `backend/tests/processing/test_validation_engine.py:206` — утверждение `covered_revisions == 2` пустое: `ValidationEngine` безусловно возвращает `covered_revisions=textual` (`backend/app/processing/validation_engine.py:167`). Фиксирует контракт шага 7, но не может провалиться независимо от строки выше.
- **F1-B10-Ф2**: `backend/tests/api/test_protocols.py:202-224` — API-фикстура дублирует табличные `INS`/`DEL` одновременно в `ClauseModel.revisions` и в revisions object-ячейки, хотя production writer хранит их только в ячейке.
- **F1-B11-Ф2**: пакет diff был усечён инструментом посреди хунка; контролёр дочитал оборванные production-функции и round-trip тесты отдельно.

## Open at accept

Единственный BLOCKING-пункт раунда (`F1-B8-Ф2`, codex-control, label `plan-mandated`, `authorization_relation: PLAN_ACCEPTANCE`) не был триажирован в ACCEPTED/REJECTED — по протоколу такие пункты эскалируются человеку. Ниже — вердикт контролёра, конфликтующий текст плана и решение пользователя дословно.

**Вердикт контролёра (4.2, Codex Sol xhigh):**

> BLOCKING:
> 1. authorization_relation: PLAN_ACCEPTANCE
>    subtle regression — backend/app/processing/changed_clause_detector.py:16-18; backend/app/api/protocols.py:206-212 — plan-mandated: `STANDALONE_TABLE` безусловно включает строку, даже когда единственная revision в ячейке — `FORMAT_ONLY` и `table.has_revisions == False`. Точечная проба подтвердила включение такой clause. Это нарушает инвариант Ф1 и шаг 4 Ф2 как в памяти, так и после SQLite round-trip.
>    why_now: Ф2 впервые переносит cell-level `FORMAT_ONLY` через весь pipeline; отсутствие строки протокола для такой правки — прямой Acceptance-контракт фазы.
>    minimal_fix: в обоих селекторах исключить standalone clause, если её единственные найденные revisions — cell-level `FORMAT_ONLY`, сохранив существующее поведение для standalone-таблиц без revisions и с текстовыми `INS`/`DEL`; закрепить одним in-memory и одним persisted/API тестом.

**Конфликт двух правил плана:**

Plan Ф2 Step 4: «`has_revisions` остаётся textual INS/DEL сигналом: format-only cell не создаёт protocol row».

Существующее (пре-Ф2) правило `STANDALONE_TABLE`: отдельно стоящая таблица всегда даёт строку ручной проверки независимо от правок — правило, которое `minimal_fix` самого контролёра предлагал сохранить для случая «standalone-таблица без revisions».

Буквальное исполнение `minimal_fix` даёт несогласованность: standalone-таблица без правок → строка есть; та же таблица с одной форматной правкой в ячейке → строки нет. Opus 4.1 в этом же раунде проверил инвариант Ф1 (`has_revisions` = `.//w:ins`/`.//w:del` only) и счёл его выполненным, не подняв это как блокер.

**Решение пользователя (2026-07-26):**

> Главнее правило `STANDALONE_TABLE` — отдельно стоящая таблица всегда даёт строку ручной проверки, потому что инструмент не умеет разбивать её на пункты; правило «format-only не создаёт строку» относится к таблицам внутри пункта.

Код не меняется, фикс не диспатчится. Ledger-статус закрыт как `resolved-by-user`.
