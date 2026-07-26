import sys

from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import RawParagraph, RawTable
from tests.fixtures.builders import (
    build_docx_with_deletion,
    build_docx_with_empty_format_only_run,
    build_docx_with_format_only_revisions,
    build_docx_with_many_run_format_only_revisions,
    build_docx_with_insertion,
    build_docx_with_table_cell_replacement,
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


def test_resolve_format_only_changes_keeps_text_and_reports_authors():
    data = build_docx_with_format_only_revisions()
    raw = OOXMLParser().parse(data)

    rmap, diags = RevisionResolver().resolve(data, raw)

    paragraph = next(block for block in raw.blocks if isinstance(block, RawParagraph))
    revision_data = rmap[paragraph.block_id]
    assert revision_data.original_text == "Форматный текст"
    assert revision_data.accepted_text == "Форматный текст"
    assert {
        (revision.type, revision.text, revision.author)
        for revision in revision_data.revisions
    } == {
        ("FORMAT_ONLY", "Форматный текст", "Автор run"),
        ("FORMAT_ONLY", "Форматный текст", "Автор абзаца"),
    }
    assert len(diags) == 1
    assert diags[0].code == "FORMAT_ONLY_MISMATCH"
    assert diags[0].block_id == paragraph.block_id


def test_resolve_empty_format_only_run_uses_paragraph_text():
    data = build_docx_with_empty_format_only_run()
    raw = OOXMLParser().parse(data)

    rmap, diags = RevisionResolver().resolve(data, raw)

    paragraph = next(block for block in raw.blocks if isinstance(block, RawParagraph))
    revision_data = rmap[paragraph.block_id]
    assert revision_data.original_text == ""
    assert revision_data.accepted_text == ""
    assert [(revision.type, revision.text, revision.author) for revision in revision_data.revisions] == [
        ("FORMAT_ONLY", "", "Автор paragraph mark"),
    ]
    assert [diagnostic.code for diagnostic in diags] == ["FORMAT_ONLY_MISMATCH"]


def test_resolve_many_run_format_changes_extracts_text_once():
    change_count = 8
    data = build_docx_with_many_run_format_only_revisions(change_count)
    raw = OOXMLParser().parse(data)
    run_text_calls = 0

    def trace(frame, event, _arg):
        nonlocal run_text_calls
        if event == "call" and frame.f_code.co_name == "run_text":
            run_text_calls += 1
        return trace

    previous_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        rmap, _ = RevisionResolver().resolve(data, raw)
    finally:
        sys.settrace(previous_trace)

    paragraph = next(block for block in raw.blocks if isinstance(block, RawParagraph))
    revision_data = rmap[paragraph.block_id]
    assert len(revision_data.revisions) == change_count
    assert run_text_calls == 1


def test_resolve_table_cell_replacement_keeps_original_and_accepted_versions():
    data = build_docx_with_table_cell_replacement()
    raw = OOXMLParser().parse(data)
    table = next(block for block in raw.blocks if isinstance(block, RawTable))
    target_cell = table.rows[1].cells[1]
    target_paragraph = target_cell.paragraphs[0]

    revision_map, diagnostics = RevisionResolver().resolve(data, raw)

    revision_data = revision_map[target_paragraph.block_id]
    assert revision_data.original_text == "1 200"
    assert revision_data.accepted_text == "1 100"
    assert [(revision.type, revision.text) for revision in revision_data.revisions] == [
        ("DEL", "1 200"),
        ("INS", "1 100"),
    ]
    assert diagnostics == []

    unchanged_cells = [
        table.rows[0].cells[0],
        table.rows[0].cells[1],
        table.rows[0].cells[2],
        table.rows[1].cells[0],
        table.rows[1].cells[2],
    ]
    assert all(
        revision_map[cell.paragraphs[0].block_id].original_text
        == revision_map[cell.paragraphs[0].block_id].accepted_text
        for cell in unchanged_cells
    )
