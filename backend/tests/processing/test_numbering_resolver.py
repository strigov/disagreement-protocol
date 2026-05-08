import sys
import zipfile
from io import BytesIO
from types import ModuleType, SimpleNamespace

from app.processing.ooxml_parser import OOXMLParser
from app.processing.numbering_resolver import NumberingResolver
from app.processing.types import RawDocument, RawParagraph, Run
from tests.fixtures.builders import build_docx_with_manual_numbering


def _build_docx_package_with_numbering() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "word/numbering.xml",
            (
                '<w:numbering xmlns:w="http://schemas.openxmlformats.org/'
                'wordprocessingml/2006/main"><w:num w:numId="1"/></w:numbering>'
            ),
        )
    return buf.getvalue()


def test_docx2python_body_depth_populates_numbers(monkeypatch):
    fake_docx2python_module = ModuleType("docx2python")

    def fake_docx2python(_data, html=False):
        assert html is False
        return SimpleNamespace(
            body=[
                [
                    [
                        [
                            "1. Предмет договора",
                            "1.1. Исполнитель обязуется",
                        ]
                    ]
                ]
            ]
        )

    fake_docx2python_module.docx2python = fake_docx2python
    monkeypatch.setitem(sys.modules, "docx2python", fake_docx2python_module)

    raw = RawDocument(
        blocks=(
            RawParagraph("p_0001", (Run("Предмет договора"),), 1, 0, None),
            RawParagraph("p_0002", (Run("Исполнитель обязуется"),), 1, 1, None),
        )
    )
    nmap, diags = NumberingResolver().resolve(_build_docx_package_with_numbering(), raw)

    assert nmap["p_0001"].rendered_number == "1."
    assert nmap["p_0002"].rendered_number == "1.1."
    assert nmap["p_0001"].source == "docx2python"
    assert nmap["p_0002"].confidence == 1.0
    assert not diags


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
    from tests.fixtures.builders import build_docx_with_unknown_numid
    data = build_docx_with_unknown_numid("Пункт со сломанной нумерацией", num_id=999)
    raw = OOXMLParser().parse(data)
    _, diags = NumberingResolver().resolve(data, raw)
    assert any(
        d.component == "numbering" and "numId 999 not found" in d.message
        for d in diags
    )
