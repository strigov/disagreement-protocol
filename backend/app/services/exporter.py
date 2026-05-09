from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument
from docx.shared import Pt


class ProtocolExporter:
    def export(
        self,
        rows: list[dict],
        drafting_role: str,
        counterparty_role: str,
        contract_name: str | None,
    ) -> bytes:
        doc = DocxDocument()
        title = (
            f"Протокол разногласий к договору {contract_name}"
            if contract_name
            else "Протокол разногласий"
        )
        heading = doc.add_heading(title, level=1)
        for run in heading.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(14)

        table = doc.add_table(rows=1 + len(rows), cols=4)
        table.style = "Table Grid"
        headers = [
            "Пункт договора",
            f"Редакция {counterparty_role}" if counterparty_role else "Редакция Стороны 1",
            f"Редакция {drafting_role}" if drafting_role else "Редакция Стороны 2",
            "Согласованная редакция",
        ]
        for index, header_text in enumerate(headers):
            cell = table.rows[0].cells[index]
            cell.text = header_text
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)

        for row_index, row in enumerate(rows, start=1):
            cells = table.rows[row_index].cells
            cells[0].text = row["point_label"]
            cells[1].text = row["party_1_text"]
            cells[2].text = row["party_2_text"]
            cells[3].text = row["agreed_text"]
            for cell in cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(11)

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
