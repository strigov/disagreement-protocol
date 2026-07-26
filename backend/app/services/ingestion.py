from __future__ import annotations

import io
import re
import zipfile
from typing import Any

from app.processing.changed_clause_detector import ChangedClauseDetector
from app.processing.clause_segmenter import ClauseSegmenter
from app.processing.numbering_resolver import NumberingResolver
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import (
    EnrichedParagraph,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
)
from app.services.party_extractor import PartyExtractor

MAX_BYTES = 25 * 1024 * 1024


class IngestError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


def validate_upload(filename: str, data: bytes) -> None:
    if not filename.lower().endswith(".docx"):
        raise IngestError(400, "Поддерживаются только файлы .docx без макросов")
    if len(data) > MAX_BYTES:
        raise IngestError(413, "Размер файла превышает 25 MB")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as exc:
        raise IngestError(400, "Файл повреждён или не является документом Word") from exc
    if "word/document.xml" not in names:
        raise IngestError(400, "В архиве отсутствует word/document.xml — это не Word-документ")
    if "word/vbaProject.bin" in names:
        raise IngestError(415, "Документ содержит макросы (vbaProject.bin) — не поддерживается")


def derive_contract_name(filename: str) -> str | None:
    name = filename
    if name.lower().endswith(".docx"):
        name = name[:-5]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name or None


def _resolve_table(table: RawTable, revision_map: dict) -> RawTable:
    rows: list[RawTableRow] = []
    for row in table.rows:
        cells: list[RawTableCell] = []
        for cell in row.cells:
            original_parts: list[str] = []
            accepted_parts: list[str] = []
            revisions = []
            for paragraph in cell.paragraphs:
                revision_data = revision_map.get(paragraph.block_id)
                if revision_data is None:
                    original_parts.append(paragraph.text())
                    accepted_parts.append(paragraph.text())
                    continue
                original_parts.append(revision_data.original_text)
                accepted_parts.append(revision_data.accepted_text)
                revisions.extend(revision_data.revisions)
            cells.append(
                RawTableCell(
                    paragraphs=cell.paragraphs,
                    original_text=" ".join(original_parts).strip(),
                    accepted_text=" ".join(accepted_parts).strip(),
                    revisions=tuple(revisions),
                ),
            )
        rows.append(RawTableRow(cells=tuple(cells)))
    return RawTable(
        block_id=table.block_id,
        block_index=table.block_index,
        rows=tuple(rows),
        has_revisions=table.has_revisions,
    )


def _iter_clause_revisions(clauses):
    for clause in clauses:
        for paragraph in clause.paragraphs:
            yield from paragraph.revisions
        for table in clause.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.revisions


def run_pipeline(data: bytes) -> dict[str, Any]:
    parser = OOXMLParser()
    raw = parser.parse(data)
    revisions, revision_diags = RevisionResolver().resolve(data, raw)
    numbering, numbering_diags = NumberingResolver().resolve(data, raw)

    segmenter_blocks: list[EnrichedParagraph | RawTable] = []
    for block in raw.blocks:
        if isinstance(block, RawParagraph):
            rd = revisions.get(block.block_id)
            nd = numbering.get(block.block_id)
            enriched = EnrichedParagraph(
                block_id=block.block_id,
                text_runs=block.text(),
                num_id=block.num_id,
                ilvl=block.ilvl,
                original_text=rd.original_text if rd else block.text(),
                accepted_text=rd.accepted_text if rd else block.text(),
                revisions=rd.revisions if rd else (),
                rendered_number=nd.rendered_number if nd else None,
                numbering_confidence=nd.confidence if nd else 0.0,
            )
            segmenter_blocks.append(enriched)
        elif isinstance(block, RawTable):
            segmenter_blocks.append(_resolve_table(block, revisions))

    clauses = ClauseSegmenter().segment(segmenter_blocks)
    changed = ChangedClauseDetector().detect(clauses)
    preamble_text = ""
    for clause in clauses:
        if clause.label == "Преамбула":
            preamble_text = "\n".join(paragraph.accepted_text for paragraph in clause.paragraphs)
            break
    if not preamble_text and clauses:
        preamble_text = "\n".join(paragraph.accepted_text for paragraph in clauses[0].paragraphs)

    parties = PartyExtractor().extract(preamble_text)
    all_revisions = list(_iter_clause_revisions(clauses))
    diagnostics = [
        {
            "level": diagnostic.level,
            "component": diagnostic.component,
            "code": diagnostic.code,
            "message": diagnostic.message,
            "block_id": diagnostic.block_id,
        }
        for diagnostic in (*revision_diags, *numbering_diags)
    ]
    paragraph_count = sum(len(clause.paragraphs) for clause in clauses)
    return {
        "clauses": clauses,
        "changed_clauses": changed,
        "parties": parties,
        "preflight_metrics": {
            "revisions_total": sum(
                1 for revision in all_revisions if revision.type in ("INS", "DEL")
            ),
            "format_only_count": sum(1 for revision in all_revisions if revision.type == "FORMAT_ONLY"),
            "paragraphs_with_numbering": sum(
                1
                for clause in clauses
                for paragraph in clause.paragraphs
                if paragraph.rendered_number
            ),
            "numbering_confidence_mean": (
                sum(
                    paragraph.numbering_confidence
                    for clause in clauses
                    for paragraph in clause.paragraphs
                )
                / max(1, paragraph_count)
            ),
        },
        "preflight_diagnostics": diagnostics,
    }
