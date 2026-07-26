from pathlib import Path

from app.services.ingestion import run_pipeline


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
