from app.processing.changed_clause_detector import ChangedClauseDetector
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import Clause, EnrichedParagraph, RevisionRecord
from tests.fixtures.builders import build_docx_with_format_only_revisions


def _ep_with_rev(
    block_id: str,
    text: str,
    accepted: str,
    rev_type: str,
) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id=block_id,
        text_runs=accepted,
        num_id=1,
        ilvl=0,
        original_text=text,
        accepted_text=accepted,
        revisions=(
            RevisionRecord(
                type=rev_type,
                text=accepted if rev_type == "INS" else text,
            ),
        ),
        rendered_number="1.",
        numbering_confidence=1.0,
    )


def _clause_with(paragraphs):
    clause = Clause(clause_key="c_p_0001", label="1.", level=0, parent_key=None)
    clause.paragraphs.extend(paragraphs)
    return clause


def test_detects_clause_with_textual_revision():
    paragraph = _ep_with_rev("p_0001", "old", "new", "INS")
    clauses = [_clause_with([paragraph])]

    changed = ChangedClauseDetector().detect(clauses)

    assert len(changed) == 1


def test_skips_clause_with_only_format_only_revisions_from_resolver():
    data = build_docx_with_format_only_revisions()
    raw = OOXMLParser().parse(data)
    revisions, _ = RevisionResolver().resolve(data, raw)
    raw_paragraph = next(block for block in raw.blocks if block.block_id == "p_0001")
    revision_data = revisions[raw_paragraph.block_id]
    paragraph = EnrichedParagraph(
        block_id=raw_paragraph.block_id,
        text_runs=raw_paragraph.text(),
        num_id=raw_paragraph.num_id,
        ilvl=raw_paragraph.ilvl,
        original_text=revision_data.original_text,
        accepted_text=revision_data.accepted_text,
        revisions=revision_data.revisions,
        rendered_number="1.",
        numbering_confidence=1.0,
    )
    clauses = [_clause_with([paragraph])]

    assert ChangedClauseDetector().detect(clauses) == []


def test_marks_new_clause_when_all_paragraphs_are_inserts():
    paragraph = _ep_with_rev("p_0001", "", "Новый текст", "INS")
    clauses = [_clause_with([paragraph])]

    changed = ChangedClauseDetector().detect(clauses)

    assert "NEW_CLAUSE" in changed[0].flags


def test_marks_deleted_clause_when_all_paragraphs_are_deletes():
    paragraph = _ep_with_rev("p_0001", "Старый текст", "", "DEL")
    clauses = [_clause_with([paragraph])]

    changed = ChangedClauseDetector().detect(clauses)

    assert "DELETED_CLAUSE" in changed[0].flags


def test_includes_clause_with_table_revisions_even_without_paragraph_revisions():
    from app.processing.types import RawParagraph, RawTable, RawTableCell, RawTableRow, Run

    paragraph = EnrichedParagraph(
        block_id="p_0001",
        text_runs="Шапка",
        num_id=1,
        ilvl=0,
        original_text="Шапка",
        accepted_text="Шапка",
        revisions=(),
        rendered_number="1.",
        numbering_confidence=1.0,
    )
    cell = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="X"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    table = RawTable(
        block_id="t_0001",
        block_index=1,
        rows=(RawTableRow(cells=(cell,)),),
        has_revisions=True,
    )
    clause = _clause_with([paragraph])
    clause.tables.append(table)

    changed = ChangedClauseDetector().detect([clause])

    assert len(changed) == 1


def test_skips_clause_with_table_having_no_revisions():
    from app.processing.types import RawParagraph, RawTable, RawTableCell, RawTableRow, Run

    paragraph = EnrichedParagraph(
        block_id="p_0001",
        text_runs="Шапка",
        num_id=1,
        ilvl=0,
        original_text="Шапка",
        accepted_text="Шапка",
        revisions=(),
        rendered_number="1.",
        numbering_confidence=1.0,
    )
    cell = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="X"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    table = RawTable(
        block_id="t_0001",
        block_index=1,
        rows=(RawTableRow(cells=(cell,)),),
        has_revisions=False,
    )
    clause = _clause_with([paragraph])
    clause.tables.append(table)

    assert ChangedClauseDetector().detect([clause]) == []


def test_includes_standalone_table_clause_even_without_revisions():
    from app.processing.types import RawParagraph, RawTable, RawTableCell, RawTableRow, Run

    cell = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="X"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    table = RawTable(
        block_id="t_0001",
        block_index=0,
        rows=(RawTableRow(cells=(cell,)),),
        has_revisions=False,
    )
    clause = Clause(clause_key="c_t_0001", label="Таблица", level=0, parent_key=None)
    clause.tables.append(table)
    clause.flags.add("STANDALONE_TABLE")

    changed = ChangedClauseDetector().detect([clause])

    assert len(changed) == 1
