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
