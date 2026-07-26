from io import BytesIO
from pathlib import Path

from docx import Document

from app.services.exporter import ProtocolExporter
from app.services.ingestion import run_pipeline
from app.services.protocol_generator import BuildContext, ProtocolRowBuilder


SAMPLES_DIR = Path(__file__).resolve().parents[3] / "samples"


def _sample_bytes(filename: str) -> bytes:
    return (SAMPLES_DIR / filename).read_bytes()


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
