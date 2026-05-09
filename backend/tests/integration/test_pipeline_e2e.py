from io import BytesIO

from docx import Document

from app.processing.changed_clause_detector import ChangedClauseDetector
from app.services.exporter import ProtocolExporter
from app.services.ingestion import run_pipeline
from app.services.protocol_generator import BuildContext, ProtocolRowBuilder
from tests.fixtures.builders import (
    build_autonumbering_contract,
    build_deleted_clause_contract,
    build_multipar_contract,
    build_new_clause_contract,
    build_simple_contract_with_revision,
)


def _full_run(data: bytes, drafting_role: str, counterparty_role: str):
    pipeline = run_pipeline(data)
    changed = ChangedClauseDetector().detect(pipeline["clauses"])
    rows = ProtocolRowBuilder().build(
        changed,
        BuildContext(
            drafting_party_role=drafting_role,
            counterparty_role=counterparty_role,
        ),
    )
    docx_bytes = ProtocolExporter().export(
        [
            {
                "point_label": r.point_label,
                "party_1_text": r.party_1_text,
                "party_2_text": r.party_2_text,
                "agreed_text": r.agreed_text,
            }
            for r in rows
        ],
        drafting_role,
        counterparty_role,
        "Договор",
    )
    return rows, docx_bytes


def test_simple_contract_yields_one_row_and_valid_docx():
    rows, data = _full_run(build_simple_contract_with_revision(), "Сторона2", "Сторона1")
    assert len(rows) == 1
    doc = Document(BytesIO(data))
    assert len(doc.tables) == 1
    assert len(doc.tables[0].rows) == 2


def test_autonumbering_contract_pipeline():
    rows, _ = _full_run(build_autonumbering_contract(), "Арендатор", "Арендодатель")
    assert any(r.point_label.startswith("1.1") for r in rows)


def test_multipar_contract_keeps_continuation():
    rows, _ = _full_run(build_multipar_contract(), "Сторона2", "Сторона1")
    assert any("ВСТАВКА" in r.party_2_text for r in rows)


def test_new_clause_contract_produces_new_pungkt_label():
    rows, _ = _full_run(build_new_clause_contract(), "Сторона2", "Сторона1")
    new_rows = [r for r in rows if r.point_label.startswith("Новый пункт")]
    assert len(new_rows) >= 1
    assert new_rows[0].party_1_text == "—"


def test_deleted_clause_contract_produces_exclude_text():
    rows, _ = _full_run(build_deleted_clause_contract(), "Сторона2", "Сторона1")
    excl = [r for r in rows if r.party_2_text.startswith("Исключить пункт")]
    assert len(excl) >= 1
