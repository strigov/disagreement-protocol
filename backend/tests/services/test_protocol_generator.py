import pytest

from app.processing.types import (
    Clause,
    EnrichedParagraph,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
    RevisionRecord,
    Run,
)
from app.services.protocol_generator import BuildContext, BuiltRow, ProtocolRowBuilder


def _make_clause(
    label: str,
    original: str,
    accepted: str,
    flags: set[str] | None = None,
    rev_type: str = "INS",
) -> Clause:
    paragraph = EnrichedParagraph(
        block_id="p_0001",
        text_runs=accepted or original,
        num_id=1,
        ilvl=0,
        original_text=original,
        accepted_text=accepted,
        revisions=(RevisionRecord(type=rev_type, text=accepted or original),),
        rendered_number=label,
        numbering_confidence=1.0,
    )
    clause = Clause(clause_key="c_p_0001", label=label, level=0, parent_key=None)
    clause.paragraphs.append(paragraph)
    if flags:
        clause.flags.update(flags)
    return clause


def test_basic_row_maps_columns():
    clause = _make_clause("1.", "Старый текст", "Новый текст")
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, BuiltRow)
    assert row.point_label == "1."
    assert row.party_1_text == "Старый текст"
    assert row.party_2_text == "Новый текст"
    assert row.agreed_text == "Редакция Арендатора"


def test_new_clause_uses_dash_in_counterparty_and_label_with_counter():
    clause = _make_clause(
        "1.",
        "",
        "Совсем новый пункт",
        flags={"NEW_CLAUSE"},
        rev_type="INS",
    )
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert rows[0].party_1_text == "—"
    assert rows[0].party_2_text == "Совсем новый пункт"
    assert rows[0].point_label == "Новый пункт 1"


def test_deleted_clause_uses_exclude_in_drafting():
    clause = _make_clause(
        "3.5.",
        "Старый текст пункта",
        "",
        flags={"DELETED_CLAUSE"},
        rev_type="DEL",
    )
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert rows[0].party_1_text == "Старый текст пункта"
    assert rows[0].party_2_text == "Исключить пункт 3.5."
    assert rows[0].point_label == "3.5."


def test_empty_role_falls_back_to_storona_2():
    clause = _make_clause("1.", "old", "new")
    ctx = BuildContext(drafting_party_role="", counterparty_role="")

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert rows[0].agreed_text == "Редакция Стороны 2"


def test_clause_with_table_emits_table_cell_change_flag_and_renders_cells():
    from app.processing.types import RawParagraph, RawTable, RawTableCell, RawTableRow, Run

    clause = _make_clause("1.", "Старый", "Новый")
    cell_a = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="A1"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    cell_b = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0002",
                runs=(Run(text="B1"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    table = RawTable(
        block_id="t_0001",
        block_index=2,
        rows=(RawTableRow(cells=(cell_a, cell_b)),),
        has_revisions=True,
    )
    clause.tables.append(table)
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert "TABLE_CELL_CHANGE" in rows[0].flags
    assert "A1" in rows[0].party_2_text
    assert "B1" in rows[0].party_2_text


def test_clause_with_unrevised_table_does_not_emit_table_cell_change_flag():
    from app.processing.types import RawParagraph, RawTable, RawTableCell, RawTableRow, Run

    clause = _make_clause("1.", "Старый", "Новый")
    cell = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="Z1"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )
    table = RawTable(
        block_id="t_0001",
        block_index=2,
        rows=(RawTableRow(cells=(cell,)),),
        has_revisions=False,
    )
    clause.tables.append(table)
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([clause], ctx)

    assert "TABLE_CELL_CHANGE" not in rows[0].flags
    assert "Z1" in rows[0].party_2_text


def test_standalone_table_clause_without_revisions_has_no_table_cell_change():
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
    standalone = Clause(
        clause_key="c_t_0001",
        label="Таблица",
        level=0,
        parent_key=None,
    )
    standalone.tables.append(table)
    standalone.flags.add("STANDALONE_TABLE")
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([standalone], ctx)

    assert len(rows) == 1
    assert rows[0].point_label == "Таблица"
    assert "STANDALONE_TABLE" in rows[0].flags
    assert "manual_review" in rows[0].flags
    assert "TABLE_CELL_CHANGE" not in rows[0].flags


def test_standalone_table_clause_with_revisions_gets_table_cell_change():
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
        has_revisions=True,
    )
    standalone = Clause(
        clause_key="c_t_0001",
        label="Таблица",
        level=0,
        parent_key=None,
    )
    standalone.tables.append(table)
    standalone.flags.add("STANDALONE_TABLE")
    ctx = BuildContext(
        drafting_party_role="Арендатор",
        counterparty_role="Арендодатель",
    )

    rows = ProtocolRowBuilder().build([standalone], ctx)

    assert len(rows) == 1
    assert rows[0].point_label == "Таблица"
    assert "STANDALONE_TABLE" in rows[0].flags
    assert "TABLE_CELL_CHANGE" in rows[0].flags
    assert "manual_review" in rows[0].flags


def test_versioned_table_renders_original_and_accepted_columns_separately():
    clause = _make_clause("1.", "Старый", "Новый")
    table = RawTable(
        block_id="t_0001",
        block_index=1,
        rows=(
            RawTableRow(
                cells=(
                    RawTableCell(
                        paragraphs=(
                            RawParagraph(
                                block_id="t_0001_p_0001",
                                runs=(Run(text="fallback"),),
                                num_id=None,
                                ilvl=None,
                                style_id=None,
                                is_in_table=True,
                            ),
                        ),
                        original_text="1 200",
                        accepted_text="1 100",
                        revisions=(
                            RevisionRecord(type="DEL", text="1 200"),
                            RevisionRecord(type="INS", text="1 100"),
                        ),
                    ),
                ),
            ),
        ),
        has_revisions=True,
    )
    clause.tables.append(table)

    row = ProtocolRowBuilder().build(
        [clause],
        BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель"),
    )[0]

    assert row.party_1_text.endswith("Старый\n1 200")
    assert row.party_2_text.endswith("Новый\n1 100")
    assert "1 2001 100" not in row.party_1_text + row.party_2_text
    assert "TABLE_CELL_CHANGE" in row.flags


def test_standalone_versioned_table_uses_original_and_accepted_columns():
    standalone = Clause(
        clause_key="c_t_0001",
        label="Таблица",
        level=0,
        parent_key=None,
        tables=[
            RawTable(
                block_id="t_0001",
                block_index=0,
                rows=(
                    RawTableRow(
                        cells=(
                            RawTableCell(
                                paragraphs=(),
                                original_text="1 200",
                                accepted_text="1 100",
                                revisions=(RevisionRecord(type="DEL", text="1 200"),),
                            ),
                        ),
                    ),
                ),
                has_revisions=True,
            ),
        ],
    )
    standalone.flags.add("STANDALONE_TABLE")

    row = ProtocolRowBuilder().build(
        [standalone],
        BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель"),
    )[0]

    assert row.party_1_text == "1 200"
    assert row.party_2_text == "1 100"


def test_table_cell_text_validates_version_and_uses_plain_text_fallback():
    cell = RawTableCell(
        paragraphs=(
            RawParagraph(
                block_id="t_0001_p_0001",
                runs=(Run(text="часть 1"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
            RawParagraph(
                block_id="t_0001_p_0002",
                runs=(Run(text="часть 2"),),
                num_id=None,
                ilvl=None,
                style_id=None,
                is_in_table=True,
            ),
        ),
    )

    assert cell.text("original") == "часть 1 часть 2"
    assert cell.text("accepted") == "часть 1 часть 2"
    with pytest.raises(ValueError, match="Неизвестная версия"):
        cell.text("draft")
