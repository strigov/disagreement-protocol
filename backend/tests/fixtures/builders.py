from io import BytesIO

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def build_simple_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_insertion(
    before: str, inserted: str, after: str, author: str = "Editor"
) -> bytes:
    """Build a DOCX where `inserted` is wrapped in <w:ins>."""
    doc = DocxDocument()
    p = doc.add_paragraph(before)
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), author)
    ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = inserted
    t.set(qn("xml:space"), "preserve")
    if after:
        r2 = etree.SubElement(pelem, qn("w:r"))
        t2 = etree.SubElement(r2, qn("w:t"))
        t2.text = after
        t2.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_table(rows: list[list[str]], leading_paragraph: str = "") -> bytes:
    """Build a DOCX with one table whose cells contain the given strings."""
    doc = DocxDocument()
    if leading_paragraph:
        doc.add_paragraph(leading_paragraph)
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows) if rows else 0
    table = doc.add_table(rows=n_rows, cols=n_cols)
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_deletion(
    before: str, deleted: str, after: str, author: str = "Editor"
) -> bytes:
    """Build a DOCX where `deleted` is wrapped in <w:del>/<w:delText>."""
    doc = DocxDocument()
    p = doc.add_paragraph(before)
    pelem = p._p
    deln = etree.SubElement(pelem, qn("w:del"))
    deln.set(qn("w:id"), "1")
    deln.set(qn("w:author"), author)
    deln.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(deln, qn("w:r"))
    t = etree.SubElement(r, qn("w:delText"))
    t.text = deleted
    t.set(qn("xml:space"), "preserve")
    if after:
        r2 = etree.SubElement(pelem, qn("w:r"))
        t2 = etree.SubElement(r2, qn("w:t"))
        t2.text = after
        t2.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_manual_numbering(items: list[str]) -> bytes:
    """Items already include literal numbers like '1.', '1.1.', '2.'."""
    return build_simple_docx(items)


def build_docx_with_unknown_numid(text: str, num_id: int = 999) -> bytes:
    """Build a DOCX where a paragraph references a numId that does not exist in numbering.xml."""
    doc = DocxDocument()
    p = doc.add_paragraph(text)
    pPr = p._p.get_or_add_pPr()
    numPr = etree.SubElement(pPr, qn("w:numPr"))
    ilvl = etree.SubElement(numPr, qn("w:ilvl"))
    ilvl.set(qn("w:val"), "0")
    numId = etree.SubElement(numPr, qn("w:numId"))
    numId.set(qn("w:val"), str(num_id))
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_autonumbering_contract() -> bytes:
    """A contract with manual numeric labels '1.' / '1.1.' / '2.', one INS revision in clause 1.1."""
    doc = DocxDocument()
    doc.add_paragraph(
        'ООО "Ромашка", в лице директора, именуемое в дальнейшем "Арендодатель", '
        'и АО "Василёк", именуемое в дальнейшем "Арендатор", заключили настоящий договор.'
    )
    doc.add_paragraph("1. Предмет договора")
    p = doc.add_paragraph("1.1. Исполнитель обязуется оказать услуги ")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "Editor")
    ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = "качественно и в срок"
    t.set(qn("xml:space"), "preserve")
    doc.add_paragraph("2. Цена договора")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_multipar_contract() -> bytes:
    """A clause that spans 2 paragraphs."""
    doc = DocxDocument()
    doc.add_paragraph(
        'ООО "А", именуемое в дальнейшем "Сторона1", и ООО "Б", именуемое в дальнейшем "Сторона2".'
    )
    doc.add_paragraph("1. Раздел один")
    p = doc.add_paragraph("Дополнительный текст пункта ")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "X")
    ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = "ВСТАВКА"
    t.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_new_clause_contract() -> bytes:
    """A whole paragraph wrapped in <w:ins>."""
    doc = DocxDocument()
    doc.add_paragraph(
        'ООО "А", именуемое в дальнейшем "Сторона1", и ООО "Б", именуемое в дальнейшем "Сторона2".'
    )
    doc.add_paragraph("1. Старый пункт")
    p = doc.add_paragraph("")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "X")
    ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = "2. Совершенно новый пункт"
    t.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_deleted_clause_contract() -> bytes:
    """A whole paragraph wrapped in <w:del>."""
    doc = DocxDocument()
    doc.add_paragraph(
        'ООО "А", именуемое в дальнейшем "Сторона1", и ООО "Б", именуемое в дальнейшем "Сторона2".'
    )
    doc.add_paragraph("1. Остающийся пункт")
    p = doc.add_paragraph("")
    pelem = p._p
    deln = etree.SubElement(pelem, qn("w:del"))
    deln.set(qn("w:id"), "1")
    deln.set(qn("w:author"), "X")
    deln.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(deln, qn("w:r"))
    t = etree.SubElement(r, qn("w:delText"))
    t.text = "2. Удаляемый пункт целиком"
    t.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_simple_contract_with_revision() -> bytes:
    return build_docx_with_insertion(
        'ООО "А", именуемое в дальнейшем "Сторона1", и ООО "Б", именуемое в дальнейшем "Сторона2". '
        "1. Услуги оказываются ",
        "вовремя",
        ".",
    )
