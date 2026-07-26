from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from app.api.protocols import _restore_paragraph
from app.processing.types import Clause as ClauseData
from app.processing.validation_engine import ValidationEngine
from app.services.exporter import ProtocolExporter
from app.services.ingestion import run_pipeline
from app.services.protocol_generator import BuildContext, ProtocolRowBuilder


SAMPLES_DIR = Path(__file__).resolve().parents[3] / "samples"


def _sample_bytes(filename: str) -> bytes:
    return (SAMPLES_DIR / filename).read_bytes()


def _serialize_paragraph_for_clause_model(paragraph) -> dict:
    return {
        "block_id": paragraph.block_id,
        "text_runs": paragraph.text_runs,
        "num_id": paragraph.num_id,
        "ilvl": paragraph.ilvl,
        "original_text": paragraph.original_text,
        "accepted_text": paragraph.accepted_text,
        "revisions": [
            {
                "type": revision.type,
                "text": revision.text,
                "author": revision.author,
            }
            for revision in paragraph.revisions
        ],
        "rendered_number": paragraph.rendered_number,
        "numbering_confidence": paragraph.numbering_confidence,
        "numbering_level": paragraph.numbering_level,
    }


def _restore_clauses_from_persisted_paragraphs(result) -> list[ClauseData]:
    restored_clauses = []
    for clause in result["clauses"]:
        restored_clause = ClauseData(
            clause_key=clause.clause_key,
            label=clause.label,
            level=clause.level,
            parent_key=clause.parent_key,
        )
        restored_clause.flags = set(clause.flags)
        paragraph_confidences = [
            paragraph.numbering_confidence for paragraph in clause.paragraphs
        ]
        fallback_confidence = (
            sum(paragraph_confidences) / len(paragraph_confidences)
            if paragraph_confidences
            else 0.0
        )
        for paragraph in clause.paragraphs:
            restored_clause.paragraphs.append(
                _restore_paragraph(
                    _serialize_paragraph_for_clause_model(paragraph),
                    fallback_confidence=fallback_confidence,
                ),
            )
        restored_clauses.append(restored_clause)
    return restored_clauses


def test_sample_09_xml_comment_reaches_pipeline_result():
    result = run_pipeline(_sample_bytes("09_edge_xml_comment.docx"))

    assert result["clauses"]
    assert result["preflight_metrics"]["revisions_total"] == 1


def test_sample_03_counts_format_only_without_changed_clause():
    result = run_pipeline(_sample_bytes("03_complex_styles_annex_tables.docx"))

    assert result["preflight_metrics"]["format_only_count"] == 1
    format_only_clause_keys = {
        clause.clause_key
        for clause in result["clauses"]
        if any(
            revision.type == "FORMAT_ONLY"
            for paragraph in clause.paragraphs
            for revision in paragraph.revisions
        )
    }
    assert len(format_only_clause_keys) == 1
    assert format_only_clause_keys.isdisjoint(
        {clause.clause_key for clause in result["changed_clauses"]}
    )


def test_sample_03_table_replacement_uses_original_and_accepted_columns():
    result = run_pipeline(_sample_bytes("03_complex_styles_annex_tables.docx"))
    rows = ProtocolRowBuilder().build(
        result["changed_clauses"],
        BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель"),
    )

    table_rows = [row for row in rows if "2026 год" in row.party_1_text]
    assert len(table_rows) == 1
    row = table_rows[0]
    assert "2026 год | 1 200 | 192 500" in row.party_1_text
    assert "2026 год | 1 100 | 192 500" in row.party_2_text
    assert "1 2001 100" not in row.party_1_text + row.party_2_text
    assert "TABLE_CELL_CHANGE" in row.flags

    exported = ProtocolExporter().export(
        [
            {
                "point_label": row.point_label,
                "party_1_text": row.party_1_text,
                "party_2_text": row.party_2_text,
                "agreed_text": row.agreed_text,
            },
        ],
        "Арендатор",
        "Арендодатель",
        "Договор",
    )
    assert len(Document(BytesIO(exported)).tables) == 1


def test_sample_01_regex_numbering_has_no_per_paragraph_low_confidence_noise():
    result = run_pipeline(_sample_bytes("01_simple_manual_numbering.docx"))

    preflight_mean = result["preflight_metrics"]["numbering_confidence_mean"]
    assert preflight_mean == pytest.approx(0.4)
    restored_clauses = _restore_clauses_from_persisted_paragraphs(result)
    persisted_report = ValidationEngine().validate([], restored_clauses, [])
    assert persisted_report.numbering_confidence_mean == pytest.approx(preflight_mean)
    assert not any(
        diagnostic["code"] == "LOW_CONFIDENCE"
        for diagnostic in result["preflight_diagnostics"]
    )


def test_sample_02_preserves_deleted_numbers_and_does_not_number_inserted_clause():
    result = run_pipeline(_sample_bytes("02_medium_auto_numbering.docx"))
    rows = ProtocolRowBuilder().build(
        result["changed_clauses"],
        BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель"),
    )

    assert [row.point_label for row in rows] == ["1.1.", "Новый пункт 1", "2.1.", "2.2."]
    assert next(row for row in rows if "DELETED_CLAUSE" in row.flags).point_label == "2.2."
    assert not any(row.point_label == "2.3." for row in rows)


def test_sample_03_keeps_style_and_override_numbering():
    result = run_pipeline(_sample_bytes("03_complex_styles_annex_tables.docx"))

    assert [
        clause.label
        for clause in result["clauses"]
        if clause.label.startswith("Статья")
    ] == ["Статья I.", "Статья II.", "Статья III."]
    assert any(
        paragraph.rendered_number == "1.4.1."
        for clause in result["clauses"]
        for paragraph in clause.paragraphs
    )


def test_sample_10_uses_original_number_for_changed_clause_and_new_label_for_insertion():
    result = run_pipeline(_sample_bytes("10_edge_renumbering.docx"))
    rows = ProtocolRowBuilder().build(
        result["changed_clauses"],
        BuildContext(drafting_party_role="Поставщик", counterparty_role="Покупатель"),
    )

    assert [row.point_label for row in rows] == ["Новый пункт 1", "1.2."]
    changed_row = next(row for row in rows if row.point_label == "1.2.")
    assert "14 календарных дней" in changed_row.party_1_text
    assert "7 календарных дней" in changed_row.party_2_text
