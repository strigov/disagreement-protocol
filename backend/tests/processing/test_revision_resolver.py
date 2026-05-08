from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import RawParagraph
from tests.fixtures.builders import (
    build_docx_with_deletion,
    build_docx_with_insertion,
    build_simple_docx,
)


def test_resolve_insertion_yields_original_without_inserted_text():
    data = build_docx_with_insertion("before ", "INSERTED", " after")
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "before  after"
    assert rd.accepted_text == "before INSERTED after"
    assert any(rev.type == "INS" and rev.text == "INSERTED" for rev in rd.revisions)
    assert diags == []


def test_resolve_deletion_yields_original_with_deleted_text_and_accepted_without():
    data = build_docx_with_deletion("before ", "DELETED", " after")
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "before DELETED after"
    assert rd.accepted_text == "before  after"
    assert any(rev.type == "DEL" and rev.text == "DELETED" for rev in rd.revisions)
    assert diags == []


def test_resolve_no_revisions_yields_identical_texts():
    data = build_simple_docx(["Plain paragraph"])
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "Plain paragraph"
    assert rd.accepted_text == "Plain paragraph"
    assert rd.revisions == ()
    assert diags == []
