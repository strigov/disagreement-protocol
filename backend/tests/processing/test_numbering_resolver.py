from app.processing.numbering_resolver import NumberingResolver
from app.processing.ooxml_parser import OOXMLParser
from app.processing.types import RawParagraph
from tests.fixtures.builders import (
    W_NS,
    build_docx_with_manual_numbering,
    build_docx_with_native_numbering,
    build_docx_with_unknown_numid,
)


def _resolve(data: bytes):
    raw = OOXMLParser().parse(data)
    nmap, diags = NumberingResolver().resolve(data, raw)
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
    nmap, diags = NumberingResolver().resolve(data, raw)
    paragraphs = [b for b in raw.blocks if isinstance(b, RawParagraph)]
    assert nmap[paragraphs[0].block_id].rendered_number == "1."
    assert nmap[paragraphs[1].block_id].rendered_number == "1.1."
    assert nmap[paragraphs[2].block_id].rendered_number == "2."
    assert nmap[paragraphs[0].block_id].source == "regex"
    assert nmap[paragraphs[0].block_id].confidence == 0.7
    # regex confidence is 0.7 < 0.85 threshold -> low-confidence diagnostics emitted.
    assert any(d.component == "numbering" and "low confidence" in d.message for d in diags)


def test_unnumbered_paragraph_gets_unmapped():
    data = build_docx_with_manual_numbering(["Просто текст без номера"])
    raw = OOXMLParser().parse(data)
    nmap, _ = NumberingResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    nd = nmap[p.block_id]
    assert nd.rendered_number is None
    assert nd.confidence == 0.0
    assert nd.source == "unmapped"


def test_unknown_numid_emits_diagnostic():
    """A paragraph whose numPr references a numId not in numbering.xml emits a warning."""
    data = build_docx_with_unknown_numid("Пункт со сломанной нумерацией", num_id=999)
    raw = OOXMLParser().parse(data)
    _, diags = NumberingResolver().resolve(data, raw)
    assert any(
        d.component == "numbering" and "numId 999 not found" in d.message
        for d in diags
    )
