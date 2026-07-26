from app.processing.ooxml_parser import OOXMLParser
from app.processing.types import RawDocument, RawParagraph, RawTable
from tests.fixtures.builders import build_docx_with_non_element_nodes, build_simple_docx


def test_parse_returns_raw_document_with_paragraphs():
    data = build_simple_docx(["Hello", "World"])
    doc = OOXMLParser().parse(data)
    assert isinstance(doc, RawDocument)
    paragraphs = [b for b in doc.blocks if isinstance(b, RawParagraph)]
    assert len(paragraphs) == 2
    assert paragraphs[0].text() == "Hello"
    assert paragraphs[1].text() == "World"
    assert paragraphs[0].block_id == "p_0001"
    assert paragraphs[1].block_id == "p_0002"


def test_parse_preserves_text_inside_w_ins():
    from tests.fixtures.builders import build_docx_with_insertion

    data = build_docx_with_insertion("before ", "INSERTED", " after")
    doc = OOXMLParser().parse(data)
    paragraphs = [b for b in doc.blocks if isinstance(b, RawParagraph)]
    assert paragraphs[0].text() == "before INSERTED after"


def test_parse_emits_raw_table_with_rows_and_cells():
    from app.processing.types import RawTable
    from tests.fixtures.builders import build_docx_with_table

    data = build_docx_with_table(
        rows=[["A1", "B1"], ["A2", "B2"]],
        leading_paragraph="Перед таблицей",
    )
    doc = OOXMLParser().parse(data)
    tables = [b for b in doc.blocks if isinstance(b, RawTable)]
    assert len(tables) == 1
    t = tables[0]
    assert t.block_id == "t_0001"
    assert t.block_index == 1  # one paragraph at index 0, table at index 1
    assert len(t.rows) == 2
    assert len(t.rows[0].cells) == 2
    assert t.rows[0].cells[0].text() == "A1"
    assert t.rows[1].cells[1].text() == "B2"
    # Each cell holds RawParagraph objects flagged as is_in_table.
    assert t.rows[0].cells[0].paragraphs[0].is_in_table is True


def test_parse_ignores_comments_and_processing_instructions_everywhere():
    data = build_docx_with_non_element_nodes()

    doc = OOXMLParser().parse(data)

    assert [type(block) for block in doc.blocks] == [
        RawParagraph,
        RawParagraph,
        RawParagraph,
        RawTable,
    ]
    paragraphs = [block for block in doc.blocks if isinstance(block, RawParagraph)]
    assert [paragraph.text() for paragraph in paragraphs] == [
        "До body",
        "После body",
        "До run после run",
    ]
    table = next(block for block in doc.blocks if isinstance(block, RawTable))
    assert table.rows[0].cells[0].text() == "До cell после cell"
