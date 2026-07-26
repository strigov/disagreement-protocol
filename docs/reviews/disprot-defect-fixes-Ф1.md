# Review: disprot-defect-fixes — Ф1

- **Date**: 2026-07-26
- **Phase scope**: Безопасный разбор OOXML и реальные format-only правки
- **Base commit**: c6d4ea6188f278bda9f5f8eb1d6f88dd97bc5ea2
- **Rounds**: 2 (Opus 4.1 + Codex xhigh 4.2 control)
- **Outcome**: CLEAN

## Findings history

| id | reviewer | finding (one line) | decision | final status |
|---|---|---|---|---|
| F1-B1-Ф1 | opus-review | CANNOT_VERIFY: в samples/README.md изменены только expected-result ячейки для samples 03 и 09 — весь samples/ не отслеживается, базовой версии для diff нет; подтверждено по mtime | ACCEPTED | verified-by-controller |
| F1-B2-Ф1 | opus-review | CANNOT_VERIFY: критерий «sample 09 доходит до parsed» не закреплён тестом на уровне сервиса; статус PARSED следует структурно из processing.py | ACCEPTED | verified-by-controller |
| F1-B3-Ф1 | opus-review | В коммит фазы попадают ранее не отслеживаемые samples/*.docx, samples/07_edge_plain.txt и scripts/make_samples.py (569 строк); не закоммитить их — new test_sample_regressions.py упадёт на чистом checkout | DEFER | deferred |
| F1-B4-Ф1 | opus-review | run_text() в revision_resolver.py дублирует извлечение t/delText/tab/br из ooxml_parser.py; общий helper предотвратил бы расхождение двух копий | DEFER | deferred |
| F1-B5-Ф1 | opus-review | Контрактный пункт «для пустого paragraph-mark run — accepted_text всего параграфа» тестом не закреплён отличимо от ветки run-text | NIT | deferred |
| F1-B6-Ф1 | opus-review | test_resolve_format_only_changes_keeps_text_and_reports_authors сравнивает множество кортежей — число records закреплено лишь косвенно через format_only_count == 2 | NIT | deferred |
| F1-B7-Ф1 | opus-review | Шаг 1 плана просит комментарий/PI «внутрь cell», фикстура помещает их внутрь w:r ячейки, а не прямым потомком w:tc | NIT | deferred |
| F1-B8-Ф1 | opus-review | containing_run() идёт по getparent() без ограничения на p_elem: для text-box абзаца rPrChange paragraph-mark мог бы подхватить текст внешнего run | NIT | deferred |
| F1-B9-Ф1 | opus-review | Фикстура-билдер содержит собственный assert (проверку инварианта построения) — такие проверки принадлежат тесту, а не билдеру | NIT | deferred |
| F1-B10-Ф1 | opus-review | Предсуществующий шум PytestDeprecationWarning про незаданный asyncio_default_fixture_loop_scope — не из этого diff и вне списка файлов Ф1 | NIT | deferred |
| F1-B11-Ф1 | codex-control | Квадратичное время: для каждого найденного w:rPrChange заново обходится весь содержащий w:r — 0,11/0,46/1,75/7,12 с при 500/1000/2000/4000 элементах; требуется кэшировать run_text по содержащему w:r | ACCEPTED | fixed |
| F1-B12-Ф1 | codex-control | Явно передавать XMLParser(resolve_entities=False, no_network=True) в оба разбора XML (ooxml_parser.py, revision_resolver.py) — defense-in-depth, lxml 5.3 уже отклоняет внешние сущности | DEFER | deferred |
| F1-B13-Ф1 | codex-control | Review package был усечён инструментом посреди хунков; ревьюер дочитал файлы вручную — замечание про инструментарий, не про код | NIT | deferred |
| F2-B1-Ф1 | opus | w:rPrChange на run внутри w:ins/w:del тоже даёт запись FORMAT_ONLY — ровно то, что предписывает ## Contracts → Revision semantics; на строки протокола и covered_revisions не влияет | DEFER | deferred |
| F2-B2-Ф1 | opus | Устаревший английский текст старого diagnostic-сообщения остался в тесте test_validation_engine.py:114; строка нигде не сравнивается с production-кодом, файл вне списка файлов Ф1 | NIT | nit |
| F2-B3-Ф1 | opus | Тест линейности использует sys.settrace и матчится на имя приватного вложенного замыкания run_text — сломал бы измерение покрытия под pytest --cov (не используется в репозитории) и станет ложным провалом при переименовании замыкания | NIT | nit |
| F2-B4-Ф1 | opus | build_docx_with_many_run_format_only_revisions кладёт 8 w:rPrChange в один w:rPr — невалидно по схеме OOXML (один rPrChange на rPr), хотя воспроизводит замеренный вектор блокера; реалистичная форма масштабирования (N runs × 1 change) тестом не закреплена | NIT | nit |

## Deferred

- **F1-B3-Ф1** (BUILD_BREAK): в коммит фазы попадают ранее не отслеживаемые `samples/*.docx`, `samples/07_edge_plain.txt` и `scripts/make_samples.py` (569 строк). По mtime фаза их не создавала и не перегенерировала; закоммитить их обязательно, иначе новый `backend/tests/integration/test_sample_regressions.py` упадёт на чистом checkout. Совпадает с `P1-B2`.
- **F1-B4-Ф1** (NICE_TO_HAVE): `revision_resolver.py`: `run_text()` дублирует извлечение `t`/`delText`/`tab`/`br` из `ooxml_parser.py`; общий helper предотвратил бы расхождение двух копий. `run_text` и `containing_run` — замыкания без захваченного состояния, могли бы быть module-level.
- **F1-B12-Ф1** (SECURITY): явно передавать `XMLParser(resolve_entities=False, no_network=True)` в оба разбора XML (`ooxml_parser.py`, `revision_resolver.py`). Установленный lxml 5.3 уже отклоняет внешние сущности, поэтому это defense-in-depth.
- **F2-B1-Ф1** (NONE, информационное): `w:rPrChange` на run, который сам находится внутри `w:ins`/`w:del`, также даёт запись `FORMAT_ONLY`, так что `format_only_count` может включать форматные правки вставленного/удалённого текста — `backend/app/processing/revision_resolver.py:171-194`. Это ровно то, что предписывает `## Contracts → Revision semantics` («каждый отдельный `w:rPrChange` … создаёт ровно один `RevisionRecord`»), и это не влияет на строки протокола или `covered_revisions`. Изменение семантики потребовало бы правки `## Contracts` — вне объёма Ф1; не триггерит новый раунд фиксов.

## Nits (informational)

- **F1-B5-Ф1**: контрактный пункт «для пустого paragraph-mark run — `accepted_text` всего параграфа» тестом не закреплён отличимо от ветки run-text (в одной фикстуре текст run непустой, в другой `accepted_text` пуст). Ревьюер проверил работу fallback пробой — это пробел покрытия, не дефект.
- **F1-B6-Ф1**: `test_resolve_format_only_changes_keeps_text_and_reports_authors` сравнивает множество кортежей, поэтому дубль record тест не уронит; число записей закреплено лишь косвенно через `format_only_count == 2`. Явный `len(...) == 2` отвечал бы шагу плана «Проверить число records».
- **F1-B7-Ф1**: шаг 1 плана просит комментарий/PI «внутрь cell», а фикстура помещает их внутрь `w:r` ячейки, а не прямым потомком `w:tc`. Ревьюер пробой подтвердил, что guard достаточен для `w:tc`/`w:tr`/`w:tbl` — замечание только к тесту, не к коду.
- **F1-B8-Ф1**: `containing_run()` идёт по `getparent()` без ограничения на `p_elem`: для абзаца внутри text-box run правка paragraph-mark `rPrChange` подхватила бы текст внешнего run. Согласуется с уже существующим поведением walk для INS/DEL.
- **F1-B9-Ф1**: фикстура-билдер содержит собственный assert (проверку инварианта построения); такие проверки принадлежат тесту, а не билдеру.
- **F1-B10-Ф1**: предсуществующий шум в каждом backend-прогоне: `PytestDeprecationWarning` про незаданный `asyncio_default_fixture_loop_scope` (`backend/pyproject.toml`). Не из этого diff и вне списка файлов Ф1.
- **F1-B13-Ф1**: review package был усечён инструментом посреди хунков; контрольный ревьюер для их оценки дополнительно прочитал `ooxml_parser.py`, `revision_resolver.py`, `test_ooxml_parser.py` и `test_revision_resolver.py`. Замечание про инструментарий: при больших пакетах ревьюеры могут видеть неполный diff.
- **F2-B2-Ф1**: `backend/tests/processing/test_validation_engine.py:114` — в тесте остался устаревший английский текст старого diagnostic-сообщения («format-only revisions detected (original==accepted)»). Строка нигде не сравнивается с production-кодом, файл вне списка файлов Ф1.
- **F2-B3-Ф1**: `backend/tests/processing/test_revision_resolver.py:642-658` — тест линейности использует `sys.settrace` и матчится на имя приватного вложенного замыкания `run_text`. Ломал бы измерение покрытия под `pytest --cov` (в репозитории не используется) и молча превратится в ложный провал при переименовании/инлайне замыкания.
- **F2-B4-Ф1**: `backend/tests/fixtures/builders.py:321-335` — `build_docx_with_many_run_format_only_revisions` кладёт 8 `w:rPrChange` в один `w:rPr`, что невалидно по схеме OOXML (допускается один `rPrChange` на `rPr`), хотя точно воспроизводит замеренный вектор блокера. Реалистичная форма масштабирования (N runs × 1 change) тестом не закреплена; ревьюер проверил её линейность пробой.
