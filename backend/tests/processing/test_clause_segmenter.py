from app.processing.clause_segmenter import ClauseSegmenter
from app.processing.types import (
    EnrichedParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
)


def _ep(
    block_id: str,
    text: str,
    num: str | None,
    level: int | None,
    numbering_level: int | None = None,
) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id=block_id,
        text_runs=text,
        num_id=1 if num else None,
        ilvl=level,
        original_text=text,
        accepted_text=text,
        revisions=(),
        rendered_number=num,
        numbering_confidence=1.0 if num else 0.0,
        numbering_level=numbering_level,
    )


def _table(block_id: str, block_index: int, has_revisions: bool = False) -> RawTable:
    return RawTable(
        block_id=block_id,
        block_index=block_index,
        rows=(RawTableRow(cells=(RawTableCell(paragraphs=()),)),),
        has_revisions=has_revisions,
    )


def test_segments_top_level_numbered_paragraphs():
    paras = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert [c.label for c in clauses] == ["1.", "2."]
    assert all(c.level == 0 for c in clauses)


def test_continuation_paragraph_attaches_to_current_clause():
    paras = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Дополнительное предложение.", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert len(clauses) == 2
    assert len(clauses[0].paragraphs) == 2
    assert "MULTI_PARAGRAPH" in clauses[0].flags


def test_inserted_paragraph_with_structural_level_is_separate_nested_clause():
    paras = [
        _ep("p_0001", "1. Раздел", "1.", 0),
        _ep("p_0002", "1.1. Исходный подпункт", "1.1.", 1),
        _ep("p_0003", "Вставленный подпункт", None, None, numbering_level=1),
    ]

    clauses = ClauseSegmenter().segment(paras)

    assert [clause.label for clause in clauses] == ["1.", "1.1.", "Вставленный подпункт"]
    assert clauses[2].level == 1
    assert clauses[2].parent_key == clauses[0].clause_key


def test_nested_numbering_builds_parent_links():
    paras = [
        _ep("p_0001", "1. Раздел", "1.", 0),
        _ep("p_0002", "1.1. Подпункт", "1.1.", 1),
        _ep("p_0003", "2. Раздел два", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert len(clauses) == 3
    by_label = {c.label: c for c in clauses}
    assert by_label["1.1."].parent_key == by_label["1."].clause_key
    assert by_label["2."].parent_key is None


def test_preamble_collects_unnumbered_prefix():
    paras = [
        _ep("p_0001", "Договор № 5", None, None),
        _ep("p_0002", "ООО Ромашка, в лице ...", None, None),
        _ep("p_0003", "1. Предмет", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert clauses[0].label == "Преамбула"
    assert len(clauses[0].paragraphs) == 2
    assert clauses[1].label == "1."


def test_table_inside_clause_attaches_to_current_clause():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _table("t_0001", block_index=1),
        _ep("p_0002", "Продолжение пункта 1", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    assert len(clauses) == 2
    assert clauses[0].label == "1."
    assert len(clauses[0].tables) == 1
    assert clauses[0].tables[0].block_id == "t_0001"
    assert clauses[1].label == "2."
    assert clauses[1].tables == []


def test_standalone_table_outside_any_clause_gets_its_own_clause_with_flag():
    blocks = [
        _table("t_0001", block_index=0),
        _ep("p_0001", "1. Предмет", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    table_clauses = [c for c in clauses if c.label == "Таблица"]
    assert len(table_clauses) == 1
    assert "STANDALONE_TABLE" in table_clauses[0].flags
    assert len(table_clauses[0].tables) == 1
    assert table_clauses[0].tables[0].block_id == "t_0001"


def test_table_after_requisites_heading_attaches_to_requisites_clause():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Реквизиты сторон", None, None),
        _table("t_0001", block_index=3),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000, ...", None, None),
        _ep("p_0005", "ООО Лютик, ИНН 7700000001, ...", None, None),
        _ep("p_0006", "Контактное лицо: ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    assert len(req.tables) == 1
    assert req.tables[0].block_id == "t_0001"
    assert len(req.paragraphs) == 4
    assert [p.block_id for p in req.paragraphs] == [
        "p_0003",
        "p_0004",
        "p_0005",
        "p_0006",
    ]
    for label in ("1.", "2."):
        clause_n = next(c for c in clauses if c.label == label)
        assert clause_n.tables == []
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)


def test_signatures_heading_variant_also_starts_requisites_clause():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Подписи сторон", None, None),
        _table("t_0001", block_index=3),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000, ...", None, None),
        _ep("p_0005", "ООО Лютик, ИНН 7700000001, ...", None, None),
        _ep("p_0006", "Контактное лицо: ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    assert len(req.paragraphs) == 4
    assert [p.block_id for p in req.paragraphs] == [
        "p_0003",
        "p_0004",
        "p_0005",
        "p_0006",
    ]
    assert len(req.tables) == 1
    assert req.tables[0].block_id == "t_0001"
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)


def test_mid_document_requisites_phrase_does_not_trigger_requisites_mode():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "В случае изменения реквизитов стороны", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
        _ep("p_0004", "3. Сроки", "3.", 0),
        _ep("p_0005", "4. Ответственность", "4.", 0),
        _ep("p_0006", "5. Прочее", "5.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    assert not any(c.label == "Реквизиты сторон" for c in clauses)
    labels = [c.label for c in clauses]
    assert labels == ["1.", "2.", "3.", "4.", "5."]
    clause_one = next(c for c in clauses if c.label == "1.")
    assert any("изменения реквизитов" in p.text_runs for p in clause_one.paragraphs)


def test_small_doc_requisites_at_middle_position_still_found():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Реквизиты сторон", None, None),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000", None, None),
        _ep("p_0005", "АО Василёк, ИНН 7700000001", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == [
        "p_0003",
        "p_0004",
        "p_0005",
    ]


def test_multiple_requisites_headings_uses_first_in_tail_window():
    blocks: list = [
        _ep(f"p_{i:04d}", f"{i + 1}. п", f"{i + 1}.", 0) for i in range(25)
    ]
    blocks.append(_ep("p_0025", "Реквизиты", None, None))
    blocks.append(_ep("p_0026", "ООО Ромашка ...", None, None))
    blocks.append(_ep("p_0027", "АО Василёк ...", None, None))
    blocks.append(_ep("p_0028", "Подписи сторон", None, None))
    blocks.append(_ep("p_0029", "________________", None, None))
    blocks.append(_ep("p_0030", "________________", None, None))
    blocks.append(_ep("p_0031", "Дата: ...", None, None))
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    assert [p.block_id for p in req.paragraphs] == [
        "p_0025",
        "p_0026",
        "p_0027",
        "p_0028",
        "p_0029",
        "p_0030",
        "p_0031",
    ]


def test_mid_document_heading_outside_tail_window_ignored():
    blocks: list = [_ep("p_0000", "1. Предмет", "1.", 0)]
    blocks.append(_ep("p_0001", "Лирическое отступление", None, None))
    blocks.append(_ep("p_0002", "ещё немного", None, None))
    blocks.append(_ep("p_0003", "продолжение", None, None))
    blocks.append(_ep("p_0004", "финал отступления", None, None))
    blocks.append(_ep("p_0005", "Реквизиты сторон", None, None))
    for k in range(2, 37):
        blocks.append(_ep(f"p_{k + 4:04d}", f"{k}. п", f"{k}.", 0))
    clauses = ClauseSegmenter().segment(blocks)
    assert not any(c.label == "Реквизиты сторон" for c in clauses)
    clause_one = next(c for c in clauses if c.label == "1.")
    assert any(p.text_runs == "Реквизиты сторон" for p in clause_one.paragraphs)


def test_signatures_and_requisites_combined_heading_triggers_requisites_mode():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Подписи и реквизиты сторон", None, None),
        _ep("p_0003", "ООО Ромашка ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == ["p_0002", "p_0003"]


def test_addresses_and_requisites_combined_heading_triggers_requisites_mode():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Адреса и реквизиты сторон", None, None),
        _ep("p_0003", "ООО Ромашка, г. Москва ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == ["p_0002", "p_0003"]


def test_annex_section_prefixes_subsequent_numbered_clauses():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Приложение № 1", None, None),
        _ep("p_0003", "1. Перечень оборудования", "1.", 0),
        _ep("p_0004", "2. Стоимость", "2.", 0),
        _ep("p_0005", "Приложение № 2", None, None),
        _ep("p_0006", "1. Сроки поставки", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    labels = [c.label for c in clauses]
    assert labels == [
        "1.",
        "Приложение № 1",
        "Приложение № 1, п. 1",
        "Приложение № 1, п. 2",
        "Приложение № 2",
        "Приложение № 2, п. 1",
    ]
    by_label = {c.label: c for c in clauses}
    assert by_label["Приложение № 1"].parent_key is None
    assert (
        by_label["Приложение № 1, п. 1"].parent_key
        == by_label["Приложение № 1"].clause_key
    )
    assert (
        by_label["Приложение № 1, п. 2"].parent_key
        == by_label["Приложение № 1"].clause_key
    )
    assert (
        by_label["Приложение № 2, п. 1"].parent_key
        == by_label["Приложение № 2"].clause_key
    )


def test_annex_unnumbered_paragraph_attaches_to_current_annex_clause():
    blocks = [
        _ep("p_0001", "Приложение № 1", None, None),
        _ep("p_0002", "1. Перечень оборудования", "1.", 0),
        _ep("p_0003", "Дополнительное описание", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    annex_clause_1 = by_label["Приложение № 1, п. 1"]
    assert [p.block_id for p in annex_clause_1.paragraphs] == ["p_0002", "p_0003"]
    assert "MULTI_PARAGRAPH" in annex_clause_1.flags


def test_annex_unnumbered_paragraph_between_annex_header_and_first_clause_attaches_to_header():
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Приложение № 1", None, None),
        _ep("p_0003", "Вступительный текст приложения", None, None),
        _ep("p_0004", "1. Перечень оборудования", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    annex_header = by_label["Приложение № 1"]
    assert [p.block_id for p in annex_header.paragraphs] == ["p_0002", "p_0003"]
    assert [p.block_id for p in by_label["1."].paragraphs] == ["p_0001"]


def test_annex_table_attaches_to_current_annex_clause():
    blocks = [
        _ep("p_0001", "Приложение № 1", None, None),
        _table("t_0001", block_index=1),
        _ep("p_0002", "1. Перечень оборудования", "1.", 0),
        _table("t_0002", block_index=3),
        _ep("p_0003", "Продолжение пункта 1", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)
    assert [t.block_id for t in by_label["Приложение № 1"].tables] == ["t_0001"]
    assert [t.block_id for t in by_label["Приложение № 1, п. 1"].tables] == [
        "t_0002"
    ]
