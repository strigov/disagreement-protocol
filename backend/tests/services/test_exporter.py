from io import BytesIO

from docx import Document

from app.services.exporter import ProtocolExporter


def test_export_produces_docx_with_4col_table_and_headers():
    rows = [
        {
            "point_label": "1.",
            "party_1_text": "old",
            "party_2_text": "new",
            "agreed_text": "Редакция Арендатора",
        }
    ]

    data = ProtocolExporter().export(
        rows,
        drafting_role="Арендатор",
        counterparty_role="Арендодатель",
        contract_name="Договор",
    )

    doc = Document(BytesIO(data))
    assert any("Протокол разногласий" in p.text for p in doc.paragraphs)
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert len(table.columns) == 4
    headers = [c.text for c in table.rows[0].cells]
    assert headers == [
        "Пункт договора",
        "Редакция Арендодатель",
        "Редакция Арендатор",
        "Согласованная редакция",
    ]
    body = [c.text for c in table.rows[1].cells]
    assert body == ["1.", "old", "new", "Редакция Арендатора"]


def test_export_falls_back_to_storona_labels_for_empty_roles():
    rows = [{"point_label": "1.", "party_1_text": "a", "party_2_text": "b", "agreed_text": "c"}]

    data = ProtocolExporter().export(rows, drafting_role="", counterparty_role="", contract_name=None)

    doc = Document(BytesIO(data))
    headers = [c.text for c in doc.tables[0].rows[0].cells]
    assert headers[1] == "Редакция Стороны 1"
    assert headers[2] == "Редакция Стороны 2"
