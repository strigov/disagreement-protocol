import time
import zipfile
from io import BytesIO

import app.processing.numbering_resolver as numbering_resolver
from app.processing.numbering_resolver import NumberingResolver
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import RawParagraph
from tests.fixtures.builders import (
    W_NS,
    build_docx_with_manual_numbering,
    build_docx_with_native_numbering,
    build_docx_with_unknown_numid,
)


def _resolve(data: bytes):
    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    nmap, diags = NumberingResolver().resolve(data, raw, revision_map)
    paragraphs = [b for b in raw.blocks if isinstance(b, RawParagraph)]
    return [nmap[p.block_id] for p in paragraphs], diags


def test_native_multilevel_decimal_sequence_with_restarts():
    data = build_docx_with_native_numbering([
        (0, "Предмет договора"),
        (1, "Исполнитель обязуется"),
        (1, "Заказчик обязуется"),
        (2, "Подпункт"),
        (0, "Цена договора"),
        (1, "Порядок оплаты"),
    ])
    numbers, diags = _resolve(data)
    assert [n.rendered_number for n in numbers] == ["1.", "1.1.", "1.2.", "1.2.1.", "2.", "2.1."]
    assert all(n.source == "native" for n in numbers)
    assert all(n.confidence == 0.95 for n in numbers)
    assert not diags


def test_native_start_and_start_override_are_honoured():
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="3"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
      <w:num w:numId="2">
        <w:abstractNumId w:val="0"/>
        <w:lvlOverride w:ilvl="0"><w:startOverride w:val="7"/></w:lvlOverride>
      </w:num>
    </w:numbering>"""
    start_doc = build_docx_with_native_numbering([(0, "А"), (0, "Б")], numbering_xml=numbering)
    numbers, _ = _resolve(start_doc)
    assert [n.rendered_number for n in numbers] == ["3.", "4."]

    override_doc = build_docx_with_native_numbering(
        [(0, "А"), (0, "Б")], numbering_xml=numbering, num_id=2
    )
    numbers, _ = _resolve(override_doc)
    assert [n.rendered_number for n in numbers] == ["7.", "8."]


def test_native_letter_and_roman_formats():
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1)"/></w:lvl>
        <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerRoman"/><w:lvlText w:val="%2."/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    data = build_docx_with_native_numbering(
        [(0, "первый"), (1, "вложенный"), (1, "вложенный"), (1, "вложенный"), (0, "второй")],
        numbering_xml=numbering,
    )
    numbers, _ = _resolve(data)
    assert [n.rendered_number for n in numbers] == ["a)", "i.", "ii.", "iii.", "b)"]


def test_native_bullet_lists_are_not_clause_numbers():
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val=""/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    data = build_docx_with_native_numbering([(0, "маркированный пункт")], numbering_xml=numbering)
    numbers, _ = _resolve(data)
    assert numbers[0].rendered_number is None
    assert numbers[0].source == "unmapped"


def test_native_style_based_numbering_via_based_on_chain():
    styles = f"""<w:styles xmlns:w="{W_NS}">
      <w:style w:type="paragraph" w:styleId="BaseNum">
        <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Clause">
        <w:basedOn w:val="BaseNum"/>
      </w:style>
    </w:styles>"""
    data = build_docx_with_native_numbering(
        [(None, "Первый пункт"), (None, "Второй пункт")],
        styles_xml=styles,
        style_ids=["Clause", "Clause"],
    )
    numbers, _ = _resolve(data)
    assert [n.rendered_number for n in numbers] == ["1.", "2."]
    assert all(n.source == "native" for n in numbers)


def test_native_number_disagreeing_with_typed_number_lowers_confidence():
    data = build_docx_with_native_numbering([
        (0, "7. Пункт с чужим ручным номером"),
    ])
    numbers, diags = _resolve(data)
    assert numbers[0].rendered_number == "1."
    assert numbers[0].confidence == 0.6
    assert any(d.code == "NUMBERING_TEXT_MISMATCH" for d in diags)
    assert any(d.code == "LOW_CONFIDENCE" for d in diags)


def test_native_number_agreeing_with_typed_number_keeps_confidence():
    data = build_docx_with_native_numbering([
        (0, "1. Пункт с совпадающим ручным номером"),
    ])
    numbers, diags = _resolve(data)
    assert numbers[0].rendered_number == "1."
    assert numbers[0].confidence == 0.95
    assert not any(d.code == "NUMBERING_TEXT_MISMATCH" for d in diags)


def test_regex_fallback_extracts_dotted_numbers():
    data = build_docx_with_manual_numbering([
        "1. Предмет договора",
        "1.1. Исполнитель обязуется",
        "2. Цена договора",
    ])
    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    nmap, diags = NumberingResolver().resolve(data, raw, revision_map)
    paragraphs = [b for b in raw.blocks if isinstance(b, RawParagraph)]
    assert nmap[paragraphs[0].block_id].rendered_number == "1."
    assert nmap[paragraphs[1].block_id].rendered_number == "1.1."
    assert nmap[paragraphs[2].block_id].rendered_number == "2."
    assert nmap[paragraphs[0].block_id].source == "regex"
    assert nmap[paragraphs[0].block_id].confidence == 0.7
    assert [nmap[paragraph.block_id].numbering_level for paragraph in paragraphs] == [0, 1, 0]
    assert not any(d.code == "LOW_CONFIDENCE" for d in diags)


def test_unnumbered_paragraph_gets_unmapped():
    data = build_docx_with_manual_numbering(["Просто текст без номера"])
    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    nmap, _ = NumberingResolver().resolve(data, raw, revision_map)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    nd = nmap[p.block_id]
    assert nd.rendered_number is None
    assert nd.confidence == 0.0
    assert nd.source == "unmapped"


def test_unknown_numid_emits_diagnostic():
    """A paragraph whose numPr references a numId not in numbering.xml emits a warning."""
    data = build_docx_with_unknown_numid("Пункт со сломанной нумерацией", num_id=999)
    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    _, diags = NumberingResolver().resolve(data, raw, revision_map)
    assert any(
        d.component == "numbering" and "numId 999 отсутствует" in d.message
        for d in diags
    )


def test_inserted_paragraph_does_not_consume_original_counter_but_mark_on_existing_does():
    data = build_docx_with_native_numbering(
        [(0, "Первый пункт"), (0, "Вставленный пункт"), (0, "Следующий пункт")],
        content_revisions=[None, "INS", None],
        paragraph_mark_revisions=["INS", "INS", None],
    )
    numbers, diags = _resolve(data)

    assert [number.rendered_number for number in numbers] == ["1.", None, "2."]
    assert [number.numbering_level for number in numbers] == [0, 0, 0]
    assert not diags

    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    paragraphs = [block for block in raw.blocks if isinstance(block, RawParagraph)]
    assert [revision_map[paragraph.block_id].exists_in_original for paragraph in paragraphs] == [
        True,
        False,
        True,
    ]


def test_deleted_paragraph_advances_original_counter():
    data = build_docx_with_native_numbering(
        [(0, "Первый пункт"), (0, "Удалённый пункт"), (0, "Следующий пункт")],
        content_revisions=[None, "DEL", None],
    )
    numbers, _ = _resolve(data)

    assert [number.rendered_number for number in numbers] == ["1.", "2.", "3."]


def test_deleted_paragraph_mark_on_existing_text_advances_original_counter():
    data = build_docx_with_native_numbering(
        [(0, "Первый пункт"), (0, "Пункт с удалённым знаком абзаца"), (0, "Следующий пункт")],
        paragraph_mark_revisions=[None, "DEL", None],
    )
    numbers, _ = _resolve(data)

    assert [number.rendered_number for number in numbers] == ["1.", "2.", "3."]


def test_inserted_paragraph_at_end_does_not_advance_counter():
    data = build_docx_with_native_numbering(
        [(0, "Исходный пункт"), (0, "Вставленный пункт")],
        content_revisions=[None, "INS"],
        paragraph_mark_revisions=[None, "INS"],
    )
    numbers, _ = _resolve(data)

    assert [number.rendered_number for number in numbers] == ["1.", None]


def test_inserted_paragraph_does_not_consume_first_start_override():
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="2">
        <w:abstractNumId w:val="0"/>
        <w:lvlOverride w:ilvl="0"><w:startOverride w:val="7"/></w:lvlOverride>
      </w:num>
    </w:numbering>"""
    data = build_docx_with_native_numbering(
        [(0, "Вставленный пункт"), (0, "Исходный пункт")],
        numbering_xml=numbering,
        num_id=2,
        content_revisions=["INS", None],
        paragraph_mark_revisions=["INS", None],
    )
    numbers, _ = _resolve(data)

    assert [number.rendered_number for number in numbers] == [None, "7."]


def test_inserted_native_number_keeps_structural_level_without_rendered_number():
    data = build_docx_with_native_numbering(
        [(0, "Раздел"), (1, "Вставленный подпункт"), (1, "Исходный подпункт")],
        content_revisions=[None, "INS", None],
        paragraph_mark_revisions=[None, "INS", None],
    )
    numbers, _ = _resolve(data)

    assert numbers[1].rendered_number is None
    assert numbers[1].numbering_level == 1
    assert numbers[1].source == "native"
    assert numbers[1].confidence == 0.95
    assert numbers[2].rendered_number == "1.1."


def test_ppr_change_uses_original_numpr_and_style_for_numbering():
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
      <w:num w:numId="2">
        <w:abstractNumId w:val="0"/>
        <w:lvlOverride w:ilvl="0"><w:startOverride w:val="7"/></w:lvlOverride>
      </w:num>
    </w:numbering>"""
    direct_numpr_doc = build_docx_with_native_numbering(
        [(0, "Удалённый текст")],
        numbering_xml=numbering,
        num_id=2,
        content_revisions=["DEL"],
        original_num_prs=[(1, 0)],
    )
    direct_numpr_numbers, _ = _resolve(direct_numpr_doc)

    styles = f"""<w:styles xmlns:w="{W_NS}">
      <w:style w:type="paragraph" w:styleId="OriginalStyle">
        <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="AcceptedStyle">
        <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr></w:pPr>
      </w:style>
    </w:styles>"""
    style_doc = build_docx_with_native_numbering(
        [(None, "Удалённый текст")],
        numbering_xml=numbering,
        styles_xml=styles,
        style_ids=["AcceptedStyle"],
        content_revisions=["DEL"],
        original_style_ids=["OriginalStyle"],
    )
    style_numbers, _ = _resolve(style_doc)

    assert direct_numpr_numbers[0].rendered_number == "1."
    assert style_numbers[0].rendered_number == "1."


def test_numbering_rejects_out_of_range_ilvl_without_replay():
    hostile_ilvl = 9_999_999
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="{hostile_ilvl}"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(hostile_ilvl, "Пункт без ручного номера")],
            numbering_xml=numbering,
        ),
    )

    assert numbers[0].rendered_number is None


def test_numbering_rejects_out_of_range_start_and_start_override():
    safe_start_limit = 100_000
    hostile_start = safe_start_limit + 1
    start_numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="{hostile_start}"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1)"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    start_numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(0, "Пункт")],
            numbering_xml=start_numbering,
        ),
    )

    override_numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1)"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="2">
        <w:abstractNumId w:val="0"/>
        <w:lvlOverride w:ilvl="0"><w:startOverride w:val="{hostile_start}"/></w:lvlOverride>
      </w:num>
    </w:numbering>"""
    override_numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(0, "Пункт")],
            numbering_xml=override_numbering,
            num_id=2,
        ),
    )

    assert start_numbers[0].rendered_number == "a)"
    assert override_numbers[0].rendered_number == "a)"


def test_numbering_bounds_repeated_placeholders_at_allowed_start():
    allowed_start = 100_000
    placeholder_count = 2_000
    lvl_text = "%1" * placeholder_count
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="{allowed_start}"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="{lvl_text}"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    started = time.perf_counter()
    numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(0, "Пункт 1"), (0, "Пункт 2"), (0, "Пункт 3")],
            numbering_xml=numbering,
        ),
    )
    elapsed = time.perf_counter() - started
    rendered = [number.rendered_number or "" for number in numbers]

    assert elapsed < 1.0
    assert max(map(len, rendered)) <= 4_096
    assert sum(map(len, rendered)) <= 1_000_000
    assert all(number.rendered_number is None for number in numbers)


def test_numbering_bounds_cumulative_rendered_output_across_paragraphs():
    lvl_text = "%1." * 1_000
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="{lvl_text}"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(0, f"Пункт {index}") for index in range(300)],
            numbering_xml=numbering,
        ),
    )
    rendered = [number.rendered_number or "" for number in numbers]

    assert rendered[0]
    assert rendered[-1] == ""
    assert max(map(len, rendered)) <= 4_096
    assert sum(map(len, rendered)) <= 1_000_000


def test_numbering_bounds_derived_counter_after_allowed_start():
    allowed_start = 100_000
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="{allowed_start}"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    numbers, _ = _resolve(
        build_docx_with_native_numbering(
            [(0, "Пункт 1"), (0, "Пункт 2")],
            numbering_xml=numbering,
        ),
    )

    assert numbers[0].rendered_number
    assert len(numbers[0].rendered_number) <= 4_096
    assert numbers[1].rendered_number is None


def test_regex_numbering_rejects_oversized_typed_number_before_capture():
    typed_number = "1" * 1_100_000
    started = time.perf_counter()
    numbers, _ = _resolve(build_docx_with_manual_numbering([f"{typed_number} Пункт"]))
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0
    assert numbers[0].rendered_number is None
    assert len(numbers[0].rendered_number or "") <= 4_096


def test_native_mismatch_diagnostic_does_not_embed_oversized_typed_number():
    typed_number = "1" * 1_100_000
    numbers, diags = _resolve(
        build_docx_with_native_numbering([(0, f"{typed_number} Пункт")]),
    )
    mismatch = next(d for d in diags if d.code == "NUMBERING_TEXT_MISMATCH")

    assert numbers[0].rendered_number == "1."
    assert len(mismatch.message) < 1_000
    assert str(len(typed_number)) in mismatch.message


def test_regex_numbering_obeys_cumulative_rendered_output_budget():
    typed_number = "1" * 4_095
    numbers, _ = _resolve(
        build_docx_with_manual_numbering(
            [f"{typed_number} Пункт {index}" for index in range(300)],
        ),
    )
    rendered = [number.rendered_number or "" for number in numbers]

    assert rendered[0]
    assert rendered[243]
    assert rendered[244] == ""
    assert rendered[-1] == ""
    assert max(map(len, rendered)) <= 4_096
    assert sum(map(len, rendered)) <= 1_000_000


def test_oversized_lvl_text_is_rejected_before_repeated_scan():
    lvl_text = "%x" * 35_000
    numbering = f"""<w:numbering xmlns:w="{W_NS}">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="{lvl_text}"/></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""
    data = build_docx_with_native_numbering(
        [(0, f"Пункт {index}") for index in range(10_000)],
        numbering_xml=numbering,
    )
    with zipfile.ZipFile(BytesIO(data)) as package:
        source_size = package.getinfo("word/numbering.xml").file_size
    started = time.perf_counter()
    numbers, _ = _resolve(data)
    elapsed = time.perf_counter() - started

    assert len(lvl_text) > 65_536
    assert 65_536 < source_size < 5_000_000
    assert elapsed < 1.0
    assert all(number.rendered_number is None for number in numbers)


def test_oversized_numbering_xml_is_skipped_before_model_materialization(monkeypatch):
    abstracts = "".join(
        f"<w:abstractNum w:abstractNumId=\"{index}\">"
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
        '<w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
        for index in range(35_000)
    )
    numbering = f"<w:numbering xmlns:w=\"{W_NS}\">{abstracts}<w:num w:numId=\"1\"><w:abstractNumId w:val=\"0\"/></w:num></w:numbering>"
    data = build_docx_with_native_numbering([(0, "Пункт")], numbering_xml=numbering)

    with zipfile.ZipFile(BytesIO(data)) as package:
        assert package.getinfo("word/numbering.xml").file_size > 5_000_000

    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    parse_calls = 0
    real_parse = numbering_resolver.etree.parse

    def recording_parse(*args, **kwargs):
        nonlocal parse_calls
        parse_calls += 1
        return real_parse(*args, **kwargs)

    monkeypatch.setattr(numbering_resolver.etree, "parse", recording_parse)
    nmap, _ = NumberingResolver().resolve(data, raw, revision_map)
    paragraph = next(block for block in raw.blocks if isinstance(block, RawParagraph))

    assert parse_calls == 0
    assert nmap[paragraph.block_id].rendered_number is None


def test_oversized_styles_xml_is_skipped_before_style_materialization(monkeypatch):
    styles = (
        f'<w:styles xmlns:w="{W_NS}">'
        '<w:style w:type="paragraph" w:styleId="Numbered">'
        '<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        "</w:style>"
        + "".join(
            f'<w:style w:type="paragraph" w:styleId="S{index}"/>'
            for index in range(110_000)
        )
        + "</w:styles>"
    )
    data = build_docx_with_native_numbering(
        [(None, "Пункт")],
        styles_xml=styles,
        style_ids=["Numbered"],
    )

    with zipfile.ZipFile(BytesIO(data)) as package:
        assert package.getinfo("word/styles.xml").file_size > 5_000_000

    raw = OOXMLParser().parse(data)
    revision_map, _ = RevisionResolver().resolve(data, raw)
    style_parse_calls = 0
    real_parse = numbering_resolver.etree.parse

    def recording_parse(*args, **kwargs):
        nonlocal style_parse_calls
        if getattr(args[0], "name", None) == "word/styles.xml":
            style_parse_calls += 1
        return real_parse(*args, **kwargs)

    monkeypatch.setattr(numbering_resolver.etree, "parse", recording_parse)
    nmap, _ = NumberingResolver().resolve(data, raw, revision_map)
    paragraph = next(block for block in raw.blocks if isinstance(block, RawParagraph))

    assert style_parse_calls == 0
    assert nmap[paragraph.block_id].rendered_number is None
